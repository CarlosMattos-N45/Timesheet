---
checkpoint: null
complexity: P
created_at: "2026-05-28 09:42:46"
criteria:
    - done: true
      test: pytest -k test_ready_returns_200_when_db_and_scheduler_up
      text: GET /api/v1/ready sem auth com banco up + scheduler running retorna 200 {status:ready}
    - done: true
      test: pytest -k test_ready_no_auth_required
      text: GET /ready não exige Bearer (status_code != 401 != 403)
    - done: true
      test: pytest -k test_ready_returns_503_when_scheduler_disabled
      text: GET /ready com TIMESHEET_SCHEDULER_ENABLED=false (scheduler não iniciado) retorna 503 {status:not-ready}
    - done: true
      test: pytest -k test_ready_returns_503_when_db_unreachable
      text: GET /ready com banco inacessível (URL inválida) retorna 503 sem expor detalhe do erro
    - done: true
      test: pytest -k test_config_returns_settings_snapshot
      text: GET /api/v1/config retorna {port, version, timezone:'America/Sao_Paulo', dev_mode} sem auth
    - done: true
      test: pytest -k test_config_no_auth_required
      text: GET /config não exige auth
    - done: true
      test: pytest -k test_all_expected_endpoints_registered
      text: Todos os endpoints esperados (sistema, auth, terceiros, privacidade, smtp, marcacoes, jornadas, atividades, auditoria, relatorios) estão registrados em app.routes
    - done: true
      test: pytest -k test_full_signup_login_flow
      text: Fluxo completo cadastro -> login -> /me -> /privacidade -> /health -> /config funciona end-to-end
    - done: true
      test: pytest -k test_security_headers_present_on_all_endpoints
      text: Security headers (X-Content-Type-Options:nosniff, X-Frame-Options:DENY, CSP) presentes em todos endpoints
    - done: true
      test: pytest -k test_invalid_host_blocked_on_all_endpoints
      text: Host header invalido bloqueia /health e /auth/login com 400 INVALID_HOST
    - done: true
      test: pytest -k test_error_shape_consistent_across_endpoints
      text: Shape de erro {code, message, details:list} consistente em 401, 422, 404 de endpoints diferentes
    - done: true
      test: grep -E 'include_router|limiter.limit' apps/api/app/main.py
      text: main.py registra os 10 routers na ordem canonica e aplica rate limit em /auth/login e /auth/refresh
    - done: true
      test: pytest tests/ -v
      text: Suite completa passa apos wiring final (todos os modulos integrados)
deps:
    - TASK-012
    - TASK-013
    - TASK-014
    - TASK-015
    - TASK-016
    - TASK-017
    - TASK-018
id: TASK-019
linter: ruff check . && mypy --strict app
n45_version: 0.2.0
persona: backend
phase: Phase 3 — Backend por Domínio
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: done
tdd:
    green: true
    red: true
    refactor: true
tests: pytest tests/test_ready_endpoint.py tests/test_config_endpoint.py tests/test_smoke_integration.py -v
title: 'Wiring final + /ready + /config: registra todos routers em main.py, /api/v1/ready (db+scheduler check), /config, smoke integrado'
updated_at: "2026-05-28 12:20:36"
---
## Contexto

Esta é a **task final de wiring da Phase 3**. Implementa o endpoint `/api/v1/ready` (readiness probe — RF-013), atualiza `/api/v1/config`, garante que todos os routers das tasks anteriores estão registrados em `main.py`, e roda smoke integrado de todos os endpoints juntos para detectar conflitos de wiring.

Per regra: "Task final de wiring — obrigatória quando ≥2 tasks criam módulos que precisam ser registrados em arquivo central". As tasks TASK-013..018 cada uma modifica `main.py` para `app.include_router(...)` do seu domínio. Esta task **revisita** `main.py` final para:

