from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session, get_sessionmaker


@pytest_asyncio.fixture
async def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{db_file}")
    monkeypatch.delenv("TIMESHEET_DB_CIPHER_KEY", raising=False)
    # Recarrega settings + engine
    from app.core import config, db

    config.settings = config.Settings()  # type: ignore[call-arg]
    db._engine = None
    db._sessionmaker = None
    return db_file


@pytest.mark.asyncio
async def test_session_executes_select_1(db_path: Path) -> None:
    sm = get_sessionmaker()
    async with sm() as session:  # type: AsyncSession
        result = await session.execute(text("SELECT 1"))
        assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_pragma_foreign_keys_is_on(db_path: Path) -> None:
    sm = get_sessionmaker()
    async with sm() as session:
        row = (await session.execute(text("PRAGMA foreign_keys"))).scalar_one()
        assert row == 1, "foreign_keys must be ON in every session"


@pytest.mark.asyncio
async def test_pragma_journal_mode_is_wal(db_path: Path) -> None:
    sm = get_sessionmaker()
    async with sm() as session:
        mode = (await session.execute(text("PRAGMA journal_mode"))).scalar_one()
        assert str(mode).lower() == "wal"


@pytest.mark.asyncio
async def test_get_session_dependency_yields_and_closes(db_path: Path) -> None:
    seen: list[bool] = []

    async def consumer() -> AsyncIterator[AsyncSession]:
        async for s in get_session():
            seen.append(s.is_active)
            yield s

    async for s in consumer():
        await s.execute(text("SELECT 1"))
    assert seen == [True]


@pytest.mark.asyncio
async def test_dbcheck_endpoint_only_in_dev(db_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TIMESHEET_DEV", "true")
    from app.core import config
    from app.main import create_app

    config.settings = config.Settings()  # type: ignore[call-arg]
    app: FastAPI = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        r = await client.get("/api/v1/_dbcheck")
        assert r.status_code == 200
        assert r.json() == {"db": "ok", "result": 1}


@pytest.mark.asyncio
async def test_dbcheck_endpoint_absent_in_prod(
    db_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TIMESHEET_DEV", "false")
    from app.core import config
    from app.main import create_app

    config.settings = config.Settings()  # type: ignore[call-arg]
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        r = await client.get("/api/v1/_dbcheck")
        assert r.status_code == 404


def test_invalid_cipher_key_rejected_at_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TIMESHEET_DB_CIPHER_KEY", "naoehex")  # 7 chars, sem ser hex valido
    from pydantic import ValidationError

    from app.core import config

    with pytest.raises(ValidationError):
        config.Settings()  # type: ignore[call-arg]


def test_valid_cipher_key_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TIMESHEET_DB_CIPHER_KEY", "a" * 64)
    from app.core import config

    s = config.Settings()  # type: ignore[call-arg]
    assert s.db_cipher_key == "a" * 64
