"""
Tests para a rota POST /sefaz/sync
"""

import pytest

from src.api.routes import sefaz as sefaz_route
from src.config.settings import settings
from src.sefaz.client import SEFAZClientError


def test_sync_sefaz_requires_auth(unauthenticated_client):
    response = unauthenticated_client.post("/api/v1/sefaz/sync")
    assert response.status_code == 401


def test_sync_sefaz_mock_mode(client, monkeypatch):
    monkeypatch.setattr(settings, "SEFAZ_MODE", "mock")

    response = client.post("/api/v1/sefaz/sync")

    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "mock"
    assert data["documents_saved"] == 2
    assert data["caught_up"] is True


def test_sync_sefaz_invalid_mode_returns_400(client, monkeypatch):
    monkeypatch.setattr(settings, "SEFAZ_MODE", "bogus")

    response = client.post("/api/v1/sefaz/sync")

    assert response.status_code == 400
    assert "SEFAZ_MODE" in response.json()["error"]


def test_sync_sefaz_client_error_returns_502(client, monkeypatch):
    monkeypatch.setattr(settings, "SEFAZ_MODE", "real")

    async def _boom(db, extractor):
        raise SEFAZClientError("SEFAZ indisponível")

    monkeypatch.setattr(sefaz_route, "sync_documents", _boom)

    response = client.post("/api/v1/sefaz/sync")

    assert response.status_code == 502
    assert "indisponível" in response.json()["error"]
