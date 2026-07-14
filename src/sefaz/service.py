"""
Sincronização com a SEFAZ — busca documentos novos (real ou mock, conforme
SEFAZ_MODE) e persiste cada um pelo mesmo pipeline usado no upload manual
(src/services/xml_pipeline.py).

Modo "real" pagina a Distribuição de DFe por NSU (ver src/sefaz/client.py),
retomando de onde parou via o cursor salvo em SefazSyncState. Modo "mock"
ignora paginação e apenas devolve os documentos fixos de MockSEFAZClient,
para desenvolvimento sem certificado A1.
"""

import logging
from typing import Dict

from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.extractor import XMLExtractor
from src.config.settings import settings
from src.models import XMLDocument, XMLStatus
from src.models.sefaz_sync_state import DEFAULT_SYNC_STATE_ID, SefazSyncState
from src.sefaz.client import SEFAZClient
from src.sefaz.mock import MockSEFAZClient
from src.services.xml_pipeline import process_xml_document

logger = logging.getLogger(__name__)

# Limite de páginas por chamada de sync — evita uma requisição HTTP que nunca
# retorna caso a SEFAZ tenha um backlog muito grande; o cursor fica salvo e a
# próxima chamada a /sefaz/sync continua de onde parou.
_MAX_PAGES_PER_SYNC = 20


async def _get_or_create_state(db: AsyncSession) -> SefazSyncState:
    state = await db.get(SefazSyncState, DEFAULT_SYNC_STATE_ID)
    if state is None:
        state = SefazSyncState(id=DEFAULT_SYNC_STATE_ID, last_nsu="0")
        db.add(state)
        await db.flush()
    return state


async def _store_document(
    db: AsyncSession, filename: str, xml: str, extractor: XMLExtractor
) -> XMLDocument:
    xml_document = XMLDocument(filename=filename, status=XMLStatus.PENDING)
    db.add(xml_document)
    await db.flush()  # atribui xml_document.id, necessário para os ExtractedItem

    await process_xml_document(db, xml_document, xml, extractor)
    return xml_document


async def sync_documents(db: AsyncSession, extractor: XMLExtractor) -> Dict:
    """
    Busca documentos novos da SEFAZ e persiste cada um. Lança ValueError se
    SEFAZ_MODE for inválido, e SEFAZClientError (ver src/sefaz/client.py) se o
    modo "real" falhar ao consultar a SEFAZ — quem chama decide como mapear
    isso para uma resposta HTTP (ver src/api/routes/sefaz.py).
    """
    mode = (settings.SEFAZ_MODE or "mock").lower()

    if mode == "mock":
        return await _sync_from_mock(db, extractor)
    if mode == "real":
        return await _sync_from_real(db, extractor)
    raise ValueError(f"SEFAZ_MODE inválido: {mode!r} (use 'mock' ou 'real')")


async def _sync_from_mock(db: AsyncSession, extractor: XMLExtractor) -> Dict:
    documents = await MockSEFAZClient.query_xml(settings.SEFAZ_CNPJ or "00000000000000")

    saved = 0
    for doc in documents:
        await _store_document(db, filename=f"sefaz-mock-{doc['nsu']}.xml", xml=doc["xml"], extractor=extractor)
        saved += 1

    await db.commit()
    logger.info(f"SEFAZ sync (mock): {saved} documento(s) salvo(s)")
    return {"mode": "mock", "documents_saved": saved, "caught_up": True}


async def _sync_from_real(db: AsyncSession, extractor: XMLExtractor) -> Dict:
    state = await _get_or_create_state(db)

    saved = 0
    caught_up = False
    pages = 0

    async with SEFAZClient() as client:
        while pages < _MAX_PAGES_PER_SYNC:
            result = await client.consultar_nsu(state.last_nsu)
            pages += 1

            for doc in result.documents:
                if not doc.is_full_document:
                    # resNFe/resEvento são resumos sem itens — nada para extrair
                    continue
                await _store_document(db, filename=f"sefaz-nsu-{doc.nsu}.xml", xml=doc.xml, extractor=extractor)
                saved += 1

            state.last_nsu = result.ult_nsu
            caught_up = result.caught_up
            if caught_up:
                break

    await db.commit()
    logger.info(
        f"SEFAZ sync (real): {saved} documento(s) salvo(s) em {pages} página(s), "
        f"ultNSU={state.last_nsu}, caught_up={caught_up}"
    )
    return {
        "mode": "real",
        "documents_saved": saved,
        "caught_up": caught_up,
        "last_nsu": state.last_nsu,
        "pages_fetched": pages,
    }
