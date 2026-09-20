from app.core.config import get_settings
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.user import UserOut

class GoogleAuthRequest(BaseModel):
    """Google Identity Services ID token."""

    credential: str = Field(min_length=1)


class RegisterRequest(BaseModel):
    """``POST /api/auth/register`` body."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    """``POST /api/auth/login`` body."""

    model_config = ConfigDict(str_strip_whitespace=True)

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AuthResponse(BaseModel):
    """Login/register response — matches the frontend contract exactly."""

    access_token: str
    token_type: str = "bearer"
    user: UserOut
