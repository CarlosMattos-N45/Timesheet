from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def app_running(tmp_path, monkeypatch):
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{tmp_path}/t.sqlite")
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "x" * 40)
    monkeypatch.setenv("TIMESHEET_KEK_PATH", str(tmp_path / "key.kek"))
    monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    monkeypatch.setenv("TIMESHEET_SCHEDULER_ENABLED", "true")
    monkeypatch.setenv("TIMESHEET_SCHEDULER_JOBSTORE", str(tmp_path / "sched.sqlite"))
    monkeypatch.setenv("TIMESHEET_PDF_DIR", str(tmp_path / "pdf"))
    from app.core import config
    from app.core import db as db_mod
    config.settings = config.Settings()  # type: ignore[call-arg]
    db_mod._engine = None
    db_mod._sessionmaker = None
    import app.models  # noqa: F401 — registers all ORM models on Base.metadata
    from app.core.base import Base
    engine = db_mod.get_engine()
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    from app.main import create_app
    from app.modules.relatorios.scheduler import start_scheduler, stop_scheduler
    start_scheduler()
    app = create_app()
    yield app
    stop_scheduler()
    await engine.dispose()


@pytest.mark.asyncio
async def test_ready_returns_200_when_db_and_scheduler_up(app_running) -> None:
    transport = ASGITransport(app=app_running)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/ready")
    assert r.status_code == 200
    assert r.json() == {"status": "ready"}


@pytest.mark.asyncio
async def test_ready_no_auth_required(app_running) -> None:
    transport = ASGITransport(app=app_running)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/ready")
    assert r.status_code != 401
    assert r.status_code != 403


@pytest.mark.asyncio
async def test_ready_returns_503_when_scheduler_disabled(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{tmp_path}/t.sqlite")
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "x" * 40)
    monkeypatch.setenv("TIMESHEET_KEK_PATH", str(tmp_path / "key.kek"))
    monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    monkeypatch.setenv("TIMESHEET_SCHEDULER_ENABLED", "false")
    from app.core import config
    from app.core import db as db_mod
    config.settings = config.Settings()  # type: ignore[call-arg]
    db_mod._engine = None
    db_mod._sessionmaker = None
    import app.models  # noqa: F401 — registers all ORM models on Base.metadata
    from app.core.base import Base
    engine = db_mod.get_engine()
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    from app.main import create_app

    # Não chama start_scheduler — scheduler permanece None
    from app.modules.relatorios import scheduler as sched_mod
    sched_mod._scheduler_instance = None  # garante limpo
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/ready")
    assert r.status_code == 503
    assert r.json() == {"status": "not-ready"}
    await engine.dispose()


@pytest.mark.asyncio
async def test_ready_returns_503_when_db_unreachable(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("TIMESHEET_DB_URL", "sqlite+aiosqlite:////tmp/__never_existed__/x.sqlite")
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "x" * 40)
    monkeypatch.setenv("TIMESHEET_KEK_PATH", str(tmp_path / "key.kek"))
    monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    monkeypatch.setenv("TIMESHEET_SCHEDULER_ENABLED", "true")
    monkeypatch.setenv("TIMESHEET_SCHEDULER_JOBSTORE", str(tmp_path / "sched.sqlite"))
    from app.core import config
    from app.core import db as db_mod
    config.settings = config.Settings()  # type: ignore[call-arg]
    db_mod._engine = None
    db_mod._sessionmaker = None
    from app.main import create_app
    from app.modules.relatorios.scheduler import start_scheduler, stop_scheduler
    start_scheduler()
    try:
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
            r = await c.get("/api/v1/ready")
        assert r.status_code == 503
    finally:
        stop_scheduler()
