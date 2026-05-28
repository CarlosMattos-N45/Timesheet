---
checkpoint: null
complexity: G
created_at: "2026-05-28 09:19:57"
criteria:
    - done: false
      test: pytest -k test_hash_and_verify_password_roundtrip or test_verify_password_returns_false_for_wrong_password or test_hash_password_uses_argon2id
      text: hash_password produz Argon2id e verify_password retorna True para senha correta, False para errada
    - done: false
      test: pytest -k test_create_access_token_contains_required_claims or test_decode_expired_token_raises
      text: create_access_token contém claims sub/exp/iat/jti/type=access e decode rejeita expirado com DomainError(code=UNAUTHORIZED)
    - done: false
      test: pytest -k test_create_refresh_token_persists_in_db or test_rotate_refresh_token_revokes_old_and_issues_new
      text: create_refresh_token persiste RefreshToken(token_hash=sha256(jwt)) e rotate revoga antigo + emite novo par
    - done: false
      test: pytest -k test_reuse_of_revoked_token_revokes_full_chain
      text: Reuso de refresh token revogado revoga toda a cadeia do terceiro
    - done: false
      test: pytest -k test_validation_error_returns_padronizado or test_domain_error_serializes_padronizado
      text: RequestValidationError retorna 422 com shape {code:VALIDATION_ERROR,message,details:[{field,issue}]} e DomainError serializa com http_status correto
    - done: false
      test: pytest -k test_response_has_security_headers
      text: Toda resposta contem X-Content-Type-Options:nosniff, X-Frame-Options:DENY e CSP com default-src self + script-src self + style-src self unsafe-inline
    - done: false
      test: pytest -k test_invalid_host_rejected or test_valid_host_localhost_passes
      text: Host header diferente de 127.0.0.1/localhost retorna 400 com code=INVALID_HOST; localhost passa 200
    - done: false
      test: pytest -k test_log_audit_inserts_row or test_log_audit_rejects_invalid_entidade or test_log_audit_accepts_null_antes_and_motivo
      text: log_audit insere LogAuditoria com antes_json/depois_json serializado, motivo nullable, criado_em ISO8601 UTC e sem commit; entidade fora de Jornada/Marcacao/Terceiro/Atividade levanta ValueError
    - done: false
      test: pytest -k test_redact_sensitive_fields_in_log_output
      text: Logger structlog redacta campos sensíveis (senha, password_enc, token_hash) substituindo por [REDACTED]
    - done: false
      test: pytest -k test_rate_limit_login_5_per_minute
      text: POST /api/v1/auth/_smoke_login 6 vezes em <1min retorna 429 na 6a com code=RATE_LIMITED
    - done: false
      test: pytest -k test_current_terceiro_valid_token or test_current_terceiro_missing_header or test_current_terceiro_expired_token
      text: CurrentTerceiroDep com Bearer valido retorna Terceiro ORM; sem header retorna 401; token expirado retorna 401 — todos com shape padronizado
    - done: false
      test: pytest --cov=app/core --cov-fail-under=80
      text: Suite completa passa com cobertura >= 80% no app/core/
    - done: false
      test: grep -E 'router_dev|dev_mode' apps/api/app/main.py
      text: Fundacao registra apenas as rotas smoke em dev (auth/_smoke_login + _auth_smoke nao expostas em prod)
    - done: false
      test: grep -E 'min_length=8' apps/api/app/modules/sistema/router.py
      text: Pydantic forca senha min_length=8 nas entradas do dominio (validador documentado em _SmokeLoginBody)
deps: []
id: TASK-012
linter: ruff check . && mypy --strict app
n45_version: 0.2.0
persona: backend
phase: Phase 3 — Backend por Domínio
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: pending
tdd:
    green: false
    red: false
    refactor: false
tests: pytest tests/test_security_password.py tests/test_security_jwt.py tests/test_errors_handler.py tests/test_security_middleware.py tests/test_audit.py tests/test_logging_redact.py tests/test_rate_limit.py tests/test_deps_current_terceiro.py -v
title: 'Fundação Backend: errors padronizados, security (Argon2id + JWT rotation), middleware (CSP/Host/headers), rate limit slowapi, structlog redact, audit log helper, deps central'
updated_at: "2026-05-28 09:19:57"
---
## Contexto

A Phase 3 entrega o Backend por Domínio em slices verticais. Antes de qualquer domínio, esta task estabelece a **Fundação Backend** — os transversais consumidos por toda task de domínio subsequente (TASK-013..018) — e **decide explicitamente os padrões arquiteturais** do projeto:

1. **Formato de erro padronizado** (todos os 4xx/5xx) com `code`/`message`/`details` e handlers FastAPI que convertem `RequestValidationError`/`HTTPException`/exceções customizadas para esse shape.
2. **Auth helpers**: hashing de senha com Argon2id via `passlib`; emissão/verificação/rotation de JWT (access 15 min, refresh 30 dias) via `python-jose`; persistência de refresh tokens em `RefreshToken` (modelo já existe); `get_current_terceiro` como FastAPI Dependency consumido por todos os endpoints autenticados.
3. **Rate limiting** com `slowapi` (`≤5/min` em `/auth/login`, `≤10/min` em `/auth/refresh`) por IP+email.
4. **Middleware de segurança HTTP**: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'`, validação do header `Host` (aceitar apenas `127.0.0.1`, `localhost`).
5. **Logger estruturado** (`structlog`) com sink rotativo + redact de campos sensíveis (`senha`, `senha_hash`, `password_enc`, `username_enc`, `jwt_access_token`, `jwt_refresh_token`, `token_hash`).
6. **Audit log service helper genérico** (`log_audit(session, entidade, entidade_id, autor, antes, depois, motivo)`) consumido por todos os endpoints que mutam estado.
7. **Repository pattern decision**: cada domínio terá uma classe `<Dominio>Repository` (Python class, **nunca** módulos de funções).
8. **Dependencies central** (`app/core/deps.py`) expondo `SessionDep`, `CurrentTerceiroDep`, `BearerTokenDep`.

**Decisões explícitas registradas aqui** (consumidas pelas TASK-013..018, nunca recriadas):

- Repository: **classe Python (`class <Dominio>Repository`)**. Nunca módulos de funções soltas.
- DI: **FastAPI `Depends`** com factories simples; sem container externo. Razão: 1 app local, baixíssima complexidade.
- Response/error: **modelo único** `ErrorResponse` em `app/core/errors.py`; toda exceção de negócio herda de `DomainError` com `code`/`http_status`.
- Audit log: helper **`log_audit`** em `app/core/audit.py`; cada endpoint mutador chama-o **dentro da mesma transação** que o write.
- Auth: header `Authorization: Bearer <jwt>`; `get_current_terceiro` retorna o ORM `Terceiro`.
- JWT: claims `sub=<terceiro_id>`, `exp`, `iat`, `jti`, `type="access"|"refresh"`. Refresh tokens persistidos: `token_hash = sha256(jwt)`; rotation invalida o anterior; reuso de token revogado revoga toda a cadeia.

Estado atual:
- Phase 1: FastAPI scaffold em `apps/api/app/main.py` com `create_app()` factory + `_lifespan`; router `sistema` com `/health` e `/_dbcheck` (dev-only).
- Phase 2: `app/core/config.py` (pydantic-settings), `app/core/db.py` (engine async + `get_session`), `app/core/crypto.py` (KEK + HKDF + AES-GCM), `app/core/base.py` (`Base = DeclarativeBase`), 11 modelos ORM em `app/modules/<dominio>/model.py`, migração `0001_initial`.

Esta task **não** introduz endpoints de domínio — apenas fundação + 1 endpoint de smoke (`GET /api/v1/_auth_smoke` e `POST /api/v1/auth/_smoke_login` em dev) para validar a stack inteira. Os endpoints reais ficam nas TASK-013..018.

## Comportamento Esperado

| Entrada / Ação | Saída / Efeito esperado |
| --- | --- |
| `hash_password("MinhaSenha123!")` + `verify_password(hash, "MinhaSenha123!")` | Retorna `True`; `time_cost=3, memory_cost=65536, parallelism=4` |
| `verify_password(hash, "errada")` | Retorna `False` (sem levantar) |
| `create_access_token({"sub": "t-uuid"})` | Retorna JWT assinado HS256, `exp = now+900s`, claim `type="access"`, `jti` UUID v4 |
| `create_refresh_token({"sub": "t-uuid"}, session)` | Retorna JWT + persiste `RefreshToken(token_hash=sha256(jwt), expira_em=now+30d, criado_em=now)` |
| `rotate_refresh_token(old_jwt, session)` | Valida `old_jwt`, marca o `RefreshToken` antigo como `revogado_em=now`, emite novo par (access+refresh), retorna `{access_token, refresh_token, expires_in: 900}` |
| `rotate_refresh_token(jwt_já_revogado, session)` | Levanta `DomainError(code="UNAUTHORIZED")` **e** marca toda a cadeia (todos `RefreshToken` do mesmo `terceiro_id` com `revogado_em IS NULL`) como `revogado_em=now` |
| `await get_current_terceiro(token, session)` para token válido | Retorna ORM `Terceiro` correspondente ao `sub` claim |
| `await get_current_terceiro(token_expirado, session)` | Levanta `HTTPException(401, code="UNAUTHORIZED")` em formato padronizado |
| `GET /api/v1/_auth_smoke` com token válido (dev-only) | Retorna `{"terceiro_id": "<uuid>"}` |
| `GET /api/v1/_auth_smoke` sem token (dev-only) | Retorna `401` com `{"code":"UNAUTHORIZED","message":"Token ausente ou inválido","details":[]}` |
| `POST /api/v1/auth/_smoke_login` chamado 6× no mesmo segundo do mesmo IP | 6ª chamada retorna `429` com `{"code":"RATE_LIMITED","message":"Muitas tentativas. Tente novamente em alguns instantes.","details":[]}` |
| Resposta de qualquer endpoint | Contém headers `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'` |
| Requisição com header `Host: evil.com` | Retorna `400` com `{"code":"INVALID_HOST","message":"Host inválido","details":[]}` |
| Requisição com header `Host: 127.0.0.1:8765` | Passa normalmente (200 ou 401 conforme rota) |
| Requisição com payload Pydantic inválido (ex: senha="abc") | Retorna `422` com `{"code":"VALIDATION_ERROR","message":"Erro de validação","details":[{"field":"body.senha","issue":"..."}]}` |
| `await log_audit(session, "Jornada", "j-uuid", "user@example.com", {"a":1}, {"a":2}, "motivo")` | Insere 1 linha em `log_auditoria` com `entidade="Jornada"`, `antes_json='{"a":1}'`, `depois_json='{"a":2}'`, `motivo="motivo"`, `criado_em=now ISO 8601 UTC`; **não commita** (deixa para o caller) |
| `await log_audit(session, "EntidadeInvalida", ...)` | Levanta `ValueError("entidade inválida: ...")` antes do INSERT |
| `structlog.get_logger().info("login", senha="abc")` | Output JSON com campo `senha="[REDACTED]"` |
| `structlog.get_logger().info("login", token_hash="abc")` | Output JSON com campo `token_hash="[REDACTED]"` |

## TDD (red → green → refactor)

**Testes a escrever antes da implementação (1 arquivo por área):**

### `apps/api/tests/test_security_password.py`

```python
from __future__ import annotations

from app.core.security import hash_password, verify_password


def test_hash_and_verify_password_roundtrip() -> None:
    h = hash_password("MinhaSenha123!")
    assert h != "MinhaSenha123!"
    assert verify_password(h, "MinhaSenha123!") is True


def test_verify_password_returns_false_for_wrong_password() -> None:
    h = hash_password("MinhaSenha123!")
    assert verify_password(h, "outraSenha") is False


def test_hash_password_uses_argon2id() -> None:
    h = hash_password("x")
    assert h.startswith("$argon2id$")
```

### `apps/api/tests/test_security_jwt.py`

```python
from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import db as db_mod
from app.core.base import Base
from app.core.errors import DomainError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    rotate_refresh_token,
)
from app.models import RefreshToken, Terceiro


@pytest_asyncio.fixture
async def session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
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
            id="t-1", nome="X", empresa_nome="Y", empresa_cnpj="00000000000191",
            horario_inicio_jornada="09:00:00", horario_saida_almoco="12:00:00",
            horario_retorno_almoco="13:00:00", horario_fim_jornada="18:00:00",
            trabalha_fim_de_semana=0, email_contato="x@y.com", senha_hash="h",
            criado_em=datetime.now(UTC).isoformat(), atualizado_em=datetime.now(UTC).isoformat(),
        )
        s.add(t)
        await s.commit()
        yield s
    await engine.dispose()


def test_create_access_token_contains_required_claims() -> None:
    tok = create_access_token({"sub": "t-1"})
    payload = decode_token(tok)
    assert payload["sub"] == "t-1"
    assert payload["type"] == "access"
    assert "exp" in payload and "iat" in payload and "jti" in payload


def test_decode_expired_token_raises() -> None:
    tok = create_access_token({"sub": "t-1"}, ttl_seconds=-1)
    with pytest.raises(DomainError) as exc:
        decode_token(tok)
    assert exc.value.code == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_create_refresh_token_persists_in_db(session: AsyncSession) -> None:
    jwt = await create_refresh_token({"sub": "t-1"}, session)
    await session.commit()
    rows = (await session.execute(select(RefreshToken))).scalars().all()
    assert len(rows) == 1
    assert rows[0].revogado_em is None
    assert rows[0].token_hash == hashlib.sha256(jwt.encode()).hexdigest()


@pytest.mark.asyncio
async def test_rotate_refresh_token_revokes_old_and_issues_new(session: AsyncSession) -> None:
    old = await create_refresh_token({"sub": "t-1"}, session)
    await session.commit()
    pair = await rotate_refresh_token(old, session)
    await session.commit()
    assert "access_token" in pair and "refresh_token" in pair
    assert pair["expires_in"] == 900
    assert pair["refresh_token"] != old
    rows = (await session.execute(select(RefreshToken).order_by(RefreshToken.criado_em))).scalars().all()
    assert len(rows) == 2
    assert rows[0].revogado_em is not None
    assert rows[1].revogado_em is None


@pytest.mark.asyncio
async def test_reuse_of_revoked_token_revokes_full_chain(session: AsyncSession) -> None:
    r1 = await create_refresh_token({"sub": "t-1"}, session)
    await session.commit()
    pair = await rotate_refresh_token(r1, session)  # r1 revogado, r2 ativo
    await session.commit()
    r2 = pair["refresh_token"]
    pair2 = await rotate_refresh_token(r2, session)  # r2 revogado, r3 ativo
    await session.commit()
    with pytest.raises(DomainError) as exc:
        await rotate_refresh_token(r1, session)
    await session.commit()
    assert exc.value.code == "UNAUTHORIZED"
    rows = (await session.execute(select(RefreshToken))).scalars().all()
    assert all(rt.revogado_em is not None for rt in rows)
```

### `apps/api/tests/test_errors_handler.py`

```python
from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, Field

from app.core.errors import DomainError, install_error_handlers


class BodyIn(BaseModel):
    senha: str = Field(min_length=8)


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()
    install_error_handlers(app)

    @app.post("/v")
    async def v(b: BodyIn) -> dict[str, str]:
        return {"ok": "1"}

    @app.get("/boom")
    async def boom() -> None:
        raise DomainError(code="CONFLICT", message="Conflito", http_status=409)

    return app


@pytest.mark.asyncio
async def test_validation_error_returns_padronizado(app: FastAPI) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        r = await client.post("/v", json={"senha": "abc"})
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["message"] == "Erro de validação"
    assert isinstance(body["details"], list) and len(body["details"]) >= 1
    assert "field" in body["details"][0] and "issue" in body["details"][0]


@pytest.mark.asyncio
async def test_domain_error_serializes_padronizado(app: FastAPI) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        r = await client.get("/boom")
    assert r.status_code == 409
    assert r.json() == {"code": "CONFLICT", "message": "Conflito", "details": []}
```

### `apps/api/tests/test_security_middleware.py`

```python
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.mark.asyncio
async def test_response_has_security_headers() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
        r = await client.get("/api/v1/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    csp = r.headers["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "style-src 'self' 'unsafe-inline'" in csp


@pytest.mark.asyncio
async def test_invalid_host_rejected() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://evil.com") as client:
        r = await client.get("/api/v1/health")
    assert r.status_code == 400
    assert r.json()["code"] == "INVALID_HOST"


@pytest.mark.asyncio
async def test_valid_host_localhost_passes() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost") as client:
        r = await client.get("/api/v1/health")
    assert r.status_code == 200
```

### `apps/api/tests/test_audit.py`

```python
from __future__ import annotations

import json
from datetime import UTC, datetime
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
```

### `apps/api/tests/test_logging_redact.py`

```python
from __future__ import annotations

import io
import logging


def test_redact_sensitive_fields_in_log_output() -> None:
    import structlog
    from app.core.logging import configure_logging

    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    configure_logging(extra_handlers=[handler])
    log = structlog.get_logger("test")
    log.info(
        "login_attempt",
        email="user@example.com",
        senha="MinhaSenha123!",
        password_enc="abc=",
        token_hash="ff00",
    )
    out = buf.getvalue()
    assert "MinhaSenha123!" not in out
    assert "[REDACTED]" in out
    assert "user@example.com" in out  # email não é redacted
    assert "ff00" not in out
```

### `apps/api/tests/test_rate_limit.py`

```python
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_rate_limit_login_5_per_minute(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TIMESHEET_DEV", "true")
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "test-secret-key-min-32-chars-abcdef")
    from app.core import config
    config.settings = config.Settings()  # type: ignore[call-arg]
    from app.main import create_app
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
        last = None
        for _ in range(6):
            last = await client.post(
                "/api/v1/auth/_smoke_login",
                json={"email": "x@y.com", "senha": "abc12345"},
            )
        assert last is not None
        assert last.status_code == 429
        assert last.json()["code"] == "RATE_LIMITED"
```

