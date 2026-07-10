"""
Data extraction routes
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from src.config.database import get_db
from src.models import ExtractedItem, XMLDocument, XMLStatus

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/extracted/{xml_id}")
async def get_extracted_data(xml_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get extracted data from XML
    """
    xml_document = await db.get(XMLDocument, xml_id)
    if xml_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"XML {xml_id} not found",
        )

    result = await db.execute(
        select(ExtractedItem).where(ExtractedItem.xml_document_id == xml_id)
    )
    items = result.scalars().all()

    return {
        "xml_id": xml_id,
        "items": [
            {
                "ncm": item.ncm,
                "cfop": item.cfop,
                "cst": item.cst,
                "quantity": item.quantity,
                "value": item.value,
            }
            for item in items
        ],
        "confidence_score": xml_document.confidence_score,
    }

@router.get("/dashboard")
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    """
    Get dashboard summary
    """
    result = await db.execute(
        select(
            func.count(XMLDocument.id),
            func.count(XMLDocument.id).filter(XMLDocument.status == XMLStatus.PROCESSED),
            func.count(XMLDocument.id).filter(XMLDocument.status == XMLStatus.PENDING),
            func.count(XMLDocument.id).filter(XMLDocument.status == XMLStatus.FAILED),
            func.avg(XMLDocument.confidence_score),
        )
    )
    total_xmls, processed, pending, failed, avg_confidence = result.one()

    return {
        "total_xmls": total_xmls,
        "processed": processed,
        "pending": pending,
        "failed": failed,
        "avg_confidence": round(avg_confidence, 4) if avg_confidence is not None else 0.0,
    }
