"""AWS Cost Notification Agent - Production Version
Version: 4.0.0

NOTE: This is a "professionalized" scaffold generated from Perplexity recommendations.
It is intentionally conservative and may require wiring to your existing business logic.
"""

import asyncio
import signal
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.config import settings
from app.api.routes import api_router
from app.api.middleware import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    RequestLoggingMiddleware,
)
from app.services.storage_service import storage
from app.services.ai_service import ai_service
from app.services.datadog_service import datadog_service
from app.utils.logging import get_logger, setup_logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Global scheduler
scheduler = AsyncIOScheduler(timezone="UTC")
shutdown_event = asyncio.Event()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager for startup and shutdown."""

    logger.info(f"Starting AWS Cost AI Agent v{settings.VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Storage: {'S3' if storage.use_s3 else 'Local'}")
    logger.info(f"AI: {'Enabled' if ai_service.api_key else 'Disabled'}")

    # Initialize services
    await storage.initialize()
    await datadog_service.initialize()

    # Setup scheduler
    config = storage.get_config()
    schedule_weekly_job(config)
    scheduler.start()
    logger.info("Scheduler started")

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown()))

    yield

    # Shutdown
    logger.info("Initiating graceful shutdown...")
    shutdown_event.set()

    scheduler.shutdown(wait=True)
    logger.info("Scheduler stopped")

    await datadog_service.cleanup()
    await storage.cleanup()

    logger.info("Shutdown complete")


async def shutdown():
    """Handle graceful shutdown."""
    shutdown_event.set()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="AI-powered AWS cost monitoring and anomaly detection",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)

# Add middleware (order matters!)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware, calls=settings.RATE_LIMIT_CALLS, period=settings.RATE_LIMIT_PERIOD)

# CORS
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

# Trusted hosts
if settings.ALLOWED_HOSTS:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )

# Include API routes
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "operational",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled exception: {exc}",
        extra={"path": request.url.path, "method": request.method},
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error" if settings.ENVIRONMENT == "production" else str(exc),
            "type": "internal_error",
        },
    )


def schedule_weekly_job(config: dict):
    """Schedule weekly cost report job."""

    # Imported here to avoid circular imports in scaffolding.
    from app.services.cost_analyzer import run_weekly_report

    day_map = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    day = str(config.get("schedule_day", "monday")).lower()
    hour = int(config.get("schedule_hour", 9))

    if scheduler.get_job("weekly_cost_report"):
        scheduler.remove_job("weekly_cost_report")

    scheduler.add_job(
        run_weekly_report,
        CronTrigger(day_of_week=day_map.get(day, 0), hour=hour, minute=0, timezone="UTC"),
        id="weekly_cost_report",
        name="Weekly AI Cost Report",
        replace_existing=True,
    )

    logger.info(f"Scheduled weekly report: {day} at {hour}:00 UTC")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
    )
