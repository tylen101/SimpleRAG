from __future__ import annotations

import json
import array
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import text

from models.Models import (
    Document,
    DocumentVersion,
    DocumentBlob,
    DocumentText,
    DocumentChunk,
    ChunkEmbedding,
)
from services.extraction_service import extract_text
from services.chunking_service import chunk_extracted, ChunkSpec
from services.embedding_service import EmbeddingService


class IngestPipeline:
    """
    Synchronous ingestion pipeline for MVP:
      blob -> extract -> document_text -> chunks -> embeddings -> ready/failed
    """

    def load_latest_version(self, db: Session, doc_id: int) -> DocumentVersion:
        ver = (
            db.query(DocumentVersion)
            .filter(DocumentVersion.doc_id == doc_id)
            .order_by(DocumentVersion.version_num.desc())
            .first()
        )
        if not ver:
            raise ValueError("No document_versions found for doc_id")
        return ver

    def load_blob_bytes(self, db: Session, version_id: int) -> bytes:
        blob = db.get(DocumentBlob, version_id)
        if not blob or not blob.blob_data:
            raise ValueError("document_blobs missing or empty for version_id")
        return blob.blob_data

    def upsert_document_text(
        self,
        db: Session,
        version_id: int,
        extracted_text: str,
        structure: Dict[str, Any],
    ) -> None:
        row = db.get(DocumentText, version_id)
        payload_structure = json.dumps(structure)
        if row:
            row.extracted_text = extracted_text
            row.structure_json = payload_structure
        else:
            db.add(
                DocumentText(
                    version_id=version_id,
                    extracted_text=extracted_text,
                    structure_json=payload_structure,
                )
            )

    def upsert_chunks(
        self,
        db: Session,
        tenant_id: int,
        doc_id: int,
        version_id: int,
        chunk_specs: List[ChunkSpec],
    ) -> List[DocumentChunk]:
        """
        Upsert by (version_id, chunk_index).
        Returns the persisted DocumentChunk rows (with chunk_id populated).
        """
        out: List[DocumentChunk] = []
        for spec in chunk_specs:
            existing = (
                db.query(DocumentChunk)
                .filter(
                    DocumentChunk.version_id == version_id,
                    DocumentChunk.chunk_index == spec.chunk_index,
                )
                .first()
            )
            if existing:
                existing.doc_id = doc_id
                existing.tenant_id = tenant_id
                existing.page_start = spec.page_start
                existing.page_end = spec.page_end
                existing.section_path = spec.section_path
                existing.token_count = spec.token_count
                existing.chunk_text = spec.chunk_text
                out.append(existing)
            else:
                row = DocumentChunk(
                    version_id=version_id,
                    doc_id=doc_id,
                    tenant_id=tenant_id,
                    chunk_index=spec.chunk_index,
                    page_start=spec.page_start,
                    page_end=spec.page_end,
                    section_path=spec.section_path,
                    token_count=spec.token_count,
                    chunk_text=spec.chunk_text,
                )
                db.add(row)
                out.append(row)

        db.flush()  # assign chunk_id for new rows
        return out

    async def embed_and_persist(
        self,
        db: Session,
        tenant_id: int,
        chunks: List[DocumentChunk],
        embedding_service: EmbeddingService,
    ) -> int:
        """
        Inserts embeddings via raw SQL (VECTOR binding) for any chunk missing an embedding.
        Returns count inserted.
        """
        inserted = 0
        insert_sql = text(
            """
            INSERT INTO chunk_embeddings
              (chunk_id, tenant_id, embedding_model_id, embedding_dim, embedding, created_at)
            VALUES
              (:chunk_id, :tenant_id, :embedding_model_id, :embedding_dim, :embedding, SYSTIMESTAMP)
        """
        )

        # You *can* check via ORM mapping, but use EXISTS query for speed if you want later.
        for ch in chunks:
            exists = db.get(ChunkEmbedding, ch.chunk_id)
            if exists:
                continue

            vec = await embedding_service.embed_text(ch.chunk_text)
            vec_arr = array.array("f", vec)

            db.execute(
                insert_sql,
                {
                    "chunk_id": ch.chunk_id,
                    "tenant_id": tenant_id,
                    "embedding_model_id": "qwen3-embedding",
                    "embedding_dim": 4096,
                    "embedding": vec_arr,
                },
            )
            inserted += 1

        return inserted

    async def process_document(
        self,
        db: Session,
        tenant_id: int,
        doc_id: int,
        embedding_service: EmbeddingService,
        max_chars: int = 5000,
    ) -> Dict[str, Any]:
        """
        Runs full ingestion for latest version of a doc.
        """
        doc = db.get(Document, doc_id)
        if not doc or doc.tenant_id != tenant_id:
            raise ValueError("Document not found")

        # Set processing state
        doc.status = "processing"

        try:
            version = self.load_latest_version(db, doc_id)
            file_bytes = self.load_blob_bytes(db, version.version_id)

            extracted = extract_text(file_bytes=file_bytes, mime_type=doc.mime_type)

            # Persist canonical extracted text
            self.upsert_document_text(
                db=db,
                version_id=version.version_id,
                extracted_text=extracted.full_text,
                structure=extracted.structure,
            )

            # Chunk
            chunk_specs = chunk_extracted(extracted, max_chars=max_chars)
            chunk_rows = self.upsert_chunks(
                db=db,
                tenant_id=tenant_id,
                doc_id=doc_id,
                version_id=version.version_id,
                chunk_specs=chunk_specs,
            )

            # Embeddings
            embedded_count = await self.embed_and_persist(
                db=db,
                tenant_id=tenant_id,
                chunks=chunk_rows,
                embedding_service=embedding_service,
            )

            # Finalize
            doc.status = "ready"
            db.commit()

            return {
                "doc_id": doc_id,
                "version_id": version.version_id,
                "status": doc.status,
                "chunks": len(chunk_rows),
                "embedded": embedded_count,
                "notes": {
                    "method": extracted.method,
                    "ocr_needed": extracted.structure.get("extraction", {}).get(
                        "ocr_needed", False
                    ),
                    "stats": extracted.structure.get("stats", {}),
                },
            }

        except Exception as e:
            db.rollback()
            # mark failed
            doc = db.get(Document, doc_id)
            if doc:
                doc.status = "failed"
                db.commit()
            return {
                "doc_id": doc_id,
                "version_id": None,
                "status": "failed",
                "chunks": 0,
                "embedded": 0,
                "notes": {},
                "error": str(e),
            }
