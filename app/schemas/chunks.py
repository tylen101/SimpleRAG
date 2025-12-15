from pydantic import BaseModel, Field
from typing import List, Optional


class ChunkBatchIn(BaseModel):
    chunk_ids: List[int] = Field(default_factory=list)
    max_chars: int = 2000


class ChunkOut(BaseModel):
    chunk_id: int
    doc_id: int
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    section_path: Optional[str] = None
    chunk_text: str
