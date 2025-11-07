"""Document data models."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    """Document creation model."""
    filename: str
    checksum: str
    kind: str = Field(..., description="Document type: pdf, md, docx, epub, html")
    mime: Optional[str] = None
    size: int
    source_id: Optional[str] = None
    meta: Optional[dict] = None


class Document(BaseModel):
    """Document model."""
    id: str
    filename: str
    checksum: str
    kind: str
    mime: Optional[str] = None
    size: int
    path: Optional[str] = None
    source_id: Optional[str] = None
    meta: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class Chunk(BaseModel):
    """Text chunk model."""
    doc_id: str
    chunk_id: str
    text: str
    meta: dict = Field(default_factory=dict, description="Metadata: page, section, offset, etc.")


class Triplet(BaseModel):
    """Triplet (subject-predicate-object) model."""
    subject: str
    predicate: str
    object: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: dict = Field(default_factory=dict, description="Evidence: docId, chunkId, page, offset")
    doc_id: Optional[str] = None
    chunk_id: Optional[str] = None

