"""
Tests para xml_capture routes
"""


def test_upload_xml_rejects_non_xml_extension(client):
    response = client.post(
        "/api/v1/xml/upload",
        files={"file": ("test.txt", b"not xml", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json() == {"error": "File must be .xml", "status_code": 400}


def test_upload_xml_accepts_xml_file(client, mock_xml):
    response = client.post(
        "/api/v1/xml/upload",
        files={"file": ("nfe.xml", mock_xml.encode("utf-8"), "application/xml")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "nfe.xml"
    assert data["status"] == "received"
    assert data["size"] == len(mock_xml.encode("utf-8"))


def test_get_xml_info_returns_placeholder(client):
    response = client.get("/api/v1/xml/some-id")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "some-id"
    assert data["status"] == "processing"


def test_list_xmls_returns_empty_list(client):
    response = client.get("/api/v1/xml")
    assert response.status_code == 200
    assert response.json() == {"total": 0, "items": []}
