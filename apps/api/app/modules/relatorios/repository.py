from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import HistoricoEnvioRelatorio, RelatorioGerado


class RelatorioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_mes(self, mes: str) -> RelatorioGerado | None:
        return (
            await self.session.execute(
                select(RelatorioGerado).where(RelatorioGerado.mes_referencia == mes)
            )
        ).scalar_one_or_none()

    async def upsert(self, mes: str, caminho: str) -> RelatorioGerado:
        existing = await self.get_by_mes(mes)
        now = datetime.now(UTC).isoformat()
        if existing is None:
            r = RelatorioGerado(
                id=str(uuid4()),
                mes_referencia=mes,
                caminho_arquivo=caminho,
                gerado_em=now,
                invalidado_em=None,
            )
            self.session.add(r)
            return r
        existing.caminho_arquivo = caminho
        existing.gerado_em = now
        existing.invalidado_em = None
        return existing

    async def mark_invalidado(self, mes: str) -> None:
        r = await self.get_by_mes(mes)
        if r is not None and r.invalidado_em is None:
            r.invalidado_em = datetime.now(UTC).isoformat()

    async def list_to_purge(self, cutoff_iso: str) -> list[RelatorioGerado]:
        stmt = select(RelatorioGerado).where(RelatorioGerado.gerado_em < cutoff_iso)
        return list((await self.session.execute(stmt)).scalars().all())

    async def delete(self, r: RelatorioGerado) -> None:
        await self.session.delete(r)


class HistoricoEnvioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, *, mes: str, email: str, status: str, erro: str | None
    ) -> HistoricoEnvioRelatorio:
        h = HistoricoEnvioRelatorio(
            id=str(uuid4()),
            mes_referencia=mes,
            email_destinatario=email,
            status=status,
            erro_mensagem=erro,
            enviado_em=datetime.now(UTC).isoformat(),
        )
        self.session.add(h)
        return h

    async def list_by_mes(self, mes: str) -> list[HistoricoEnvioRelatorio]:
        stmt = (
            select(HistoricoEnvioRelatorio)
            .where(HistoricoEnvioRelatorio.mes_referencia == mes)
            .order_by(HistoricoEnvioRelatorio.enviado_em.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())
