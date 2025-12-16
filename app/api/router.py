from fastapi import APIRouter
from api import documents, conversations, retrieve, chunks, auth

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["Auth"])
router.include_router(documents.router, tags=["documents"])
router.include_router(conversations.router, tags=["conversations"])
router.include_router(retrieve.router, tags=["retrieve"])
router.include_router(chunks.router, tags=["chunks"])
