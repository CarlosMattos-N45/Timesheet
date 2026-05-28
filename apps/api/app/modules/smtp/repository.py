from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import aes_gcm_decrypt, aes_gcm_encrypt
from app.models import SmtpConfig


class SmtpRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_none(self) -> SmtpConfig | None:
        return (
            await self.session.execute(select(SmtpConfig).where(SmtpConfig.id == 1))
        ).scalar_one_or_none()

    async def upsert(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        use_starttls: bool,
        from_address: str,
        subkey: bytes,
    ) -> SmtpConfig:
        existing = await self.get_or_none()
        now = datetime.now(UTC).isoformat()
        username_enc = aes_gcm_encrypt(subkey, username.encode("utf-8"))
        password_enc = aes_gcm_encrypt(subkey, password.encode("utf-8"))
        if existing is None:
            cfg = SmtpConfig(
                id=1, host=host, port=port,
                username_enc=username_enc, password_enc=password_enc,
                use_starttls=1 if use_starttls else 0,
                from_address=from_address, atualizado_em=now,
            )
            self.session.add(cfg)
            return cfg
        existing.host = host
        existing.port = port
        existing.username_enc = username_enc
        existing.password_enc = password_enc
        existing.use_starttls = 1 if use_starttls else 0
        existing.from_address = from_address
        existing.atualizado_em = now
        return existing

    @staticmethod
    def decrypt_username(cfg: SmtpConfig, subkey: bytes) -> str:
        return aes_gcm_decrypt(subkey, cfg.username_enc).decode("utf-8")

    @staticmethod
    def decrypt_password(cfg: SmtpConfig, subkey: bytes) -> str:
        return aes_gcm_decrypt(subkey, cfg.password_enc).decode("utf-8")
