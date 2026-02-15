"""
AWS Cost Notification Agent - Production Ready
Version: 3.2.0 - Internal Network Only with Vertex AI

Key Changes:
- Vertex AI instead of AI Studio (Service Account auth)
- Internal network binding only (127.0.0.1)
- No public network exposure
- Improved error handling and logging
"""

from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, Query, Depends, Security
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import os
import logging
import json
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import httpx
import secrets
import signal
import asyncio

# Load environment FIRST
from dotenv import load_dotenv
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Import configuration
from config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_FILE) if settings.LOG_FILE else logging.StreamHandler(),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create FastAPI app - INTERNAL ONLY
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    docs_url=None if settings.ENVIRONMENT == "production" else "/docs",  # Disable in prod
    redoc_url=None if settings.ENVIRONMENT == "production" else "/redoc",
    openapi_url=None if settings.ENVIRONMENT == "production" else "/openapi.json"
)

# Create API router
api_router = APIRouter(prefix="/api")

# CORS - Internal IPs only
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,  # Only internal origins
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Scheduler with UTC timezone
scheduler = AsyncIOScheduler(timezone='UTC')
shutdown_event = asyncio.Event()

# ==================== IMPORT YOUR EXISTING SERVICES ====================
# Keep your existing S3Storage class (no changes needed)
# Keep your existing DatadogService class (no changes needed)
# Keep your existing EmailService if you have one

# Import NEW Vertex AI service
from services.vertex_ai_service import VertexAIService
ai_service = VertexAIService()

# Your existing storage service (S3Storage class from your code)
# I'll keep this as-is, just import it
from services.storage_service import S3Storage
storage = S3Storage()

# ==================== API AUTHENTICATION ====================

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_api_key() -> str:
    """Get API key from environment"""
    api_key = settings.AGENT_API_KEY
    if not api_key:
        api_key = secrets.token_urlsafe(32)
        logger.warning(f"Generated temporary API key: {api_key[:8]}...")
    return api_key

AGENT_API_KEY = get_api_key()

async def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> bool:
    """Verify API key"""
    if settings.DISABLE_AUTH:
        return True
    
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    
    if not secrets.compare_digest(api_key, AGENT_API_KEY):
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    return True

# ==================== IP WHITELIST MIDDLEWARE ====================

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import ipaddress

class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """Allow only internal IPs"""
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else None
        
        # Skip for health check
        if request.url.path in ["/health", "/api/health"]:
            return await call_next(request)
        
        if client_ip:
            # Check if IP is in allowed ranges
            allowed = False
            try:
                client_addr = ipaddress.ip_address(client_ip)
                for allowed_range in settings.ALLOWED_INTERNAL_IPS:
                    if "/" in allowed_range:
                        if client_addr in ipaddress.ip_network(allowed_range):
                            allowed = True
                            break
                    else:
                        if str(client_addr) == allowed_range:
                            allowed = True
                            break
            except ValueError:
                pass
            
            if not allowed:
                logger.warning(f"Blocked request from non-whitelisted IP: {client_ip}")
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Access denied - IP not whitelisted"}
                )
        
        return await call_next(request)

# Add IP whitelist middleware
app.add_middleware(IPWhitelistMiddleware)

# ==================== HEALTH CHECK ====================

@app.get("/health")
async def health_check():
    """Health check endpoint - no auth required"""
    health_status = {
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "storage": "healthy" if storage.use_s3 or storage.local_storage_dir.exists() else "unhealthy",
            "vertex_ai": "healthy" if ai_service.initialized else "not_configured",
            "scheduler": "running" if scheduler.running else "stopped"
        }
    }
    
    # Check if any service is unhealthy
    if any(v == "unhealthy" for v in health_status["services"].values()):
        health_status["status"] = "degraded"
    
    status_code = 200 if health_status["status"] in ["healthy", "degraded"] else 503
    return JSONResponse(content=health_status, status_code=status_code)

# ==================== YOUR EXISTING ROUTES ====================
# Keep all your existing routes from the original code
# Just replace ai_service calls to use VertexAIService

# Example: Keep your team management routes as-is
@api_router.post("/teams", dependencies=[Depends(verify_api_key)])
async def create_team(team: 'TeamCreate'):  # Use your existing Team model
    """Create a new team"""
    # Your existing code here
    pass

@api_router.get("/teams", dependencies=[Depends(verify_api_key)])
async def get_teams():
    """Get all teams"""
    teams = storage.get_all_teams()
    return {"teams": teams, "count": len(teams)}

# ... keep all your other routes ...

# ==================== STARTUP/SHUTDOWN ====================

@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Listening on: {settings.HOST}:{settings.PORT} (INTERNAL ONLY)")
    logger.info(f"Storage: {'S3' if storage.use_s3 else 'Local'}")
    logger.info(f"AI: {'Vertex AI (Enabled)' if ai_service.initialized else 'Not configured'}")
    
    # Start scheduler
    config = storage.get_config()
    schedule_weekly_job(config)
    scheduler.start()
    logger.info("Scheduler started")
    
    # Setup signal handlers
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))

@app.on_event("shutdown")
async def shutdown_event():
    """Graceful shutdown"""
    logger.info("Initiating graceful shutdown...")
    shutdown_event.set()
    
    scheduler.shutdown(wait=True)
    logger.info("Scheduler stopped")
    
    logger.info("Shutdown complete")

async def shutdown():
    """Handle shutdown signal"""
    shutdown_event.set()

def schedule_weekly_job(config: dict):
    """Schedule weekly cost report"""
    # Your existing scheduling code
    pass

# Include API router
app.include_router(api_router)

# Root endpoint
@app.get("/")
async def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "operational",
        "network": "internal_only"
    }

if __name__ == "__main__":
    import uvicorn
    
    # Internal network binding only
    uvicorn.run(
        "main:app",
        host=settings.HOST,  # 127.0.0.1 - localhost only
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )
