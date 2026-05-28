---
checkpoint: null
complexity: G
created_at: "2026-05-28 09:24:05"
criteria:
    - done: true
      test: pytest -k test_post_terceiros_creates_first_terceiro or test_post_terceiros_second_call_returns_setup_already_done
      text: POST /api/v1/terceiros em banco vazio cria Terceiro (201, terceiro_id+criado_em, sem access_token) e segundo POST retorna 403 SETUP_ALREADY_DONE
    - done: true
      test: pytest -k test_post_terceiros_rejects_invalid_cnpj
      text: POST /terceiros com CNPJ digito verificador invalido retorna 422 com details.field=body.empresa_cnpj
    - done: true
      test: pytest -k test_post_terceiros_rejects_non_chronological_horarios
      text: POST /terceiros com horarios fora de ordem cronologica retorna 422
    - done: true
      test: pytest -k test_post_terceiros_rejects_mismatched_passwords
      text: POST /terceiros com senha != senha_confirmacao retorna 422 com field contendo senha_confirmacao
    - done: true
      test: pytest -k test_login_success_returns_token_pair or test_login_invalid_password or test_login_unknown_email
      text: POST /auth/login credenciais validas retorna {access_token,refresh_token,terceiro_id,expires_in=900}; senha errada retorna 401 com code=UNAUTHORIZED message E-mail ou senha invalidos
    - done: true
      test: pytest -k test_login_rate_limit_5_per_minute
      text: POST /auth/login 6 vezes em <60s retorna 429 RATE_LIMITED na 6a
    - done: true
      test: pytest -k test_refresh_returns_new_pair_and_revokes_old
      text: POST /auth/refresh com refresh valido retorna novo par e revoga o antigo (RefreshToken anterior fica com revogado_em populado, novo ativo)
    - done: true
      test: pytest -k test_refresh_reuse_revokes_full_chain
      text: Reuso de refresh ja revogado em /auth/refresh retorna 401 e marca TODOS RefreshToken do terceiro como revogados
    - done: true
      test: pytest -k test_logout_revokes_current_refresh
      text: POST /auth/logout autenticado revoga o RefreshToken passado no body (204)
    - done: true
      test: pytest -k test_get_me_returns_terceiro_without_senha_hash or test_get_me_without_auth_401
      text: GET /terceiros/me autenticado retorna TerceiroResponse sem senha_hash; sem auth retorna 401
    - done: true
      test: pytest -k test_put_me_updates_and_creates_audit_log
      text: PUT /terceiros/me atualiza Terceiro, persiste atualizado_em novo, e insere 1 LogAuditoria com entidade=Terceiro autor=email do terceiro
    - done: true
      test: pytest -k test_put_me_senha_revokes_all_refresh_tokens
      text: PUT /terceiros/me/senha senha atual correta + nova >=8 chars retorna 204 e revoga TODOS RefreshToken do terceiro na mesma transacao
    - done: true
      test: pytest -k test_put_me_senha_with_wrong_current_returns_401
      text: PUT /terceiros/me/senha com senha atual errada retorna 401 code=UNAUTHORIZED message=Senha atual incorreta
    - done: true
      test: pytest --cov=app/modules/auth --cov=app/modules/terceiros --cov-fail-under=80
      text: Cobertura >= 80% em apps/api/app/modules/auth e apps/api/app/modules/terceiros
    - done: true
      test: grep -E '^class (Terceiro|Auth)Repository' apps/api/app/modules/terceiros/repository.py apps/api/app/modules/auth/repository.py
      text: 'Repository pattern: classes TerceiroRepository e AuthRepository definidas em repository.py (nao modulo de funcoes)'
deps:
    - TASK-012
id: TASK-013
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
tests: pytest tests/test_terceiros_post.py tests/test_auth_login.py tests/test_auth_refresh_logout.py tests/test_terceiros_me.py -v
title: 'Auth + Terceiros: POST /terceiros (single-tenant guard), /auth/login (rate-limit 5/min), /auth/refresh (rotation + chain revoke), /auth/logout, GET/PUT /terceiros/me, PUT /me/senha (revoga refresh tokens)'
updated_at: "2026-05-28 10:30:37"
---
## Contexto

Esta task entrega o **slice vertical de Auth + Terceiros** — login JWT, refresh com rotation, logout, e o cadastro/edição do Terceiro (sistema single-tenant). Tudo num único slice porque (a) consomem o mesmo modelo `Terceiro`, (b) `PUT /terceiros/me/senha` precisa revogar refresh tokens (mesmo domínio), (c) `POST /terceiros` retorna `403 SETUP_ALREADY_DONE` após o primeiro cadastro — fluxo entrelaçado com auth.

Estado atual (fim TASK-012):
- `app.core.security`: `hash_password`/`verify_password` (Argon2id), `create_access_token`/`create_refresh_token`/`decode_token`/`rotate_refresh_token`/`revoke_token_chain` (JWT HS256, refresh persistido com `token_hash=sha256(jwt)`).
- `app.core.deps`: `SessionDep`, `CurrentTerceiroDep`.
- `app.core.errors`: `DomainError(code, message, http_status, details)` + handlers padronizados.
- `app.core.audit`: `log_audit(session, entidade=, entidade_id=, autor=, antes=, depois=, motivo=)`.
- `app.state.limiter`: `slowapi.Limiter` exposto.
- `settings.rate_limit_login` (default `5/minute`), `settings.rate_limit_refresh` (default `10/minute`).
- ORM `Terceiro`, `RefreshToken`, `LogAuditoria` em `app.models`.

