"""
Health check routes
"""

from fastapi import APIRouter
from datetime import datetime
from src.config.settings import settings

router = APIRouter()

@router.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.ENVIRONMENT,
        "version": settings.API_VERSION,
    }

@router.get("/health/deep", tags=["health"])
async def deep_health_check():
    """
    Deep health check - validates dependencies
    """
    checks = {
        "api": "ok",
        "database": "unknown",
        "key_vault": "unknown",
        "anthropic": "unknown",
        "storage": "unknown",
    }
    
    # TODO: Implement actual checks
    # - Database connection
    # - Key Vault access
    # - Anthropic API
    # - Storage access
    
    return {
        "status": "checking",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
    }

@router.get("/ready", tags=["health"])
async def readiness():
    """
    Kubernetes readiness probe
    """
    return {"ready": True}
