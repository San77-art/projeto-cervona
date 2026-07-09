"""
Pytest fixtures and configuration
"""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app

@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)

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
