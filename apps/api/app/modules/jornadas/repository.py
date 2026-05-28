from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Jornada


class JornadaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_terceiro_and_data(self, terceiro_id: str, data: str) -> Jornada | None:
        return (
            await self.session.execute(
                select(Jornada).where(Jornada.terceiro_id == terceiro_id, Jornada.data == data)
            )
        ).scalar_one_or_none()

    async def get_or_create_for_day(self, terceiro_id: str, data: str) -> Jornada:
        existing = await self.get_by_terceiro_and_data(terceiro_id, data)
        if existing is not None:
            return existing
        j = Jornada(
            id=str(uuid4()), terceiro_id=terceiro_id, data=data,
            status="EM_ANDAMENTO", criada_em=datetime.now(UTC).isoformat(),
        )
        self.session.add(j)
        return j

    async def set_status_ajustada(self, jornada_id: str) -> None:
        result = await self.session.execute(select(Jornada).where(Jornada.id == jornada_id))
        j = result.scalar_one()
        if j.status != "AJUSTADA_MANUALMENTE":
            j.status = "AJUSTADA_MANUALMENTE"

    async def list_for_month(self, terceiro_id: str, mes: str) -> list[Jornada]:
        """mes: 'YYYY-MM' — filtra data com LIKE 'YYYY-MM-%'."""
        stmt = (
            select(Jornada)
            .where(Jornada.terceiro_id == terceiro_id, Jornada.data.like(f"{mes}-%"))
            .options(selectinload(Jornada.marcacoes))
            .order_by(Jornada.data.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_detalhe(self, jornada_id: str, terceiro_id: str) -> Jornada | None:
        stmt = (
            select(Jornada)
            .where(Jornada.id == jornada_id, Jornada.terceiro_id == terceiro_id)
            .options(
                selectinload(Jornada.marcacoes),
                selectinload(Jornada.atividade),
                selectinload(Jornada.justificativas),
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def update_total_horas(self, j: Jornada, total_s: int | None) -> None:
        j.total_horas_apuradas_s = total_s
