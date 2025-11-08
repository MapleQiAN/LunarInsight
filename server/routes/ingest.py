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
from services.ai_segmenter import AISegmenter

router = APIRouter(prefix="/ingest", tags=["ingest"])

storage = Storage()
extractor = TripletExtractor()
linker = EntityLinker()
graph_service = GraphService()

# Initialize AI segmenter (optional)
try:
    ai_segmenter = AISegmenter()
except ValueError:
    ai_segmenter = None

# Simple job storage (in production, use Redis/RQ)
jobs: Dict[str, Dict] = {}


def process_document(
    doc_id: str, 
    file_path: str, 
    kind: str, 
    job_id: str, 
    chunk_size: int = 2000,
    enable_ai_segmentation: bool = False,
    user_prompt: Optional[str] = None,
    optimize_prompt: bool = True
):
    """
    Process document: parse, extract, link, and ingest.
    
    Args:
        doc_id: Document ID
        file_path: Path to document file
        kind: Document type
        job_id: Job ID for tracking
        chunk_size: Maximum characters per chunk (default: 2000)
        enable_ai_segmentation: Enable AI-powered intelligent segmentation
        user_prompt: User-defined analysis prompt
        optimize_prompt: Whether to optimize user prompt with AI
    """
    jobs[job_id] = {
        "status": "processing",
        "documentId": doc_id,
        "progress": 0,
        "message": "Starting parsing..."
    }
    
    try:
        # Parse document
        jobs[job_id]["message"] = "Parsing document..."
        jobs[job_id]["progress"] = 10
        
        parser = ParserFactory.create_parser(kind, chunk_size=chunk_size)
        full_text, chunks = parser.parse(file_path)
        
        # AI智能分词模式
        if enable_ai_segmentation and ai_segmenter:
            # Optimize user prompt if provided
            final_prompt = None
            if user_prompt:
                jobs[job_id]["message"] = "Optimizing prompt..."
                jobs[job_id]["progress"] = 15
                
                if optimize_prompt:
                    final_prompt = ai_segmenter.optimize_user_prompt(user_prompt)
                else:
                    final_prompt = user_prompt
            
            # Analyze document structure
            jobs[job_id]["message"] = "Analyzing document structure..."
            jobs[job_id]["progress"] = 20
            
            doc_context = ai_segmenter.analyze_document_structure(chunks, final_prompt)
            
            # Extract rich knowledge from each chunk
            jobs[job_id]["message"] = "Extracting rich knowledge..."
            jobs[job_id]["progress"] = 30
            
            all_triplets = []
            all_concepts = []
            all_insights = []
            
            for i, chunk in enumerate(chunks, 1):
                knowledge = ai_segmenter.extract_rich_knowledge(chunk, doc_context, final_prompt)
                
                all_triplets.extend(knowledge.get("triplets", []))
                all_concepts.extend(knowledge.get("concepts", []))
                all_insights.extend(knowledge.get("insights", []))
                
                jobs[job_id]["progress"] = 30 + int((i / len(chunks)) * 40)
                jobs[job_id]["message"] = f"AI analyzing... ({i}/{len(chunks)})"
            
            # Ingest rich concepts first
            jobs[job_id]["message"] = "Ingesting rich concepts..."
            jobs[job_id]["progress"] = 75
            
            graph_service.ingest_rich_concepts(doc_id, all_concepts)
            
            # Link and merge entities
            jobs[job_id]["message"] = "Linking entities..."
            jobs[job_id]["progress"] = 80
            
            linked_triplets = linker.link_and_merge(all_triplets)
            
            # Ingest triplets
            jobs[job_id]["message"] = "Ingesting into graph..."
            jobs[job_id]["progress"] = 90
            
            graph_service.ingest_triplets(doc_id, linked_triplets)
            
            concept_names = set(c["name"] for c in all_concepts)
            
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["progress"] = 100
            jobs[job_id]["message"] = "AI analysis completed!"
            jobs[job_id]["stats"] = {
                "chunks": len(chunks),
                "triplets": len(linked_triplets),
                "concepts": len(concept_names),
                "insights": len(all_insights),
                "mode": "ai_segmentation"
            }
            if all_insights:
                jobs[job_id]["insights"] = all_insights[:10]
        
        else:
            # 传统模式
            jobs[job_id]["message"] = f"Extracted {len(chunks)} chunks. Extracting triplets..."
            jobs[job_id]["progress"] = 30
            
            all_triplets = []
            for i, chunk in enumerate(chunks):
                triplets = extractor.extract(chunk)
                all_triplets.extend(triplets)
                jobs[job_id]["progress"] = 30 + int((i + 1) / len(chunks) * 40)
            
            jobs[job_id]["message"] = f"Extracted {len(all_triplets)} triplets. Linking entities..."
            jobs[job_id]["progress"] = 70
            
            linked_triplets = linker.link_and_merge(all_triplets)
            
            jobs[job_id]["message"] = "Ingesting into graph..."
            jobs[job_id]["progress"] = 90
            
            graph_service.ingest_triplets(doc_id, linked_triplets)
            
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["progress"] = 100
            jobs[job_id]["message"] = f"Successfully processed {len(linked_triplets)} triplets"
            jobs[job_id]["stats"] = {
                "chunks": len(chunks),
                "triplets": len(linked_triplets),
                "concepts": len(set(t.subject for t in linked_triplets) | set(t.object for t in linked_triplets)),
                "mode": "traditional"
            }
        
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["message"] = f"Error: {str(e)}"
        jobs[job_id]["progress"] = 0
        import traceback
        jobs[job_id]["error"] = traceback.format_exc()


@router.post("/{document_id}")
async def ingest_document(
    document_id: str, 
    background_tasks: BackgroundTasks,
    chunk_size: int = 2000,
    enable_ai_segmentation: bool = False,
    user_prompt: Optional[str] = None,
    optimize_prompt: bool = True
):
    """
    Trigger ingestion for a document.
    
    Args:
        document_id: Document ID to ingest
        chunk_size: Maximum characters per chunk (default: 2000)
        enable_ai_segmentation: Enable AI-powered intelligent segmentation
        user_prompt: User-defined analysis prompt
        optimize_prompt: Whether to optimize user prompt with AI
    
    Returns:
        {
            "jobId": "...",
            "documentId": "...",
            "status": "queued"
        }
    """
    # Validate chunk_size
    if chunk_size < 100:
        raise HTTPException(status_code=400, detail="chunk_size 不能小于 100 字符")
    if chunk_size > 20000:
        raise HTTPException(status_code=400, detail="chunk_size 不能大于 20000 字符（建议不超过 8000）")
    
    # Validate AI segmentation
    if enable_ai_segmentation and not ai_segmenter:
        raise HTTPException(
            status_code=400, 
            detail="AI智能分词需要配置 OPENAI_API_KEY 环境变量"
        )
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
    background_tasks.add_task(
        process_document, 
        document_id, 
        str(file_path), 
        kind, 
        job_id, 
        chunk_size,
        enable_ai_segmentation,
        user_prompt,
        optimize_prompt
    )
    
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

