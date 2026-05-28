from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.privacidade.repository import PrivacyRepository
from app.modules.privacidade.schema import PrivacyStatus

VERSAO_AVISO_ATUAL = "1.0"


async def get_status(session: AsyncSession) -> PrivacyStatus:
    repo = PrivacyRepository(session)
    row = await repo.get_or_none()
    if row is None:
        return PrivacyStatus(accepted=False, versao_aviso=None, aceito_em=None)
    return PrivacyStatus(
        accepted=row.versao_aviso == VERSAO_AVISO_ATUAL,
        versao_aviso=row.versao_aviso,
        aceito_em=row.aceito_em,
    )


async def aceitar(session: AsyncSession) -> None:
    repo = PrivacyRepository(session)
    existing = await repo.get_or_none()
    if existing is not None and existing.versao_aviso == VERSAO_AVISO_ATUAL:
        return  # idempotente
    await repo.upsert(VERSAO_AVISO_ATUAL)
    await session.commit()
