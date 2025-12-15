import httpx
from typing import List, Dict, Any


class OllamaClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def embed(self, model: str, text: str) -> List[float]:
        # Ollama embeddings endpoint
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": model, "prompt": text},
            )
            r.raise_for_status()
            data = r.json()
            return data["embedding"]

    async def chat(self, model: str, messages: List[Dict[str, str]]) -> str:
        # Non-streaming for MVP
        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(
                f"{self.base_url}/api/chat",
                json={"model": model, "messages": messages, "stream": False},
            )
            r.raise_for_status()
            data = r.json()
            # Ollama returns: {"message": {"role": "...", "content": "..."}, ...}
            return data["message"]["content"]