### `apps/api/tests/test_deps_current_terceiro.py`

```python
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
```

**Refatoração:** Após o green, extrair fixture `session` repetida para `tests/conftest.py` (`@pytest_asyncio.fixture async def db_session(tmp_path, monkeypatch)`). Manter testes auto-contidos quando possível.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| --- | --- | --- |
| `apps/api/pyproject.toml` | Modificar | Adicionar `python-jose[cryptography]==3.3.*`, `passlib[argon2]==1.7.*`, `argon2-cffi==23.*`, `slowapi==0.1.9` em `dependencies` |
| `apps/api/.env.example` | Modificar | Adicionar `TIMESHEET_JWT_SECRET=`, `TIMESHEET_RATE_LIMIT_LOGIN=5/minute`, `TIMESHEET_RATE_LIMIT_REFRESH=10/minute` |
| `apps/api/app/core/config.py` | Modificar | Adicionar `jwt_secret`, `jwt_algorithm` (HS256), `access_token_ttl_seconds=900`, `refresh_token_ttl_seconds=2592000`, `rate_limit_login`, `rate_limit_refresh`; validator que exige `jwt_secret` >=32 chars |
| `apps/api/app/core/errors.py` | Criar | `DomainError`, `ErrorResponse`, `ErrorDetail`, `install_error_handlers(app)` |
| `apps/api/app/core/security.py` | Criar | `hash_password`, `verify_password`, `create_access_token`, `create_refresh_token`, `decode_token`, `rotate_refresh_token`, `revoke_token_chain` |
| `apps/api/app/core/deps.py` | Criar | `SessionDep`, `BearerTokenDep`, `CurrentTerceiroDep`, `get_current_terceiro` |
| `apps/api/app/core/audit.py` | Criar | `async def log_audit(session, *, entidade, entidade_id, autor, antes, depois, motivo) -> None` |
| `apps/api/app/core/logging.py` | Criar | `configure_logging(extra_handlers=None)` com structlog + redact processor |
| `apps/api/app/core/middleware.py` | Criar | `SecurityHeadersMiddleware`, `HostHeaderValidationMiddleware`, `make_limiter()` |
| `apps/api/app/main.py` | Modificar | Em `create_app()`: instalar middlewares, limiter (`app.state.limiter`), error handlers, configurar logging, expor smoke routes em dev e aplicar rate limit no `/auth/_smoke_login` |
| `apps/api/app/modules/sistema/router.py` | Modificar | Adicionar rotas dev `_auth_smoke` (autenticada) e `auth/_smoke_login` (rate-limited 5/min) |
| `apps/api/tests/conftest.py` | Modificar | Adicionar fixture compartilhada `db_session` (opcional, se houver duplicação) |
| `apps/api/tests/test_security_password.py` | Criar | 3 testes |
| `apps/api/tests/test_security_jwt.py` | Criar | 5 testes |
| `apps/api/tests/test_errors_handler.py` | Criar | 2 testes |
| `apps/api/tests/test_security_middleware.py` | Criar | 3 testes |
| `apps/api/tests/test_audit.py` | Criar | 3 testes |
| `apps/api/tests/test_logging_redact.py` | Criar | 1 teste |
| `apps/api/tests/test_rate_limit.py` | Criar | 1 teste |
| `apps/api/tests/test_deps_current_terceiro.py` | Criar | 3 testes |

> **Total: 19 arquivos**. Excede o teto de 8 — exceção explícita prevista no instrutivo: "Fundação Backend (Phase 3) ... coesão justifica o tamanho". Os 19 arquivos compõem **um único contrato transversal** que toda task de domínio consome; dividir geraria deps artificiais e conflito de merge em `main.py`/`config.py`.

### Detalhamento Técnico

**1. `apps/api/pyproject.toml`** — `dependencies` finais:

```toml
dependencies = [
  "fastapi==0.115.*",
  "uvicorn[standard]==0.32.*",
  "pydantic==2.9.*",
  "pydantic-settings==2.6.*",
  "structlog==24.4.*",
  "sqlalchemy==2.0.*",
  "alembic==1.13.*",
  "aiosqlite==0.20.*",
  "cryptography==43.*",
  "python-jose[cryptography]==3.3.*",
  "passlib[argon2]==1.7.*",
  "argon2-cffi==23.*",
  "slowapi==0.1.9",
]
```

**2. `apps/api/.env.example`** — append:

