from fastapi import APIRouter
from api import documents, conversations, retrieve

router = APIRouter()
router.include_router(documents.router, tags=["documents"])
router.include_router(conversations.router, tags=["conversations"])
router.include_router(retrieve.router, tags=["retrieve"])
