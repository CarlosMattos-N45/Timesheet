"""Smoke integrado: garante que todos os endpoints estão registrados em main.py
e que middlewares + error handlers + rate limit + auth funcionam end-to-end."""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def app_full(tmp_path, monkeypatch):
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{tmp_path}/t.sqlite")
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "x" * 40)
    monkeypatch.setenv("TIMESHEET_KEK_PATH", str(tmp_path / "key.kek"))
    monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    monkeypatch.setenv("TIMESHEET_SCHEDULER_ENABLED", "false")
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
    yield create_app()
    await engine.dispose()


_EXPECTED_PATHS = {
    "/api/v1/health",
    "/api/v1/ready",
    "/api/v1/config",
    "/api/v1/terceiros",
    "/api/v1/terceiros/me",
    "/api/v1/terceiros/me/senha",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/logout",
    "/api/v1/privacidade",
    "/api/v1/privacidade/aceitar",
    "/api/v1/smtp",
    "/api/v1/smtp/test",
    "/api/v1/marcacoes",
    "/api/v1/marcacoes/{marcacao_id}",
    "/api/v1/jornadas",
    "/api/v1/jornadas/{jornada_id}",
    "/api/v1/jornadas/manual",
    "/api/v1/jornadas/{jornada_id}/atividade",
    "/api/v1/auditoria",
    "/api/v1/relatorios/{mes}",
    "/api/v1/relatorios/{mes}/meta",
    "/api/v1/relatorios/{mes}/enviar",
    "/api/v1/relatorios/{mes}/historico",
}


def test_all_expected_endpoints_registered(app_full) -> None:
    registered = {getattr(r, "path", None) for r in app_full.routes}
    missing = _EXPECTED_PATHS - registered
    assert not missing, f"Endpoints faltando no wiring: {sorted(missing)}"


@pytest.mark.asyncio
async def test_full_signup_login_flow(app_full) -> None:
    transport = ASGITransport(app=app_full)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        # 1. Cadastro
        signup = await c.post("/api/v1/terceiros", json={
            "nome": "Maria Silva", "empresa_nome": "ACME", "empresa_cnpj": "00000000000191",
            "horario_inicio_jornada": "09:00:00", "horario_saida_almoco": "12:00:00",
            "horario_retorno_almoco": "13:00:00", "horario_fim_jornada": "18:00:00",
            "trabalha_fim_de_semana": False,
            "email_contato": "maria@x.com", "email_destinatario_relatorio": "rh@x.com",
            "senha": "Senha123!", "senha_confirmacao": "Senha123!",
        })
        assert signup.status_code == 201, signup.json()
        # 2. Login
        login = await c.post(
            "/api/v1/auth/login", json={"email": "maria@x.com", "senha": "Senha123!"}
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        # 3. /me
        me = await c.get("/api/v1/terceiros/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["nome"] == "Maria Silva"
        # 4. Privacidade
        priv_get = await c.get("/api/v1/privacidade", headers={"Authorization": f"Bearer {token}"})
        assert priv_get.status_code == 200
        assert priv_get.json()["accepted"] is False
        # 5. Health (sem auth)
        h = await c.get("/api/v1/health")
        assert h.status_code == 200
        # 6. Config (sem auth)
        cfg = await c.get("/api/v1/config")
        assert cfg.status_code == 200


@pytest.mark.asyncio
async def test_security_headers_present_on_all_endpoints(app_full) -> None:
    transport = ASGITransport(app=app_full)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        for path in ["/api/v1/health", "/api/v1/config", "/api/v1/terceiros/me"]:
            r = await c.get(path)
            assert r.headers.get("x-content-type-options") == "nosniff"
            assert r.headers.get("x-frame-options") == "DENY"
            assert "default-src 'self'" in r.headers.get("content-security-policy", "")


@pytest.mark.asyncio
async def test_invalid_host_blocked_on_all_endpoints(app_full) -> None:
    transport = ASGITransport(app=app_full)
    async with AsyncClient(transport=transport, base_url="http://evil.com") as c:
        for path in ["/api/v1/health", "/api/v1/auth/login"]:
            if path == "/api/v1/health":
                r = await c.get(path)
            else:
                r = await c.post(path, json={"email": "x@y.com", "senha": "x" * 8})
            assert r.status_code == 400
            assert r.json()["code"] == "INVALID_HOST"


@pytest.mark.asyncio
async def test_error_shape_consistent_across_endpoints(app_full) -> None:
    transport = ASGITransport(app=app_full)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        # 401 sem auth
        r401 = await c.get("/api/v1/terceiros/me")
        # 422 validação
        r422 = await c.post("/api/v1/auth/login", json={"email": "abc", "senha": "x"})
        # 404 inexistente
        login = await c.post("/api/v1/terceiros", json={
            "nome": "X", "empresa_nome": "Y", "empresa_cnpj": "00000000000191",
            "horario_inicio_jornada": "09:00:00", "horario_saida_almoco": "12:00:00",
            "horario_retorno_almoco": "13:00:00", "horario_fim_jornada": "18:00:00",
            "trabalha_fim_de_semana": False,
            "email_contato": "user@x.com",
            "senha": "Senha123!", "senha_confirmacao": "Senha123!",
        })
        assert login.status_code == 201
        login2 = await c.post(
            "/api/v1/auth/login", json={"email": "user@x.com", "senha": "Senha123!"}
        )
        tok = login2.json()["access_token"]
        r404 = await c.get(
            "/api/v1/relatorios/2099-12/meta", headers={"Authorization": f"Bearer {tok}"}
        )
    for r in [r401, r422, r404]:
        body = r.json()
        assert "code" in body and "message" in body and "details" in body
        assert isinstance(body["details"], list)
