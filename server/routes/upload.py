"""File upload routes."""
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional
from pathlib import Path
import aiofiles
from infra.storage import Storage
from infra.neo4j_client import neo4j_client
from models.document import DocumentCreate, Document
from datetime import datetime

router = APIRouter(prefix="/uploads", tags=["uploads"])

storage = Storage()


def get_document_kind(filename: str) -> str:
    """Determine document kind from filename."""
    ext = Path(filename).suffix.lower()
    kind_map = {
        ".pdf": "pdf",
        ".md": "md",
        ".markdown": "md",
        ".docx": "docx",
        ".epub": "epub",
        ".html": "html",
        ".htm": "html",
    }
    return kind_map.get(ext, "unknown")


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
            detail=f"Unsupported file type: {Path(file.filename).suffix}"
        )
    
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

