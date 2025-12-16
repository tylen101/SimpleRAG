from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from passlib.context import CryptContext
from core.db import get_db
from core.deps import get_current_user
from models.Models import AppUser

# from models import AppUser

# from utils.db_util import get_db
# from utils.security import get_current_user
from sqlalchemy.orm import Session

# from db.models.user import User
from core.config import settings


ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 72
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter()


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    print("\nLOGGING IN...\n---------------")

    user = db.query(AppUser).filter(AppUser.display_name == form_data.username).first()
    if not user or not pwd_context.verify(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user.last_login = datetime.utcnow()
    db.commit()

    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = {"sub": str(user.user_id), "exp": expire}
    token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    response = JSONResponse(
        {
            "message": "Logged in successfully",
            "user": {"user_id": user.user_id, "display_name": user.display_name},
        }
    )
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=3600,
        path="/",
    )
    return response


@router.post("/logout")
def logout():
    response = JSONResponse({"message": "Logged out"})
    response.delete_cookie("access_token")
    return response


@router.post("/register")
def register(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    print("\nREGISTERING USER...\n---------------")

    if db.query(AppUser).filter(AppUser.display_name == form_data.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    user = AppUser(display_name=form_data.username)
    user.password_hash = pwd_context.hash(form_data.password)
    user.created_at = datetime.utcnow()

    db.add(user)
    db.commit()
    db.refresh(user)

    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = {"sub": str(user.user_id), "exp": expire}
    token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    response = JSONResponse(
        {
            "message": "Registered successfully",
            "user": {"user_id": user.user_id, "display_name": user.display_name},
        }
    )
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/me")
def get_profile(user: AppUser = Depends(get_current_user)):
    return {
        "display_name": user.display_name,
        "last_login": user.last_login,
        "created_at": user.created_at,
    }
