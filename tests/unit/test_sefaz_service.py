"""
Tests para src.sefaz.service (sincronização com a SEFAZ, real e mock)
"""

import pytest
from sqlalchemy import select

from src.config.settings import settings
from src.models import XMLDocument
from src.models.sefaz_sync_state import SefazSyncState
from src.sefaz import service as sefaz_service
from src.sefaz.client import DistDFeResult, SEFAZClientError, SEFAZDocument


class _StubExtractor:
    def __init__(self, result=None):
        self.result = result or {"items": [], "overall_confidence": 1.0, "warnings": []}

    async def extract(self, xml_content):
        return self.result


class _FakeSEFAZClient:
    """Substitui SEFAZClient nos testes de sync real, devolvendo páginas fixas"""

    def __init__(self, pages):
        self._pages = list(pages)
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        pass

    async def consultar_nsu(self, ult_nsu):
        self.calls.append(ult_nsu)
        return self._pages.pop(0)


@pytest.mark.asyncio
async def test_sync_documents_rejects_invalid_mode(session_factory, monkeypatch):
    monkeypatch.setattr(settings, "SEFAZ_MODE", "bogus")
    async with session_factory() as db:
        with pytest.raises(ValueError, match="SEFAZ_MODE"):
            await sefaz_service.sync_documents(db, _StubExtractor())


@pytest.mark.asyncio
async def test_sync_from_mock_persists_documents(session_factory, monkeypatch):
    monkeypatch.setattr(settings, "SEFAZ_MODE", "mock")

    async with session_factory() as db:
        result = await sefaz_service.sync_documents(db, _StubExtractor())

    assert result == {"mode": "mock", "documents_saved": 2, "caught_up": True}

    async with session_factory() as db:
        docs = (await db.execute(select(XMLDocument))).scalars().all()
    assert len(docs) == 2


@pytest.mark.asyncio
async def test_sync_from_real_paginates_until_caught_up(session_factory, monkeypatch):
    monkeypatch.setattr(settings, "SEFAZ_MODE", "real")

    page1 = DistDFeResult(
        documents=[SEFAZDocument(nsu="1", schema="procNFe_v1.01.xsd", xml="<nfeProc/>")],
        ult_nsu="1", max_nsu="2", status_code="138", status_reason="OK",
    )
    page2 = DistDFeResult(
        documents=[SEFAZDocument(nsu="2", schema="resNFe_v1.01.xsd", xml="<resNFe/>")],
        ult_nsu="2", max_nsu="2", status_code="138", status_reason="OK",
    )
    fake_client = _FakeSEFAZClient([page1, page2])
    monkeypatch.setattr(sefaz_service, "SEFAZClient", lambda: fake_client)

    async with session_factory() as db:
        result = await sefaz_service.sync_documents(db, _StubExtractor())

    assert result["mode"] == "real"
    assert result["documents_saved"] == 1  # resNFe (resumo) é ignorado
    assert result["caught_up"] is True
    assert result["last_nsu"] == "2"
    assert result["pages_fetched"] == 2
    assert fake_client.calls == ["0", "1"]

    async with session_factory() as db:
        state = await db.get(SefazSyncState, "default")
        assert state.last_nsu == "2"


@pytest.mark.asyncio
async def test_sync_from_real_resumes_from_saved_cursor(session_factory, monkeypatch):
    monkeypatch.setattr(settings, "SEFAZ_MODE", "real")

    async with session_factory() as db:
        db.add(SefazSyncState(id="default", last_nsu="41"))
        await db.commit()

    page = DistDFeResult(documents=[], ult_nsu="41", max_nsu="41", status_code="137", status_reason="OK")
    fake_client = _FakeSEFAZClient([page])
    monkeypatch.setattr(sefaz_service, "SEFAZClient", lambda: fake_client)

    async with session_factory() as db:
        await sefaz_service.sync_documents(db, _StubExtractor())

    assert fake_client.calls == ["41"]


@pytest.mark.asyncio
async def test_sync_from_real_propagates_client_errors(session_factory, monkeypatch):
    monkeypatch.setattr(settings, "SEFAZ_MODE", "real")

    class _FailingClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc_info):
            pass

        async def consultar_nsu(self, ult_nsu):
            raise SEFAZClientError("boom")

    monkeypatch.setattr(sefaz_service, "SEFAZClient", lambda: _FailingClient())

    async with session_factory() as db:
        with pytest.raises(SEFAZClientError):
            await sefaz_service.sync_documents(db, _StubExtractor())
