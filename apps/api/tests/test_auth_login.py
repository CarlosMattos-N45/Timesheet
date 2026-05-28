from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def app_and_terceiro(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{tmp_path}/t.sqlite")
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "x" * 40)
    from app.core import config
    from app.core import db as db_mod

    config.settings = config.Settings()  # type: ignore[call-arg]
    db_mod._engine = None
    db_mod._sessionmaker = None
    import app.models  # noqa: F401 — registers all ORM models on Base.metadata
    from app.core.base import Base
    from app.core.security import hash_password
    from app.models import Terceiro

    engine = db_mod.get_engine()
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    sm = db_mod.get_sessionmaker()
    async with sm() as s:
        s.add(
            Terceiro(
                id="t-1",
                nome="X",
                empresa_nome="Y",
                empresa_cnpj="00000000000191",
                horario_inicio_jornada="09:00:00",
                horario_saida_almoco="12:00:00",
                horario_retorno_almoco="13:00:00",
                horario_fim_jornada="18:00:00",
                trabalha_fim_de_semana=0,
                email_contato="user@example.com",
                senha_hash=hash_password("MinhaSenha123!"),
                criado_em=datetime.now(UTC).isoformat(),
                atualizado_em=datetime.now(UTC).isoformat(),
            )
        )
        await s.commit()
    from app.main import create_app

    yield create_app()
    await engine.dispose()


@pytest.mark.asyncio
async def test_login_success_returns_token_pair(app_and_terceiro) -> None:
    transport = ASGITransport(app=app_and_terceiro)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "senha": "MinhaSenha123!"},
        )
    assert r.status_code == 200, r.json()
    body = r.json()
    assert "access_token" in body and "refresh_token" in body
    assert body["terceiro_id"] == "t-1"
    assert body["expires_in"] == 900


@pytest.mark.asyncio
async def test_login_invalid_password(app_and_terceiro) -> None:
    transport = ASGITransport(app=app_and_terceiro)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "senha": "errada123"},
        )
    assert r.status_code == 401
    assert r.json() == {
        "code": "UNAUTHORIZED",
        "message": "E-mail ou senha inválidos",
        "details": [],
    }


@pytest.mark.asyncio
async def test_login_unknown_email(app_and_terceiro) -> None:
    transport = ASGITransport(app=app_and_terceiro)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post(
            "/api/v1/auth/login",
            json={"email": "nope@example.com", "senha": "MinhaSenha123!"},
        )
    assert r.status_code == 401
    assert r.json()["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_login_rate_limit_5_per_minute(app_and_terceiro) -> None:
    transport = ASGITransport(app=app_and_terceiro)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        last = None
        for _ in range(6):
            last = await c.post(
                "/api/v1/auth/login",
                json={"email": "user@example.com", "senha": "errada"},
            )
        assert last is not None
        assert last.status_code == 429
        assert last.json()["code"] == "RATE_LIMITED"
