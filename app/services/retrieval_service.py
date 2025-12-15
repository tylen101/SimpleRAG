import array
import math
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Tuple
import re


_ORA_TEXT_BAD = re.compile(r"""[(){}\[\]"'~|&!?:\\/]""")


class RetrievalService:
    def _doc_filter_sql(self, doc_ids: Optional[List[int]]) -> Tuple[str, dict]:
        if doc_ids is None:
            return "1=1", {}
        if len(doc_ids) == 0:
            # caller explicitly passed empty list -> match nothing
            return "1=0", {}

        binds = {}
        placeholders = []
        for i, d in enumerate(doc_ids):
            key = f"d{i}"
            placeholders.append(f":{key}")
            binds[key] = int(d)
        return f"c.doc_id IN ({', '.join(placeholders)})", binds

    def vector_search(
        self,
        db: Session,
        tenant_id: int,
        query_vec: List[float],
        doc_ids: Optional[List[int]],
        k: int,
        embedding_model_id: str = "qwen3-embedding",
        embedding_dim: int = 4096,
    ) -> List[Dict[str, Any]]:
        doc_filter_sql, doc_binds = self._doc_filter_sql(doc_ids)

        sql = text(
            f"""
        SELECT * FROM (
          SELECT
            c.chunk_id,
            c.doc_id,
            c.page_start,
            c.page_end,
            c.section_path,
            c.chunk_text,
            VECTOR_DISTANCE(e.embedding, :query_vec, COSINE) AS vector_distance
          FROM chunk_embeddings e
          JOIN document_chunks c ON c.chunk_id = e.chunk_id
          WHERE e.tenant_id = :tenant_id
            AND c.tenant_id = :tenant_id
            AND e.embedding_model_id = :embedding_model_id
            AND e.embedding_dim = :embedding_dim
            AND {doc_filter_sql}
          ORDER BY vector_distance ASC
        )
        WHERE ROWNUM <= :k
        """
        )

        vec = array.array("f", query_vec)
        params = {
            "tenant_id": tenant_id,
            "query_vec": vec,
            "k": int(k),
            "embedding_model_id": embedding_model_id,
            "embedding_dim": int(embedding_dim),
            **doc_binds,
        }
        rows = db.execute(sql, params).mappings().all()
        out = []
        for r in rows:
            d = dict(r)
            d["source"] = "vector"
            out.append(d)
        return out

    def text_search(
        self,
        db: Session,
        tenant_id: int,
        query: str,
        doc_ids: Optional[List[int]],
        k: int,
    ) -> List[Dict[str, Any]]:
        doc_filter_sql, doc_binds = self._doc_filter_sql(doc_ids)

        oracle_q = self._oracle_text_query(query)
        if not oracle_q:
            return []
        # Note: SCORE(1) requires the CONTAINS label "1"
        sql = text(
            f"""
        SELECT * FROM (
          SELECT
            c.chunk_id,
            c.doc_id,
            c.page_start,
            c.page_end,
            c.section_path,
            c.chunk_text,
            SCORE(1) AS text_score
          FROM document_chunks c
          WHERE c.tenant_id = :tenant_id
            AND {doc_filter_sql}
            AND CONTAINS(c.chunk_text, :q, 1) > 0
          ORDER BY text_score DESC
        )
        WHERE ROWNUM <= :k
        """
        )

        params = {"tenant_id": tenant_id, "q": oracle_q, "k": int(k), **doc_binds}
        rows = db.execute(sql, params).mappings().all()
        out = []
        for r in rows:
            d = dict(r)
            d["source"] = "text"
            out.append(d)
        return out

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
        alpha: float = 0.70,  # weight vector similarity more by default
    ) -> List[Dict[str, Any]]:
        vec_results = self.vector_search(db, tenant_id, query_vec, doc_ids, k_vec)
        text_results = (
            self.text_search(db, tenant_id, query_text, doc_ids, k_text)
            if use_text
            else []
        )

        merged: Dict[int, Dict[str, Any]] = {}

        for r in vec_results:
            cid = int(r["chunk_id"])
            merged[cid] = r

        for r in text_results:
            cid = int(r["chunk_id"])
            if cid in merged:
                merged[cid]["text_score"] = float(r["text_score"])
                merged[cid]["source"] = "hybrid"
            else:
                merged[cid] = r

        # Normalize + combine
        # vector_similarity = 1/(1+distance) -> [0..1]
        # text_norm = log(1+score) scaled by max in this result set
        max_log_text = 0.0
        for v in merged.values():
            ts = v.get("text_score")
            if ts is not None:
                max_log_text = max(max_log_text, math.log1p(float(ts)))
        if max_log_text <= 0:
            max_log_text = 1.0

        for v in merged.values():
            dist = v.get("vector_distance")
            if dist is not None:
                vs = 1.0 / (1.0 + float(dist))
            else:
                vs = 0.0

            ts = v.get("text_score")
            if ts is not None:
                tn = math.log1p(float(ts)) / max_log_text
            else:
                tn = 0.0

            v["vector_similarity"] = vs
            v["text_norm"] = tn
            v["hybrid_score"] = alpha * vs + (1.0 - alpha) * tn

        out = list(merged.values())
        out.sort(key=lambda x: float(x.get("hybrid_score", 0.0)), reverse=True)
        return out[: max(k_vec, k_text)]

    def _oracle_text_query(self, user_query: str) -> str:
        """
        Convert free text into a safe Oracle Text CONTAINS query.
        """
        q = (user_query or "").strip().lower()
        q = _ORA_TEXT_BAD.sub(" ", q)
        q = re.sub(r"\s+", " ", q).strip()
        if not q:
            return ""

        tokens = [t for t in q.split(" ") if t and len(t) > 1]
        if not tokens:
            return ""

        # AND tokens is conservative and avoids parser issues
        return " AND ".join(tokens)
