from __future__ import annotations

import contextlib
import smtplib
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import crypto_state
from app.core.errors import DomainError
from app.modules.smtp.repository import SmtpRepository

_SMTP_TIMEOUT = 10  # seconds


async def get_config(session: AsyncSession) -> dict[str, Any]:
    repo = SmtpRepository(session)
    cfg = await repo.get_or_none()
    if cfg is None:
        raise DomainError(code="NOT_FOUND", message="SMTP não configurado", http_status=404)
    return {
        "host": cfg.host,
        "port": cfg.port,
        "username": repo.decrypt_username(cfg, crypto_state.SUBKEY_SMTP),
        "use_starttls": bool(cfg.use_starttls),
        "from_address": cfg.from_address,
        "atualizado_em": cfg.atualizado_em,
    }


async def put_config(session: AsyncSession, payload: dict[str, Any]) -> dict[str, Any]:
    repo = SmtpRepository(session)
    await repo.upsert(
        host=payload["host"],
        port=payload["port"],
        username=payload["username"],
        password=payload["password"].get_secret_value(),
        use_starttls=payload["use_starttls"],
        from_address=str(payload["from_address"]),
        subkey=crypto_state.SUBKEY_SMTP,
    )
    await session.commit()
    return await get_config(session)


async def test_connection(session: AsyncSession) -> dict[str, Any]:
    repo = SmtpRepository(session)
    cfg = await repo.get_or_none()
    if cfg is None:
        raise DomainError(
            code="SMTP_NOT_CONFIGURED", message="SMTP não configurado", http_status=422
        )
    username = repo.decrypt_username(cfg, crypto_state.SUBKEY_SMTP)
    password = repo.decrypt_password(cfg, crypto_state.SUBKEY_SMTP)
    try:
        if cfg.port == 465:
            with smtplib.SMTP_SSL(cfg.host, cfg.port, timeout=_SMTP_TIMEOUT) as smtp:
                if username and password:
                    smtp.login(username, password)
        else:
            with smtplib.SMTP(cfg.host, cfg.port, timeout=_SMTP_TIMEOUT) as smtp:
                if cfg.use_starttls:
                    smtp.starttls()
                if username and password:
                    with contextlib.suppress(smtplib.SMTPNotSupportedError):
                        smtp.login(username, password)
    except (OSError, TimeoutError, smtplib.SMTPException) as exc:
        raise DomainError(
            code="SMTP_TEST_FAILED", message=str(exc), http_status=400
        ) from exc
    return {"ok": True}