Esta task **decide e implementa** o padrão repository do projeto inteiro: classe Python `class TerceiroRepository`/`class AuthRepository` em `repository.py` dentro do módulo do domínio. Demais tasks (TASK-014..018) seguem este mesmo padrão.

**Validação de CNPJ:** módulo 11 server-side (`cnpj.is_valid(s)` via biblioteca `python-stdnum`). Falha → `DomainError(code="VALIDATION_ERROR", details=[{"field":"empresa_cnpj","issue":"CNPJ inválido (dígito verificador incorreto)"}], http_status=422)`. Adicionar `python-stdnum==1.20.*` em deps.

**Single-tenant guard:** `POST /api/v1/terceiros` consulta `SELECT COUNT(*) FROM terceiro` — se ≥1 → `403 SETUP_ALREADY_DONE`. Implementado como check **dentro da transação** (`SELECT` + `INSERT` em mesma transação para evitar TOCTOU).

**Rate limit nos endpoints reais:** `/auth/login` e `/auth/refresh` recebem `@app.state.limiter.limit(settings.rate_limit_login)` e `(...rate_limit_refresh)` respectivamente. A key combina `IP+email` lendo o body com Dependency Pydantic — implementação detalhada abaixo.

## Comportamento Esperado

| Entrada / Ação | Saída / Efeito esperado |
| --- | --- |
| `POST /api/v1/terceiros` em banco vazio com payload válido | `201`, body `{"terceiro_id": "<uuid>", "criado_em": "<iso>"}`; insere 1 linha em `terceiro` com `senha_hash` Argon2id; **não** retorna access_token |
| `POST /api/v1/terceiros` em banco com Terceiro existente | `403` com `{"code":"SETUP_ALREADY_DONE","message":"Cadastro inicial já realizado","details":[]}` |
| `POST /api/v1/terceiros` com CNPJ `"00000000000191"` (válido) | `201` |
| `POST /api/v1/terceiros` com CNPJ `"12345678901234"` (inválido) | `422` com `details=[{"field":"body.empresa_cnpj","issue":"CNPJ inválido (dígito verificador incorreto)"}]` |
| `POST /api/v1/terceiros` com horários fora de ordem (ex: `inicio=14:00, almoco_saida=12:00`) | `422` com `details=[{"field":"body","issue":"horários devem ser cronológicos"}]` |
| `POST /api/v1/terceiros` com senha < 8 chars | `422` com `details=[{"field":"body.senha","issue":"..."}]` |
| `POST /api/v1/terceiros` com `senha != senha_confirmacao` | `422` com `details=[{"field":"body.senha_confirmacao","issue":"Senhas não coincidem"}]` |
| `POST /api/v1/auth/login` com credenciais válidas | `200`, body `{access_token, refresh_token, terceiro_id, expires_in: 900}`; persiste `RefreshToken` |
| `POST /api/v1/auth/login` com senha errada | `401`, body `{"code":"UNAUTHORIZED","message":"E-mail ou senha inválidos","details":[]}` |
| `POST /api/v1/auth/login` 6× no mesmo IP+email em <60s | 6ª retorna `429` com `code=RATE_LIMITED` |
| `POST /api/v1/auth/refresh` com refresh válido | `200`, body novo par `{access_token, refresh_token, expires_in: 900}`; revoga refresh anterior |
| `POST /api/v1/auth/refresh` com refresh já revogado | `401` com `code=UNAUTHORIZED`; revoga toda a cadeia (todos `RefreshToken` ativos do terceiro) |
| `POST /api/v1/auth/refresh` 11× em <60s | 11ª retorna `429` |
| `POST /api/v1/auth/logout` autenticado | `204`; o `RefreshToken` do refresh atual fica `revogado_em=now` |
| `GET /api/v1/terceiros/me` autenticado | `200`, body com todos os campos do Terceiro **exceto** `senha_hash` |
| `GET /api/v1/terceiros/me` sem auth | `401` com `code=UNAUTHORIZED` |
| `PUT /api/v1/terceiros/me` autenticado, payload válido | `200`, retorna terceiro atualizado; insere 1 linha em `log_auditoria` com `entidade="Terceiro"`, `antes_json`, `depois_json`, `autor=<email>`, `motivo=null` (RF-007.5 não exige motivo na edição do próprio cadastro) |
| `PUT /api/v1/terceiros/me/senha` com `senha_atual` correta + nova senha válida | `204`; `senha_hash` atualizado; **todos** os `RefreshToken` do terceiro com `revogado_em IS NULL` recebem `revogado_em=now` na mesma transação |
| `PUT /api/v1/terceiros/me/senha` com `senha_atual` incorreta | `401` com `{"code":"UNAUTHORIZED","message":"Senha atual incorreta","details":[]}` |
| `PUT /api/v1/terceiros/me/senha` com `nova_senha` < 8 chars | `422` |

## TDD (red → green → refactor)

**Testes a escrever antes da implementação:**

### `apps/api/tests/test_terceiros_post.py`

