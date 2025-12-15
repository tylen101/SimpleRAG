# import json
# from sqlalchemy.orm import Session
# from typing import List, Dict, Any, Optional

# from core.config import settings
# from models.Models import Conversation, Message, RetrievalEvent
# from services.ollama_client import OllamaClient
# from services.retrieval_service import RetrievalService

# SYSTEM_PROMPT = """You are a private enterprise RAG assistant.
# Use ONLY the provided context snippets to answer.
# If the context does not contain the answer, say you don't have enough information and suggest what to look for.
# Always cite sources by chunk_id and doc_id when you use a snippet.
# """


# class ChatService:
#     def __init__(self, ollama: OllamaClient, retrieval: RetrievalService):
#         self.ollama = ollama
#         self.retrieval = retrieval

#     async def chat(
#         self,
#         db: Session,
#         tenant_id: int,
#         user_id: int,
#         conversation_id: int,
#         user_text: str,
#         doc_ids: Optional[List[int]],
#         k_vec: int,
#         k_text: int,
#         use_text: bool,
#     ) -> tuple[Message, str, List[Dict[str, Any]]]:
#         convo = db.get(Conversation, conversation_id)
#         if not convo or convo.tenant_id != tenant_id or convo.user_id != user_id:
#             raise ValueError("Conversation not found")

#         # 1) store user message
#         user_msg = Message(
#             conversation_id=conversation_id, role="user", content=user_text
#         )
#         db.add(user_msg)
#         db.flush()

#         # 2) embed query
#         q_vec = await self.ollama.embed(settings.EMBEDDING_MODEL, user_text)
#         if len(q_vec) != settings.EMBEDDING_DIM:
#             raise ValueError(
#                 f"Embedding dim mismatch: got {len(q_vec)} expected {settings.EMBEDDING_DIM}"
#             )

#         # 3) retrieve
#         hits = self.retrieval.hybrid_search(
#             db=db,
#             tenant_id=tenant_id,
#             query_vec=q_vec,
#             query_text=user_text,
#             doc_ids=doc_ids,
#             k_vec=k_vec,
#             k_text=k_text,
#             use_text=use_text,
#         )

#         # 4) build context
#         context_lines = []
#         for h in hits:
#             context_lines.append(
#                 f"[doc_id={h['doc_id']} chunk_id={h['chunk_id']} page={h.get('page_start','?')}-{h.get('page_end','?')} section={h.get('section_path')}]"
#             )
#             context_lines.append(h["chunk_text"])
#             context_lines.append("")

#         context_block = "\n".join(context_lines).strip()

#         # 5) assemble messages for chat model
#         messages = [
#             {"role": "system", "content": SYSTEM_PROMPT},
#             {
#                 "role": "system",
#                 "content": (
#                     f"CONTEXT:\n{context_block}" if context_block else "CONTEXT: (none)"
#                 ),
#             },
#             {"role": "user", "content": user_text},
#         ]

#         answer = await self.ollama.chat(convo.chat_model_id, messages)

#         # 6) store assistant message + retrieval event
#         assistant_msg = Message(
#             conversation_id=conversation_id, role="assistant", content=answer
#         )
#         db.add(assistant_msg)
#         db.flush()

#         event = RetrievalEvent(
#             message_id=assistant_msg.message_id,
#             query_text=user_text,
#             filters_json=json.dumps(
#                 {
#                     "doc_ids": doc_ids or [],
#                     "k_vec": k_vec,
#                     "k_text": k_text,
#                     "use_text": use_text,
#                 }
#             ),
#             results_json=json.dumps(
#                 [
#                     {
#                         "chunk_id": h["chunk_id"],
#                         "doc_id": h["doc_id"],
#                         "score": float(h["score"]),
#                         "source": h.get("source"),
#                     }
#                     for h in hits
#                 ]
#             ),
#         )
#         db.add(event)

#         db.commit()
#         db.refresh(assistant_msg)
#         return assistant_msg, answer, hits


# from __future__ import annotations

# import json
# from typing import Any, Dict, List, Optional, Tuple

# from sqlalchemy.orm import Session

# from core.config import settings
# from models.Models import Conversation, Message, RetrievalEvent
# from services.ollama_client import OllamaClient
# from services.retrieval_service import RetrievalService
# from services.embedding_service import EmbeddingService


# class ChatService:
#     def __init__(self, ollama: OllamaClient, retrieval: RetrievalService):
#         self.ollama = ollama
#         self.retrieval = retrieval
#         self.embedder = EmbeddingService(ollama)

#     async def chat(
#         self,
#         db: Session,
#         tenant_id: int,
#         user_id: int,
#         conversation_id: int,
#         user_text: str,
#         doc_ids: Optional[List[int]],
#         k_vec: int,
#         k_text: int,
#         use_text: bool,
#     ) -> Tuple[Message, str, List[Dict[str, Any]]]:
#         """
#         Returns:
#           (user_message_row, assistant_answer_text, retrieval_hits)
#         Raises:
#           ValueError if conversation not found / wrong tenant/user.
#         """