```env
# Segredo HS256 do JWT. Obrigatorio em producao. Minimo 32 chars.
# TIMESHEET_JWT_SECRET=

# Rate limits (slowapi: N/unidade)
# TIMESHEET_RATE_LIMIT_LOGIN=5/minute
# TIMESHEET_RATE_LIMIT_REFRESH=10/minute
```

**3. `apps/api/app/core/config.py`** — adicionar (mantém o que existe):

```python
    jwt_secret: str = Field(
        default="dev-only-jwt-secret-min-32-chars-aaaaaaaaaaa",
        validation_alias=AliasChoices("TIMESHEET_JWT_SECRET", "jwt_secret"),
    )
    jwt_algorithm: str = Field(default="HS256")
    access_token_ttl_seconds: int = Field(default=900)
    refresh_token_ttl_seconds: int = Field(default=2592000)
    rate_limit_login: str = Field(
        default="5/minute",
        validation_alias=AliasChoices("TIMESHEET_RATE_LIMIT_LOGIN", "rate_limit_login"),
    )
    rate_limit_refresh: str = Field(
        default="10/minute",
        validation_alias=AliasChoices("TIMESHEET_RATE_LIMIT_REFRESH", "rate_limit_refresh"),
    )

    @field_validator("jwt_secret")
    @classmethod
    def _validate_jwt_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("TIMESHEET_JWT_SECRET deve ter pelo menos 32 caracteres")
        return v
```

**4. `apps/api/app/core/errors.py`:**

```python
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorDetail(BaseModel):
    field: str
    issue: str


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = []


class DomainError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        http_status: int = 400,
        details: list[ErrorDetail] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or []


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_handler(_req: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content={
                "code": exc.code,
                "message": exc.message,
                "details": [d.model_dump() for d in exc.details],
            },
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_req: Request, exc: RequestValidationError) -> JSONResponse:
        details: list[dict[str, Any]] = []
        for err in exc.errors():
            loc = ".".join(str(p) for p in err.get("loc", []) if p != "")
            details.append({"field": loc, "issue": err.get("msg", "")})
        return JSONResponse(
            status_code=422,
            content={"code": "VALIDATION_ERROR", "message": "Erro de validação", "details": details},
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_handler(_req: Request, exc: StarletteHTTPException) -> JSONResponse:
        code_map = {
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            409: "CONFLICT",
            429: "RATE_LIMITED",
        }
        code = code_map.get(exc.status_code, "INTERNAL_ERROR")
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": code, "message": str(exc.detail), "details": []},
        )
```

**5. `apps/api/app/core/security.py`:**

```python
from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import DomainError
from app.models import RefreshToken

_pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__time_cost=3,
    argon2__memory_cost=65536,
    argon2__parallelism=4,
)


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(hashed: str, password: str) -> bool:
    try:
        return _pwd_context.verify(password, hashed)
    except Exception:
        return False


def _sign(payload: dict[str, Any]) -> str:
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(claims: dict[str, Any], ttl_seconds: int | None = None) -> str:
    now = datetime.now(UTC)
    exp = now + timedelta(seconds=ttl_seconds if ttl_seconds is not None else settings.access_token_ttl_seconds)
    payload = {
        **claims,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": str(uuid4()),
        "type": "access",
    }
    return _sign(payload)


async def create_refresh_token(claims: dict[str, Any], session: AsyncSession) -> str:
    now = datetime.now(UTC)
    exp = now + timedelta(seconds=settings.refresh_token_ttl_seconds)
    payload = {
        **claims,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": str(uuid4()),
        "type": "refresh",
    }
    token = _sign(payload)
    rt = RefreshToken(
        id=str(uuid4()),
        terceiro_id=claims["sub"],
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expira_em=exp.isoformat(),
        criado_em=now.isoformat(),
    )
    session.add(rt)
    return token


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise DomainError(code="UNAUTHORIZED", message="Token inválido ou expirado", http_status=401) from exc


async def rotate_refresh_token(token: str, session: AsyncSession) -> dict[str, Any]:
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise DomainError(code="UNAUTHORIZED", message="Tipo de token inválido", http_status=401)
    sub = payload["sub"]
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    rt = (
        await session.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    ).scalar_one_or_none()
    if rt is None:
        raise DomainError(code="UNAUTHORIZED", message="Refresh token não reconhecido", http_status=401)
    if rt.revogado_em is not None:
        await revoke_token_chain(sub, session)
        raise DomainError(code="UNAUTHORIZED", message="Reuso de refresh token detectado — sessão revogada", http_status=401)
    rt.revogado_em = datetime.now(UTC).isoformat()
    new_access = create_access_token({"sub": sub})
    new_refresh = await create_refresh_token({"sub": sub}, session)
    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "expires_in": settings.access_token_ttl_seconds,
    }


async def revoke_token_chain(terceiro_id: str, session: AsyncSession) -> None:
    now_iso = datetime.now(UTC).isoformat()
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.terceiro_id == terceiro_id, RefreshToken.revogado_em.is_(None))
        .values(revogado_em=now_iso)
    )
```

