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
  AND (:doc_filter_off = 1 OR c.doc_id IN (SELECT column_value FROM TABLE(:doc_ids)))
  AND CONTAINS(c.chunk_text, :q, 1) > 0
ORDER BY text_score DESC
FETCH FIRST :k_text ROWS ONLY



-- Pull k_vec from vector + k_text from text

-- Deduplicate by chunk_id