```python
from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture(autouse=True)
def _env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{tmp_path}/t.sqlite")
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "x" * 40)
    from app.core import config, db as db_mod
    config.settings = config.Settings()  # type: ignore[call-arg]
    db_mod._engine = None
    db_mod._sessionmaker = None
    yield


def _payload() -> dict:
    return {
        "nome": "Maria Silva",
        "empresa_nome": "ACME LTDA",
        "empresa_cnpj": "00000000000191",  # CNPJ valido
        "horario_inicio_jornada": "09:00:00",
        "horario_saida_almoco": "12:00:00",
        "horario_retorno_almoco": "13:00:00",
        "horario_fim_jornada": "18:00:00",
        "trabalha_fim_de_semana": False,
        "email_contato": "maria@acme.com",
        "email_destinatario_relatorio": "rh@acme.com",
        "senha": "MinhaSenha123!",
        "senha_confirmacao": "MinhaSenha123!",
    }


async def _migrate() -> None:
    from app.core.base import Base
    from app.core.db import get_engine
    eng = get_engine()
    async with eng.begin() as c:
        await c.run_sync(Base.metadata.create_all)


@pytest.mark.asyncio
async def test_post_terceiros_creates_first_terceiro() -> None:
    await _migrate()
    from app.main import create_app
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post("/api/v1/terceiros", json=_payload())
    assert r.status_code == 201, r.json()
    body = r.json()
    assert "terceiro_id" in body and "criado_em" in body
    assert "access_token" not in body  # endpoint NAO retorna token


@pytest.mark.asyncio
async def test_post_terceiros_second_call_returns_setup_already_done() -> None:
    await _migrate()
    from app.main import create_app
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r1 = await c.post("/api/v1/terceiros", json=_payload())
        assert r1.status_code == 201
        payload2 = _payload() | {"email_contato": "outra@acme.com"}
        r2 = await c.post("/api/v1/terceiros", json=payload2)
    assert r2.status_code == 403
    assert r2.json() == {"code": "SETUP_ALREADY_DONE", "message": "Cadastro inicial já realizado", "details": []}


@pytest.mark.asyncio
async def test_post_terceiros_rejects_invalid_cnpj() -> None:
    await _migrate()
    from app.main import create_app
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        bad = _payload() | {"empresa_cnpj": "12345678901234"}
        r = await c.post("/api/v1/terceiros", json=bad)
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert any(d["field"].endswith("empresa_cnpj") for d in body["details"])


@pytest.mark.asyncio
async def test_post_terceiros_rejects_non_chronological_horarios() -> None:
    await _migrate()
    from app.main import create_app
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        bad = _payload() | {"horario_inicio_jornada": "14:00:00"}  # depois do almoço
        r = await c.post("/api/v1/terceiros", json=bad)
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_post_terceiros_rejects_mismatched_passwords() -> None:
    await _migrate()
    from app.main import create_app
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        bad = _payload() | {"senha_confirmacao": "OutraSenha456!"}
        r = await c.post("/api/v1/terceiros", json=bad)
    assert r.status_code == 422
    body = r.json()
    assert any("senha_confirmacao" in d["field"] for d in body["details"])
```

### `apps/api/tests/test_auth_login.py`

```python
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
    from app.core import config, db as db_mod
    config.settings = config.Settings()  # type: ignore[call-arg]
    db_mod._engine = None
    db_mod._sessionmaker = None
    from app.core.base import Base
    from app.core.security import hash_password
    from app.models import Terceiro
    engine = db_mod.get_engine()
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    sm = db_mod.get_sessionmaker()
    async with sm() as s:
        s.add(Terceiro(
            id="t-1", nome="X", empresa_nome="Y", empresa_cnpj="00000000000191",
            horario_inicio_jornada="09:00:00", horario_saida_almoco="12:00:00",
            horario_retorno_almoco="13:00:00", horario_fim_jornada="18:00:00",
            trabalha_fim_de_semana=0, email_contato="user@example.com",
            senha_hash=hash_password("MinhaSenha123!"),
            criado_em=datetime.now(UTC).isoformat(), atualizado_em=datetime.now(UTC).isoformat(),
        ))
        await s.commit()
    from app.main import create_app
    yield create_app()
    await engine.dispose()


@pytest.mark.asyncio
async def test_login_success_returns_token_pair(app_and_terceiro) -> None:
    transport = ASGITransport(app=app_and_terceiro)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post("/api/v1/auth/login", json={"email": "user@example.com", "senha": "MinhaSenha123!"})
    assert r.status_code == 200, r.json()
    body = r.json()
    assert "access_token" in body and "refresh_token" in body
    assert body["terceiro_id"] == "t-1"
    assert body["expires_in"] == 900


@pytest.mark.asyncio
async def test_login_invalid_password(app_and_terceiro) -> None:
    transport = ASGITransport(app=app_and_terceiro)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post("/api/v1/auth/login", json={"email": "user@example.com", "senha": "errada123"})
    assert r.status_code == 401
    assert r.json() == {"code": "UNAUTHORIZED", "message": "E-mail ou senha inválidos", "details": []}


@pytest.mark.asyncio
async def test_login_unknown_email(app_and_terceiro) -> None:
    transport = ASGITransport(app=app_and_terceiro)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post("/api/v1/auth/login", json={"email": "nope@example.com", "senha": "MinhaSenha123!"})
    assert r.status_code == 401
    assert r.json()["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_login_rate_limit_5_per_minute(app_and_terceiro) -> None:
    transport = ASGITransport(app=app_and_terceiro)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        last = None
        for _ in range(6):
            last = await c.post("/api/v1/auth/login", json={"email": "user@example.com", "senha": "errada"})
        assert last is not None
        assert last.status_code == 429
        assert last.json()["code"] == "RATE_LIMITED"
```

### `apps/api/tests/test_auth_refresh_logout.py`

