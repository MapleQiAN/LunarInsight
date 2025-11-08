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
from infra.queue import get_queue, update_job_progress

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

# Initialize Redis queue
queue = get_queue()

# Fallback job storage (used when Redis is not available)
jobs: Dict[str, Dict] = {}


def _is_job_cancelled(job_id: str) -> bool:
    """Check if job has been cancelled."""
    # Try to check via RQ if available
    if queue.is_connected():
        try:
            from rq import get_current_job
            current_job = get_current_job()
            if current_job:
                # We're in a worker, check current job meta
                meta = current_job.meta or {}
                return meta.get('_cancelled', False)
        except Exception:
            pass
        
        # Not in worker context, try to fetch job by ID
        try:
            job = queue.get_job(job_id)
            if job:
                meta = job.meta or {}
                return meta.get('_cancelled', False)
        except Exception:
            pass
    
    # Fallback to in-memory storage
    if job_id in jobs:
        return jobs[job_id].get("status") == "cancelled"
    
    return False


def _update_status(job_id: str, status: str, progress: int, message: str, **kwargs):
    """Update job status (supports both Redis and fallback storage)."""
    # Try to update via RQ if we're in a worker context
    if queue.is_connected():
        try:
            from rq import get_current_job
            current_job = get_current_job()
            if current_job:
                # We're in a worker, update current job
                meta = current_job.meta or {}
                meta.update({
                    "status": status,
                    "progress": progress,
                    "message": message,
                    **kwargs
                })
                current_job.meta = meta
                current_job.save()
                return
        except Exception:
            pass
        
        # Not in worker context, try to fetch job by ID
        try:
            job = queue.get_job(job_id)
            if job:
                meta = job.meta or {}
                meta.update({
                    "status": status,
                    "progress": progress,
                    "message": message,
                    **kwargs
                })
                job.meta = meta
                job.save()
                return
        except Exception:
            pass
    
    # Fallback to in-memory storage
    if job_id not in jobs:
        jobs[job_id] = {}
    jobs[job_id].update({
        "status": status,
        "progress": progress,
        "message": message,
        **kwargs
    })


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
    _update_status(job_id, "processing", 0, "Starting parsing...", documentId=doc_id)
    
    try:
        # Check if cancelled
        if _is_job_cancelled(job_id):
            return
        
        # Parse document
        _update_status(job_id, "processing", 10, "Parsing document...", documentId=doc_id)
        
        parser = ParserFactory.create_parser(kind, chunk_size=chunk_size)
        full_text, chunks = parser.parse(file_path)
        
        # Check if cancelled
        if _is_job_cancelled(job_id):
            return
        
        # AI智能分词模式
        if enable_ai_segmentation and ai_segmenter:
            # Optimize user prompt if provided
            final_prompt = None
            if user_prompt:
                _update_status(job_id, "processing", 15, "Optimizing prompt...", documentId=doc_id)
                
                # Check if cancelled
                if _is_job_cancelled(job_id):
                    return
                
                if optimize_prompt:
                    final_prompt = ai_segmenter.optimize_user_prompt(user_prompt)
                else:
                    final_prompt = user_prompt
            
            # Check if cancelled
            if _is_job_cancelled(job_id):
                return
            
            # Analyze document structure
            _update_status(job_id, "processing", 20, "Analyzing document structure...", documentId=doc_id)
            
            doc_context = ai_segmenter.analyze_document_structure(chunks, final_prompt)
            
            # Check if cancelled
            if _is_job_cancelled(job_id):
                return
            
            # Extract rich knowledge from each chunk
            _update_status(job_id, "processing", 30, "Extracting rich knowledge...", documentId=doc_id)
            
            all_triplets = []
            all_concepts = []
            all_insights = []
            
            for i, chunk in enumerate(chunks, 1):
                # Check if cancelled before processing each chunk
                if _is_job_cancelled(job_id):
                    return
                
                knowledge = ai_segmenter.extract_rich_knowledge(chunk, doc_context, final_prompt)
                
                all_triplets.extend(knowledge.get("triplets", []))
                all_concepts.extend(knowledge.get("concepts", []))
                all_insights.extend(knowledge.get("insights", []))
                
                progress = 30 + int((i / len(chunks)) * 40)
                _update_status(job_id, "processing", progress, f"AI analyzing... ({i}/{len(chunks)})", documentId=doc_id)
            
            # Ingest rich concepts first
            _update_status(job_id, "processing", 75, "Ingesting rich concepts...", documentId=doc_id)
            
            graph_service.ingest_rich_concepts(doc_id, all_concepts)
            
            # Link and merge entities
            _update_status(job_id, "processing", 80, "Linking entities...", documentId=doc_id)
            
            linked_triplets = linker.link_and_merge(all_triplets)
            
            # Ingest triplets
            _update_status(job_id, "processing", 90, "Ingesting into graph...", documentId=doc_id)
            
            graph_service.ingest_triplets(doc_id, linked_triplets)
            
            concept_names = set(c["name"] for c in all_concepts)
            
            stats = {
                "chunks": len(chunks),
                "triplets": len(linked_triplets),
                "concepts": len(concept_names),
                "insights": len(all_insights),
                "mode": "ai_segmentation"
            }
            
            result_data = {"stats": stats}
            if all_insights:
                result_data["insights"] = all_insights[:10]
            
            _update_status(job_id, "completed", 100, "AI analysis completed!", documentId=doc_id, **result_data)
        
        else:
            # 传统模式
            _update_status(job_id, "processing", 30, f"Extracted {len(chunks)} chunks. Extracting triplets...", documentId=doc_id)
            
            all_triplets = []
            for i, chunk in enumerate(chunks):
                # Check if cancelled before processing each chunk
                if _is_job_cancelled(job_id):
                    return
                
                triplets = extractor.extract(chunk)
                all_triplets.extend(triplets)
                progress = 30 + int((i + 1) / len(chunks) * 40)
                _update_status(job_id, "processing", progress, f"Extracting triplets... ({i + 1}/{len(chunks)})", documentId=doc_id)
            
            # Check if cancelled
            if _is_job_cancelled(job_id):
                return
            
            _update_status(job_id, "processing", 70, f"Extracted {len(all_triplets)} triplets. Linking entities...", documentId=doc_id)
            
            linked_triplets = linker.link_and_merge(all_triplets)
            
            # Check if cancelled
            if _is_job_cancelled(job_id):
                return
            
            _update_status(job_id, "processing", 90, "Ingesting into graph...", documentId=doc_id)
            
            graph_service.ingest_triplets(doc_id, linked_triplets)
            
            stats = {
                "chunks": len(chunks),
                "triplets": len(linked_triplets),
                "concepts": len(set(t.subject for t in linked_triplets) | set(t.object for t in linked_triplets)),
                "mode": "traditional"
            }
            
            _update_status(job_id, "completed", 100, f"Successfully processed {len(linked_triplets)} triplets", documentId=doc_id, stats=stats)
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        _update_status(job_id, "failed", 0, f"Error: {str(e)}", documentId=doc_id, error=error_trace)


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
    
    # Try to use RQ queue if available
    if queue.is_connected():
        job = queue.enqueue(
            process_document,
            document_id,
            str(file_path),
            kind,
            job_id,
            chunk_size,
            enable_ai_segmentation,
            user_prompt,
            optimize_prompt,
            job_timeout='1h'
        )
        
        if job:
            # Initialize job metadata
            job.meta = {
                "status": "queued",
                "documentId": document_id,
                "progress": 0,
                "message": "Queued for processing"
            }
            job.save()
            return {
                "jobId": job.id,
                "documentId": document_id,
                "status": "queued"
            }
    
    # Fallback to BackgroundTasks if Redis is not available
    _update_status(job_id, "queued", 0, "Queued for processing", documentId=document_id)
    
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
    # Try to get status from Redis first
    if queue.is_connected():
        status = queue.get_job_status(job_id)
        if status.get("status") != "not_found":
            return status
    
    # Fallback to in-memory storage
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs[job_id]


