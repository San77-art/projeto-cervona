"""
Pipeline compartilhado: parser determinístico (NCM/CFOP/CST) + extração via Claude.

Usado tanto pelo upload manual (src/api/routes/xml_capture.py) quanto pela
sincronização com a SEFAZ (src/sefaz/service.py) — mesma lógica de
processamento, independente de como o XML chegou ao sistema.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.extractor import XMLExtractor
from src.models import ExtractedItem, XMLDocument, XMLStatus
from src.sefaz.parser import parse_nfe_items

logger = logging.getLogger(__name__)


async def process_xml_document(
    db: AsyncSession,
    xml_document: XMLDocument,
    content_str: str,
    extractor: XMLExtractor,
) -> None:
    """
    Roda o parser determinístico + extração Claude sobre `content_str` e popula
    `xml_document` (status, confidence_score) e seus ExtractedItem.

    `xml_document` já deve ter sido inserido (id atribuído) antes de chamar esta
    função, pois ExtractedItem referencia xml_document.id. Não faz commit — quem
    chama decide quando persistir.
    """
    try:
        parsed_items = parse_nfe_items(content_str)
    except ValueError as e:
        logger.warning(f"Deterministic NFe parsing failed for {xml_document.filename}: {e}")
        parsed_items = []

    extraction_result = await extractor.extract(content_str)

    if "error" in extraction_result:
        xml_document.status = XMLStatus.FAILED
        logger.warning(
            f"Extraction failed for {xml_document.filename}: {extraction_result['error']}"
        )
        return

    for index, item in enumerate(extraction_result.get("items", [])):
        parsed = parsed_items[index] if index < len(parsed_items) else {}
        db.add(ExtractedItem(
            xml_document_id=xml_document.id,
            ncm=parsed.get("ncm") or item.get("ncm"),
            cfop=parsed.get("cfop") or item.get("cfop"),
            cst=parsed.get("cst") or item.get("cst_icms"),
            quantity=item.get("quantity"),
            value=item.get("total_value"),
        ))
    xml_document.confidence_score = extraction_result.get("overall_confidence")
    xml_document.status = XMLStatus.PROCESSED
