"""
Tests para extraction routes
"""


def test_get_extracted_data_returns_xml_id(client):
    response = client.get("/api/v1/extracted/abc-123")
    assert response.status_code == 200
    data = response.json()
    assert data["xml_id"] == "abc-123"
    assert data["items"] == []
    assert data["confidence_score"] == 0.95


def test_get_dashboard_returns_summary(client):
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 200
    assert response.json() == {
        "total_xmls": 0,
        "processed": 0,
        "pending": 0,
        "failed": 0,
        "avg_confidence": 0.0,
    }