```python
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select


@pytest_asyncio.fixture
async def app_and_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{tmp_path}/t.sqlite")
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "x" * 40)
    from app.core import config, db as db_mod
    config.settings = config.Settings()  # type: ignore[call-arg]
    db_mod._engine = None
    db_mod._sessionmaker = None
    from app.core.base import Base
    from app.core.security import hash_password
    from app.models import Terceiro
    engine = db_mod.get_engine()
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    sm = db_mod.get_sessionmaker()
    async with sm() as s:
        s.add(Terceiro(
            id="t-1", nome="X", empresa_nome="Y", empresa_cnpj="00000000000191",
            horario_inicio_jornada="09:00:00", horario_saida_almoco="12:00:00",
            horario_retorno_almoco="13:00:00", horario_fim_jornada="18:00:00",
            trabalha_fim_de_semana=0, email_contato="user@example.com",
            senha_hash=hash_password("Senha123!"),
            criado_em=datetime.now(UTC).isoformat(), atualizado_em=datetime.now(UTC).isoformat(),
        ))
        await s.commit()
    from app.main import create_app
    yield create_app(), sm
    await engine.dispose()


@pytest.mark.asyncio
async def test_refresh_returns_new_pair_and_revokes_old(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import RefreshToken
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        login = await c.post("/api/v1/auth/login", json={"email": "user@example.com", "senha": "Senha123!"})
        rt_old = login.json()["refresh_token"]
        r = await c.post("/api/v1/auth/refresh", json={"refresh_token": rt_old})
    assert r.status_code == 200
    new = r.json()
    assert new["refresh_token"] != rt_old
    async with sm() as s:
        rows = (await s.execute(select(RefreshToken).order_by(RefreshToken.criado_em))).scalars().all()
        assert rows[0].revogado_em is not None
        assert rows[1].revogado_em is None


@pytest.mark.asyncio
async def test_refresh_reuse_revokes_full_chain(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import RefreshToken
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        login = await c.post("/api/v1/auth/login", json={"email": "user@example.com", "senha": "Senha123!"})
        rt1 = login.json()["refresh_token"]
        r = await c.post("/api/v1/auth/refresh", json={"refresh_token": rt1})
        # rota rt2
        await c.post("/api/v1/auth/refresh", json={"refresh_token": r.json()["refresh_token"]})
        # Reuso do rt1 (já revogado) — revoga toda a cadeia
        bad = await c.post("/api/v1/auth/refresh", json={"refresh_token": rt1})
    assert bad.status_code == 401
    async with sm() as s:
        rows = (await s.execute(select(RefreshToken))).scalars().all()
        assert all(rt.revogado_em is not None for rt in rows)


@pytest.mark.asyncio
async def test_logout_revokes_current_refresh(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import RefreshToken
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        login = await c.post("/api/v1/auth/login", json={"email": "user@example.com", "senha": "Senha123!"})
        body = login.json()
        r = await c.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {body['access_token']}"},
            json={"refresh_token": body["refresh_token"]},
        )
    assert r.status_code == 204
    async with sm() as s:
        rows = (await s.execute(select(RefreshToken))).scalars().all()
        assert all(rt.revogado_em is not None for rt in rows)
```

### `apps/api/tests/test_terceiros_me.py`

```python
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select


@pytest_asyncio.fixture
async def app_and_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{tmp_path}/t.sqlite")
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "x" * 40)
    from app.core import config, db as db_mod
    config.settings = config.Settings()  # type: ignore[call-arg]
    db_mod._engine = None
    db_mod._sessionmaker = None
    from app.core.base import Base
    from app.core.security import hash_password
    from app.models import Terceiro
    engine = db_mod.get_engine()
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    sm = db_mod.get_sessionmaker()
    async with sm() as s:
        s.add(Terceiro(
            id="t-1", nome="Maria", empresa_nome="ACME", empresa_cnpj="00000000000191",
            horario_inicio_jornada="09:00:00", horario_saida_almoco="12:00:00",
            horario_retorno_almoco="13:00:00", horario_fim_jornada="18:00:00",
            trabalha_fim_de_semana=0, email_contato="user@example.com",
            senha_hash=hash_password("Senha123!"),
            criado_em=datetime.now(UTC).isoformat(), atualizado_em=datetime.now(UTC).isoformat(),
        ))
        await s.commit()
    from app.main import create_app
    yield create_app(), sm
    await engine.dispose()


async def _login(client: AsyncClient) -> str:
    r = await client.post("/api/v1/auth/login", json={"email": "user@example.com", "senha": "Senha123!"})
    return r.json()["access_token"]


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
        audits = (await s.execute(select(LogAuditoria).where(LogAuditoria.entidade == "Terceiro"))).scalars().all()
        assert len(audits) == 1
        assert audits[0].autor == "user@example.com"


@pytest.mark.asyncio
async def test_put_me_senha_revokes_all_refresh_tokens(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import RefreshToken
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        login = await c.post("/api/v1/auth/login", json={"email": "user@example.com", "senha": "Senha123!"})
        tok = login.json()["access_token"]
        # Mais 1 refresh para garantir multiplos ativos
        await c.post("/api/v1/auth/login", json={"email": "user@example.com", "senha": "Senha123!"})
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
        login = await c.post("/api/v1/auth/login", json={"email": "user@example.com", "senha": "Senha123!"})
        tok = login.json()["access_token"]
        r = await c.put(
            "/api/v1/terceiros/me/senha",
            headers={"Authorization": f"Bearer {tok}"},
            json={"senha_atual": "errada", "nova_senha": "NovaSenha456!"},
        )
    assert r.status_code == 401
    assert r.json() == {"code": "UNAUTHORIZED", "message": "Senha atual incorreta", "details": []}
```

