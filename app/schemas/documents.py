from pydantic import BaseModel
from typing import Optional, Dict, Any


class DocumentOut(BaseModel):
    doc_id: int
    title: Optional[str] = None
    filename: Optional[str] = None
    mime_type: Optional[str] = None
    sha256: str
    status: str


class UploadResponse(BaseModel):
    doc_id: int
    version_id: int
    status: str


class ProcessResponse(BaseModel):
    doc_id: int
    version_id: int
    status: str
    chunks: int
    embedded: int
    notes: Dict[str, Any] = {}
    error: Optional[str] = None
