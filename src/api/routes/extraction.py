"""
Data extraction routes
"""

from fastapi import APIRouter, HTTPException, status
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/extracted/{xml_id}")
async def get_extracted_data(xml_id: str):
    """
    Get extracted data from XML
    """
    # TODO: Query database for extracted items
    return {
        "xml_id": xml_id,
        "items": [
            # {
            #     "ncm": "12345678",
            #     "cfop": "5102",
            #     "cst": "00",
            #     "quantity": 10.0,
            #     "value": 1000.00,
            # }
        ],
        "confidence_score": 0.95,
    }

@router.get("/dashboard")
async def get_dashboard():
    """
    Get dashboard summary
    """
    # TODO: Aggregate stats from database
    return {
        "total_xmls": 0,
        "processed": 0,
        "pending": 0,
        "failed": 0,
        "avg_confidence": 0.0,
    }