1. Confirmar todos os 8 routers registrados na ordem correta: `sistema` (público) → `auth` → `terceiros` → `privacidade` → `smtp` → `marcacoes` → `jornadas` → `atividades` → `auditoria` → `relatorios`.
2. Implementar `GET /api/v1/ready` (sem auth, sem detalhes internos): verifica `SELECT 1` no banco + `scheduler.state == STATE_RUNNING`. Retorna `200 {"status": "ready"}` ou `503 {"status": "not-ready"}`.
3. Atualizar `GET /api/v1/config` para retornar `{port, version, timezone, dev_mode}` (consumido pelo tray icon do Agente).
4. Smoke test integrado: roda o app, exercita 1 endpoint de cada domínio em sequência, valida que não há regressão de wiring (middlewares aplicados, rate limit no /auth/login, error handler padronizado em todos).

Estado atual (fim TASK-018):
- 8 routers de domínio implementados.
- `main.py` modificado por cada task — possíveis conflitos de ordenação ou dupla-aplicação de middleware podem existir.
- `app.modules.relatorios.scheduler.get_scheduler()` retorna o scheduler ativo ou None.

Esta task **não** adiciona lógica de negócio nova — só wiring + 2 endpoints (`/ready`, `/config`) + suite de smoke integrado.

## Comportamento Esperado

| Entrada / Ação | Saída / Efeito esperado |
| --- | --- |
| `GET /api/v1/ready` sem auth, banco up + scheduler running | `200`, body `{"status":"ready"}` |
| `GET /api/v1/ready` sem auth, banco indisponível | `503`, body `{"status":"not-ready"}` (sem expor detalhe) |
| `GET /api/v1/ready` sem auth, scheduler não running (TIMESHEET_SCHEDULER_ENABLED=false) | `503` |
| `GET /api/v1/ready` retorna < 50ms em condição normal | (não testável programaticamente sem flaky — log estruturado) |
| `GET /api/v1/config` sem auth | `200`, body `{"port":8765,"version":"<__version__>","timezone":"America/Sao_Paulo","dev_mode":false}` |
| `GET /api/v1/health` (intacto) | `200`, body `{"status":"ok","version":"<__version__>"}` |
| `GET /api/v1/health` retorna < 50ms (sem tocar banco) | OK |
| `GET /api/v1/relatorios/2026-05/meta` com app inicializado completo | `404 NOT_FOUND` (sem dados) — não falha com erro de wiring |
| `POST /api/v1/auth/login` 6× rápidas | 6ª retorna `429` — rate limit aplicado |
| Toda resposta tem `X-Content-Type-Options: nosniff` | Confirmado para qualquer endpoint |
| Toda resposta de erro segue shape `{code, message, details}` | Confirmado para 4xx/5xx |
| `app.routes` contém todos os paths esperados (`/api/v1/auth/login`, `/api/v1/terceiros/me`, `/api/v1/jornadas`, ...) | Smoke list |

## TDD (red → green → refactor)

**Testes a escrever antes da implementação:**

### `apps/api/tests/test_ready_endpoint.py`

```python
from __future__ import annotations

from pathlib import Path

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
    from app.core import config, db as db_mod
    config.settings = config.Settings()  # type: ignore[call-arg]
    db_mod._engine = None
    db_mod._sessionmaker = None
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
    from app.core import config, db as db_mod
    config.settings = config.Settings()  # type: ignore[call-arg]
    db_mod._engine = None
    db_mod._sessionmaker = None
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
    from app.core import config, db as db_mod
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
```

### `apps/api/tests/test_config_endpoint.py`

```python
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.mark.asyncio
async def test_config_returns_settings_snapshot(monkeypatch) -> None:
    monkeypatch.setenv("TIMESHEET_PORT", "8765")
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "x" * 40)
    monkeypatch.setenv("TIMESHEET_DEV", "false")
    from app.core import config
    config.settings = config.Settings()  # type: ignore[call-arg]
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/config")
    assert r.status_code == 200
    body = r.json()
    assert body["port"] == 8765
    assert body["timezone"] == "America/Sao_Paulo"
    assert body["dev_mode"] is False
    assert body["version"]


@pytest.mark.asyncio
async def test_config_no_auth_required(monkeypatch) -> None:
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "x" * 40)
    from app.core import config
    config.settings = config.Settings()  # type: ignore[call-arg]
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/config")
    assert r.status_code == 200
```

