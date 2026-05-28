from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.models import Terceiro
from app.modules.terceiros.repository import TerceiroRepository


async def create_terceiro(session: AsyncSession, payload: dict[str, Any]) -> Terceiro:
    repo = TerceiroRepository(session)
    if await repo.count() >= 1:
        raise DomainError(
            code="SETUP_ALREADY_DONE", message="Cadastro inicial já realizado", http_status=403
        )
    t = await repo.create(payload)
    await session.commit()
    return t


async def update_me(
    session: AsyncSession, t: Terceiro, payload: dict[str, Any], autor: str
) -> Terceiro:
    repo = TerceiroRepository(session)
    updated = await repo.update(t, payload, autor)
    await session.commit()
    return updated


async def change_password(
    session: AsyncSession, t: Terceiro, senha_atual: str, nova_senha: str
) -> None:
    repo = TerceiroRepository(session)
    await repo.change_password(t, senha_atual, nova_senha)
    await session.commit()
