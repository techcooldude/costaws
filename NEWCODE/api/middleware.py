"""
Security Middleware - IP Whitelist, Logging, Security Headers
"""
import logging
import ipaddress
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings

logger = logging.getLogger(__name__)


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    Block all requests except from internal networks.
    Ensures service is only accessible internally.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host
        
        # Health check always allowed (for internal monitoring)
        if request.url.path in ["/health", "/", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        # Check if IP is in allowed ranges
        if not self._is_ip_allowed(client_ip):
            logger.warning(f"Blocked request from unauthorized IP: {client_ip}")
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Access denied - Internal network only",
                    "client_ip": client_ip
                }
            )
        
        return await call_next(request)
    
    def _is_ip_allowed(self, ip: str) -> bool:
        """Check if IP is in allowed internal ranges"""
        try:
            client_ip_obj = ipaddress.ip_address(ip)
            
            # Always allow localhost
            if client_ip_obj.is_loopback:
                return True
            
            # Check against allowed networks
            for allowed_cidr in settings.ALLOWED_INTERNAL_IPS:
                try:
                    if '/' in allowed_cidr:
                        network = ipaddress.ip_network(allowed_cidr, strict=False)
                        if client_ip_obj in network:
                            return True
                    else:
                        if str(client_ip_obj) == allowed_cidr:
                            return True
                except ValueError:
                    continue
            
            return False
            
        except ValueError:
            logger.error(f"Invalid IP address: {ip}")
            return False


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all incoming requests"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        logger.info(f"{request.method} {request.url.path} from {request.client.host}")
        
        response = await call_next(request)
        
        logger.info(f"Response status: {response.status_code}")
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response
