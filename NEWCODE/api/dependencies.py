"""
API Dependencies (Authentication)
"""
from fastapi import Header, HTTPException, status
from app.config import settings


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Verify API key from header"""
    if settings.DISABLE_AUTH:
        return True
    
    if not settings.AGENT_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key not configured on server"
        )
    
    if x_api_key != settings.AGENT_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return True
