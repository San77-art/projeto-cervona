"""
Tests para XMLExtractor (extracao de dados via Claude)
"""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.agent.extractor import XMLExtractor


def _fake_response(text: str):
    """Build a stand-in for an Anthropic Message response."""
    return SimpleNamespace(content=[SimpleNamespace(text=text)])


@pytest.fixture
def extractor():
    return XMLExtractor()


@pytest.mark.asyncio
async def test_extract_parses_valid_json(extractor, mock_xml):
    payload = {
        "items": [
            {
                "ncm": "12345678",
                "cfop": "5102",
                "cst_icms": "00",
                "quantity": 1.0,
                "unit_value": 10.0,
                "total_value": 10.0,
                "confidence": 0.9,
                "validation_notes": "",
            }
        ],
        "overall_confidence": 0.9,
        "warnings": [],
    }
    extractor.client.messages.create = AsyncMock(return_value=_fake_response(json.dumps(payload)))

    result = await extractor.extract(mock_xml)

    assert result == payload


@pytest.mark.asyncio
async def test_extract_strips_markdown_code_fences(extractor, mock_xml):
    payload = {"items": [], "overall_confidence": 0.5, "warnings": []}
    fenced = f"```json\n{json.dumps(payload)}\n```"
    extractor.client.messages.create = AsyncMock(return_value=_fake_response(fenced))

    result = await extractor.extract(mock_xml)

    assert result == payload


@pytest.mark.asyncio
async def test_extract_returns_error_on_invalid_json(extractor, mock_xml):
    extractor.client.messages.create = AsyncMock(return_value=_fake_response("not json"))

    result = await extractor.extract(mock_xml)

    assert result == {"error": "Invalid response format", "items": []}


@pytest.mark.asyncio
async def test_extract_returns_error_on_client_exception(extractor, mock_xml):
    extractor.client.messages.create = AsyncMock(side_effect=RuntimeError("boom"))

    result = await extractor.extract(mock_xml)

    assert result["items"] == []
    assert "boom" in result["error"]


@pytest.mark.asyncio
async def test_extract_sends_full_xml_without_truncation(extractor):
    large_xml = "<NFe>" + ("<det><prod><NCM>12345678</NCM></prod></det>" * 500) + "</NFe>"
    assert len(large_xml) > 4000  # would have been silently truncated under the old 4000-char cap

    payload = {"items": [], "overall_confidence": 1.0, "warnings": []}
    create_mock = AsyncMock(return_value=_fake_response(json.dumps(payload)))
    extractor.client.messages.create = create_mock

    await extractor.extract(large_xml)

    sent_prompt = create_mock.call_args.kwargs["messages"][0]["content"]
    assert large_xml in sent_prompt