### `apps/api/tests/test_smoke_integration.py`

```python
"""Smoke integrado: garante que todos os endpoints estão registrados em main.py
e que middlewares + error handlers + rate limit + auth funcionam end-to-end."""
from __future__ import annotations

from pathlib import Path

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
    from app.core import config, db as db_mod
    config.settings = config.Settings()  # type: ignore[call-arg]
    db_mod._engine = None
    db_mod._sessionmaker = None
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
        login = await c.post("/api/v1/auth/login", json={"email": "maria@x.com", "senha": "Senha123!"})
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
            r = await c.get(path) if path == "/api/v1/health" else await c.post(path, json={"email": "x@y.com", "senha": "x" * 8})
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
        login2 = await c.post("/api/v1/auth/login", json={"email": "user@x.com", "senha": "Senha123!"})
        tok = login2.json()["access_token"]
        r404 = await c.get("/api/v1/relatorios/2099-12/meta", headers={"Authorization": f"Bearer {tok}"})
    for r in [r401, r422, r404]:
        body = r.json()
        assert "code" in body and "message" in body and "details" in body
        assert isinstance(body["details"], list)
```

**Refatoração:** Após o green, considerar mover `_EXPECTED_PATHS` para `app/core/__init__.py` como tupla, exposta para futuros testes de wiring.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| --- | --- | --- |
| `apps/api/app/modules/sistema/router.py` | Modificar | Adicionar `GET /api/v1/ready` (sem auth, sem detalhes) e atualizar `GET /api/v1/config` (port, version, timezone, dev_mode) |
| `apps/api/app/main.py` | Modificar | Revisar ordem de `include_router`; confirmar `app.state.limiter`, middlewares (security headers, host, slowapi), error handlers; aplicar rate limit em `/auth/login` e `/auth/refresh` se ainda não aplicado |
| `apps/api/tests/test_ready_endpoint.py` | Criar | 4 testes |
| `apps/api/tests/test_config_endpoint.py` | Criar | 2 testes |
| `apps/api/tests/test_smoke_integration.py` | Criar | 5 testes |

> Total: 5 arquivos. Dentro do orçamento. Esta task **apenas finaliza wiring** — nenhuma criação nova de router/repo/service.

### Detalhamento Técnico

**1. `apps/api/app/modules/sistema/router.py`** — modificar (manter o que existe):

```python
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.core.config import settings
from app.core.db import get_session
from app.core.deps import CurrentTerceiroDep

router = APIRouter(prefix="/api/v1", tags=["sistema"])
router_dev = APIRouter(prefix="/api/v1", tags=["sistema-dev"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@router.get("/config")
async def config_endpoint() -> dict[str, object]:
    return {
        "port": settings.port,
        "version": __version__,
        "timezone": "America/Sao_Paulo",
        "dev_mode": settings.dev_mode,
    }


@router.get("/ready")
async def ready(response: Response, session: SessionDep) -> dict[str, str]:
    """Readiness probe — sem auth, sem detalhes internos.
    Verifica: SELECT 1 no banco + scheduler running.
    Retorna 503 + {"status": "not-ready"} em qualquer falha; latência < 50ms em sucesso.
    """
    # Banco
    try:
        await session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        response.status_code = 503
        return {"status": "not-ready"}
    # Scheduler (importado lazy para evitar dep circular em testes que não carregam relatorios)
    try:
        from apscheduler.schedulers.base import STATE_RUNNING
        from app.modules.relatorios.scheduler import get_scheduler
        sched = get_scheduler()
        if sched is None or sched.state != STATE_RUNNING:
            response.status_code = 503
            return {"status": "not-ready"}
    except Exception:
        response.status_code = 503
        return {"status": "not-ready"}
    return {"status": "ready"}


# Manter rotas dev existentes (_dbcheck, _auth_smoke, /auth/_smoke_login) — TASK-012 já criou.
@router_dev.get("/_dbcheck")
async def dbcheck(session: SessionDep) -> dict[str, object]:
    result = (await session.execute(text("SELECT 1"))).scalar_one()
    return {"db": "ok", "result": result}


@router_dev.get("/_auth_smoke")
async def auth_smoke(t: CurrentTerceiroDep) -> dict[str, str]:
    return {"terceiro_id": t.id}


class _SmokeLoginBody(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=8)


@router_dev.post("/auth/_smoke_login")
async def smoke_login(request: Request, body: _SmokeLoginBody) -> dict[str, str]:  # noqa: ARG001
    return {"status": "ok"}


def bind_smoke_rate_limit(app: FastAPI) -> None:
    """Aplica @limiter.limit(settings.rate_limit_login) ao endpoint _smoke_login."""
    limiter = app.state.limiter
    for route in app.routes:
        if getattr(route, "path", "") == "/api/v1/auth/_smoke_login":
            route.endpoint = limiter.limit(settings.rate_limit_login)(route.endpoint)
            route.dependant.call = route.endpoint  # type: ignore[attr-defined]
            return
```

