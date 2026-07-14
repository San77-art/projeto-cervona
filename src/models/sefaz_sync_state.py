"""
Cursor de paginação (NSU) da sincronização com a Distribuição de DFe da SEFAZ
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String

from src.models.base import Base

DEFAULT_SYNC_STATE_ID = "default"


class SefazSyncState(Base):
    """
    Guarda o último NSU processado para retomar a paginação (distNSU) entre
    chamadas a POST /sefaz/sync, sem reprocessar documentos já consultados.
    Linha única, id fixo em DEFAULT_SYNC_STATE_ID — não há multi-tenant ainda.
    """

    __tablename__ = "sefaz_sync_state"

    id = Column(String(20), primary_key=True, default=DEFAULT_SYNC_STATE_ID)
    last_nsu = Column(String(15), nullable=False, default="0")
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