**Refatoração:** Após o green, extrair fixture `app_and_session` repetida para `conftest.py` e função `_login(client, email, senha)` para `tests/helpers.py`.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| --- | --- | --- |
| `apps/api/pyproject.toml` | Modificar | Adicionar `python-stdnum==1.20.*` em `dependencies` |
| `apps/api/app/modules/terceiros/schema.py` | Criar | Pydantic models: `CreateTerceiroRequest`, `CreateTerceiroResponse`, `TerceiroResponse`, `UpdateTerceiroRequest`, `ChangePasswordRequest` |
| `apps/api/app/modules/terceiros/repository.py` | Criar | `class TerceiroRepository` — `count_all`, `get_by_id`, `get_by_email`, `create(payload)`, `update(t, payload, autor)` (faz log_audit), `change_password(t, senha_atual, nova_senha)` (verifica + atualiza + revoga refresh tokens) |
| `apps/api/app/modules/terceiros/service.py` | Criar | Funções de orquestração: `create_terceiro` (single-tenant guard), `get_me`, `update_me`, `change_password` |
| `apps/api/app/modules/terceiros/router.py` | Criar | Endpoints: `POST /api/v1/terceiros`, `GET /api/v1/terceiros/me`, `PUT /api/v1/terceiros/me`, `PUT /api/v1/terceiros/me/senha` |
| `apps/api/app/modules/auth/schema.py` | Criar | Pydantic: `LoginRequest`, `LoginResponse`, `RefreshRequest`, `RefreshResponse`, `LogoutRequest` |
| `apps/api/app/modules/auth/repository.py` | Criar | `class AuthRepository` — `authenticate(email, senha) -> Terceiro \| None`, `revoke_refresh(token) -> None` |
| `apps/api/app/modules/auth/service.py` | Criar | `login`, `refresh`, `logout` orquestrando repository + security helpers |
| `apps/api/app/modules/auth/router.py` | Criar | Endpoints `POST /api/v1/auth/login` (rate-limit login), `POST /api/v1/auth/refresh` (rate-limit refresh), `POST /api/v1/auth/logout` (autenticado) |
| `apps/api/app/main.py` | Modificar | `create_app()` registra `terceiros_router` e `auth_router`; aplica `limiter.limit(settings.rate_limit_login)` e `(...refresh)` aos endpoints |
| `apps/api/tests/test_terceiros_post.py` | Criar | 5 testes |
| `apps/api/tests/test_auth_login.py` | Criar | 4 testes |
| `apps/api/tests/test_auth_refresh_logout.py` | Criar | 3 testes |
| `apps/api/tests/test_terceiros_me.py` | Criar | 5 testes |

> **Total: 14 arquivos**. Excede o teto (8) mas a coesão de domínio (auth+terceiros são entrelaçados via troca-de-senha-revoga-refresh-tokens) e o orçamento por arquivo (cada um é pequeno: schema ≤ 50 linhas, repo ≤ 80, service ≤ 80, router ≤ 60, teste ≤ 130) cabem numa sessão. Dividir em 2 tasks (auth vs terceiros) criaria conflito em `main.py` e em `change_password` (que precisa de ambos os repositórios).

### Detalhamento Técnico

**1. `apps/api/app/modules/terceiros/schema.py`:**

```python
from __future__ import annotations

from datetime import time
from typing import Self

from pydantic import BaseModel, EmailStr, Field, model_validator
from stdnum.br import cnpj as cnpj_validator


class CreateTerceiroRequest(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    empresa_nome: str = Field(min_length=1, max_length=150)
    empresa_cnpj: str = Field(min_length=14, max_length=14)
    horario_inicio_jornada: time
    horario_saida_almoco: time
    horario_retorno_almoco: time
    horario_fim_jornada: time
    trabalha_fim_de_semana: bool = False
    email_contato: EmailStr
    email_destinatario_relatorio: EmailStr | None = None
    senha: str = Field(min_length=8, max_length=128)
    senha_confirmacao: str

    @model_validator(mode="after")
    def _validate(self) -> Self:
        if not cnpj_validator.is_valid(self.empresa_cnpj):
            raise ValueError({"loc": ("empresa_cnpj",), "msg": "CNPJ inválido (dígito verificador incorreto)"})
        if not (self.horario_inicio_jornada < self.horario_saida_almoco
                < self.horario_retorno_almoco < self.horario_fim_jornada):
            raise ValueError({"loc": (), "msg": "horários devem ser cronológicos"})
        if self.senha != self.senha_confirmacao:
            raise ValueError({"loc": ("senha_confirmacao",), "msg": "Senhas não coincidem"})
        return self


class CreateTerceiroResponse(BaseModel):
    terceiro_id: str
    criado_em: str


class TerceiroResponse(BaseModel):
    id: str
    nome: str
    empresa_nome: str
    empresa_cnpj: str
    horario_inicio_jornada: str
    horario_saida_almoco: str
    horario_retorno_almoco: str
    horario_fim_jornada: str
    trabalha_fim_de_semana: bool
    email_contato: str
    email_destinatario_relatorio: str | None
    criado_em: str
    atualizado_em: str


class UpdateTerceiroRequest(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    empresa_nome: str = Field(min_length=1, max_length=150)
    empresa_cnpj: str = Field(min_length=14, max_length=14)
    horario_inicio_jornada: time
    horario_saida_almoco: time
    horario_retorno_almoco: time
    horario_fim_jornada: time
    trabalha_fim_de_semana: bool = False
    email_contato: EmailStr
    email_destinatario_relatorio: EmailStr | None = None

    @model_validator(mode="after")
    def _validate(self) -> Self:
        if not cnpj_validator.is_valid(self.empresa_cnpj):
            raise ValueError({"loc": ("empresa_cnpj",), "msg": "CNPJ inválido (dígito verificador incorreto)"})
        if not (self.horario_inicio_jornada < self.horario_saida_almoco
                < self.horario_retorno_almoco < self.horario_fim_jornada):
            raise ValueError({"loc": (), "msg": "horários devem ser cronológicos"})
        return self


class ChangePasswordRequest(BaseModel):
    senha_atual: str
    nova_senha: str = Field(min_length=8, max_length=128)
```

