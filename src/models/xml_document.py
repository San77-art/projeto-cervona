"""
XML document model
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, Float, String
from sqlalchemy.orm import relationship

from src.models.base import Base


class XMLStatus(str, enum.Enum):
    """Processing status of an uploaded XML"""

    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class XMLDocument(Base):
    """An uploaded fiscal XML and its processing state"""

    __tablename__ = "xml_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String(255), nullable=False)
    status = Column(Enum(XMLStatus), nullable=False, default=XMLStatus.PENDING)
    confidence_score = Column(Float, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    items = relationship("ExtractedItem", back_populates="xml_document", cascade="all, delete-orphan")
