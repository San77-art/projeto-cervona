"""
SEFAZ sync route
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.extractor import XMLExtractor, get_extractor
from src.api.middleware.auth import get_current_user
from src.config.database import get_db
from src.sefaz.client import SEFAZClientError
from src.sefaz.service import sync_documents

router = APIRouter(dependencies=[Depends(get_current_user)])
logger = logging.getLogger(__name__)


@router.post("/sefaz/sync")
async def sync_sefaz(
    db: AsyncSession = Depends(get_db),
    extractor: XMLExtractor = Depends(get_extractor),
):
    """
    Busca documentos novos da SEFAZ (Distribuição de DFe real, ou mock conforme
    SEFAZ_MODE) e persiste cada um pelo mesmo pipeline de parsing determinístico
    + extração Claude usado no upload manual de XML.
    """
    try:
        result = await sync_documents(db, extractor)
    except SEFAZClientError as e:
        logger.error(f"SEFAZ sync failed: {e}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return result
