from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from core.db import get_db
from core.deps import get_current_user
from schemas.documents import DocumentOut, UploadResponse
from services.ingestion_service import IngestionService
from models.Models import Document
from schemas.documents import ProcessResponse
from services.ollama_client import OllamaClient
from services.embedding_service import EmbeddingService
from services.ingest_pipeline import IngestPipeline
from services.job_service import JobService

from core.config import settings


router = APIRouter()


@router.post("/documents", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    db: Session = Depends(get_db),
    me=Depends(get_current_user),
):

    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")

    svc = IngestionService()
    doc, ver = svc.create_document_with_version(
        db=db,
        tenant_id=me.tenant_id,
        owner_user_id=me.user_id,
        filename=file.filename,
        mime_type=file.content_type,
        title=title,
        file_bytes=data,
    )
    job = JobService().enqueue_ingest(db, tenant_id=me.tenant_id, doc_id=doc.doc_id)
    print(job)
    return UploadResponse(
        doc_id=doc.doc_id,
        version_id=ver.version_id,
        status=doc.status,
        job_id=job.job_id,
    )


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    me=Depends(get_current_user),
):
    print("getting docs for ", me.user_id)

    docs = (
        db.query(Document)
        .filter(Document.tenant_id == me.tenant_id)
        .order_by(Document.created_at.desc())
        .all()
    )
    return [
        DocumentOut(
            doc_id=d.doc_id,
            title=d.title,
            filename=d.filename,
            mime_type=d.mime_type,
            sha256=d.sha256,
            status=d.status,
        )
        for d in docs
    ]


@router.post("/documents/{doc_id}/process", response_model=ProcessResponse)
async def process_document(
    doc_id: int,
    db: Session = Depends(get_db),
    me=Depends(get_current_user),
):
    ollama = OllamaClient(settings.OLLAMA_BASE_URL)
    emb = EmbeddingService(ollama)
    pipeline = IngestPipeline()

    result = await pipeline.process_document(
        db=db,
        tenant_id=me.tenant_id,
        doc_id=doc_id,
        embedding_service=emb,
        max_chars=5000,
    )

    # result["version_id"] might be None on failure
    return ProcessResponse(
        doc_id=result["doc_id"],
        version_id=result.get("version_id") or 0,
        status=result["status"],
        chunks=result["chunks"],
        embedded=result["embedded"],
        notes=result.get("notes") or {},
        error=result.get("error"),
    )
