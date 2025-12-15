from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.db import get_db
from core.deps import get_current_user
from models.Models import DocumentChunk
from schemas.chunks import ChunkBatchIn, ChunkOut

router = APIRouter()


@router.post("/chunks/batch", response_model=list[ChunkOut])
def get_chunks_batch(
    body: ChunkBatchIn,
    db: Session = Depends(get_db),
    me=Depends(get_current_user),
):
    chunk_ids = [int(x) for x in (body.chunk_ids or []) if int(x) > 0]
    if not chunk_ids:
        return []

    max_chars = int(body.max_chars or 2000)
    max_chars = max(200, min(max_chars, 10000))

    rows = (
        db.query(DocumentChunk)
        .filter(
            DocumentChunk.tenant_id == me.tenant_id,
            DocumentChunk.chunk_id.in_(chunk_ids),
        )
        .all()
    )

    # Return in the same order requested
    by_id = {r.chunk_id: r for r in rows}
    out: list[ChunkOut] = []
    for cid in chunk_ids:
        r = by_id.get(cid)
        if not r:
            continue
        txt = r.chunk_text or ""
        if len(txt) > max_chars:
            txt = txt[:max_chars].rstrip() + "…"
        out.append(
            ChunkOut(
                chunk_id=r.chunk_id,
                doc_id=r.doc_id,
                page_start=r.page_start,
                page_end=r.page_end,
                section_path=r.section_path,
                chunk_text=txt,
            )
        )
    return out
