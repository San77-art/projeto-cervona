"""
Database configuration and connection
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.config.settings import settings
from src.models.base import Base
import logging

logger = logging.getLogger(__name__)

# Create engine
engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.DB_ECHO,
    future=True,
)

# Session factory
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    """Dependency injection para database session"""
    async with SessionLocal() as session:
        yield session

async def init_db():
    """Initialize database (create tables)"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
