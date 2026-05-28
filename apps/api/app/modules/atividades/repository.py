from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Atividade


class AtividadeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_jornada(self, jornada_id: str) -> Atividade | None:
        return (
            await self.session.execute(select(Atividade).where(Atividade.jornada_id == jornada_id))
        ).scalar_one_or_none()

    async def upsert(
        self, jornada_id: str, descricao: str
    ) -> tuple[Atividade, dict[str, str] | None]:
        """Returns (atividade, antes_snapshot|None se criando)."""
        existing = await self.get_by_jornada(jornada_id)
        now = datetime.now(UTC).isoformat()
        if existing is None:
            a = Atividade(
                id=str(uuid4()), jornada_id=jornada_id,
                descricao=descricao, registrada_em=now, atualizado_em=None,
            )
            self.session.add(a)
            return a, None
        antes = {"descricao": existing.descricao}
        existing.descricao = descricao
        existing.atualizado_em = now
        return existing, antes
