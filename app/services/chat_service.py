from __future__ import annotations

# load citations from DB (authoritative)
import json
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.config import settings
from models.Models import Conversation, Message, RetrievalEvent, MessageCitation
from services.ollama_client import OllamaClient
from services.retrieval_service import RetrievalService


class ChatService:
    def __init__(self, ollama: OllamaClient, retrieval: RetrievalService):
        self.ollama = ollama
        self.retrieval = retrieval

    async def _embed_query(self, text: str) -> List[float]:
        model = settings.EMBEDDING_MODEL
        return await self.ollama.embed(model=model, text=text)

    def _format_context(
        self, hits: List[Dict[str, Any]], max_chars_per_chunk: int = 1200
    ) -> str:
        blocks: List[str] = []
        for h in hits:
            doc_id = h.get("doc_id")
            chunk_id = h.get("chunk_id")
            page_start = h.get("page_start")
            page_end = h.get("page_end")
            section_path = h.get("section_path") or ""

            cite = f"[{doc_id}:{chunk_id}]"
            meta = []
            if page_start is not None:
                meta.append(
                    f"p{page_start}"
                    + (f"-{page_end}" if page_end and page_end != page_start else "")
                )
            if section_path:
                meta.append(section_path)
            meta_str = " | ".join(meta)
            header = f"{cite} ({meta_str})" if meta_str else cite

            text = (h.get("chunk_text") or "").strip()
            if len(text) > max_chars_per_chunk:
                text = text[:max_chars_per_chunk].rstrip() + "…"

            blocks.append(f"{header}\n{text}")

        return "\n\n---\n\n".join(blocks)

    def _pick_score_for_event(self, h: Dict[str, Any]) -> Dict[str, Any]:
        # store whatever exists
        return {
            "hybrid_score": h.get("hybrid_score"),
            "vector_distance": h.get("vector_distance"),
            "text_score": h.get("text_score"),
            "source": h.get("source"),
        }

    async def chat(
        self,
        db: Session,
        tenant_id: int,
        user_id: int,
        conversation_id: int,
        user_text: str,
        doc_ids: Optional[List[int]],
        k_vec: int,
        k_text: int,
        use_text: bool,
    ) -> Tuple[Message, str, List[MessageCitation]]:

        convo = (
            db.query(Conversation)
            .filter(
                Conversation.conversation_id == conversation_id,
                Conversation.tenant_id == tenant_id,
                Conversation.user_id == user_id,
            )
            .first()
        )
        if not convo:
            raise ValueError("Conversation not found")

        q = (user_text or "").strip()
        if not q:
            raise ValueError("Message content cannot be empty")

        history = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(10)
            .all()
        )
        history.reverse()

        # 1) Store user message
        user_msg = Message(conversation_id=conversation_id, role="user", content=q)
        db.add(user_msg)
        db.flush()

        # 2) Embed + retrieve
        query_vec = await self._embed_query(q)

        hits = self.retrieval.hybrid_search(
            db=db,
            tenant_id=tenant_id,
            query_vec=query_vec,
            query_text=q,
            doc_ids=doc_ids,
            k_vec=k_vec,
            k_text=k_text,
            use_text=use_text,
            alpha=0.70,
        )

        # 3) Persist retrieval event
        ev = RetrievalEvent(
            message_id=user_msg.message_id,
            query_text=q,
            filters_json=json.dumps(
                {
                    "doc_ids": doc_ids,
                    "k_vec": k_vec,
                    "k_text": k_text,
                    "use_text": use_text,
                }
            ),
            results_json=json.dumps(
                [
                    {
                        "chunk_id": h.get("chunk_id"),
                        "doc_id": h.get("doc_id"),
                        "page_start": h.get("page_start"),
                        "page_end": h.get("page_end"),
                        "section_path": h.get("section_path"),
                        **self._pick_score_for_event(h),
                    }
                    for h in hits
                ]
            ),
        )
        db.add(ev)

        # bump conversation updated time
        convo.updated_at = None

        db.commit()
        db.refresh(user_msg)

        # 4) Build messages for Ollama /api/chat
        system_msg = {
            "role": "system",
            "content": (
                "You are a private enterprise RAG assistant.\n"
                "Use ONLY the provided CONTEXT to answer.\n"
                "If the answer is not in the context, say you don't know.\n"
                "Cite sources like [doc_id:chunk_id] after the sentence(s) they support."
            ),
        }

        context = self._format_context(hits)

        messages: List[Dict[str, str]] = [system_msg]

        if context:
            messages.append({"role": "system", "content": f"CONTEXT:\n{context}"})

        # Add prior history
        for m in history:
            if m.role in ("user", "assistant", "system"):
                messages.append({"role": m.role, "content": m.content})

        # Add new user query as last user message
        messages.append({"role": "user", "content": q})

        # 5) Generate answer
        try:
            answer = await self.ollama.chat(
                model=convo.chat_model_id, messages=messages
            )
        except Exception as e:
            raise RuntimeError(f"Model generation failed: {e}")

        # 6) Store assistant message
        asst_msg = Message(
            conversation_id=conversation_id, role="assistant", content=answer
        )
        db.add(asst_msg)
        db.flush()  # assigns asst_msg.message_id

        # 7) Store citations for assistant message (using retrieval hits)

        def citation_score_from_hit(h: dict) -> float:
            if h.get("hybrid_score") is not None:
                return float(h["hybrid_score"])
            if h.get("text_score") is not None:
                return float(h["text_score"])
            if h.get("vector_distance") is not None:
                return 1.0 / (1.0 + float(h["vector_distance"]))
            return 0.0

        for h in hits:
            db.add(
                MessageCitation(
                    message_id=asst_msg.message_id,
                    doc_id=int(h["doc_id"]),
                    chunk_id=int(h["chunk_id"]),
                    page_start=h.get("page_start"),
                    page_end=h.get("page_end"),
                    section_path=h.get("section_path"),
                    score=citation_score_from_hit(h),
                )
            )

        db.commit()
        db.refresh(asst_msg)

        # If you want them returned sorted:
        cits = (
            db.query(MessageCitation)
            .filter(MessageCitation.message_id == asst_msg.message_id)
            .order_by(MessageCitation.score.desc().nullslast())
            .all()
        )

        return asst_msg, answer, cits
