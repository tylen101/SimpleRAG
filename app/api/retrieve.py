from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.db import get_db
from core.deps import get_current_user
from core.config import settings

from services.ollama_client import OllamaClient
from services.embedding_service import EmbeddingService
from services.retrieval_service import RetrievalService

from schemas.retrieval import RetrieveRequest, RetrieveResponse, RetrievedChunk


router = APIRouter()


@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve(
    payload: RetrieveRequest,
    db: Session = Depends(get_db),
    me=Depends(get_current_user),
):
    q = payload.query.strip()
    if not q:
        raise HTTPException(400, "query must not be empty")

    # 1) Embed the query using the same embedding model used for chunks
    ollama = OllamaClient(settings.OLLAMA_BASE_URL)
    emb = EmbeddingService(ollama)

    try:
        query_vec = await emb.embed_text(q)
    except Exception as e:
        raise HTTPException(502, f"Embedding provider error: {e}")

    # 2) Retrieve (hybrid)
    svc = RetrievalService()
    try:
        results = svc.hybrid_search(
            db=db,
            tenant_id=me.tenant_id,
            query_vec=query_vec,
            query_text=q,
            doc_ids=payload.doc_ids,
            k_vec=payload.k_vec,
            k_text=payload.k_text,
            use_text=payload.use_text,
            alpha=payload.alpha,
        )
    except Exception as e:
        raise HTTPException(500, f"Retrieval failed: {e}")

    return RetrieveResponse(
        query=q,
        tenant_id=me.tenant_id,
        doc_ids=payload.doc_ids,
        results=[RetrievedChunk(**r) for r in results],
        debug={
            "k_vec": payload.k_vec,
            "k_text": payload.k_text,
            "use_text": payload.use_text,
            "alpha": payload.alpha,
        },
    )