**2. `apps/api/app/main.py`** — versão consolidada (substitui o acumulado de TASK-012..018):

```python
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app import __version__
from app.core import config as _config
from app.core.db import dispose_engine
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import (
    HostHeaderValidationMiddleware,
    SecurityHeadersMiddleware,
    make_limiter,
)
from app.modules.atividades.router import router as atividades_router
from app.modules.auditoria.router import router as auditoria_router
from app.modules.auth.router import router as auth_router
from app.modules.jornadas.router import router as jornadas_router
from app.modules.marcacoes.router import router as marcacoes_router
from app.modules.privacidade.router import router as privacidade_router
from app.modules.relatorios.router import router as relatorios_router
from app.modules.sistema.router import bind_smoke_rate_limit
from app.modules.sistema.router import router as sistema_router
from app.modules.sistema.router import router_dev as sistema_router_dev
from app.modules.smtp.router import router as smtp_router
from app.modules.terceiros.router import router as terceiros_router


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    configure_logging()
    from app.core import crypto_state
    crypto_state.configure()
    from app.modules.relatorios.invalidation import register_invalidation_listener
    register_invalidation_listener()
    from app.modules.relatorios.scheduler import start_scheduler, stop_scheduler
    start_scheduler()
    yield
    stop_scheduler()
    await dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title="TimeSheet Terceiros API",
        version=__version__,
        lifespan=_lifespan,
        docs_url="/docs" if _config.settings.dev_mode else None,
        redoc_url="/redoc" if _config.settings.dev_mode else None,
        openapi_url="/openapi.json" if _config.settings.dev_mode else None,
    )

    # Middlewares + limiter + error handlers (ordem importa: SlowAPI dentro, security headers fora)
    app.state.limiter = make_limiter()
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(HostHeaderValidationMiddleware)
    install_error_handlers(app)

    @app.exception_handler(RateLimitExceeded)
    async def _rl(_req, _exc):  # type: ignore[no-untyped-def]
        return JSONResponse(
            status_code=429,
            content={
                "code": "RATE_LIMITED",
                "message": "Muitas tentativas. Tente novamente em alguns instantes.",
                "details": [],
            },
        )

    # ROUTERS — ordem canônica
    app.include_router(sistema_router)            # /health /config /ready
    app.include_router(auth_router)               # /auth/*
    app.include_router(terceiros_router)          # /terceiros/*
    app.include_router(privacidade_router)        # /privacidade/*
    app.include_router(smtp_router)               # /smtp/*
    app.include_router(marcacoes_router)          # /marcacoes/*
    app.include_router(jornadas_router)           # /jornadas/*
    app.include_router(atividades_router)         # /jornadas/{id}/atividade
    app.include_router(auditoria_router)          # /auditoria
    app.include_router(relatorios_router)         # /relatorios/*

    if _config.settings.dev_mode:
        app.include_router(sistema_router_dev)
        bind_smoke_rate_limit(app)

    # Rate limit aplicado aos endpoints reais de auth
    limiter = app.state.limiter
    for route in app.routes:
        p = getattr(route, "path", "")
        if p == "/api/v1/auth/login":
            route.endpoint = limiter.limit(_config.settings.rate_limit_login)(route.endpoint)
            route.dependant.call = route.endpoint  # type: ignore[attr-defined]
        elif p == "/api/v1/auth/refresh":
            route.endpoint = limiter.limit(_config.settings.rate_limit_refresh)(route.endpoint)
            route.dependant.call = route.endpoint  # type: ignore[attr-defined]

    return app


app = create_app()
```

