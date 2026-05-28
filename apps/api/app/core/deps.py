from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import DomainError
from app.core.security import decode_token
from app.models import Terceiro

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def _extract_bearer(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise DomainError(code="UNAUTHORIZED", message="Token ausente ou inválido", http_status=401)
    return authorization.split(" ", 1)[1].strip()


BearerTokenDep = Annotated[str, Depends(_extract_bearer)]


async def get_current_terceiro(token: BearerTokenDep, session: SessionDep) -> Terceiro:
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise DomainError(code="UNAUTHORIZED", message="Tipo de token inválido", http_status=401)
    sub = payload.get("sub")
    if not sub:
        raise DomainError(code="UNAUTHORIZED", message="Token sem sujeito", http_status=401)
    t = (await session.execute(select(Terceiro).where(Terceiro.id == sub))).scalar_one_or_none()
    if t is None:
        raise DomainError(code="UNAUTHORIZED", message="Terceiro não encontrado", http_status=401)
    return t


CurrentTerceiroDep = Annotated[Terceiro, Depends(get_current_terceiro)]
