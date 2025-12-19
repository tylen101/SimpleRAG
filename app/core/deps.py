from dataclasses import dataclass
from fastapi import Depends, HTTPException, Request, status, WebSocket
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from core.db import get_db
from models.Models import AppUser

from core.config import settings


@dataclass(frozen=True)
class CurrentUser:
    user_id: int
    tenant_id: int


# use for dev testing for now
# TODO: implement developer permissions
# TODO: implement permissions...
# def get_current_user() -> CurrentUser:
#     return CurrentUser(user_id=3, tenant_id=1)


def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication cookie",
        )

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = db.query(AppUser).filter(AppUser.user_id == user_id).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return user


WS_CLOSE_POLICY_VIOLATION = 1008  # common for auth failure


async def get_current_user_ws(ws: WebSocket, db: Session) -> AppUser:
    token = ws.cookies.get("access_token")
    if not token:
        await ws.close(
            code=WS_CLOSE_POLICY_VIOLATION, reason="Missing authentication cookie"
        )
        raise RuntimeError("Missing authentication cookie")

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        if user_id is None:
            await ws.close(
                code=WS_CLOSE_POLICY_VIOLATION, reason="Invalid token payload"
            )
            raise RuntimeError("Invalid token payload")
    except JWTError:
        await ws.close(
            code=WS_CLOSE_POLICY_VIOLATION, reason="Invalid or expired token"
        )
        raise RuntimeError("Invalid or expired token")

    user = db.query(AppUser).filter(AppUser.user_id == user_id).first()
    if not user:
        await ws.close(code=WS_CLOSE_POLICY_VIOLATION, reason="Invalid credentials")
        raise RuntimeError("Invalid credentials")

    return user
