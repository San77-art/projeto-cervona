"""
Tests para MockSEFAZClient
"""

import pytest

from src.sefaz.mock import MockSEFAZClient


def test_mock_nfe_structure():
    data = MockSEFAZClient.mock_nfe()

    assert data["status"] == "success"
    assert "<NFe>" in data["xml"]
    assert data["nsu"] == "12345"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_query_xml_returns_two_mock_nfes():
    result = await MockSEFAZClient.query_xml("12345678901234")

    assert len(result) == 2
    assert all(item["status"] == "success" for item in result)


@pytest.mark.asyncio
async def test_manifest_echoes_nsu():
    result = await MockSEFAZClient.manifest("999")

    assert result["status"] == "success"
    assert result["nsu"] == "999"
    assert "timestamp" in result
