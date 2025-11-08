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

router = APIRouter(prefix="/uploads", tags=["uploads"])

storage = Storage()
extractor = TripletExtractor()
linker = EntityLinker()
graph_service = GraphService()

# Job storage for tracking processing status
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


def process_document_background(doc_id: str, file_path: str, kind: str, job_id: str):
    """Background task for processing document into knowledge graph."""
    processing_jobs[job_id] = {
        "status": "processing",
        "documentId": doc_id,
        "progress": 0,
        "message": "开始处理文档..."
    }
    
    try:
        print(f"\n{'#'*80}")
        print(f"🚀 [文档处理] 开始处理文档")
        print(f"   - 文档ID: {doc_id}")
        print(f"   - 文件路径: {file_path}")
        print(f"   - 文件类型: {kind}")
        print(f"   - 任务ID: {job_id}")
        print(f"{'#'*80}\n")
        
        # Step 1: Parse document
        processing_jobs[job_id]["message"] = "正在解析文档..."
        processing_jobs[job_id]["progress"] = 10
        
        print(f"📖 [步骤1] 解析文档...")
        parser = ParserFactory.create_parser(kind)
        full_text, chunks = parser.parse(file_path)
        print(f"✅ [步骤1] 解析完成: {len(chunks)} 个文本块，总长度 {len(full_text)} 字符")
        
        processing_jobs[job_id]["message"] = f"已提取 {len(chunks)} 个文本块，正在进行知识抽取..."
        processing_jobs[job_id]["progress"] = 30
        
        # Step 2: Extract triplets using AI
        print(f"\n🤖 [步骤2] 开始知识抽取 (共 {len(chunks)} 个文本块)...")
        all_triplets = []
        chunk_triplet_counts = []
        
        for i, chunk in enumerate(chunks, 1):
            print(f"\n📦 [文本块 {i}/{len(chunks)}] 处理中...")
            triplets = extractor.extract(chunk)
            all_triplets.extend(triplets)
            chunk_triplet_counts.append(len(triplets))
            processing_jobs[job_id]["progress"] = 30 + int((i / len(chunks)) * 40)
            processing_jobs[job_id]["message"] = f"正在抽取知识... ({i}/{len(chunks)})"
        
        print(f"\n📊 [步骤2] 知识抽取完成:")
        print(f"   - 总三元组数: {len(all_triplets)}")
        print(f"   - 各文本块三元组数: {chunk_triplet_counts}")
        print(f"   - 平均每个文本块: {len(all_triplets) / len(chunks) if chunks else 0:.2f} 个三元组")
        
        processing_jobs[job_id]["message"] = f"已抽取 {len(all_triplets)} 个知识三元组，正在链接实体..."
        processing_jobs[job_id]["progress"] = 70
        
        # Step 3: Link and merge entities
        print(f"\n🔗 [步骤3] 开始实体链接和合并...")
        linked_triplets = linker.link_and_merge(all_triplets)
        print(f"✅ [步骤3] 实体链接完成: {len(linked_triplets)} 个三元组")
        
        processing_jobs[job_id]["message"] = "正在构建知识图谱..."
        processing_jobs[job_id]["progress"] = 85
        
        # Step 4: Ingest into Neo4j
        print(f"\n💾 [步骤4] 开始构建知识图谱...")
        graph_service.ingest_triplets(doc_id, linked_triplets)
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
        
        processing_jobs[job_id]["status"] = "completed"
        processing_jobs[job_id]["progress"] = 100
        processing_jobs[job_id]["message"] = "知识图谱构建完成！"
        processing_jobs[job_id]["stats"] = {
            "chunks": len(chunks),
            "triplets": len(linked_triplets),
            "concepts": len(concept_names),
            "textLength": len(full_text)
        }
        
    except Exception as e:
        print(f"\n{'#'*80}")
        print(f"❌ [文档处理] 处理失败!")
        print(f"   - 错误信息: {str(e)}")
        import traceback
        error_trace = traceback.format_exc()
        print(f"   - 错误详情:\n{error_trace}")
        print(f"{'#'*80}\n")
        
        processing_jobs[job_id]["status"] = "failed"
        processing_jobs[job_id]["message"] = f"处理失败: {str(e)}"
        processing_jobs[job_id]["progress"] = 0
        processing_jobs[job_id]["error"] = error_trace


@router.post("/process", response_model=dict)
async def upload_and_process(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    auto_process: bool = True
):
    """
    一体化接口：上传文件并自动进行知识抽取和图谱构建。
    
    Args:
        file: 上传的文件
        auto_process: 是否自动处理（默认 True）
        
    Returns:
        {
            "documentId": "...",
            "filename": "...",
            "status": "uploaded" or "processing",
            "jobId": "..." (if auto_process=True)
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
        processing_jobs[job_id] = {
            "status": "queued",
            "documentId": doc_id,
            "progress": 0,
            "message": "等待处理..."
        }
        
        background_tasks.add_task(
            process_document_background,
            doc_id,
            file_path,
            kind,
            job_id
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
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return processing_jobs[job_id]


# Pydantic models for text and URL uploads
class TextUploadRequest(BaseModel):
    """Request model for text content upload."""
    content: str
    title: Optional[str] = None
    auto_process: bool = True


class URLUploadRequest(BaseModel):
    """Request model for URL content upload."""
    url: str
    title: Optional[str] = None
    auto_process: bool = True


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
        
    Returns:
        {
            "documentId": "...",
            "filename": "...",
            "status": "uploaded" or "processing",
            "jobId": "..." (if auto_process=True)
        }
    """
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
        processing_jobs[job_id] = {
            "status": "queued",
            "documentId": doc_id,
            "progress": 0,
            "message": "等待处理..."
        }
        
        background_tasks.add_task(
            process_document_background,
            doc_id,
            file_path,
            "txt",
            job_id
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
        
    Returns:
        {
            "documentId": "...",
            "filename": "...",
            "status": "uploaded" or "processing",
            "jobId": "..." (if auto_process=True)
        }
    """
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
        processing_jobs[job_id] = {
            "status": "queued",
            "documentId": doc_id,
            "progress": 0,
            "message": "等待处理..."
        }
        
        background_tasks.add_task(
            process_document_background,
            doc_id,
            file_path,
            "txt",
            job_id
        )
        
        response["status"] = "processing"
        response["jobId"] = job_id
        response["message"] = "网页内容已抓取，正在后台处理..."
    
    return response