**6. `apps/api/app/core/deps.py`:**

```python
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import DomainError
from app.core.security import decode_token
from app.models import Terceiro

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def _extract_bearer(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise DomainError(code="UNAUTHORIZED", message="Token ausente ou inválido", http_status=401)
    return authorization.split(" ", 1)[1].strip()


BearerTokenDep = Annotated[str, Depends(_extract_bearer)]


async def get_current_terceiro(token: BearerTokenDep, session: SessionDep) -> Terceiro:
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise DomainError(code="UNAUTHORIZED", message="Tipo de token inválido", http_status=401)
    sub = payload.get("sub")
    if not sub:
        raise DomainError(code="UNAUTHORIZED", message="Token sem sujeito", http_status=401)
    t = (await session.execute(select(Terceiro).where(Terceiro.id == sub))).scalar_one_or_none()
    if t is None:
        raise DomainError(code="UNAUTHORIZED", message="Terceiro não encontrado", http_status=401)
    return t


CurrentTerceiroDep = Annotated[Terceiro, Depends(get_current_terceiro)]
```

**7. `apps/api/app/core/audit.py`:**

```python
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LogAuditoria

_ALLOWED: set[str] = {"Jornada", "Marcacao", "Terceiro", "Atividade"}


async def log_audit(
    session: AsyncSession,
    *,
    entidade: str,
    entidade_id: str,
    autor: str,
    antes: dict[str, Any] | None,
    depois: dict[str, Any],
    motivo: str | None,
) -> None:
    """Insere uma linha em log_auditoria. NÃO commita — caller é responsável."""
    if entidade not in _ALLOWED:
        raise ValueError(f"entidade inválida: {entidade}")
    row = LogAuditoria(
        id=str(uuid4()),
        entidade=entidade,
        entidade_id=entidade_id,
        autor=autor,
        antes_json=json.dumps(antes, ensure_ascii=False, sort_keys=True) if antes is not None else None,
        depois_json=json.dumps(depois, ensure_ascii=False, sort_keys=True),
        motivo=motivo,
        criado_em=datetime.now(UTC).isoformat(),
        expira_em=None,
    )
    session.add(row)
```

**8. `apps/api/app/core/logging.py`:**

```python
from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

_SENSITIVE_FIELDS = {
    "senha", "senha_atual", "nova_senha", "senha_hash",
    "password", "password_enc", "username_enc",
    "jwt_access_token", "jwt_refresh_token", "access_token", "refresh_token",
    "token_hash", "kek",
}


def _redact_sensitive(_logger: Any, _name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    for k in list(event_dict.keys()):
        if k.lower() in _SENSITIVE_FIELDS:
            event_dict[k] = "[REDACTED]"
    return event_dict


def configure_logging(extra_handlers: list[logging.Handler] | None = None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if extra_handlers:
        handlers.extend(extra_handlers)
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=handlers,
        force=True,
    )
    structlog.configure(
        processors=[
            _redact_sensitive,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )
```

**9. `apps/api/app/core/middleware.py`:**

```python
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

_CSP = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
_VALID_HOSTS = {"127.0.0.1", "localhost"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = _CSP
        return response


class HostHeaderValidationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, valid_hosts: set[str] | None = None) -> None:
        super().__init__(app)
        self._valid = valid_hosts or _VALID_HOSTS

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        raw_host = request.headers.get("host", "").split(":")[0]
        if raw_host and raw_host not in self._valid:
            return JSONResponse(
                status_code=400,
                content={"code": "INVALID_HOST", "message": "Host inválido", "details": []},
            )
        return await call_next(request)


def make_limiter() -> Limiter:
    return Limiter(key_func=get_remote_address, default_limits=[])
```

