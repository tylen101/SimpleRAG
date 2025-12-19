from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.db import get_db
from core.deps import get_current_user, get_current_user_ws
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

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from core.db import get_db
from core.config import settings
from schemas.conversations import Citation
from services.ollama_client import OllamaClient
from services.retrieval_service import RetrievalService
from services.chat_service import ChatService

router = APIRouter()


@router.websocket("/ws/chat")
async def ws_chat(ws: WebSocket):
    await ws.accept()

    # Create a db session for the lifetime of this WS connection
    db_gen = get_db()
    db: Session = next(db_gen)

    try:
        me = await get_current_user_ws(ws, db)

        ollama = OllamaClient(settings.OLLAMA_BASE_URL)
        retrieval = RetrievalService()
        chat = ChatService(ollama, retrieval)

        while True:
            data = await ws.receive_json()

            # Expect: { type: "user_message", request_id, conversation_id, content, scope, k_vec, k_text, use_text }
            if data.get("type") != "user_message":
                await ws.send_json({"type": "error", "detail": "Unknown message type"})
                continue

            request_id = data.get("request_id")
            conversation_id = int(data.get("conversation_id", 0))
            content = (data.get("content") or "").strip()

            if not content:
                await ws.send_json(
                    {
                        "type": "error",
                        "request_id": request_id,
                        "detail": "Empty message",
                    }
                )
                continue

            scope = data.get("scope") or {"mode": "all", "doc_ids": []}
            mode = scope.get("mode", "all")
            doc_ids = scope.get("doc_ids") or []

            if mode == "selected" and len(doc_ids) == 0:
                await ws.send_json(
                    {
                        "type": "error",
                        "request_id": request_id,
                        "detail": "doc_ids must be provided when mode='selected'",
                    }
                )
                continue

            # clamp
            k_vec = max(1, min(int(data.get("k_vec", 10)), 50))
            k_text = max(1, min(int(data.get("k_text", 10)), 50))
            use_text = bool(data.get("use_text", True))

            # 1) Create conversation if needed
            if conversation_id == 0:
                convo = create_conversation(
                    db=db,
                    tenant_id=me.tenant_id,
                    user_id=me.user_id,
                    chat_model_id=settings.DEFAULT_CHAT_MODEL,
                )
                conversation_id = convo.conversation_id

            # 2) Immediately tell client the chat id
            await ws.send_json(
                {
                    "type": "chat_id",
                    "request_id": request_id,
                    "conversation_id": conversation_id,
                }
            )

            # 3) Run your existing chat pipeline (non-stream)
            try:
                asst_msg, answer, citations_rows = await chat.chat(
                    db=db,
                    tenant_id=me.tenant_id,
                    user_id=me.user_id,
                    conversation_id=conversation_id,
                    user_text=content,
                    doc_ids=doc_ids if mode == "selected" else None,
                    k_vec=k_vec,
                    k_text=k_text,
                    use_text=use_text,
                )
            except ValueError as e:
                await ws.send_json(
                    {"type": "error", "request_id": request_id, "detail": str(e)}
                )
                continue
            except Exception as e:
                await ws.send_json(
                    {
                        "type": "error",
                        "request_id": request_id,
                        "detail": f"Chat failed: {e}",
                    }
                )
                continue

            citations = [
                Citation(
                    chunk_id=c.chunk_id,
                    doc_id=c.doc_id,
                    page_start=c.page_start,
                    page_end=c.page_end,
                    section_path=c.section_path,
                    score=float(c.score or 0.0),
                ).model_dump()
                for c in (citations_rows or [])
            ]

            # 4) Send final assistant response
            await ws.send_json(
                {
                    "type": "assistant_done",
                    "request_id": request_id,
                    "conversation_id": conversation_id,
                    "message_id": asst_msg.message_id,
                    "answer": answer or "",
                    "citations": citations,
                }
            )

    except WebSocketDisconnect:
        pass
    finally:
        try:
            db.close()
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
