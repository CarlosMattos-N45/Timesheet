from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LogAuditoria


class AuditoriaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, entidade: str, entidade_id: str) -> list[LogAuditoria]:
        stmt = (
            select(LogAuditoria)
            .where(LogAuditoria.entidade == entidade, LogAuditoria.entidade_id == entidade_id)
            .order_by(LogAuditoria.criado_em.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())
