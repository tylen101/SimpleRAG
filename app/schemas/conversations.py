from pydantic import BaseModel
from typing import Optional, List


class ConversationCreate(BaseModel):
    chat_model_id: Optional[str] = None
    title: Optional[str] = None


class ConversationOut(BaseModel):
    conversation_id: int
    chat_model_id: str
    title: Optional[str] = None


class ChatScope(BaseModel):
    mode: str = "all"  # "all" or "selected"
    doc_ids: List[int] = []


class ChatMessageIn(BaseModel):
    content: str
    scope: ChatScope = ChatScope()
    k_vec: int = 8
    k_text: int = 6
    use_text: bool = True


class Citation(BaseModel):
    chunk_id: int
    doc_id: int
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    section_path: Optional[str] = None
    score: float


class ChatMessageOut(BaseModel):
    message_id: int
    answer: str
    citations: List[Citation]
