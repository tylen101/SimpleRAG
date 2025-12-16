from fastapi import FastAPI
from contextlib import asynccontextmanager
from api.router import router as v1_router
import uvicorn
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from workers.document_worker import DocumentWorker
import asyncio
import os


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Starts the background document worker on startup
    and shuts it down gracefully on shutdown.
    """
    worker: DocumentWorker | None = None
    worker_task: asyncio.Task | None = None

    if os.getenv("RUN_DOCUMENT_WORKER", "1") == "1":
        worker = DocumentWorker(poll_seconds=1.0)
        worker_task = asyncio.create_task(worker.run_forever())

    try:
        yield
    finally:
        if worker:
            worker.stop()
        if worker_task:
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title="Enterprise Local RAG API",
    version="0.1.0",
    lifespan=lifespan,  # ✅ THIS is the key
)


origins = [
    "http://localhost:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)

app.include_router(v1_router)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health")
def health():
    return {"ok": True}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="localhost",
        port=8000,
        reload=True,
    )
