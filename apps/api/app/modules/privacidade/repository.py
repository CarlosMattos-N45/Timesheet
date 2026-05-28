from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PrivacyAcceptance


class PrivacyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_none(self) -> PrivacyAcceptance | None:
        return (
            await self.session.execute(select(PrivacyAcceptance).where(PrivacyAcceptance.id == 1))
        ).scalar_one_or_none()

    async def upsert(self, versao: str) -> PrivacyAcceptance:
        existing = await self.get_or_none()
        now = datetime.now(UTC).isoformat()
        if existing is None:
            row = PrivacyAcceptance(id=1, aceito_em=now, versao_aviso=versao)
            self.session.add(row)
            return row
        existing.aceito_em = now
        existing.versao_aviso = versao
        return existing
