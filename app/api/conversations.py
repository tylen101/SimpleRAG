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
    ChatMessageRecord,
)
from models.Models import Conversation, MessageCitation, Message
from services.ollama_client import OllamaClient
from services.retrieval_service import RetrievalService
from services.chat_service import ChatService
from core.config import settings

router = APIRouter()


# create new conversation if no conversation_id is provided
def create_conversation(
    db: Session,
    tenant_id: int,
    user_id: int,
    title: str | None = None,
    chat_model_id: str | str = settings.DEFAULT_CHAT_MODEL,
) -> Conversation:
    convo = Conversation(
        tenant_id=tenant_id,
        user_id=user_id,
        title=title or "New Conversation",
        chat_model_id=chat_model_id,
    )
    db.add(convo)
    db.flush()
    db.refresh(convo)
    return convo


@router.post("/conversations/{conversation_id}/messages", response_model=ChatMessageOut)
async def send_message(
    conversation_id: int,
    body: ChatMessageIn,
    db: Session = Depends(get_db),
    me=Depends(get_current_user),
):

    if conversation_id == 0:
        convo = create_conversation(
            db=db,
            tenant_id=me.tenant_id,
            user_id=me.user_id,
            chat_model_id=settings.DEFAULT_CHAT_MODEL,  # TODO
        )
        conversation_id = convo.conversation_id

    doc_ids = None
    if body.scope.mode == "selected":
        if not body.scope.doc_ids:
            raise HTTPException(400, "doc_ids must be provided when mode='selected'")
        doc_ids = body.scope.doc_ids

    k_vec = max(1, min(int(body.k_vec), 50))
    k_text = max(1, min(int(body.k_text), 50))

    ollama = OllamaClient(settings.OLLAMA_BASE_URL)
    retrieval = RetrievalService()
    chat = ChatService(ollama, retrieval)

    try:
        asst_msg, answer, citations_rows = await chat.chat(
            db=db,
            tenant_id=me.tenant_id,
            user_id=me.user_id,
            conversation_id=conversation_id,
            user_text=body.content,
            doc_ids=doc_ids,
            k_vec=k_vec,
            k_text=k_text,
            use_text=body.use_text,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Chat failed: {e}")

    citations = [
        Citation(
            chunk_id=c.chunk_id,
            doc_id=c.doc_id,
            page_start=c.page_start,
            page_end=c.page_end,
            section_path=c.section_path,
            score=float(c.score or 0.0),
        )
        for c in (citations_rows or [])
    ]

    return ChatMessageOut(
        conversation_id=conversation_id,
        message_id=asst_msg.message_id,
        answer=answer,
        citations=citations,
    )


@router.get(
    "/conversations/{conversation_id}/messages", response_model=list[ChatMessageRecord]
)
def list_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    me=Depends(get_current_user),
):
    convo = (
        db.query(Conversation)
        .filter(
            Conversation.conversation_id == conversation_id,
            Conversation.tenant_id == me.tenant_id,
            Conversation.user_id == me.user_id,
        )
        .first()
    )
    if not convo:
        raise HTTPException(404, "Conversation not found")

    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )

    msg_ids = [m.message_id for m in msgs]
    cits = (
        db.query(MessageCitation).filter(MessageCitation.message_id.in_(msg_ids)).all()
    )

    cits_by_msg: dict[int, list[MessageCitation]] = {}
    for c in cits:
        cits_by_msg.setdefault(c.message_id, []).append(c)

    out = []
    for m in msgs:
        citations = [
            Citation(
                chunk_id=c.chunk_id,
                doc_id=c.doc_id,
                page_start=c.page_start,
                page_end=c.page_end,
                section_path=c.section_path,
                score=float(c.score or 0.0),
            )
            for c in sorted(
                cits_by_msg.get(m.message_id, []),
                key=lambda x: (x.score or 0),
                reverse=True,
            )
        ]
        out.append(
            ChatMessageRecord(
                message_id=m.message_id,
                role=m.role,
                content=m.content,
                citations=citations if m.role == "assistant" else [],
            )
        )

    return out
