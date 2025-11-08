"""Document data models."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class DocumentCreate(BaseModel):
    """Document creation model."""
    filename: str
    checksum: str
    kind: str = Field(..., description="Document type: pdf, md, docx, epub, html")
    mime: Optional[str] = None
    size: int
    source_id: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class Document(BaseModel):
    """Document model."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    filename: str
    checksum: str
    kind: str
    mime: Optional[str] = None
    size: int
    path: Optional[str] = None
    source_id: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class Chunk(BaseModel):
    """Text chunk model."""
    doc_id: str
    chunk_id: str
    text: str
    meta: Dict[str, Any] = Field(default_factory=dict, description="Metadata: page, section, offset, etc.")


class Triplet(BaseModel):
    """Triplet (subject-predicate-object) model."""
    subject: str
    predicate: str
    object: str
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Evidence: docId, chunkId, page, offset")
    doc_id: Optional[str] = None
    chunk_id: Optional[str] = None
    context: Optional[str] = Field(None, description="Contextual information about the relationship")


class AIExtractionRequest(BaseModel):
    """AI extraction configuration."""
    enable_ai_segmentation: bool = Field(False, description="Enable AI-powered intelligent segmentation")
    user_prompt: Optional[str] = Field(None, description="User-defined analysis prompt")
    optimize_prompt: bool = Field(True, description="Whether to optimize user prompt with AI")