> **Pydantic V2 quirk**: levantar `ValueError(dict)` com `loc` permite que o handler de erros mapeie corretamente o `field`. Alternativa: `PydanticCustomError`. Manter `ValueError(dict)` para simplicidade — `install_error_handlers` faz `str(err.get("loc",...))` etc.

**2. `apps/api/app/modules/terceiros/repository.py`:**

```python
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_audit
from app.core.errors import DomainError
from app.core.security import (
    hash_password,
    revoke_token_chain,
    verify_password,
)
from app.models import Terceiro


class TerceiroRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def count(self) -> int:
        n = (await self.session.execute(select(func.count()).select_from(Terceiro))).scalar_one()
        return int(n)

    async def get_by_id(self, terceiro_id: str) -> Terceiro | None:
        return (await self.session.execute(select(Terceiro).where(Terceiro.id == terceiro_id))).scalar_one_or_none()

    async def get_by_email(self, email: str) -> Terceiro | None:
        return (await self.session.execute(select(Terceiro).where(Terceiro.email_contato == email))).scalar_one_or_none()

    async def create(self, payload: dict[str, Any]) -> Terceiro:
        now = datetime.now(UTC).isoformat()
        t = Terceiro(
            id=str(uuid4()),
            nome=payload["nome"],
            empresa_nome=payload["empresa_nome"],
            empresa_cnpj=payload["empresa_cnpj"],
            horario_inicio_jornada=payload["horario_inicio_jornada"].isoformat(),
            horario_saida_almoco=payload["horario_saida_almoco"].isoformat(),
            horario_retorno_almoco=payload["horario_retorno_almoco"].isoformat(),
            horario_fim_jornada=payload["horario_fim_jornada"].isoformat(),
            trabalha_fim_de_semana=1 if payload["trabalha_fim_de_semana"] else 0,
            email_contato=payload["email_contato"],
            email_destinatario_relatorio=payload.get("email_destinatario_relatorio"),
            senha_hash=hash_password(payload["senha"]),
            criado_em=now,
            atualizado_em=now,
        )
        self.session.add(t)
        return t

    @staticmethod
    def _snapshot(t: Terceiro) -> dict[str, Any]:
        return {
            "nome": t.nome, "empresa_nome": t.empresa_nome, "empresa_cnpj": t.empresa_cnpj,
            "horario_inicio_jornada": t.horario_inicio_jornada,
            "horario_saida_almoco": t.horario_saida_almoco,
            "horario_retorno_almoco": t.horario_retorno_almoco,
            "horario_fim_jornada": t.horario_fim_jornada,
            "trabalha_fim_de_semana": t.trabalha_fim_de_semana,
            "email_contato": t.email_contato,
            "email_destinatario_relatorio": t.email_destinatario_relatorio,
        }

    async def update(self, t: Terceiro, payload: dict[str, Any], autor: str) -> Terceiro:
        antes = self._snapshot(t)
        t.nome = payload["nome"]
        t.empresa_nome = payload["empresa_nome"]
        t.empresa_cnpj = payload["empresa_cnpj"]
        t.horario_inicio_jornada = payload["horario_inicio_jornada"].isoformat()
        t.horario_saida_almoco = payload["horario_saida_almoco"].isoformat()
        t.horario_retorno_almoco = payload["horario_retorno_almoco"].isoformat()
        t.horario_fim_jornada = payload["horario_fim_jornada"].isoformat()
        t.trabalha_fim_de_semana = 1 if payload["trabalha_fim_de_semana"] else 0
        t.email_contato = payload["email_contato"]
        t.email_destinatario_relatorio = payload.get("email_destinatario_relatorio")
        t.atualizado_em = datetime.now(UTC).isoformat()
        await log_audit(
            self.session, entidade="Terceiro", entidade_id=t.id,
            autor=autor, antes=antes, depois=self._snapshot(t), motivo=None,
        )
        return t

    async def change_password(self, t: Terceiro, senha_atual: str, nova_senha: str) -> None:
        if not verify_password(t.senha_hash, senha_atual):
            raise DomainError(code="UNAUTHORIZED", message="Senha atual incorreta", http_status=401)
        t.senha_hash = hash_password(nova_senha)
        t.atualizado_em = datetime.now(UTC).isoformat()
        await revoke_token_chain(t.id, self.session)
```

**3. `apps/api/app/modules/terceiros/service.py`:**

```python
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.models import Terceiro
from app.modules.terceiros.repository import TerceiroRepository


async def create_terceiro(session: AsyncSession, payload: dict[str, Any]) -> Terceiro:
    repo = TerceiroRepository(session)
    if await repo.count() >= 1:
        raise DomainError(code="SETUP_ALREADY_DONE", message="Cadastro inicial já realizado", http_status=403)
    t = await repo.create(payload)
    await session.commit()
    return t


async def update_me(session: AsyncSession, t: Terceiro, payload: dict[str, Any], autor: str) -> Terceiro:
    repo = TerceiroRepository(session)
    updated = await repo.update(t, payload, autor)
    await session.commit()
    return updated


async def change_password(session: AsyncSession, t: Terceiro, senha_atual: str, nova_senha: str) -> None:
    repo = TerceiroRepository(session)
    await repo.change_password(t, senha_atual, nova_senha)
    await session.commit()
```

**4. `apps/api/app/modules/terceiros/router.py`:**

