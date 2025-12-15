import array
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional


class RetrievalService:
    def _doc_filter_sql(self, doc_ids: Optional[List[int]]) -> tuple[str, dict]:
        if not doc_ids:
            return "1=1", {}
        binds = {}
        placeholders = []
        for i, d in enumerate(doc_ids):
            key = f"d{i}"
            placeholders.append(f":{key}")
            binds[key] = d
        return f"c.doc_id IN ({','.join(placeholders)})", binds

    def vector_search(
        self,
        db: Session,
        tenant_id: int,
        query_vec: List[float],
        doc_ids: Optional[List[int]],
        k: int,
    ) -> List[Dict[str, Any]]:
        doc_filter_sql, doc_binds = self._doc_filter_sql(doc_ids)

        # VECTOR_DISTANCE(...) function name/syntax may vary by your exact Oracle build/config.

        sql = text(
            f"""
        SELECT
          c.chunk_id,
          c.doc_id,
          c.page_start,
          c.page_end,
          c.section_path,
          c.chunk_text,
          VECTOR_DISTANCE(e.embedding, :query_vec, COSINE) AS score
        FROM chunk_embeddings e
        JOIN document_chunks c ON c.chunk_id = e.chunk_id
        WHERE e.tenant_id = :tenant_id
          AND c.tenant_id = :tenant_id
          AND {doc_filter_sql}
        ORDER BY score
        FETCH FIRST :k ROWS ONLY
        """
        )

        vec = array.array("f", query_vec)
        params = {"tenant_id": tenant_id, "query_vec": vec, "k": k, **doc_binds}
        rows = db.execute(sql, params).mappings().all()
        return [dict(r) for r in rows]

    def text_search(
        self,
        db: Session,
        tenant_id: int,
        query: str,
        doc_ids: Optional[List[int]],
        k: int,
    ) -> List[Dict[str, Any]]:
        doc_filter_sql, doc_binds = self._doc_filter_sql(doc_ids)

        sql = text(
            f"""
        SELECT
          c.chunk_id,
          c.doc_id,
          c.page_start,
          c.page_end,
          c.section_path,
          c.chunk_text,
          SCORE(1) AS score
        FROM document_chunks c
        WHERE c.tenant_id = :tenant_id
          AND {doc_filter_sql}
          AND CONTAINS(c.chunk_text, :q, 1) > 0
        ORDER BY score DESC
        FETCH FIRST :k ROWS ONLY
        """
        )

        params = {"tenant_id": tenant_id, "q": query, "k": k, **doc_binds}
        rows = db.execute(sql, params).mappings().all()
        return [dict(r) for r in rows]

    def hybrid_search(
        self,
        db: Session,
        tenant_id: int,
        query_vec: List[float],
        query_text: str,
        doc_ids: Optional[List[int]],
        k_vec: int,
        k_text: int,
        use_text: bool = True,
    ) -> List[Dict[str, Any]]:
        vec_results = self.vector_search(db, tenant_id, query_vec, doc_ids, k_vec)
        text_results = (
            self.text_search(db, tenant_id, query_text, doc_ids, k_text)
            if use_text
            else []
        )

        merged: Dict[int, Dict[str, Any]] = {}

        # For vector results: smaller distance is better; keep as-is for now.
        for r in vec_results:
            merged[r["chunk_id"]] = {**r, "source": "vector"}

        # For text results: larger score is better.
        for r in text_results:
            cid = r["chunk_id"]
            if cid in merged:
                # keep both scores
                merged[cid]["text_score"] = float(r["score"])
            else:
                merged[cid] = {**r, "source": "text"}

        # Basic ordering: prefer vector source, then distance ascending; text-only after.
        def sort_key(item: Dict[str, Any]):
            src = item.get("source")
            if src == "vector":
                return (0, float(item.get("score", 1e9)))
            return (1, -float(item.get("score", 0)))

        out = list(merged.values())
        out.sort(key=sort_key)
        return out[: max(k_vec, k_text)]
