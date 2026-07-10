"""
Tests para extraction routes
"""

import asyncio

from src.models import ExtractedItem, XMLDocument, XMLStatus


def _seed(session_factory, documents=(), items=()):
    async def _run():
        async with session_factory() as session:
            session.add_all(documents)
            session.add_all(items)
            await session.commit()

    asyncio.run(_run())


def test_get_extracted_data_returns_items(client, session_factory):
    _seed(
        session_factory,
        documents=[
            XMLDocument(
                id="abc-123",
                filename="nota.xml",
                status=XMLStatus.PROCESSED,
                confidence_score=0.95,
            )
        ],
        items=[
            ExtractedItem(
                xml_document_id="abc-123",
                ncm="12345678",
                cfop="5102",
                cst="00",
                quantity=10.0,
                value=1000.00,
            )
        ],
    )

    response = client.get("/api/v1/extracted/abc-123")
    assert response.status_code == 200
    data = response.json()
    assert data["xml_id"] == "abc-123"
    assert data["confidence_score"] == 0.95
    assert data["items"] == [
        {
            "ncm": "12345678",
            "cfop": "5102",
            "cst": "00",
            "quantity": 10.0,
            "value": 1000.00,
        }
    ]


def test_get_extracted_data_returns_404_when_xml_not_found(client):
    response = client.get("/api/v1/extracted/does-not-exist")
    assert response.status_code == 404


def test_get_dashboard_returns_summary_with_no_data(client):
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 200
    assert response.json() == {
        "total_xmls": 0,
        "processed": 0,
        "pending": 0,
        "failed": 0,
        "avg_confidence": 0.0,
    }


def test_get_dashboard_aggregates_stats(client, session_factory):
    _seed(
        session_factory,
        documents=[
            XMLDocument(id="a", filename="a.xml", status=XMLStatus.PROCESSED, confidence_score=0.9),
            XMLDocument(id="b", filename="b.xml", status=XMLStatus.PENDING),
            XMLDocument(id="c", filename="c.xml", status=XMLStatus.FAILED),
            XMLDocument(id="d", filename="d.xml", status=XMLStatus.PROCESSED, confidence_score=0.8),
        ],
    )

    response = client.get("/api/v1/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["total_xmls"] == 4
    assert data["processed"] == 2
    assert data["pending"] == 1
    assert data["failed"] == 1
    assert data["avg_confidence"] == 0.85
