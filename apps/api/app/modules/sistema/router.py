from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.core.config import settings
from app.core.db import get_session
from app.core.deps import CurrentTerceiroDep

router = APIRouter(prefix="/api/v1", tags=["sistema"])
router_dev = APIRouter(prefix="/api/v1", tags=["sistema-dev"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@router_dev.get("/_dbcheck")
async def dbcheck(session: SessionDep) -> dict[str, object]:
    result = (await session.execute(text("SELECT 1"))).scalar_one()
    return {"db": "ok", "result": result}


@router_dev.get("/_auth_smoke")
async def auth_smoke(t: CurrentTerceiroDep) -> dict[str, str]:
    return {"terceiro_id": t.id}


class _SmokeLoginBody(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=8)


@router_dev.post("/auth/_smoke_login")
async def smoke_login(request: Request, body: _SmokeLoginBody) -> dict[str, str]:  # noqa: ARG001
    return {"status": "ok"}


def bind_smoke_rate_limit(app: FastAPI) -> None:
    """Aplica @limiter.limit(settings.rate_limit_login) ao endpoint _smoke_login."""
    limiter = app.state.limiter
    for route in app.routes:
        if getattr(route, "path", "") == "/api/v1/auth/_smoke_login":
            route.endpoint = limiter.limit(settings.rate_limit_login)(route.endpoint)  # type: ignore[attr-defined]
            route.dependant.call = route.endpoint  # type: ignore[attr-defined]
            return
