
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select

from app.api.dependencies import (
    CurrentUser,
    DbSession,
    require_csrf,
)
from app.core.config import settings
from app.core.security import (
    create_access_token,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, UserResponse


router = APIRouter(prefix="/auth", tags=["Authentication"])

COOKIE_MAX_AGE = settings.access_token_expire_minutes * 60


@router.post("/login", response_model=UserResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: DbSession,
) -> User:
    email = payload.email.strip().lower()

    user = db.scalar(
        select(User).where(func.lower(User.email) == email)
    )

    if user is None or not verify_password(
        payload.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = create_access_token(user.id, user.role)
    csrf_token = secrets.token_urlsafe(32)

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=COOKIE_MAX_AGE,
        path="/",
    )

    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=COOKIE_MAX_AGE,
        path="/",
    )

    return user


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    response: Response,
    _: Annotated[None, Depends(require_csrf)],
    current_user: CurrentUser,
) -> dict[str, str]:
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )
    response.delete_cookie(
        key="csrf_token",
        path="/",
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: CurrentUser) -> User:
    return current_user
@router.get("/admins", response_model=list[UserResponse])
def get_admin_users(
    db: DbSession,
    current_user: CurrentUser,
):
    role = getattr(current_user.role, "value", current_user.role)

    if role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    return db.scalars(
        select(User).where(User.role == "admin")
    ).all()