from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1)
    doc_ids: Optional[List[int]] = None

    # retrieval knobs
    k_vec: int = 10
    k_text: int = 10
    use_text: bool = True
    alpha: float = 0.70  # weight vector similarity more than text

    # future: filters
    # mime_types: Optional[List[str]] = None


class RetrievedChunk(BaseModel):
    chunk_id: int
    doc_id: int
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    section_path: Optional[str] = None
    chunk_text: str

    source: str
    vector_distance: Optional[float] = None
    vector_similarity: Optional[float] = None
    text_score: Optional[float] = None
    text_norm: Optional[float] = None
    hybrid_score: Optional[float] = None


class RetrieveResponse(BaseModel):
    query: str
    tenant_id: int
    doc_ids: Optional[List[int]] = None
    results: List[RetrievedChunk]
    debug: Dict[str, Any] = {}
