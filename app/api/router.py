from fastapi import APIRouter, Depends
from api import documents, conversations, retrieve, chunks, auth
from core.deps import get_current_user


router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["Auth"])
router.include_router(
    documents.router,
    tags=["documents"],
    # dependencies=[Depends(get_current_user)],
)
router.include_router(
    conversations.router,
    tags=["conversations"],
    # dependencies=[Depends(get_current_user)],
)
router.include_router(
    retrieve.router,
    tags=["retrieve"],
    # dependencies=[Depends(get_current_user)],
)
router.include_router(
    chunks.router,
    tags=["chunks"],
    # dependencies=[Depends(get_current_user)],
)
