"""
XML capture and upload routes
"""

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from src.agent.extractor import XMLExtractor, get_extractor
from src.config.database import get_db
from src.models import ExtractedItem, XMLDocument, XMLStatus

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/xml/upload")
async def upload_xml(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    extractor: XMLExtractor = Depends(get_extractor),
):
    """
    Upload XML file for processing
    """
    if not file.filename.endswith('.xml'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be .xml"
        )

    try:
        content = await file.read()

        # TODO: Validate XML structure
        # TODO: Upload to Blob Storage
        # TODO: Queue for IA processing (run extraction asynchronously instead of inline)

        xml_document = XMLDocument(filename=file.filename, status=XMLStatus.PENDING)
        db.add(xml_document)
        await db.commit()
        await db.refresh(xml_document)

        extraction_result = await extractor.extract(content.decode("utf-8"))

        if "error" in extraction_result:
            xml_document.status = XMLStatus.FAILED
            logger.warning(
                f"Extraction failed for {file.filename}: {extraction_result['error']}"
            )
        else:
            for item in extraction_result.get("items", []):
                db.add(ExtractedItem(
                    xml_document_id=xml_document.id,
                    ncm=item.get("ncm"),
                    cfop=item.get("cfop"),
                    cst=item.get("cst_icms"),
                    quantity=item.get("quantity"),
                    value=item.get("total_value"),
                ))
            xml_document.confidence_score = extraction_result.get("overall_confidence")
            xml_document.status = XMLStatus.PROCESSED

        await db.commit()
        await db.refresh(xml_document)

        logger.info(f"XML uploaded: {file.filename} ({len(content)} bytes)")

        return {
            "filename": xml_document.filename,
            "size": len(content),
            "status": xml_document.status.value,
            "id": xml_document.id,
        }

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/xml/{xml_id}")
async def get_xml_info(xml_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get XML upload information
    """
    xml_document = await db.get(XMLDocument, xml_id)
    if xml_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"XML {xml_id} not found",
        )

    return {
        "id": xml_document.id,
        "filename": xml_document.filename,
        "uploaded_at": xml_document.uploaded_at,
        "status": xml_document.status.value,
    }

@router.get("/xml")
async def list_xmls(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db)):
    """
    List uploaded XMLs
    """
    total = (await db.execute(select(func.count(XMLDocument.id)))).scalar_one()

    result = await db.execute(
        select(XMLDocument).order_by(XMLDocument.uploaded_at.desc()).offset(skip).limit(limit)
    )
    documents = result.scalars().all()

    return {
        "total": total,
        "items": [
            {
                "id": doc.id,
                "filename": doc.filename,
                "uploaded_at": doc.uploaded_at,
                "status": doc.status.value,
            }
            for doc in documents
        ],
    }