```python
from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import CurrentTerceiroDep, SessionDep
from app.modules.terceiros import service
from app.modules.terceiros.schema import (
    ChangePasswordRequest,
    CreateTerceiroRequest,
    CreateTerceiroResponse,
    TerceiroResponse,
    UpdateTerceiroRequest,
)

router = APIRouter(prefix="/api/v1/terceiros", tags=["terceiros"])


@router.post("", status_code=201, response_model=CreateTerceiroResponse)
async def create(body: CreateTerceiroRequest, session: SessionDep) -> CreateTerceiroResponse:
    t = await service.create_terceiro(session, body.model_dump())
    return CreateTerceiroResponse(terceiro_id=t.id, criado_em=t.criado_em)


def _to_response(t) -> TerceiroResponse:  # type: ignore[no-untyped-def]
    return TerceiroResponse(
        id=t.id, nome=t.nome, empresa_nome=t.empresa_nome, empresa_cnpj=t.empresa_cnpj,
        horario_inicio_jornada=t.horario_inicio_jornada,
        horario_saida_almoco=t.horario_saida_almoco,
        horario_retorno_almoco=t.horario_retorno_almoco,
        horario_fim_jornada=t.horario_fim_jornada,
        trabalha_fim_de_semana=bool(t.trabalha_fim_de_semana),
        email_contato=t.email_contato,
        email_destinatario_relatorio=t.email_destinatario_relatorio,
        criado_em=t.criado_em, atualizado_em=t.atualizado_em,
    )


@router.get("/me", response_model=TerceiroResponse)
async def get_me(t: CurrentTerceiroDep) -> TerceiroResponse:
    return _to_response(t)


@router.put("/me", response_model=TerceiroResponse)
async def put_me(body: UpdateTerceiroRequest, t: CurrentTerceiroDep, session: SessionDep) -> TerceiroResponse:
    updated = await service.update_me(session, t, body.model_dump(), autor=t.email_contato)
    return _to_response(updated)


@router.put("/me/senha", status_code=status.HTTP_204_NO_CONTENT)
async def put_me_senha(body: ChangePasswordRequest, t: CurrentTerceiroDep, session: SessionDep) -> None:
    await service.change_password(session, t, body.senha_atual, body.nova_senha)
```

**5. `apps/api/app/modules/auth/schema.py`:**

```python
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=8, max_length=128)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    terceiro_id: str
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int


class LogoutRequest(BaseModel):
    refresh_token: str
```

**6. `apps/api/app/modules/auth/repository.py`:**

```python
from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models import RefreshToken, Terceiro


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def authenticate(self, email: str, senha: str) -> Terceiro | None:
        t = (await self.session.execute(select(Terceiro).where(Terceiro.email_contato == email))).scalar_one_or_none()
        if t is None:
            return None
        if not verify_password(t.senha_hash, senha):
            return None
        return t

    async def revoke_refresh(self, token: str) -> None:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        rt = (
            await self.session.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        ).scalar_one_or_none()
        if rt is not None and rt.revogado_em is None:
            rt.revogado_em = datetime.now(UTC).isoformat()
```

**7. `apps/api/app/modules/auth/service.py`:**

```python
from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.core.security import create_access_token, create_refresh_token, rotate_refresh_token
from app.modules.auth.repository import AuthRepository


async def login(session: AsyncSession, email: str, senha: str) -> dict[str, Any]:
    repo = AuthRepository(session)
    t = await repo.authenticate(email, senha)
    if t is None:
        raise DomainError(code="UNAUTHORIZED", message="E-mail ou senha inválidos", http_status=401)
    access = create_access_token({"sub": t.id})
    refresh = await create_refresh_token({"sub": t.id}, session)
    await session.commit()
    return {"access_token": access, "refresh_token": refresh, "terceiro_id": t.id, "expires_in": 900}


async def refresh(session: AsyncSession, refresh_token: str) -> dict[str, Any]:
    pair = await rotate_refresh_token(refresh_token, session)
    await session.commit()
    return pair


async def logout(session: AsyncSession, refresh_token: str) -> None:
    repo = AuthRepository(session)
    await repo.revoke_refresh(refresh_token)
    await session.commit()
```

**8. `apps/api/app/modules/auth/router.py`:**

```python
from __future__ import annotations

from fastapi import APIRouter, Request, status

from app.core.deps import CurrentTerceiroDep, SessionDep
from app.modules.auth import service
from app.modules.auth.schema import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    RefreshRequest,
    RefreshResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(request: Request, body: LoginRequest, session: SessionDep) -> LoginResponse:  # noqa: ARG001
    data = await service.login(session, body.email, body.senha)
    return LoginResponse(**data)


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(request: Request, body: RefreshRequest, session: SessionDep) -> RefreshResponse:  # noqa: ARG001
    data = await service.refresh(session, body.refresh_token)
    return RefreshResponse(**data)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: LogoutRequest, t: CurrentTerceiroDep, session: SessionDep) -> None:  # noqa: ARG001
    await service.logout(session, body.refresh_token)
```

**9. `apps/api/app/main.py`** — adicionar registro + rate limit:

```python
# Após install_error_handlers(app):
from app.modules.auth.router import router as auth_router
from app.modules.terceiros.router import router as terceiros_router
app.include_router(terceiros_router)
app.include_router(auth_router)

# Aplica rate limit em /auth/login e /auth/refresh
limiter = app.state.limiter
for route in app.routes:
    p = getattr(route, "path", "")
    if p == "/api/v1/auth/login":
        route.endpoint = limiter.limit(_config.settings.rate_limit_login)(route.endpoint)
        route.dependant.call = route.endpoint  # type: ignore[attr-defined]
    elif p == "/api/v1/auth/refresh":
        route.endpoint = limiter.limit(_config.settings.rate_limit_refresh)(route.endpoint)
        route.dependant.call = route.endpoint  # type: ignore[attr-defined]
```