@router.delete("/cancel/{job_id}")
async def cancel_ingest_job(job_id: str):
    """
    Cancel a running ingestion job.
    
    Args:
        job_id: Job ID to cancel
        
    Returns:
        Success message or error
    """
    # Try to cancel via RQ if available
    if queue.is_connected():
        success = queue.cancel_job(job_id)
        if success:
            # 成功取消后，同时更新内存状态（如果存在）
            if job_id in jobs:
                jobs[job_id].update({
                    "status": "cancelled",
                    "message": "任务已被用户取消"
                })
            return {"message": "Job cancelled successfully", "jobId": job_id}
        else:
            # Check if job exists
            status = queue.get_job_status(job_id)
            if status.get("status") == "not_found":
                # 任务未找到，可能还没开始处理，创建一个取消状态记录
                jobs[job_id] = {
                    "status": "cancelled",
                    "message": "任务已被用户取消",
                    "progress": 0
                }
                return {"message": "Job cancelled successfully", "jobId": job_id}
            else:
                raise HTTPException(status_code=400, detail="Job cannot be cancelled (already completed or failed)")
    
    # Fallback: mark job as cancelled in in-memory storage
    if job_id not in jobs:
        # 如果内存中也没有，创建一个取消状态记录
        jobs[job_id] = {
            "status": "cancelled",
            "message": "任务已被用户取消",
            "progress": 0
        }
        return {"message": "Job cancelled successfully", "jobId": job_id}
    
    current_status = jobs[job_id].get("status")
    if current_status in ["completed", "failed", "cancelled"]:
        raise HTTPException(status_code=400, detail=f"Job cannot be cancelled (status: {current_status})")
    
    # Mark as cancelled
    jobs[job_id].update({
        "status": "cancelled",
        "message": "任务已被用户取消"
    })
    
    return {"message": "Job cancelled successfully", "jobId": job_id}

