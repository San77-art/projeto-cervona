"""
Pytest fixtures and configuration
"""

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.agent.extractor import get_extractor
from src.api.main import app
from src.config.database import get_db
from src.models import Base

class StubExtractor:
    """Stand-in for XMLExtractor that avoids real Anthropic API calls in tests"""

    def __init__(self):
        self.result = {"items": [], "overall_confidence": 1.0, "warnings": []}

    async def extract(self, xml_content):
        return self.result

async def _create_schema(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@pytest.fixture
def db_engine():
    """Isolated in-memory SQLite database, fresh per test"""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    asyncio.run(_create_schema(engine))
    yield engine
    asyncio.run(engine.dispose())

@pytest.fixture
def session_factory(db_engine):
    """Sessionmaker bound to the test database, for seeding data directly in tests"""
    return sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

@pytest.fixture
def stub_extractor():
    """Extractor double that tests can configure via `.result`"""
    return StubExtractor()

@pytest.fixture
def client(session_factory, stub_extractor):
    """FastAPI test client wired to the isolated test database and stub extractor"""
    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_extractor] = lambda: stub_extractor
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_extractor, None)

@pytest.fixture
def mock_xml():
    """Sample XML for testing"""
    return """<?xml version="1.0"?>
<NFe>
    <infNFe>
        <ide>
            <dEmi>2026-07-09</dEmi>
        </ide>
        <det>
            <prod>
                <NCM>12345678</NCM>
                <CFOP>5102</CFOP>
            </prod>
        </det>
    </infNFe>
</NFe>"""
