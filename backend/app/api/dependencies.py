
from typing import Annotated
from uuid import UUID
import jwt
from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.dependencies import get_db
from app.models.user import User


DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession,
    access_token: Annotated[str | None, Cookie()] = None,
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not access_token:
        raise unauthorized

    try:
        payload = decode_access_token(access_token)
        user_id = payload.get("sub")
        if not user_id:
            raise unauthorized
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise unauthorized

    try:
      parsed_user_id = UUID(user_id)
    except (ValueError, TypeError):
      raise unauthorized

    user = db.get(User, parsed_user_id)

    if user is None:
        raise unauthorized

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


# def require_csrf(
#     csrf_cookie: Annotated[str | None, Cookie()] = None,
#     csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
# ) -> None:
#     print(
#     "CSRF debug:",
#     {
#         "cookie_present": bool(csrf_cookie),
#         "header_present": bool(csrf_header),
#         "match": (
#             csrf_cookie == csrf_header
#             if csrf_cookie and csrf_header
#             else False
#         ),
#     },
# )
#     if (
#         not csrf_cookie
#         or not csrf_header
#         or csrf_cookie != csrf_header
#     ):
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Invalid or missing CSRF token.",
#         )
from fastapi import Request

def require_csrf(request: Request) -> None:
    csrf_cookie = request.cookies.get("csrf_token")
    csrf_header = request.headers.get("X-CSRF-Token")


    if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing CSRF token.",
        )


def require_role(*allowed_roles: str):
    def role_checker(current_user: CurrentUser) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return current_user

    return role_checker
