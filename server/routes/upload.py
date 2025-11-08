"""File upload routes."""
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile

from infra.neo4j_client import neo4j_client
from infra.storage import Storage

router = APIRouter(prefix="/uploads", tags=["uploads"])

storage = Storage()

ALLOWED_EXTENSIONS = {
    ".pdf": "pdf",
    ".md": "md",
    ".markdown": "md",
    ".txt": "txt",
    ".doc": "word",
    ".docx": "word",
}

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/markdown",
    "text/x-markdown",
    "text/plain",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",  # fallback used by some browsers
}

SUPPORTED_TYPES_LABEL = "PDF, Markdown, TXT, Word (DOC/DOCX)"


def get_document_kind(filename: str) -> str:
    """Determine document kind from filename."""
    ext = Path(filename).suffix.lower()
    return ALLOWED_EXTENSIONS.get(ext, "unknown")


def validate_content_type(content_type: Optional[str]) -> None:
    """Validate uploaded file MIME type."""
    if not content_type:
        return
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported MIME type: {content_type}. "
                f"Allowed types: {SUPPORTED_TYPES_LABEL}"
            ),
        )


@router.post("", response_model=dict)
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a file and create a document record.
    
    Returns:
        {
            "documentId": "...",
            "filename": "...",
            "checksum": "...",
            "status": "uploaded"
        }
    """
    # Read file content
    content = await file.read()
    
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    
    # Determine document kind
    kind = get_document_kind(file.filename)
    if kind == "unknown":
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported file type: {Path(file.filename).suffix or 'unknown'}. "
                f"Allowed types: {SUPPORTED_TYPES_LABEL}"
            ),
        )

    validate_content_type(file.content_type)
    
    # Save file and get checksum
    file_path, checksum = await storage.save_file(content, file.filename)
    
    # Check if document already exists (by checksum)
    existing_docs = neo4j_client.execute_query(
        "MATCH (d:Document {checksum: $checksum}) RETURN d.id as id LIMIT 1",
        {"checksum": checksum}
    )
    
    if existing_docs:
        return {
            "documentId": existing_docs[0]["id"],
            "filename": file.filename,
            "checksum": checksum,
            "status": "duplicate",
            "message": "Document already exists"
        }
    
    # Create document ID
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    
    # Create document in Neo4j
    neo4j_client.create_document(
        doc_id=doc_id,
        filename=file.filename,
        checksum=checksum,
        kind=kind,
        size=len(content),
        mime=file.content_type,
        meta={"path": file_path}
    )
    
    return {
        "documentId": doc_id,
        "filename": file.filename,
        "checksum": checksum,
        "status": "uploaded",
        "path": file_path
    }


@router.get("/{document_id}")
async def get_document(document_id: str):
    """Get document information."""
    result = neo4j_client.execute_query(
        "MATCH (d:Document {id: $doc_id}) RETURN d",
        {"doc_id": document_id}
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc_data = result[0]["d"]
    return doc_data

