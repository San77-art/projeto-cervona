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
    assert data["status"] == "processed"
    assert data["size"] == len(mock_xml.encode("utf-8"))
    assert data["id"]


def test_upload_xml_persists_document(client, mock_xml):
    upload_response = client.post(
        "/api/v1/xml/upload",
        files={"file": ("nfe.xml", mock_xml.encode("utf-8"), "application/xml")},
    )
    xml_id = upload_response.json()["id"]

    response = client.get(f"/api/v1/xml/{xml_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == xml_id
    assert data["filename"] == "nfe.xml"
    assert data["status"] == "processed"


def test_upload_xml_persists_extracted_items(client, mock_xml, stub_extractor):
    stub_extractor.result = {
        "items": [
            {
                "ncm": "12345678",
                "cfop": "5102",
                "cst_icms": "00",
                "quantity": 10.0,
                "unit_value": 100.0,
                "total_value": 1000.0,
                "confidence": 0.95,
                "validation_notes": "",
            }
        ],
        "overall_confidence": 0.95,
        "warnings": [],
    }

    upload_response = client.post(
        "/api/v1/xml/upload",
        files={"file": ("nfe.xml", mock_xml.encode("utf-8"), "application/xml")},
    )
    assert upload_response.json()["status"] == "processed"
    xml_id = upload_response.json()["id"]

    response = client.get(f"/api/v1/extracted/{xml_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["confidence_score"] == 0.95
    assert data["items"] == [
        {
            "ncm": "12345678",
            "cfop": "5102",
            "cst": "00",
            "quantity": 10.0,
            "value": 1000.0,
        }
    ]


def test_upload_xml_marks_failed_on_extraction_error(client, mock_xml, stub_extractor):
    stub_extractor.result = {"error": "Invalid response format", "items": []}

    upload_response = client.post(
        "/api/v1/xml/upload",
        files={"file": ("nfe.xml", mock_xml.encode("utf-8"), "application/xml")},
    )
    assert upload_response.status_code == 200
    data = upload_response.json()
    assert data["status"] == "failed"

    response = client.get(f"/api/v1/xml/{data['id']}")
    assert response.json()["status"] == "failed"


def test_get_xml_info_returns_404_when_not_found(client):
    response = client.get("/api/v1/xml/does-not-exist")
    assert response.status_code == 404


def test_list_xmls_returns_empty_list(client):
    response = client.get("/api/v1/xml")
    assert response.status_code == 200
    assert response.json() == {"total": 0, "items": []}


def test_list_xmls_returns_uploaded_documents(client, mock_xml):
    client.post(
        "/api/v1/xml/upload",
        files={"file": ("nfe.xml", mock_xml.encode("utf-8"), "application/xml")},
    )

    response = client.get("/api/v1/xml")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["filename"] == "nfe.xml"
