from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models import RefreshToken, Terceiro


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def authenticate(self, email: str, senha: str) -> Terceiro | None:
        t = (
            await self.session.execute(select(Terceiro).where(Terceiro.email_contato == email))
        ).scalar_one_or_none()
        if t is None:
            return None
        if not verify_password(t.senha_hash, senha):
            return None
        return t

    async def revoke_refresh(self, token: str) -> None:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        rt = (
            await self.session.execute(
                select(RefreshToken).where(RefreshToken.token_hash == token_hash)
            )
        ).scalar_one_or_none()
        if rt is not None and rt.revogado_em is None:
            rt.revogado_em = datetime.now(UTC).isoformat()
