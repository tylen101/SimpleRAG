from __future__ import annotations

from typing import List
from core.config import settings
from services.ollama_client import OllamaClient


class EmbeddingService:
    def __init__(self, ollama: OllamaClient):
        self.ollama = ollama

    async def embed_text(self, text: str) -> List[float]:
        vec = await self.ollama.embed(settings.EMBEDDING_MODEL, text)
        if len(vec) != settings.EMBEDDING_DIM:
            raise ValueError(
                f"Embedding dim mismatch: got {len(vec)} expected {settings.EMBEDDING_DIM}"
            )
        return vec
