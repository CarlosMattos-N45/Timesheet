from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Jornada, Marcacao


class MarcacaoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_idempotency(self, idempotency_key: str) -> Marcacao | None:
        stmt = select(Marcacao).where(Marcacao.idempotency_key == idempotency_key)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_in_jornada_by_tipo(self, jornada_id: str, tipo: str) -> Marcacao | None:
        return (
            await self.session.execute(
                select(Marcacao).where(Marcacao.jornada_id == jornada_id, Marcacao.tipo == tipo)
            )
        ).scalar_one_or_none()

    async def get_by_id_owned_by(self, marcacao_id: str, terceiro_id: str) -> Marcacao | None:
        # Join jornada → garante ownership
        row = (
            await self.session.execute(
                select(Marcacao).join(Jornada, Jornada.id == Marcacao.jornada_id)
                .where(Marcacao.id == marcacao_id, Jornada.terceiro_id == terceiro_id)
            )
        ).scalar_one_or_none()
        return row

    async def list_for_terceiro(self, terceiro_id: str, status: str | None) -> list[Marcacao]:
        stmt = (
            select(Marcacao).join(Jornada, Jornada.id == Marcacao.jornada_id)
            .where(Jornada.terceiro_id == terceiro_id)
            .order_by(Marcacao.criada_em.desc())
        )
        if status:
            stmt = stmt.where(Marcacao.status == status)
        return list((await self.session.execute(stmt)).scalars().all())

    async def create(
        self, *, jornada_id: str, tipo: str, horario_registrado: str,
        horario_efetivo: str | None, origem: str, idempotency_key: str,
    ) -> Marcacao:
        m = Marcacao(
            id=str(uuid4()), jornada_id=jornada_id, tipo=tipo,
            horario_registrado=horario_registrado, horario_efetivo=horario_efetivo,
            origem=origem, status="CONFIRMADA",
            confirmado_pelo_usuario=1 if origem == "AGENTE_CONFIRMADO" else 0,
            idempotency_key=idempotency_key,
            criada_em=datetime.now(UTC).isoformat(),
        )
        self.session.add(m)
        return m

    @staticmethod
    def snapshot(m: Marcacao) -> dict[str, str | None]:
        return {
            "tipo": m.tipo,
            "horario_registrado": m.horario_registrado,
            "horario_efetivo": m.horario_efetivo,
            "origem": m.origem,
            "status": m.status,
        }

    async def ajustar(self, m: Marcacao, horario_efetivo: str) -> None:
        m.horario_efetivo = horario_efetivo
        m.origem = "AJUSTE_WEB"
        m.status = "AJUSTADA"