> **Tratamento de `ValueError(dict)` em validators**: o handler em `install_error_handlers` (TASK-012) já lê `err.get("loc")` e `err.get("msg")` — Pydantic V2 converte automaticamente `ValueError(dict)` em `ValidationError` com `loc` e `msg` populados. Se o handler atual não trata `dict` em `msg`, ajustar:
> ```python
> raw_msg = err.get("msg", "")
> issue = raw_msg if isinstance(raw_msg, str) else str(raw_msg)
> ```

## Contratos com camadas adjacentes

```
Produz para:
  TASK-016 (marcações):
    - Token JWT access — Bearer no Authorization. CurrentTerceiroDep retorna Terceiro com .id usado como filtro de todas as marcações.

  TASK-017 (jornadas + auditoria endpoint):
    - log_auditoria entries com entidade=Terceiro existem após PUT /me; GET /api/v1/auditoria filtra por entidade.

  TASK-018 (relatórios):
    - email_destinatario_relatorio do Terceiro lido para envio default.

Consome de:
  TASK-012:
    - hash_password, verify_password (Argon2id).
    - create_access_token, create_refresh_token, rotate_refresh_token, revoke_token_chain, decode_token.
    - DomainError, install_error_handlers (já instalado).
    - SessionDep, CurrentTerceiroDep, BearerTokenDep.
    - log_audit.
    - app.state.limiter, settings.rate_limit_login, settings.rate_limit_refresh.

Erros:
  - SETUP_ALREADY_DONE → 403 quando POST /terceiros após primeiro.
  - VALIDATION_ERROR → 422 (CNPJ inválido, horários fora de ordem, senha != confirmação, senha < 8).
  - UNAUTHORIZED → 401 (login com credenciais erradas; senha atual errada; refresh inválido/revogado/expirado).
  - RATE_LIMITED → 429 (5/min login, 10/min refresh).
```

## Contrato HTTP

```
POST /api/v1/terceiros
Content-Type: application/json

Request body:
{
  "nome": "Maria Silva",                            // 1..120
  "empresa_nome": "ACME LTDA",                      // 1..150
  "empresa_cnpj": "00000000000191",                 // 14 dígitos + módulo 11
  "horario_inicio_jornada": "09:00:00",             // ISO time
  "horario_saida_almoco": "12:00:00",
  "horario_retorno_almoco": "13:00:00",
  "horario_fim_jornada": "18:00:00",                // ordem cronológica
  "trabalha_fim_de_semana": false,
  "email_contato": "maria@acme.com",                // EmailStr unique
  "email_destinatario_relatorio": "rh@acme.com",    // opcional
  "senha": "MinhaSenha123!",                        // min 8 max 128
  "senha_confirmacao": "MinhaSenha123!"
}

Response 201: {"terceiro_id": "<uuid>", "criado_em": "<iso-utc>"}
Response 403: {"code":"SETUP_ALREADY_DONE","message":"Cadastro inicial já realizado","details":[]}
Response 422: {"code":"VALIDATION_ERROR","message":"Erro de validação","details":[{"field":"body.empresa_cnpj","issue":"CNPJ inválido..."}]}

GET /api/v1/terceiros/me   (auth Bearer)
Response 200: TerceiroResponse (sem senha_hash)

PUT /api/v1/terceiros/me   (auth Bearer)
Response 200: TerceiroResponse atualizado + cria 1 LogAuditoria

PUT /api/v1/terceiros/me/senha   (auth Bearer)
Request body: {"senha_atual": "...", "nova_senha": "..." }  // nova_senha: min 8 max 128
Response 204: vazio + revoga TODOS RefreshToken do terceiro
Response 401: senha atual incorreta

POST /api/v1/auth/login   (rate-limit 5/minute)
Request body: {"email": "...", "senha": "..."}
Response 200: {"access_token":"...","refresh_token":"...","terceiro_id":"...","expires_in":900}
Response 401: {"code":"UNAUTHORIZED","message":"E-mail ou senha inválidos","details":[]}
Response 429: {"code":"RATE_LIMITED",...}

POST /api/v1/auth/refresh   (rate-limit 10/minute)
Request body: {"refresh_token": "..."}
Response 200: {"access_token":"...","refresh_token":"...","expires_in":900}
Response 401: refresh inválido/revogado (revoga toda cadeia)

POST /api/v1/auth/logout   (auth Bearer)
Request body: {"refresh_token": "..."}
Response 204
```

**Validação obrigatória pelo executor antes de marcar done:**

1. `cd apps/api && pip install -e ".[dev]"`.
2. `cd apps/api && pytest tests/test_terceiros_post.py tests/test_auth_login.py tests/test_auth_refresh_logout.py tests/test_terceiros_me.py -v` — todos passam.
3. `cd apps/api && pytest tests/ -v` — suite completa continua passando.
4. `cd apps/api && ruff check .` sem warnings.
5. `cd apps/api && mypy --strict app` sem erros.
6. `make smoke` (Phase 1) continua passando.

> Executor DEVE rodar 1–6 e garantir saída 0 antes de retornar. Falha = task não concluída.

**Refatoração:** Após o green, considerar extrair `_to_response(t)` para `schema.py` como classmethod `TerceiroResponse.from_orm(t)`. Manter por enquanto inline em `router.py` para clareza.
