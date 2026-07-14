"""
Tests para autenticação JWT (login + proteção de endpoints)
"""

from src.api.middleware.auth import hash_password
from src.config.settings import settings


def _set_admin_credentials(monkeypatch, username="admin", password="secret123"):
    monkeypatch.setattr(settings, "ADMIN_USERNAME", username)
    monkeypatch.setattr(settings, "ADMIN_PASSWORD_HASH", hash_password(password))


def test_login_with_correct_credentials_returns_token(unauthenticated_client, monkeypatch):
    _set_admin_credentials(monkeypatch)

    response = unauthenticated_client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "secret123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]


def test_login_with_wrong_password_returns_401(unauthenticated_client, monkeypatch):
    _set_admin_credentials(monkeypatch)

    response = unauthenticated_client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_login_with_unknown_username_returns_401(unauthenticated_client, monkeypatch):
    _set_admin_credentials(monkeypatch)

    response = unauthenticated_client.post(
        "/api/v1/auth/login",
        data={"username": "someone-else", "password": "secret123"},
    )

    assert response.status_code == 401


def test_login_without_configured_admin_hash_returns_401(unauthenticated_client, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_PASSWORD_HASH", None)

    response = unauthenticated_client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "anything"},
    )

    assert response.status_code == 401


def test_xml_endpoints_reject_requests_without_token(unauthenticated_client):
    assert unauthenticated_client.get("/api/v1/xml").status_code == 401
    assert unauthenticated_client.get("/api/v1/dashboard").status_code == 401
    assert unauthenticated_client.post("/api/v1/xml/upload").status_code == 401


def test_xml_endpoints_reject_invalid_token(unauthenticated_client):
    response = unauthenticated_client.get(
        "/api/v1/xml", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


def test_xml_endpoints_accept_valid_token(unauthenticated_client, monkeypatch):
    _set_admin_credentials(monkeypatch)

    login_response = unauthenticated_client.post(
        "/api/v1/auth/login",
        data={"username": "admin", "password": "secret123"},
    )
    token = login_response.json()["access_token"]

    response = unauthenticated_client.get(
        "/api/v1/xml", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200


def test_health_endpoints_do_not_require_token(unauthenticated_client):
    assert unauthenticated_client.get("/api/v1/health").status_code == 200
    assert unauthenticated_client.get("/api/v1/ready").status_code == 200
