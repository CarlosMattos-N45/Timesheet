from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio

from app.core import db as db_mod
from app.core.base import Base

pytest_plugins: list[str] = []


@pytest_asyncio.fixture
async def db_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Fixture compartilhada: banco SQLite em memória temporária, tabelas criadas, sessão aberta."""
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{db_file}")
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "test-secret-key-min-32-chars-abcdef")
    from app.core import config

    config.settings = config.Settings()  # type: ignore[call-arg]
    db_mod._engine = None
    db_mod._sessionmaker = None
    engine = db_mod.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = db_mod.get_sessionmaker()
    async with sm() as s:
        yield s
    await engine.dispose()
