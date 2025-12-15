import json
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from core.config import settings
from models.Models import Conversation, Message, RetrievalEvent
from services.ollama_client import OllamaClient
from services.retrieval_service import RetrievalService

SYSTEM_PROMPT = """You are a private enterprise RAG assistant.
Use ONLY the provided context snippets to answer.
If the context does not contain the answer, say you don't have enough information and suggest what to look for.
Always cite sources by chunk_id and doc_id when you use a snippet.
"""


class ChatService:
    def __init__(self, ollama: OllamaClient, retrieval: RetrievalService):
        self.ollama = ollama
        self.retrieval = retrieval

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
    ) -> tuple[Message, str, List[Dict[str, Any]]]:
        convo = db.get(Conversation, conversation_id)
        if not convo or convo.tenant_id != tenant_id or convo.user_id != user_id:
            raise ValueError("Conversation not found")

        # 1) store user message
        user_msg = Message(
            conversation_id=conversation_id, role="user", content=user_text
        )
        db.add(user_msg)
        db.flush()

        # 2) embed query
        q_vec = await self.ollama.embed(settings.EMBEDDING_MODEL, user_text)
        if len(q_vec) != settings.EMBEDDING_DIM:
            raise ValueError(
                f"Embedding dim mismatch: got {len(q_vec)} expected {settings.EMBEDDING_DIM}"
            )

        # 3) retrieve
        hits = self.retrieval.hybrid_search(
            db=db,
            tenant_id=tenant_id,
            query_vec=q_vec,
            query_text=user_text,
            doc_ids=doc_ids,
            k_vec=k_vec,
            k_text=k_text,
            use_text=use_text,
        )

        # 4) build context
        context_lines = []
        for h in hits:
            context_lines.append(
                f"[doc_id={h['doc_id']} chunk_id={h['chunk_id']} page={h.get('page_start','?')}-{h.get('page_end','?')} section={h.get('section_path')}]"
            )
            context_lines.append(h["chunk_text"])
            context_lines.append("")

        context_block = "\n".join(context_lines).strip()

        # 5) assemble messages for chat model
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "system",
                "content": (
                    f"CONTEXT:\n{context_block}" if context_block else "CONTEXT: (none)"
                ),
            },
            {"role": "user", "content": user_text},
        ]

        answer = await self.ollama.chat(convo.chat_model_id, messages)

        # 6) store assistant message + retrieval event
        assistant_msg = Message(
            conversation_id=conversation_id, role="assistant", content=answer
        )
        db.add(assistant_msg)
        db.flush()

        event = RetrievalEvent(
            message_id=assistant_msg.message_id,
            query_text=user_text,
            filters_json=json.dumps(
                {
                    "doc_ids": doc_ids or [],
                    "k_vec": k_vec,
                    "k_text": k_text,
                    "use_text": use_text,
                }
            ),
            results_json=json.dumps(
                [
                    {
                        "chunk_id": h["chunk_id"],
                        "doc_id": h["doc_id"],
                        "score": float(h["score"]),
                        "source": h.get("source"),
                    }
                    for h in hits
                ]
            ),
        )
        db.add(event)

        db.commit()
        db.refresh(assistant_msg)
        return assistant_msg, answer, hits
