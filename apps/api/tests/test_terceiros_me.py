from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from tests.helpers import login as _login


@pytest_asyncio.fixture
async def app_and_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
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
                nome="Maria",
                empresa_nome="ACME",
                empresa_cnpj="00000000000191",
                horario_inicio_jornada="09:00:00",
                horario_saida_almoco="12:00:00",
                horario_retorno_almoco="13:00:00",
                horario_fim_jornada="18:00:00",
                trabalha_fim_de_semana=0,
                email_contato="user@example.com",
                senha_hash=hash_password("Senha123!"),
                criado_em=datetime.now(UTC).isoformat(),
                atualizado_em=datetime.now(UTC).isoformat(),
            )
        )
        await s.commit()
    from app.main import create_app

    yield create_app(), sm
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_me_returns_terceiro_without_senha_hash(app_and_session) -> None:
    app, _ = app_and_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        tok = await _login(c)
        r = await c.get("/api/v1/terceiros/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    body = r.json()
    assert body["nome"] == "Maria"
    assert "senha_hash" not in body


@pytest.mark.asyncio
async def test_get_me_without_auth_401(app_and_session) -> None:
    app, _ = app_and_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/terceiros/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_put_me_updates_and_creates_audit_log(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import LogAuditoria, Terceiro

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        tok = await _login(c)
        r = await c.put(
            "/api/v1/terceiros/me",
            headers={"Authorization": f"Bearer {tok}"},
            json={
                "nome": "Maria Atualizada",
                "empresa_nome": "ACME",
                "empresa_cnpj": "00000000000191",
                "horario_inicio_jornada": "09:00:00",
                "horario_saida_almoco": "12:00:00",
                "horario_retorno_almoco": "13:00:00",
                "horario_fim_jornada": "18:00:00",
                "trabalha_fim_de_semana": False,
                "email_contato": "user@example.com",
                "email_destinatario_relatorio": "rh@acme.com",
            },
        )
    assert r.status_code == 200
    assert r.json()["nome"] == "Maria Atualizada"
    async with sm() as s:
        t = (await s.execute(select(Terceiro))).scalar_one()
        assert t.nome == "Maria Atualizada"
        stmt = select(LogAuditoria).where(LogAuditoria.entidade == "Terceiro")
        audits = (await s.execute(stmt)).scalars().all()
        assert len(audits) == 1
        assert audits[0].autor == "user@example.com"


@pytest.mark.asyncio
async def test_put_me_senha_revokes_all_refresh_tokens(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import RefreshToken

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        login_r = await c.post(
            "/api/v1/auth/login", json={"email": "user@example.com", "senha": "Senha123!"}
        )
        tok = login_r.json()["access_token"]
        # Mais 1 refresh para garantir multiplos ativos
        await c.post(
            "/api/v1/auth/login", json={"email": "user@example.com", "senha": "Senha123!"}
        )
        r = await c.put(
            "/api/v1/terceiros/me/senha",
            headers={"Authorization": f"Bearer {tok}"},
            json={"senha_atual": "Senha123!", "nova_senha": "NovaSenha456!"},
        )
    assert r.status_code == 204
    async with sm() as s:
        rows = (await s.execute(select(RefreshToken))).scalars().all()
        assert len(rows) >= 2
        assert all(rt.revogado_em is not None for rt in rows)


@pytest.mark.asyncio
async def test_put_me_senha_with_wrong_current_returns_401(app_and_session) -> None:
    app, _ = app_and_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        login_r = await c.post(
            "/api/v1/auth/login", json={"email": "user@example.com", "senha": "Senha123!"}
        )
        tok = login_r.json()["access_token"]
        r = await c.put(
            "/api/v1/terceiros/me/senha",
            headers={"Authorization": f"Bearer {tok}"},
            json={"senha_atual": "errada", "nova_senha": "NovaSenha456!"},
        )
    assert r.status_code == 401
    assert r.json() == {"code": "UNAUTHORIZED", "message": "Senha atual incorreta", "details": []}
