from __future__ import annotations

from fastapi import APIRouter, Request, status

from app.core.deps import CurrentTerceiroDep, SessionDep
from app.modules.auth import service
from app.modules.auth.schema import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    RefreshRequest,
    RefreshResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login_endpoint(
    request: Request, body: LoginRequest, session: SessionDep
) -> LoginResponse:
    data = await service.login(session, body.email, body.senha)
    return LoginResponse(**data)


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_endpoint(
    request: Request, body: RefreshRequest, session: SessionDep
) -> RefreshResponse:
    data = await service.refresh(session, body.refresh_token)
    return RefreshResponse(**data)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout_endpoint(
    body: LogoutRequest,
    t: CurrentTerceiroDep,  # noqa: ARG001
    session: SessionDep,
) -> None:
    await service.logout(session, body.refresh_token)
