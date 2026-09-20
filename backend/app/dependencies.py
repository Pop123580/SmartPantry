"""Shared FastAPI dependencies: database session + current-user auth.

Every user-scoped endpoint resolves the user ONLY from the JWT — a
``user_id`` supplied in a request body/query is never trusted.
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User

# auto_error=False so we control the 401 (FastAPI's default bare 403 when
# the header is missing would violate the API contract).
bearer_scheme = HTTPBearer(
    auto_error=False,
    description="JWT Bearer token returned by `/api/auth/login`.",
)

DbDep = Annotated[Session, Depends(get_db)]


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DbDep,
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized
    claims = decode_access_token(credentials.credentials)
    if claims is None:
        unauthorized.detail = "Invalid or expired token"
        raise unauthorized
    try:
        user_id = UUID(claims["sub"])
    except (KeyError, ValueError):
        unauthorized.detail = "Invalid token subject"
        raise unauthorized
    user = db.scalar(select(User).where(User.id == user_id))
    if user is None:
        unauthorized.detail = "User no longer exists"
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