## Contratos com camadas adjacentes

```
Produz para:
  Phase 4 (Frontend):
    - /api/v1/ready (sem auth) consumido pelo loader inicial / Axios interceptor para mostrar "Conectando ao backend..." na startup.
    - /api/v1/config (sem auth) consumido pelo bootstrap React para conhecer port/timezone/dev_mode.
  Phase 5 (Empacotamento):
    - /api/v1/ready usado pelo instalador MSI WiX para aguardar Backend pronto após start do Service.
  Phase 5 (Agente .NET):
    - /api/v1/ready usado pelo tray icon para sinalizar conectividade (verde/vermelho).

Consome de:
  TODOS os módulos (TASK-012..018) — esta é a task de wiring final.

Erros:
  - 503 em /ready quando banco indisponível OU scheduler não rodando.
  - Demais erros mantidos pelos endpoints originais.
```

## Contrato HTTP

```
GET /api/v1/ready   (sem auth)
Response 200: {"status": "ready"}
Response 503: {"status": "not-ready"}   // sem expor detalhes (auditoria/seguranca)

GET /api/v1/config   (sem auth)
Response 200: {"port": 8765, "version": "0.1.0", "timezone": "America/Sao_Paulo", "dev_mode": false}

GET /api/v1/health   (intacto, sem auth)
Response 200: {"status": "ok", "version": "0.1.0"}
```

**Validação obrigatória pelo executor antes de marcar done:**

1. `cd apps/api && pip install -e ".[dev]"`.
2. `cd apps/api && TIMESHEET_ALLOW_PLAIN_KEK=1 TIMESHEET_SCHEDULER_ENABLED=false pytest tests/test_ready_endpoint.py tests/test_config_endpoint.py tests/test_smoke_integration.py -v` — todos passam.
3. `cd apps/api && TIMESHEET_ALLOW_PLAIN_KEK=1 TIMESHEET_SCHEDULER_ENABLED=false pytest tests/ -v` — suite completa passa (todos os 8 domínios + smoke).
4. `cd apps/api && ruff check .` sem warnings.
5. `cd apps/api && mypy --strict app` sem erros.
6. **Smoke manual**:
   ```bash
   TIMESHEET_JWT_SECRET=$(python -c 'import secrets;print(secrets.token_urlsafe(48))') \
   TIMESHEET_ALLOW_PLAIN_KEK=1 \
   uvicorn app.main:app --host 127.0.0.1 --port 8765 &
   sleep 3
   curl -fsS http://127.0.0.1:8765/api/v1/health     # 200
   curl -fsS http://127.0.0.1:8765/api/v1/ready      # 200 ou 503 (se scheduler off em CI)
   curl -fsS http://127.0.0.1:8765/api/v1/config     # 200
   ```
7. `make smoke` continua passando (Phase 1 gate).

> Executor DEVE rodar 1–7 e garantir saída 0 antes de retornar. Falha = task não concluída.

**Refatoração:** Após o green, considerar criar `app/core/routes.py` com `EXPECTED_PATHS: tuple[str, ...]` exposto, para `test_smoke_integration` consumir como source-of-truth. Considerar mover `bind_smoke_rate_limit` para `app.core.middleware` quando outro endpoint smoke for adicionado.
