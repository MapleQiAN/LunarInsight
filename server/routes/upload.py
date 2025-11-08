"""File upload routes."""
import uuid
import hashlib
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile, BackgroundTasks
from pydantic import BaseModel

from infra.neo4j_client import neo4j_client
from infra.storage import Storage
from services.parser import ParserFactory
from services.extractor import TripletExtractor
from services.linker import EntityLinker
from services.graph_service import GraphService
from services.ai_segmenter import AISegmenter
from models.document import AIExtractionRequest
from infra.queue import get_queue

router = APIRouter(prefix="/uploads", tags=["uploads"])

storage = Storage()
extractor = TripletExtractor()
linker = EntityLinker()
graph_service = GraphService()

# Initialize AI segmenter (optional, based on configured AI provider)
try:
    ai_segmenter = AISegmenter()
except ValueError as e:
    ai_segmenter = None
    print(f"⚠️  AI segmentation disabled: {str(e)}")

# Initialize Redis queue
queue = get_queue()

# Fallback job storage (used when Redis is not available)
processing_jobs = {}

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


def _update_upload_status(job_id: str, status: str, progress: int, message: str, **kwargs):
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
    if job_id not in processing_jobs:
        processing_jobs[job_id] = {}
    processing_jobs[job_id].update({
        "status": status,
        "progress": progress,
        "message": message,
        **kwargs
    })


