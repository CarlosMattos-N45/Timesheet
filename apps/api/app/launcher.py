"""Production entrypoint for the Timesheet Terceiros backend.

Responsibilities (executed in order by ``main()``):
1. Configure structured logging.
2. Load KEK → derive SQLCipher key → inject into ``settings`` and ``os.environ``.
3. Run Alembic migrations (cipher key already in env for ``env.py``).
4. Start Uvicorn with a single worker (no reload).

Invocation modes:
- ``timesheet-backend.exe``          → console mode (migrate + serve uvicorn)
- ``timesheet-backend.exe service``  → Windows Service mode (SCM dispatcher)

Public surface for tests:
- ``derive_db_cipher_key_hex(kek_path)``  — pure derivation helper
- ``prepare_runtime(settings)``           — idempotent env setup
- ``static_dir_for_bundle()``             — resolves static asset path
- ``run_migrations()``                    — Alembic upgrade head
- ``build_server()``                      — construct uvicorn.Server (shutdown-capable)
- ``run_server(server)``                  — start server.run() (blocking)
- ``serve()``                             — build + run (console shortcut)
- ``main()``                              — CLI entrypoint
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import uvicorn

logger = logging.getLogger(__name__)

_SERVER_STARTED_TIMEOUT_S = 30
_STOP_JOIN_TIMEOUT_S = 10


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
    from alembic import command  # noqa: PLC0415
    from alembic.config import Config  # noqa: PLC0415

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


def build_server() -> uvicorn.Server:
    """Construct a uvicorn.Server using settings.host/port with a single worker.

    Returns a Server instance whose ``should_exit`` attribute can be set to
    True for graceful programmatic shutdown without OS signals.
    """
    import uvicorn  # noqa: PLC0415

    from app.core.config import settings  # noqa: PLC0415
    from app.main import create_app  # noqa: PLC0415

    config = uvicorn.Config(
        create_app(),
        host=settings.host,
        port=settings.port,
        workers=1,
        log_config=None,
    )
    return uvicorn.Server(config)


def run_server(server: uvicorn.Server) -> None:
    """Start *server* (blocking).  Thin wrapper for testability."""
    server.run()


def serve() -> None:
    """Console mode — blocking, behaviour identical to the previous implementation."""
    run_server(build_server())


if sys.platform == "win32":
    import win32event  # type: ignore  # noqa: PLC0415,E402
    import win32service  # type: ignore  # noqa: PLC0415,E402
    import win32serviceutil  # type: ignore  # noqa: PLC0415,E402

    class TimesheetBackendService(win32serviceutil.ServiceFramework):  # type: ignore
        """Windows Service that wraps the uvicorn HTTP server.

        Implements the SCM protocol:
        SERVICE_START_PENDING → SERVICE_RUNNING → SERVICE_STOPPED
        """

        _svc_name_ = "TimesheetBackend"
        _svc_display_name_ = "Timesheet Backend"

        def __init__(self, args: list[str]) -> None:
            super().__init__(args)
            self._stop_event = win32event.CreateEvent(None, 0, 0, None)
            self._server: uvicorn.Server | None = None
            self._thread: threading.Thread | None = None

        def SvcDoRun(self) -> None:  # noqa: N802
            import servicemanager  # type: ignore  # noqa: PLC0415

            from app.core.config import settings  # noqa: PLC0415
            from app.core.logging import configure_logging  # noqa: PLC0415

            logger.info(
                "service start_pending",
                extra={"event": "service_start_pending", "svc_name": self._svc_name_},
            )
            self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
            try:
                configure_logging()
                prepare_runtime(settings)
                run_migrations()
                self._server = build_server()
                self._thread = threading.Thread(
                    target=self._server.run,
                    daemon=True,
                )
                self._thread.start()
                elapsed = 0.0
                while (
                    not getattr(self._server, "started", False)
                    and elapsed < _SERVER_STARTED_TIMEOUT_S
                ):
                    time.sleep(0.1)
                    elapsed += 0.1
                if not getattr(self._server, "started", False):
                    raise RuntimeError(
                        "uvicorn server não confirmou started no timeout"
                    )
                logger.info(
                    "service running",
                    extra={"event": "service_running", "svc_name": self._svc_name_},
                )
                self.ReportServiceStatus(win32service.SERVICE_RUNNING)
                win32event.WaitForSingleObject(self._stop_event, win32event.INFINITE)
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "service bootstrap falhou",
                    extra={
                        "event": "service_bootstrap_error",
                        "svc_name": self._svc_name_,
                    },
                )
                # Nunca expor str(exc): pode conter secrets (DPAPI blobs, connection strings).
                # Logar apenas tipo + camada.
                servicemanager.LogErrorMsg(
                    f"{type(exc).__name__} durante bootstrap do serviço (camada: launcher)"
                )
                # Retornar sem travar em START_PENDING: o framework reporta SERVICE_STOPPED.

        def SvcStop(self) -> None:  # noqa: N802
            logger.info(
                "service stop_pending",
                extra={"event": "service_stop_pending", "svc_name": self._svc_name_},
            )
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            if self._server is not None:
                self._server.should_exit = True
            win32event.SetEvent(self._stop_event)
            if self._thread is not None:
                self._thread.join(timeout=_STOP_JOIN_TIMEOUT_S)
                if self._thread.is_alive():
                    logger.warning(
                        "service stop_timeout",
                        extra={
                            "event": "service_stop_timeout",
                            "svc_name": self._svc_name_,
                        },
                    )
                    return
            logger.info(
                "service stopped",
                extra={"event": "service_stopped", "svc_name": self._svc_name_},
            )


def _run_service() -> None:
    # RESTRIÇÃO: nenhum código privilegiado (DPAPI, migrations, uvicorn,
    # leitura de secrets) antes de StartServiceCtrlDispatcher(). O bootstrap
    # completo ocorre apenas dentro de SvcDoRun, após o dispatcher validar
    # que o processo foi invocado pelo SCM.
    import servicemanager  # noqa: PLC0415

    servicemanager.Initialize()
    servicemanager.PrepareToHostSingle(TimesheetBackendService)
    servicemanager.StartServiceCtrlDispatcher()


def _run_console() -> None:
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


def main() -> None:
    """CLI entrypoint: route to service or console mode based on sys.argv."""
    if sys.platform == "win32" and len(sys.argv) > 1 and sys.argv[1] == "service":
        _run_service()
        return
    _run_console()


if __name__ == "__main__":
    main()
