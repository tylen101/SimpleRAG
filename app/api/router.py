from fastapi import APIRouter
from api import documents, conversations

router = APIRouter()
print("building router")
router.include_router(documents.router, tags=["documents"])
router.include_router(conversations.router, tags=["conversations"])