#         convo = (
#             db.query(Conversation)
#             .filter(
#                 Conversation.conversation_id == conversation_id,
#                 Conversation.tenant_id == tenant_id,
#                 Conversation.user_id == user_id,
#             )
#             .first()
#         )
#         if not convo:
#             raise ValueError("Conversation not found")

#         q = (user_text or "").strip()
#         if not q:
#             raise ValueError("Message content cannot be empty")

#         # 1) Persist the user message first (so RetrievalEvent can FK to it)
#         user_msg = Message(conversation_id=conversation_id, role="user", content=q)
#         db.add(user_msg)
#         db.flush()  # get message_id

#         # 2) Embed user query
#         query_vec = await self.embedder.embed_text(q)

#         # 3) Retrieve contexts (hybrid)
#         hits = self.retrieval.hybrid_search(
#             db=db,
#             tenant_id=tenant_id,
#             query_vec=query_vec,
#             query_text=q,
#             doc_ids=doc_ids,
#             k_vec=k_vec,
#             k_text=k_text,
#             use_text=use_text,
#             alpha=0.70,
#         )

#         # 4) Store retrieval audit (very valuable for enterprise/debug)
#         event = RetrievalEvent(
#             message_id=user_msg.message_id,
#             query_text=q,
#             filters_json=json.dumps(
#                 {
#                     "doc_ids": doc_ids,
#                     "k_vec": k_vec,
#                     "k_text": k_text,
#                     "use_text": use_text,
#                 }
#             ),
#             results_json=json.dumps(
#                 [
#                     {
#                         "chunk_id": h.get("chunk_id"),
#                         "doc_id": h.get("doc_id"),
#                         "page_start": h.get("page_start"),
#                         "page_end": h.get("page_end"),
#                         "section_path": h.get("section_path"),
#                         # store all scores that might exist
#                         "hybrid_score": h.get("hybrid_score"),
#                         "vector_distance": h.get("vector_distance"),
#                         "text_score": h.get("text_score"),
#                         "source": h.get("source"),
#                     }
#                     for h in hits
#                 ]
#             ),
#         )
#         db.add(event)

#         # 5) Build prompt
#         context_block = self._format_context(hits)

#         system = (
#             "You are a private enterprise RAG assistant. "
#             "Answer using ONLY the provided context. "
#             "If the answer is not in the context, say you don't know. "
#             "Cite sources using [doc_id:chunk_id] after the sentence(s) they support."
#         )

#         # Include limited history (last N messages) - MVP: last 8 messages
#         history_rows = (
#             db.query(Message)
#             .filter(Message.conversation_id == conversation_id)
#             .order_by(Message.created_at.desc())
#             .limit(8)
#             .all()
#         )
#         history_rows.reverse()

#         history_text = "\n".join(
#             [
#                 f"{m.role.upper()}: {m.content}"
#                 for m in history_rows
#                 if m.message_id != user_msg.message_id
#             ]
#         )

#         final_prompt = (
#             f"{system}\n\n"
#             f"CONTEXT:\n{context_block}\n\n"
#             f"HISTORY:\n{history_text}\n\n"
#             f"USER:\n{q}\n\n"
#             f"ASSISTANT:"
#         )

#         # 6) Call chat model
#         answer = await self.ollama.chat(convo.chat_model_id, final_prompt)

#         # 7) Persist assistant message
#         asst_msg = Message(
#             conversation_id=conversation_id, role="assistant", content=answer
#         )
#         db.add(asst_msg)

#         db.commit()
#         db.refresh(user_msg)
#         return user_msg, answer, hits

#     def _format_context(
#         self, hits: List[Dict[str, Any]], max_chars_per_chunk: int = 1200
#     ) -> str:
#         """
#         Format contexts with stable citation handles: [doc_id:chunk_id]
#         """
#         blocks = []
#         for h in hits:
#             doc_id = h.get("doc_id")
#             chunk_id = h.get("chunk_id")
#             page_start = h.get("page_start")
#             page_end = h.get("page_end")
#             section_path = h.get("section_path") or ""

#             header = f"[{doc_id}:{chunk_id}]"
#             meta_parts = []
#             if page_start is not None:
#                 meta_parts.append(
#                     f"p{page_start}"
#                     + (f"-{page_end}" if page_end and page_end != page_start else "")
#                 )
#             if section_path:
#                 meta_parts.append(section_path)
#             meta = " | ".join(meta_parts)
#             if meta:
#                 header = f"{header} ({meta})"

#             text = (h.get("chunk_text") or "").strip()
#             if len(text) > max_chars_per_chunk:
#                 text = text[:max_chars_per_chunk].rstrip() + "…"

#             blocks.append(f"{header}\n{text}")
#         return "\n\n---\n\n".join(blocks)
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import text as sql_text  # optional if you want raw update
from sqlalchemy.orm import Session

from core.config import settings
from models.Models import Conversation, Message, RetrievalEvent
from services.ollama_client import OllamaClient
from services.retrieval_service import RetrievalService


