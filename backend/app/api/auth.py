"""Authentication endpoints — JWT Bearer.

Tokens are stateless; ``/logout`` is provided for the frontend contract
(client discards the token).
"""
from app.core.config import get_settings

from fastapi import APIRouter, HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy import select

from app.core.security import create_access_token, hash_password, verify_password
from app.dependencies import CurrentUser, DbDep
from app.models import User
from app.schemas.auth import AuthResponse, GoogleAuthRequest, LoginRequest, RegisterRequest
from app.schemas.user import UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _issue_token(user: User) -> AuthResponse:
    return AuthResponse(
        access_token=create_access_token(str(user.id)),
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
)
def register(payload: RegisterRequest, db: DbDep) -> AuthResponse:
    email = payload.email.lower()

    existing = db.scalar(select(User).where(User.email == email))

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return _issue_token(user)


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Log in",
)
def login(payload: LoginRequest, db: DbDep) -> AuthResponse:
    user = db.scalar(
        select(User).where(User.email == payload.email.lower())
    )

    if (
        user is None
        or user.password_hash is None
        or not verify_password(payload.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return _issue_token(user)


@router.post(
    "/google",
    response_model=AuthResponse,
    summary="Sign in with Google",
    responses={
        401: {"description": "Invalid Google credential"},
        500: {"description": "Google authentication is not configured"},
    },
)
def google_auth(
    payload: GoogleAuthRequest,
    db: DbDep,
) -> AuthResponse:

    settings = get_settings()
    google_client_id = settings.google_client_id


    if not google_client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google authentication is not configured on the server",
        )

    try:
        idinfo = id_token.verify_oauth2_token(
            payload.credential,
            google_requests.Request(),
            google_client_id,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google credential",
        )

    email = idinfo.get("email")
    name = idinfo.get("name") or idinfo.get("given_name") or "Google User"

    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google account information is incomplete",
        )

    email = email.lower()

    user = db.scalar(
        select(User).where(User.email == email)
    )

    if user is None:
        user = User(
            name=name.strip()[:120],
            email=email,
            password_hash=None,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

    return _issue_token(user)


@router.get(
    "/me",
    response_model=UserOut,
    summary="Current profile",
)
def me(current_user: CurrentUser) -> UserOut:
    return UserOut.model_validate(current_user)


@router.post(
    "/logout",
    summary="Log out",
)
def logout(current_user: CurrentUser) -> dict:
    return {
        "message": "Logged out — discard the stored token on this device.",
        "revokedOnServer": False,
    }