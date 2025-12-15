SELECT
  c.chunk_id,
  c.doc_id,
  c.page_start,
  c.page_end,
  c.section_path,
  c.chunk_text,
  VECTOR_DISTANCE(e.embedding, :query_vec, COSINE) AS dist
FROM chunk_embeddings e
JOIN document_chunks c ON c.chunk_id = e.chunk_id
WHERE e.tenant_id = :tenant_id
  AND (:doc_id IS NULL OR c.doc_id = :doc_id)
ORDER BY dist
FETCH FIRST :k ROWS ONLY;
