from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Justificativa


class JustificativaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, *, jornada_id: str, motivo: str, usuario_responsavel: str
    ) -> Justificativa:
        j = Justificativa(
            id=str(uuid4()), jornada_id=jornada_id, motivo=motivo,
            usuario_responsavel=usuario_responsavel,
            criada_em=datetime.now(UTC).isoformat(),
        )
        self.session.add(j)
        return j
