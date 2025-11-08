"""Document ingestion routes."""
import json
import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Optional
from pathlib import Path
from infra.neo4j_client import neo4j_client
from infra.storage import Storage
from services.parser import ParserFactory
from services.extractor import TripletExtractor
from services.linker import EntityLinker
from services.graph_service import GraphService

router = APIRouter(prefix="/ingest", tags=["ingest"])

storage = Storage()
extractor = TripletExtractor()
linker = EntityLinker()
graph_service = GraphService()

# Simple job storage (in production, use Redis/RQ)
jobs: Dict[str, Dict] = {}


def process_document(doc_id: str, file_path: str, kind: str, job_id: str):
    """Process document: parse, extract, link, and ingest."""
    jobs[job_id] = {
        "status": "processing",
        "documentId": doc_id,
        "progress": 0,
        "message": "Starting parsing..."
    }
    
    try:
        # Update job status
        jobs[job_id]["message"] = "Parsing document..."
        jobs[job_id]["progress"] = 10
        
        # Parse document
        parser = ParserFactory.create_parser(kind)
        full_text, chunks = parser.parse(file_path)
        
        jobs[job_id]["message"] = f"Extracted {len(chunks)} chunks. Extracting triplets..."
        jobs[job_id]["progress"] = 30
        
        # Extract triplets
        all_triplets = []
        for i, chunk in enumerate(chunks):
            triplets = extractor.extract(chunk)
            all_triplets.extend(triplets)
            jobs[job_id]["progress"] = 30 + int((i + 1) / len(chunks) * 40)
        
        jobs[job_id]["message"] = f"Extracted {len(all_triplets)} triplets. Linking entities..."
        jobs[job_id]["progress"] = 70
        
        # Link and merge entities
        linked_triplets = linker.link_and_merge(all_triplets)
        
        jobs[job_id]["message"] = "Ingesting into graph..."
        jobs[job_id]["progress"] = 90
        
        # Ingest into Neo4j
        graph_service.ingest_triplets(doc_id, linked_triplets)
        
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["progress"] = 100
        jobs[job_id]["message"] = f"Successfully processed {len(linked_triplets)} triplets"
        jobs[job_id]["stats"] = {
            "chunks": len(chunks),
            "triplets": len(linked_triplets),
            "concepts": len(set(t.subject for t in linked_triplets) | set(t.object for t in linked_triplets))
        }
        
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["message"] = f"Error: {str(e)}"
        jobs[job_id]["progress"] = 0
        import traceback
        jobs[job_id]["error"] = traceback.format_exc()


@router.post("/{document_id}")
async def ingest_document(document_id: str, background_tasks: BackgroundTasks):
    """
    Trigger ingestion for a document.
    
    Returns:
        {
            "jobId": "...",
            "documentId": "...",
            "status": "queued"
        }
    """
    # Get document info
    result = neo4j_client.execute_query(
        "MATCH (d:Document {id: $doc_id}) RETURN d.filename as filename, d.kind as kind, d.meta as meta",
        {"doc_id": document_id}
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc_data = result[0]
    filename = doc_data["filename"]
    kind = doc_data["kind"]
    
    # Parse meta JSON string if it exists
    meta = {}
    if doc_data.get("meta"):
        try:
            meta = json.loads(doc_data["meta"]) if isinstance(doc_data["meta"], str) else doc_data["meta"]
        except (json.JSONDecodeError, TypeError):
            meta = {}
    
    file_path = meta.get("path") or storage.get_file_path(filename)
    
    if not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    # Create job ID first
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    jobs[job_id] = {
        "status": "queued",
        "documentId": document_id,
        "progress": 0,
        "message": "Queued for processing"
    }
    
    # Start background processing
    background_tasks.add_task(process_document, document_id, str(file_path), kind, job_id)
    
    return {
        "jobId": job_id,
        "documentId": document_id,
        "status": "queued"
    }


@router.get("/status/{job_id}")
async def get_ingest_status(job_id: str):
    """Get ingestion job status."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs[job_id]

