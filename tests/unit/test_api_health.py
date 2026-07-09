"""
Tests para health endpoints
"""

def test_health_check(client):
    """Test health endpoint"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data

def test_readiness(client):
    """Test readiness endpoint"""
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    assert response.json()["ready"] is True
