from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core import db as db_mod
from app.core.base import Base
from app.core.deps import CurrentTerceiroDep
from app.core.errors import install_error_handlers
from app.core.security import create_access_token
from app.models import Terceiro


@pytest_asyncio.fixture
async def app_with_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
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
        t = Terceiro(
            id="t-42", nome="A", empresa_nome="B", empresa_cnpj="00000000000191",
            horario_inicio_jornada="09:00:00", horario_saida_almoco="12:00:00",
            horario_retorno_almoco="13:00:00", horario_fim_jornada="18:00:00",
            trabalha_fim_de_semana=0, email_contato="a@b.com", senha_hash="h",
            criado_em=datetime.now(UTC).isoformat(), atualizado_em=datetime.now(UTC).isoformat(),
        )
        s.add(t)
        await s.commit()

    app = FastAPI()
    install_error_handlers(app)

    @app.get("/me")
    async def me(t: CurrentTerceiroDep) -> dict[str, str]:
        return {"id": t.id}

    yield app
    await engine.dispose()


@pytest.mark.asyncio
async def test_current_terceiro_valid_token(app_with_session: FastAPI) -> None:
    token = create_access_token({"sub": "t-42"})
    transport = ASGITransport(app=app_with_session)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
        r = await client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json() == {"id": "t-42"}


@pytest.mark.asyncio
async def test_current_terceiro_missing_header(app_with_session: FastAPI) -> None:
    transport = ASGITransport(app=app_with_session)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
        r = await client.get("/me")
    assert r.status_code == 401
    assert r.json()["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_current_terceiro_expired_token(app_with_session: FastAPI) -> None:
    token = create_access_token({"sub": "t-42"}, ttl_seconds=-1)
    transport = ASGITransport(app=app_with_session)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
        r = await client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
