"""
E-Cernova Livro Caixa Rural API
FastAPI Application
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from typing import Optional

from src.config.settings import settings
from src.config.logging import setup_logging
from src.config.database import init_db
from src.api.routes import auth, health, sefaz, xml_capture, extraction

# ========================================
# Setup
# ========================================

setup_logging()
logger = logging.getLogger(__name__)

# ========================================
# Lifespan events
# ========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown events
    """
    logger.info(f"Starting {settings.API_TITLE} v{settings.API_VERSION}")
    try:
        await init_db()
        # TODO: Validar conexão Key Vault
        # TODO: Validar conexão Anthropic API
        logger.info("✓ All startup checks passed")
    except Exception as e:
        logger.error(f"✗ Startup check failed: {e}")
        raise
    yield
    logger.info("Shutting down...")

# ========================================
# Create FastAPI app
# ========================================

app = FastAPI(
    title=settings.API_TITLE,
    description="XML fiscal processing with AI extraction",
    version=settings.API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ========================================
# CORS Middleware
# ========================================

if settings.ENVIRONMENT == "development":
    origins = ["*"]
else:
    origins = settings.CORS_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================================
# Include routers
# ========================================

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(xml_capture.router, prefix="/api/v1", tags=["xml"])
app.include_router(extraction.router, prefix="/api/v1", tags=["extraction"])
app.include_router(sefaz.router, prefix="/api/v1", tags=["sefaz"])

# ========================================
# Root endpoint
# ========================================

@app.get("/", tags=["root"])
async def root():
    """API information"""
    return {
        "title": settings.API_TITLE,
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
    }

# ========================================
# Error handlers
# ========================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.error(f"HTTP Exception: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
        },
    )

# ========================================
# Startup checks
# ========================================

@app.on_event("startup")
async def startup_event():
    """Validar conexões e dependências"""
    try:
        await init_db()
        # TODO: Validar conexão Key Vault
        # TODO: Validar conexão Anthropic API
        logger.info("✓ All startup checks passed")
    except Exception as e:
        logger.error(f"✗ Startup check failed: {e}")
        raise

# ========================================
# Run
# ========================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        workers=settings.WORKERS if not settings.DEBUG else 1,
    )
