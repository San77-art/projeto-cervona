"""
Extracted fiscal item model
"""

from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from src.models.base import Base


class ExtractedItem(Base):
    """A single fiscal line item extracted from an XML document"""

    __tablename__ = "extracted_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    xml_document_id = Column(String(36), ForeignKey("xml_documents.id"), nullable=False)
    ncm = Column(String(8), nullable=False)
    cfop = Column(String(4), nullable=False)
    cst = Column(String(3), nullable=False)
    quantity = Column(Float, nullable=False)
    value = Column(Float, nullable=False)

    xml_document = relationship("XMLDocument", back_populates="items")
