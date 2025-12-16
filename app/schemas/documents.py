from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class DocumentOut(BaseModel):
    doc_id: int
    title: Optional[str] = None
    filename: Optional[str] = None
    mime_type: Optional[str] = None
    status: str
    tenant_id: int
    created_at: datetime

    owner_user_id: Optional[int] = None

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    doc_id: int
    version_id: int
    status: str
    job_id: int | None = None


class ProcessResponse(BaseModel):
    doc_id: int
    version_id: int
    status: str
    chunks: int
    embedded: int
    notes: Dict[str, Any] = {}
    error: Optional[str] = None
