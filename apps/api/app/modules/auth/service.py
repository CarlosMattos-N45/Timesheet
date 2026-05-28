from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.core.security import create_access_token, create_refresh_token, rotate_refresh_token
from app.modules.auth.repository import AuthRepository


async def login(session: AsyncSession, email: str, senha: str) -> dict[str, Any]:
    repo = AuthRepository(session)
    t = await repo.authenticate(email, senha)
    if t is None:
        raise DomainError(code="UNAUTHORIZED", message="E-mail ou senha inválidos", http_status=401)
    access = create_access_token({"sub": t.id})
    refresh = await create_refresh_token({"sub": t.id}, session)
    await session.commit()
    return {
        "access_token": access,
        "refresh_token": refresh,
        "terceiro_id": t.id,
        "expires_in": 900,
    }


async def refresh(session: AsyncSession, refresh_token: str) -> dict[str, Any]:
    pair = await rotate_refresh_token(refresh_token, session)
    await session.commit()
    return pair


async def logout(session: AsyncSession, refresh_token: str) -> None:
    repo = AuthRepository(session)
    await repo.revoke_refresh(refresh_token)
    await session.commit()
