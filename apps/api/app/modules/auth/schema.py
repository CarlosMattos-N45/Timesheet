from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    terceiro_id: str
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int


class LogoutRequest(BaseModel):
    refresh_token: str
