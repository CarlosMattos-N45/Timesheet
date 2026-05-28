"""Global crypto state: SMTP subkey kept in memory after KEK load."""
from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.core.crypto import derive_subkey, ensure_kek

SUBKEY_SMTP: bytes = b""


def configure() -> None:
    """Idempotent. Lê KEK do disco e deriva subkey SMTP."""
    global SUBKEY_SMTP
    if SUBKEY_SMTP:
        return
    kek = ensure_kek(Path(settings.kek_path))
    SUBKEY_SMTP = derive_subkey(kek, info=b"smtp")


def reset_for_tests() -> None:
    """Limpa estado global. Apenas para testes."""
    global SUBKEY_SMTP
    SUBKEY_SMTP = b""