class ChatService:
    def __init__(self, ollama: OllamaClient, retrieval: RetrievalService):
        self.ollama = ollama
        self.retrieval = retrieval

    async def _embed_query(self, text: str) -> List[float]:
        # Use your configured embedding model (qwen3-embedding)
        model = settings.EMBEDDING_MODEL  # e.g. "qwen3-embedding"
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
        # store whatever exists; helps later debugging
        return {
            "hybrid_score": h.get("hybrid_score"),
            "vector_distance": h.get("vector_distance"),
            "text_score": h.get("text_score"),
            "source": h.get("source"),
        }

    # async def chat(
    #     self,
    #     db: Session,
    #     tenant_id: int,
    #     user_id: int,
    #     conversation_id: int,
    #     user_text: str,
    #     doc_ids: Optional[List[int]],
    #     k_vec: int,
    #     k_text: int,
    #     use_text: bool,
    # ) -> Tuple[Message, str, List[Dict[str, Any]]]:
    #     convo = (
    #         db.query(Conversation)
    #         .filter(
    #             Conversation.conversation_id == conversation_id,
    #             Conversation.tenant_id == tenant_id,
    #             Conversation.user_id == user_id,
    #         )
    #         .first()
    #     )
    #     if not convo:
    #         raise ValueError("Conversation not found")

    #     q = (user_text or "").strip()
    #     if not q:
    #         raise ValueError("Message content cannot be empty")

    #     # 1) Store user message first
    #     user_msg = Message(conversation_id=conversation_id, role="user", content=q)
    #     db.add(user_msg)
    #     db.flush()  # assigns message_id

    #     # 2) Embed + retrieve
    #     query_vec = await self._embed_query(q)

    #     hits = self.retrieval.hybrid_search(
    #         db=db,
    #         tenant_id=tenant_id,
    #         query_vec=query_vec,
    #         query_text=q,
    #         doc_ids=doc_ids,
    #         k_vec=k_vec,
    #         k_text=k_text,
    #         use_text=use_text,
    #         alpha=0.70,
    #     )

    #     # 3) Persist retrieval event (audit)
    #     ev = RetrievalEvent(
    #         message_id=user_msg.message_id,
    #         query_text=q,
    #         filters_json=json.dumps(
    #             {
    #                 "doc_ids": doc_ids,
    #                 "k_vec": k_vec,
    #                 "k_text": k_text,
    #                 "use_text": use_text,
    #             }
    #         ),
    #         results_json=json.dumps(
    #             [
    #                 {
    #                     "chunk_id": h.get("chunk_id"),
    #                     "doc_id": h.get("doc_id"),
    #                     "page_start": h.get("page_start"),
    #                     "page_end": h.get("page_end"),
    #                     "section_path": h.get("section_path"),
    #                     **self._pick_score_for_event(h),
    #                 }
    #                 for h in hits
    #             ]
    #         ),
    #     )
    #     db.add(ev)

    #     # 4) Build messages for Ollama /api/chat
    #     system_msg = {
    #         "role": "system",
    #         "content": (
    #             "You are a private enterprise RAG assistant.\n"
    #             "Use ONLY the provided CONTEXT to answer.\n"
    #             "If the answer is not in the context, say you don't know.\n"
    #             "Cite sources like [doc_id:chunk_id] after the sentence(s) they support."
    #         ),
    #     }

    #     context = self._format_context(hits)

    #     # Pull a small amount of history (MVP)
    #     history = (
    #         db.query(Message)
    #         .filter(Message.conversation_id == conversation_id)
    #         .order_by(Message.created_at.desc())
    #         .limit(10)
    #         .all()
    #     )
    #     history.reverse()

    #     messages: List[Dict[str, str]] = [system_msg]

    #     if context:
    #         messages.append({"role": "system", "content": f"CONTEXT:\n{context}"})

    #     # Add history excluding the just-added user_msg (we'll add it last)
    #     for m in history:
    #         if m.message_id == user_msg.message_id:
    #             continue
    #         if m.role in ("user", "assistant", "system"):
    #             messages.append({"role": m.role, "content": m.content})

    #     # Add the new user query
    #     messages.append({"role": "user", "content": q})

    #     # 5) Generate answer
    #     answer = await self.ollama.chat(model=convo.chat_model_id, messages=messages)

    #     # 6) Store assistant message
    #     asst_msg = Message(
    #         conversation_id=conversation_id, role="assistant", content=answer
    #     )
    #     db.add(asst_msg)

    #     db.commit()
    #     db.refresh(user_msg)
    #     return user_msg, answer, hits

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
    ) -> Tuple[Message, str, List[Dict[str, Any]]]:

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

        # 0) Pull history BEFORE inserting the new user message (cleaner)
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
        db.flush()  # message_id available

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

        # 3) Persist retrieval event (audit)
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
        convo.updated_at = (
            None  # optional if you rely on DB triggers; otherwise set datetime.utcnow()
        )

        # ✅ Commit now so user msg + retrieval event are not lost if model call fails
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
            # If generation fails, you still have the user message + retrieval event stored
            raise RuntimeError(f"Model generation failed: {e}")

        # 6) Store assistant message
        asst_msg = Message(
            conversation_id=conversation_id, role="assistant", content=answer
        )
        db.add(asst_msg)
        db.commit()

        return user_msg, answer, hits
