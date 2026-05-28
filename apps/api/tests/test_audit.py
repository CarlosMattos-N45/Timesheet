from __future__ import annotations

import json
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import db as db_mod
from app.core.audit import log_audit
from app.core.base import Base
from app.models import LogAuditoria


@pytest_asyncio.fixture
async def session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{db_file}")
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


@pytest.mark.asyncio
async def test_log_audit_inserts_row(session: AsyncSession) -> None:
    await log_audit(
        session, entidade="Jornada", entidade_id="j-1", autor="user@x.com",
        antes={"a": 1}, depois={"a": 2}, motivo="ajuste",
    )
    await session.commit()
    rows = (await session.execute(select(LogAuditoria))).scalars().all()
    assert len(rows) == 1
    r = rows[0]
    assert r.entidade == "Jornada"
    assert r.entidade_id == "j-1"
    assert r.autor == "user@x.com"
    assert json.loads(r.antes_json) == {"a": 1}
    assert json.loads(r.depois_json) == {"a": 2}
    assert r.motivo == "ajuste"


@pytest.mark.asyncio
async def test_log_audit_rejects_invalid_entidade(session: AsyncSession) -> None:
    with pytest.raises(ValueError, match="entidade"):
        await log_audit(
            session, entidade="NaoExiste", entidade_id="x", autor="u",
            antes=None, depois={"a": 1}, motivo=None,
        )


@pytest.mark.asyncio
async def test_log_audit_accepts_null_antes_and_motivo(session: AsyncSession) -> None:
    await log_audit(
        session, entidade="Terceiro", entidade_id="t-1", autor="u",
        antes=None, depois={"nome": "Maria"}, motivo=None,
    )
    await session.commit()
    r = (await session.execute(select(LogAuditoria))).scalar_one()
    assert r.antes_json is None
    assert r.motivo is None
