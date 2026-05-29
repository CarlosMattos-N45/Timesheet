"""Production entrypoint for the Timesheet Terceiros backend.

Responsibilities (executed in order by ``main()``):
1. Configure structured logging.
2. Load KEK → derive SQLCipher key → inject into ``settings`` and ``os.environ``.
3. Run Alembic migrations (cipher key already in env for ``env.py``).
4. Start Uvicorn with a single worker (no reload).

Public surface for tests:
- ``derive_db_cipher_key_hex(kek_path)``  — pure derivation helper
- ``prepare_runtime(settings)``           — idempotent env setup
- ``static_dir_for_bundle()``             — resolves static asset path
- ``run_migrations()``                    — Alembic upgrade head
- ``serve()``                             — Uvicorn launcher (not covered by unit tests)
- ``main()``                              — CLI entrypoint
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def derive_db_cipher_key_hex(kek_path: Path | str) -> str:
    """Return the 64-char hex SQLCipher key derived from the KEK at *kek_path*.

    Reads (or generates) the KEK via :func:`app.core.crypto.ensure_kek`,
    then applies HKDF-Expand with ``info=b"db"`` and hex-encodes the result.
    Deterministic: same KEK file always produces the same key.
    """
    from app.core.crypto import derive_subkey, ensure_kek, format_db_cipher_key  # noqa: PLC0415

    kek = ensure_kek(Path(kek_path))
    return format_db_cipher_key(derive_subkey(kek, info=b"db"))


def prepare_runtime(settings: object) -> None:
    """Idempotent bootstrap: derive DB cipher key from KEK and inject into *settings*.

    If ``settings.db_cipher_key`` is already set, does nothing (idempotent).
    Otherwise: loads/generates the KEK, derives the ``db`` subkey, sets
    ``settings.db_cipher_key`` and propagates the value to
    ``TIMESHEET_DB_CIPHER_KEY`` so that Alembic's ``env.py`` can pick it up.
    """
    db_cipher_key: str | None = getattr(settings, "db_cipher_key", None)
    if db_cipher_key is not None:
        # Already configured — nothing to do.
        return

    kek_path: str = getattr(settings, "kek_path", "./data/key.kek")
    hex_key = derive_db_cipher_key_hex(kek_path)

    # Mutate the settings object in-place so that db.py picks up the key
    # before creating the engine.
    object.__setattr__(settings, "db_cipher_key", hex_key)

    # Propagate to environment so Alembic env.py (sync path) can read it.
    os.environ["TIMESHEET_DB_CIPHER_KEY"] = hex_key


def static_dir_for_bundle() -> Path:
    """Return the path of the ``static/`` directory, frozen-aware.

    - PyInstaller bundle (``sys.frozen=True``): ``<_MEIPASS>/static``
    - Normal execution: ``<this file's directory>/static``

    Creates the directory if it does not exist (dev mode: avoids crash when
    ``StaticFiles`` mount is called before ``apps/web`` has been built).
    """
    if getattr(sys, "frozen", False):
        # Running inside a PyInstaller bundle.
        meipass: str = getattr(sys, "_MEIPASS", str(Path(__file__).resolve().parent))
        base = Path(meipass) / "static"
    else:
        base = Path(__file__).resolve().parent / "static"

    base.mkdir(parents=True, exist_ok=True)
    return base


def run_migrations() -> None:
    """Apply all pending Alembic migrations up to HEAD.

    Resolves ``alembic.ini`` relative to this file's location, supporting both
    frozen (PyInstaller) and non-frozen execution.
    ``TIMESHEET_DB_CIPHER_KEY`` must already be in ``os.environ`` so that
    ``alembic/env.py`` can apply ``PRAGMA key`` before any DDL.
    """
    from alembic.config import Config  # noqa: PLC0415

    from alembic import command  # noqa: PLC0415

    if getattr(sys, "frozen", False):
        meipass: str = getattr(sys, "_MEIPASS", "")
        ini_path = Path(meipass) / "alembic.ini"
        script_location = str(Path(meipass) / "alembic")
    else:
        # Non-frozen: alembic.ini lives next to apps/api/
        ini_path = Path(__file__).resolve().parent.parent / "alembic.ini"
        script_location = str(Path(__file__).resolve().parent.parent / "alembic")

    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", script_location)
    command.upgrade(cfg, "head")


def serve() -> None:
    """Start Uvicorn with a single worker (no reload, no multiprocessing)."""
    import uvicorn  # noqa: PLC0415

    from app.core.config import settings  # noqa: PLC0415
    from app.main import create_app  # noqa: PLC0415

    uvicorn.run(
        create_app(),
        host=settings.host,
        port=settings.port,
        workers=1,
        log_config=None,
    )


def main() -> None:
    """CLI entrypoint: configure → bootstrap → migrate → serve."""
    from app.core.config import settings  # noqa: PLC0415
    from app.core.logging import configure_logging  # noqa: PLC0415

    configure_logging()
    try:
        prepare_runtime(settings)
        run_migrations()
        serve()
    except Exception:
        logger.exception("Bootstrap falhou — encerrando")
        sys.exit(1)


if __name__ == "__main__":
    main()
