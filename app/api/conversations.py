from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.db import get_db
from core.deps import get_current_user
from core.config import settings
from schemas.conversations import (
    ConversationCreate,
    ConversationOut,
    ChatMessageIn,
    ChatMessageOut,
    Citation,
)
from models.Models import Conversation
from services.ollama_client import OllamaClient
from services.retrieval_service import RetrievalService
from services.chat_service import ChatService

router = APIRouter()


@router.post("/conversations", response_model=ConversationOut)
def create_conversation(
    body: ConversationCreate,
    db: Session = Depends(get_db),
    me=Depends(get_current_user),
):
    # me = {"user_id": 1, "tenant_id": 1}
    print("getting convo for ", me.user_id)
    convo = Conversation(
        tenant_id=me.tenant_id,
        user_id=me.user_id,
        chat_model_id=body.chat_model_id or settings.DEFAULT_CHAT_MODEL,
        title=body.title,
    )
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return ConversationOut(
        conversation_id=convo.conversation_id,
        chat_model_id=convo.chat_model_id,
        title=convo.title,
    )


@router.post("/conversations/{conversation_id}/messages", response_model=ChatMessageOut)
async def send_message(
    conversation_id: int,
    body: ChatMessageIn,
    db: Session = Depends(get_db),
    me=Depends(get_current_user),
):
    doc_ids = None
    if body.scope.mode == "selected":
        doc_ids = body.scope.doc_ids

    ollama = OllamaClient(settings.OLLAMA_BASE_URL)
    retrieval = RetrievalService()
    chat = ChatService(ollama, retrieval)

    try:
        msg, answer, hits = await chat.chat(
            db=db,
            tenant_id=me.tenant_id,
            user_id=me.user_id,
            conversation_id=conversation_id,
            user_text=body.content,
            doc_ids=doc_ids,
            k_vec=body.k_vec,
            k_text=body.k_text,
            use_text=body.use_text,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))

    citations = [
        Citation(
            chunk_id=h["chunk_id"],
            doc_id=h["doc_id"],
            page_start=h.get("page_start"),
            page_end=h.get("page_end"),
            section_path=h.get("section_path"),
            score=float(h["score"]),
        )
        for h in hits
    ]
    return ChatMessageOut(message_id=msg.message_id, answer=answer, citations=citations)