def process_document_background(
    doc_id: str, 
    file_path: str, 
    kind: str, 
    job_id: str, 
    chunk_size: int = 2000,
    enable_ai_segmentation: bool = False,
    user_prompt: Optional[str] = None,
    optimize_prompt: bool = True,
    root_topic: Optional[str] = None
):
    """
    Background task for processing document into knowledge graph.
    
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
    _update_upload_status(job_id, "processing", 0, "开始处理文档...", documentId=doc_id)
    
    try:
        print(f"\n{'#'*80}")
        print(f"🚀 [文档处理] 开始处理文档")
        print(f"   - 文档ID: {doc_id}")
        print(f"   - 文件路径: {file_path}")
        print(f"   - 文件类型: {kind}")
        print(f"   - 任务ID: {job_id}")
        print(f"   - Chunk大小: {chunk_size} 字符")
        print(f"   - AI智能分词: {'启用' if enable_ai_segmentation else '禁用'}")
        if user_prompt:
            print(f"   - 用户Prompt: {user_prompt[:100]}...")
        print(f"{'#'*80}\n")
        
        # Step 1: Parse document
        _update_upload_status(job_id, "processing", 10, "正在解析文档...", documentId=doc_id)
        
        print(f"📖 [步骤1] 解析文档 (chunk_size={chunk_size})...")
        parser = ParserFactory.create_parser(kind, chunk_size=chunk_size)
        full_text, chunks = parser.parse(file_path)
        print(f"✅ [步骤1] 解析完成: {len(chunks)} 个文本块，总长度 {len(full_text)} 字符")
        if chunks:
            avg_chunk_size = sum(len(c.text) for c in chunks) / len(chunks)
            print(f"   - 平均每个文本块: {avg_chunk_size:.0f} 字符")
        
        # AI智能分词模式
        if enable_ai_segmentation and ai_segmenter:
            print(f"\n🧠 [AI模式] 启用智能知识抽取")
            
            # Step 1.5: Optimize user prompt if provided
            final_prompt = None
            if user_prompt:
                _update_upload_status(job_id, "processing", 15, "正在优化分析提示词...", documentId=doc_id)
                
                if optimize_prompt:
                    print(f"🔧 [Prompt优化] 优化用户提示词...")
                    final_prompt = ai_segmenter.optimize_user_prompt(user_prompt)
                else:
                    final_prompt = user_prompt
                    print(f"📝 [Prompt] 使用原始用户提示词")
            
            # Step 2: Analyze document structure
            _update_upload_status(job_id, "processing", 20, "正在分析文档结构...", documentId=doc_id)
            
            print(f"\n🔍 [文档分析] 分析文档整体结构...")
            doc_context = ai_segmenter.analyze_document_structure(chunks, final_prompt)
            print(f"✅ [文档分析] 完成:")
            print(f"   - 主题: {', '.join(doc_context.get('themes', []))}")
            print(f"   - 领域: {', '.join(doc_context.get('domains', []))}")
            print(f"   - 关键概念: {', '.join(doc_context.get('key_concepts', [])[:5])}...")
            
            # Step 3: Extract rich knowledge from each chunk
            _update_upload_status(job_id, "processing", 30, "正在进行深度知识抽取...", documentId=doc_id)
            
            print(f"\n💎 [深度抽取] 开始智能知识抽取 (共 {len(chunks)} 个文本块)...")
            all_triplets = []
            all_concepts = []
            all_insights = []
            
            for i, chunk in enumerate(chunks, 1):
                print(f"\n📦 [文本块 {i}/{len(chunks)}] AI深度分析中...")
                knowledge = ai_segmenter.extract_rich_knowledge(chunk, doc_context, final_prompt)
                
                # 收集三元组
                triplets = knowledge.get("triplets", [])
                all_triplets.extend(triplets)
                
                # 收集丰富概念
                concepts = knowledge.get("concepts", [])
                all_concepts.extend(concepts)
                
                # 收集洞察
                insights = knowledge.get("insights", [])
                all_insights.extend(insights)
                
                print(f"   ✓ 提取: {len(triplets)} 个关系, {len(concepts)} 个概念, {len(insights)} 个洞察")
                
                progress = 30 + int((i / len(chunks)) * 40)
                _update_upload_status(job_id, "processing", progress, f"AI深度分析中... ({i}/{len(chunks)})", documentId=doc_id)
            
            print(f"\n📊 [深度抽取] 完成:")
            print(f"   - 总关系数: {len(all_triplets)}")
            print(f"   - 总概念数: {len(all_concepts)}")
            print(f"   - 总洞察数: {len(all_insights)}")
            
            # Step 4: Ingest rich concepts first
            _update_upload_status(job_id, "processing", 75, "正在构建丰富概念...", documentId=doc_id)
            
            print(f"\n💎 [概念构建] 写入丰富概念信息...")
            graph_service.ingest_rich_concepts(doc_id, all_concepts, root_topic=root_topic)
            
            # Step 5: Link and merge entities
            _update_upload_status(job_id, "processing", 80, "正在链接实体...", documentId=doc_id)
            
            print(f"\n🔗 [实体链接] 开始实体链接和合并...")
            linked_triplets = linker.link_and_merge(all_triplets)
            print(f"✅ [实体链接] 完成: {len(linked_triplets)} 个三元组")
            
            # Step 6: Ingest triplets
            _update_upload_status(job_id, "processing", 90, "正在构建知识图谱...", documentId=doc_id)
            
            print(f"\n💾 [图谱构建] 开始构建知识图谱...")
            graph_service.ingest_triplets(doc_id, linked_triplets, root_topic=root_topic)
            print(f"✅ [图谱构建] 完成")
            
            # Get statistics
            concept_names = set(c["name"] for c in all_concepts)
            
            print(f"\n{'#'*80}")
            print(f"🎉 [AI智能处理] 处理完成!")
            print(f"   - 文本块数: {len(chunks)}")
            print(f"   - 丰富概念数: {len(all_concepts)}")
            print(f"   - 知识关系数: {len(linked_triplets)}")
            print(f"   - 深度洞察数: {len(all_insights)}")
            print(f"   - 文本总长度: {len(full_text)} 字符")
            if all_insights:
                print(f"\n💡 [关键洞察]:")
                for insight in all_insights[:3]:
                    print(f"   • {insight}")
            print(f"{'#'*80}\n")
            
            stats = {
                "chunks": len(chunks),
                "triplets": len(linked_triplets),
                "concepts": len(concept_names),
                "insights": len(all_insights),
                "textLength": len(full_text),
                "mode": "ai_segmentation"
            }
            result_data = {"stats": stats}
            if all_insights:
                result_data["insights"] = all_insights[:10]  # 返回前10条洞察
            
            _update_upload_status(job_id, "completed", 100, "AI智能分析完成！", documentId=doc_id, **result_data)
        
        else:
            # 传统模式
            _update_upload_status(job_id, "processing", 30, f"已提取 {len(chunks)} 个文本块，正在进行知识抽取...", documentId=doc_id)
            
            # Step 2: Extract triplets using AI
            print(f"\n🤖 [步骤2] 开始知识抽取 (共 {len(chunks)} 个文本块)...")
            all_triplets = []
            chunk_triplet_counts = []
            
            for i, chunk in enumerate(chunks, 1):
                print(f"\n📦 [文本块 {i}/{len(chunks)}] 处理中...")
                triplets = extractor.extract(chunk)
                all_triplets.extend(triplets)
                chunk_triplet_counts.append(len(triplets))
                progress = 30 + int((i / len(chunks)) * 40)
                _update_upload_status(job_id, "processing", progress, f"正在抽取知识... ({i}/{len(chunks)})", documentId=doc_id)
            
            print(f"\n📊 [步骤2] 知识抽取完成:")
            print(f"   - 总三元组数: {len(all_triplets)}")
            print(f"   - 各文本块三元组数: {chunk_triplet_counts}")
            print(f"   - 平均每个文本块: {len(all_triplets) / len(chunks) if chunks else 0:.2f} 个三元组")
            
            _update_upload_status(job_id, "processing", 70, f"已抽取 {len(all_triplets)} 个知识三元组，正在链接实体...", documentId=doc_id)
            
            # Step 3: Link and merge entities
            print(f"\n🔗 [步骤3] 开始实体链接和合并...")
            linked_triplets = linker.link_and_merge(all_triplets)
            print(f"✅ [步骤3] 实体链接完成: {len(linked_triplets)} 个三元组")
            
            _update_upload_status(job_id, "processing", 85, "正在构建知识图谱...", documentId=doc_id)
            
            # Step 4: Ingest into Neo4j
            print(f"\n💾 [步骤4] 开始构建知识图谱...")
            graph_service.ingest_triplets(doc_id, linked_triplets, root_topic=root_topic)
            print(f"✅ [步骤4] 知识图谱构建完成")
            
            # Get graph statistics
            concept_names = set(t.subject for t in linked_triplets) | set(t.object for t in linked_triplets)
            
            print(f"\n{'#'*80}")
            print(f"🎉 [文档处理] 处理完成!")
            print(f"   - 文本块数: {len(chunks)}")
            print(f"   - 知识三元组数: {len(linked_triplets)}")
            print(f"   - 概念数量: {len(concept_names)}")
            print(f"   - 文本总长度: {len(full_text)} 字符")
            print(f"{'#'*80}\n")
            
            stats = {
                "chunks": len(chunks),
                "triplets": len(linked_triplets),
                "concepts": len(concept_names),
                "textLength": len(full_text),
                "mode": "traditional"
            }
            _update_upload_status(job_id, "completed", 100, "知识图谱构建完成！", documentId=doc_id, stats=stats)
        
    except Exception as e:
        print(f"\n{'#'*80}")
        print(f"❌ [文档处理] 处理失败!")
        print(f"   - 错误信息: {str(e)}")
        import traceback
        error_trace = traceback.format_exc()
        print(f"   - 错误详情:\n{error_trace}")
        print(f"{'#'*80}\n")
        
        _update_upload_status(job_id, "failed", 0, f"处理失败: {str(e)}", documentId=doc_id, error=error_trace)


@router.post("/process", response_model=dict)
async def upload_and_process(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    auto_process: bool = True,
    chunk_size: int = 2000,
    enable_ai_segmentation: bool = False,
    user_prompt: Optional[str] = None,
    optimize_prompt: bool = True,
    root_topic: Optional[str] = None
):
    """
    一体化接口：上传文件并自动进行知识抽取和图谱构建。
    
    Args:
        file: 上传的文件
        auto_process: 是否自动处理（默认 True）
        chunk_size: 每个文本块的最大字符数（默认 2000，建议范围：1000-8000）
        enable_ai_segmentation: 启用AI智能分词（默认 False）
        user_prompt: 用户自定义分析提示词（可选）
        optimize_prompt: 是否用AI优化用户提示词（默认 True）
        root_topic: 主题根节点名称（可选），如果提供，文件内容将链接到此主题而不是文档
        
    Returns:
        {
            "documentId": "...",
            "filename": "...",
            "status": "uploaded" or "processing",
            "jobId": "..." (if auto_process=True)
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
            "message": "文档已存在"
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
    
    response = {
        "documentId": doc_id,
        "filename": file.filename,
        "checksum": checksum,
        "status": "uploaded",
        "path": file_path
    }
    
    # If auto_process is enabled, start background processing
    if auto_process and background_tasks:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        
        # Try to use RQ queue if available
        if queue.is_connected():
            job = queue.enqueue(
                process_document_background,
                doc_id,
                file_path,
                kind,
                job_id,
                chunk_size,
                enable_ai_segmentation,
                user_prompt,
                optimize_prompt,
                root_topic,
                job_timeout='1h'
            )
            
            if job:
                # Initialize job metadata
                job.meta = {
                    "status": "queued",
                    "documentId": doc_id,
                    "progress": 0,
                    "message": "等待处理..."
                }
                job.save()
                response["status"] = "processing"
                response["jobId"] = job.id
                response["message"] = "文档已上传，正在后台处理..."
                return response
        
        # Fallback to BackgroundTasks if Redis is not available
        _update_upload_status(job_id, "queued", 0, "等待处理...", documentId=doc_id)
        
        background_tasks.add_task(
            process_document_background,
            doc_id,
            file_path,
            kind,
            job_id,
            chunk_size,
            enable_ai_segmentation,
            user_prompt,
            optimize_prompt,
            root_topic
        )
        
        response["status"] = "processing"
        response["jobId"] = job_id
        response["message"] = "文档已上传，正在后台处理..."
    
    return response


@router.get("/status/{job_id}")
async def get_processing_status(job_id: str):
    """
    获取文档处理状态。
    
    Returns:
        {
            "status": "queued" | "processing" | "completed" | "failed",
            "documentId": "...",
            "progress": 0-100,
            "message": "...",
            "stats": {...} (if completed)
        }
    """
    # Try to get status from Redis first
    if queue.is_connected():
        status = queue.get_job_status(job_id)
        if status.get("status") != "not_found":
            return status
    
    # Fallback to in-memory storage
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return processing_jobs[job_id]


# Pydantic models for text and URL uploads
class TextUploadRequest(BaseModel):
    """Request model for text content upload."""
    content: str
    title: Optional[str] = None
    auto_process: bool = True
    chunk_size: int = 2000
    enable_ai_segmentation: bool = False
    user_prompt: Optional[str] = None
    optimize_prompt: bool = True
    root_topic: Optional[str] = None


class URLUploadRequest(BaseModel):
    """Request model for URL content upload."""
    url: str
    title: Optional[str] = None
    auto_process: bool = True
    chunk_size: int = 2000
    enable_ai_segmentation: bool = False
    user_prompt: Optional[str] = None
    optimize_prompt: bool = True
    root_topic: Optional[str] = None


@router.post("/text", response_model=dict)
async def upload_text(
    request: TextUploadRequest,
    background_tasks: BackgroundTasks
):
    """
    从文本内容创建文档并可选地自动处理。
    
    Args:
        content: 文本内容
        title: 文档标题（可选，默认使用前30个字符）
        auto_process: 是否自动处理（默认 True）
        chunk_size: 每个文本块的最大字符数（默认 2000）
        enable_ai_segmentation: 启用AI智能分词（默认 False）
        user_prompt: 用户自定义分析提示词（可选）
        optimize_prompt: 是否用AI优化用户提示词（默认 True）
        
    Returns:
        {
            "documentId": "...",
            "filename": "...",
            "status": "uploaded" or "processing",
            "jobId": "..." (if auto_process=True)
        }
    """
    # Validate chunk_size
    chunk_size = request.chunk_size
    if chunk_size < 100:
        raise HTTPException(status_code=400, detail="chunk_size 不能小于 100 字符")
    if chunk_size > 20000:
        raise HTTPException(status_code=400, detail="chunk_size 不能大于 20000 字符（建议不超过 8000）")
    
    # Validate AI segmentation
    if request.enable_ai_segmentation and not ai_segmenter:
        raise HTTPException(
            status_code=400, 
            detail="AI智能分词需要配置 OPENAI_API_KEY 环境变量"
        )
    
    content = request.content.strip()
    
    if not content:
        raise HTTPException(status_code=400, detail="文本内容不能为空")
    
    # Generate title from content if not provided
    title = request.title or content[:30].replace('\n', ' ') + "..."
    filename = f"{title}.txt"
    
    # Calculate checksum
    content_bytes = content.encode('utf-8')
    checksum = hashlib.sha256(content_bytes).hexdigest()
    
    # Check if document already exists
    existing_docs = neo4j_client.execute_query(
        "MATCH (d:Document {checksum: $checksum}) RETURN d.id as id LIMIT 1",
        {"checksum": checksum}
    )
    
    if existing_docs:
        return {
            "documentId": existing_docs[0]["id"],
            "filename": filename,
            "checksum": checksum,
            "status": "duplicate",
            "message": "相同内容的文档已存在"
        }
    
    # Save text as file
    file_path, _ = await storage.save_file(content_bytes, filename)
    
    # Create document ID
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    
    # Create document in Neo4j
    neo4j_client.create_document(
        doc_id=doc_id,
        filename=filename,
        checksum=checksum,
        kind="txt",
        size=len(content_bytes),
        mime="text/plain",
        meta={"path": file_path, "source": "text_input"}
    )
    
    response = {
        "documentId": doc_id,
        "filename": filename,
        "checksum": checksum,
        "status": "uploaded",
        "path": file_path
    }
    
    # Auto-process if enabled
    if request.auto_process:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        
        # Try to use RQ queue if available
        if queue.is_connected():
            job = queue.enqueue(
                process_document_background,
                doc_id,
                file_path,
                "txt",
                job_id,
                chunk_size,
                request.enable_ai_segmentation,
                request.user_prompt,
                request.optimize_prompt,
                request.root_topic,
                job_timeout='1h'
            )
            
            if job:
                # Initialize job metadata
                job.meta = {
                    "status": "queued",
                    "documentId": doc_id,
                    "progress": 0,
                    "message": "等待处理..."
                }
                job.save()
                response["status"] = "processing"
                response["jobId"] = job.id
                response["message"] = "文本已保存，正在后台处理..."
                return response
        
        # Fallback to BackgroundTasks if Redis is not available
        _update_upload_status(job_id, "queued", 0, "等待处理...", documentId=doc_id)
        
        background_tasks.add_task(
            process_document_background,
            doc_id,
            file_path,
            "txt",
            job_id,
            chunk_size,
            request.enable_ai_segmentation,
            request.user_prompt,
            request.optimize_prompt,
            request.root_topic
        )
        
        response["status"] = "processing"
        response["jobId"] = job_id
        response["message"] = "文本已保存，正在后台处理..."
    
    return response


@router.post("/url", response_model=dict)
async def upload_url(
    request: URLUploadRequest,
    background_tasks: BackgroundTasks
):
    """
    从网页URL抓取内容并创建文档。
    
    Args:
        url: 网页链接
        title: 文档标题（可选，默认使用URL）
        auto_process: 是否自动处理（默认 True）
        chunk_size: 每个文本块的最大字符数（默认 2000）
        enable_ai_segmentation: 启用AI智能分词（默认 False）
        user_prompt: 用户自定义分析提示词（可选）
        optimize_prompt: 是否用AI优化用户提示词（默认 True）
        
    Returns:
        {
            "documentId": "...",
            "filename": "...",
            "status": "uploaded" or "processing",
            "jobId": "..." (if auto_process=True)
        }
    """
    # Validate chunk_size
    chunk_size = request.chunk_size
    if chunk_size < 100:
        raise HTTPException(status_code=400, detail="chunk_size 不能小于 100 字符")
    if chunk_size > 20000:
        raise HTTPException(status_code=400, detail="chunk_size 不能大于 20000 字符（建议不超过 8000）")
    
    # Validate AI segmentation
    if request.enable_ai_segmentation and not ai_segmenter:
        raise HTTPException(
            status_code=400, 
            detail="AI智能分词需要配置 OPENAI_API_KEY 环境变量"
        )
    import httpx
    from bs4 import BeautifulSoup
    
    url = request.url.strip()
    
    if not url:
        raise HTTPException(status_code=400, detail="URL 不能为空")
    
    # Fetch webpage content
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            html_content = response.text
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=400,
            detail=f"无法访问该网页: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"抓取网页时出错: {str(e)}"
        )
    
    # Parse HTML and extract text
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Get page title
        page_title = soup.title.string if soup.title else None
        title = request.title or page_title or url
        
        # Extract text
        text_content = soup.get_text(separator='\n', strip=True)
        
        # Clean up text
        lines = [line.strip() for line in text_content.split('\n') if line.strip()]
        content = '\n'.join(lines)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"解析网页内容时出错: {str(e)}"
        )
    
    if not content or len(content) < 50:
        raise HTTPException(
            status_code=400,
            detail="网页内容过少或无法提取有效文本"
        )
    
    # Generate filename
    filename = f"{title[:50]}.txt"
    
    # Calculate checksum
    content_bytes = content.encode('utf-8')
    checksum = hashlib.sha256(content_bytes).hexdigest()
    
    # Check if document already exists
    existing_docs = neo4j_client.execute_query(
        "MATCH (d:Document {checksum: $checksum}) RETURN d.id as id LIMIT 1",
        {"checksum": checksum}
    )
    
    if existing_docs:
        return {
            "documentId": existing_docs[0]["id"],
            "filename": filename,
            "checksum": checksum,
            "status": "duplicate",
            "message": "相同内容的文档已存在"
        }
    
    # Save content as file
    file_path, _ = await storage.save_file(content_bytes, filename)
    
    # Create document ID
    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    
    # Create document in Neo4j
    neo4j_client.create_document(
        doc_id=doc_id,
        filename=filename,
        checksum=checksum,
        kind="txt",
        size=len(content_bytes),
        mime="text/plain",
        meta={"path": file_path, "source": "url", "original_url": url}
    )
    
    response = {
        "documentId": doc_id,
        "filename": filename,
        "checksum": checksum,
        "status": "uploaded",
        "path": file_path,
        "sourceUrl": url
    }
    
    # Auto-process if enabled
    if request.auto_process:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        
        # Try to use RQ queue if available
        if queue.is_connected():
            job = queue.enqueue(
                process_document_background,
                doc_id,
                file_path,
                "txt",
                job_id,
                chunk_size,
                request.enable_ai_segmentation,
                request.user_prompt,
                request.optimize_prompt,
                request.root_topic,
                job_timeout='1h'
            )
            
            if job:
                # Initialize job metadata
                job.meta = {
                    "status": "queued",
                    "documentId": doc_id,
                    "progress": 0,
                    "message": "等待处理..."
                }
                job.save()
                response["status"] = "processing"
                response["jobId"] = job.id
                response["message"] = "网页内容已抓取，正在后台处理..."
                return response
        
        # Fallback to BackgroundTasks if Redis is not available
        _update_upload_status(job_id, "queued", 0, "等待处理...", documentId=doc_id)
        
        background_tasks.add_task(
            process_document_background,
            doc_id,
            file_path,
            "txt",
            job_id,
            chunk_size,
            request.enable_ai_segmentation,
            request.user_prompt,
            request.optimize_prompt,
            request.root_topic
        )
        
        response["status"] = "processing"
        response["jobId"] = job_id
        response["message"] = "网页内容已抓取，正在后台处理..."
    
    return response