**10. `apps/api/app/main.py`:**

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
from app.modules.sistema.router import router as sistema_router
from app.modules.sistema.router import router_dev as sistema_router_dev


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    configure_logging()
    yield
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
    app.state.limiter = make_limiter()
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(HostHeaderValidationMiddleware)
    install_error_handlers(app)

    @app.exception_handler(RateLimitExceeded)
    async def _rl(_req, _exc):  # type: ignore[no-untyped-def]
        return JSONResponse(
            status_code=429,
            content={"code": "RATE_LIMITED", "message": "Muitas tentativas. Tente novamente em alguns instantes.", "details": []},
        )

    app.include_router(sistema_router)
    if _config.settings.dev_mode:
        app.include_router(sistema_router_dev)
        # Aplica rate limit dinâmico no endpoint smoke
        from app.modules.sistema.router import bind_smoke_rate_limit
        bind_smoke_rate_limit(app)

    return app


app = create_app()
```

**11. `apps/api/app/modules/sistema/router.py`** — adicionar (manter `/health` e `/_dbcheck` existentes):

```python
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
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

## Contratos com camadas adjacentes

```
Produz para:
  TASK-013 (auth + terceiros):
    - hash_password / verify_password — criar/trocar senha (Argon2id).
    - create_access_token / create_refresh_token / rotate_refresh_token / revoke_token_chain — /auth/login, /auth/refresh, /auth/logout, /terceiros/me/senha.
    - settings.rate_limit_login (5/minute), .rate_limit_refresh (10/minute) — aplicar via app.state.limiter.limit(...) nos endpoints de auth.
    - CurrentTerceiroDep — proteger /me, /me/senha, /terceiros, etc.
    - DomainError("SETUP_ALREADY_DONE", ..., http_status=403) etc.

  TASK-014/015/016/017/018 (todos os domínios):
    - SessionDep, CurrentTerceiroDep — toda rota autenticada usa.
    - log_audit(session, entidade=..., entidade_id=..., autor=..., antes=..., depois=..., motivo=...) — toda mutação Web chama dentro da mesma transação que o write.
    - DomainError — toda exceção de negócio herda dela.

  TASK-019 (wiring final + /ready):
    - app.state.limiter, install_error_handlers, middlewares — confirmar via testes integrados.

Consome de:
  - TASK-006: pyproject.toml (existente). Esta task adiciona python-jose, passlib[argon2], argon2-cffi, slowapi.
  - TASK-008: get_session do app.core.db.
  - TASK-010: modelo RefreshToken, LogAuditoria, Terceiro.

Erros:
  - DomainError → resposta padronizada via install_error_handlers.
  - RateLimitExceeded → 429 com code=RATE_LIMITED.
  - RequestValidationError → 422 com code=VALIDATION_ERROR.
  - Outros → 500 com code=INTERNAL_ERROR.
```

## Contrato HTTP

```
GET /api/v1/_auth_smoke   (dev-only)
Authorization: Bearer <jwt-access>

Response 200: {"terceiro_id": "<uuid>"}
Response 401: {"code": "UNAUTHORIZED", "message": "...", "details": []}

POST /api/v1/auth/_smoke_login   (dev-only, rate-limited 5/minute)
Content-Type: application/json

Request body:
{
  "email": "user@example.com",    // EmailStr
  "senha": "MinhaSenha123!"       // min_length=8
}

Response 200: {"status": "ok"}
Response 422: {"code": "VALIDATION_ERROR", "message": "Erro de validação", "details": [{"field": "...", "issue": "..."}]}
Response 429: {"code": "RATE_LIMITED", "message": "Muitas tentativas. Tente novamente em alguns instantes.", "details": []}
```

**Validação obrigatória pelo executor antes de marcar done:**

1. `cd apps/api && pip install -e ".[dev]"`.
2. `cd apps/api && pytest tests/ -v` — todos os testes (Phase 1 + Phase 2 + Fundação) passam.
3. `cd apps/api && ruff check .` sem warnings.
4. `cd apps/api && mypy --strict app` sem erros.
5. `TIMESHEET_DEV=true TIMESHEET_JWT_SECRET=$(python -c 'import secrets;print(secrets.token_urlsafe(48))') uvicorn app.main:app --host 127.0.0.1 --port 8765 &` então `curl -i http://127.0.0.1:8765/api/v1/health` retorna headers `X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`.
6. `curl -H "Host: evil.com" -i http://127.0.0.1:8765/api/v1/health` retorna `400` com `code=INVALID_HOST`.
7. `make smoke` (Phase 1) continua passando.

> Executor DEVE rodar 1–7 e garantir saída 0 antes de retornar. Falha = task não concluída.

**Refatoração:** Após o green, se `_redact_sensitive` ficar lento (muitos campos), cachear set. Por ora, set literal suficiente. Considerar extrair `bind_smoke_rate_limit` para `app.core.middleware` quando TASK-013 implementar `/auth/login` real.
