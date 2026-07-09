"""
Tests para o app FastAPI principal (main.py)
"""

from src.config.settings import settings


def test_root_returns_api_info(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == settings.API_TITLE
    assert data["version"] == settings.API_VERSION
    assert data["docs"] == "/docs"


def test_http_exception_handler_preserves_status_code(client):
    """
    App-raised HTTPExceptions (e.g. the xml upload's 400) must go through our
    custom handler with the original status code intact, not silently become a
    200 (dict-was-not-a-Response) or an unhandled crash.
    """
    response = client.post(
        "/api/v1/xml/upload",
        files={"file": ("test.txt", b"not xml", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json() == {"error": "File must be .xml", "status_code": 400}
