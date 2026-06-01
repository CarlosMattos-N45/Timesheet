---
checkpoint: null
complexity: M
created_at: "2026-05-28 09:27:52"
criteria:
    - done: false
      test: pytest -k test_get_smtp_returns_404_when_empty
      text: GET /api/v1/smtp autenticado com banco vazio retorna 404 code=NOT_FOUND
    - done: false
      test: pytest -k test_put_smtp_creates_and_get_returns_without_password
      text: PUT /api/v1/smtp cria SmtpConfig(id=1) e GET subsequente retorna {host,port,username (decifrado),use_starttls,from_address,atualizado_em} sem password/password_enc/username_enc no body
    - done: false
      test: pytest -k test_username_and_password_are_encrypted_on_disk
      text: Colunas username_enc e password_enc no DB são blobs base64 AES-GCM (texto claro NAO aparece) e decifragem via aes_gcm_decrypt(SUBKEY_SMTP) retorna os bytes originais
    - done: false
      test: pytest -k test_put_smtp_updates_existing
      text: PUT subsequente atualiza host/port/use_starttls da config existente (sem criar nova linha)
    - done: false
      test: pytest -k test_put_smtp_rejects_invalid_port
      text: PUT com port=0 ou port>65535 retorna 422 com field=body.port
    - done: false
      test: pytest -k test_put_smtp_rejects_invalid_email_from
      text: PUT com from_address nao-email retorna 422 com field=body.from_address
    - done: false
      test: pytest -k test_post_smtp_test_without_config_returns_422_smtp_not_configured
      text: POST /smtp/test sem config retorna 422 code=SMTP_NOT_CONFIGURED
    - done: false
      test: pytest -k test_post_smtp_test_unreachable_host_returns_400
      text: POST /smtp/test com host inalcancavel retorna 400 code=SMTP_TEST_FAILED com message contendo erro real do socket
    - done: false
      test: pytest -k test_endpoints_require_auth
      text: Todos endpoints /api/v1/smtp* exigem auth Bearer (sem header => 401)
    - done: false
      test: pytest --cov=app/modules/smtp --cov-fail-under=80
      text: Cobertura >= 80% em apps/api/app/modules/smtp
    - done: false
      test: grep -E '^class SmtpRepository' apps/api/app/modules/smtp/repository.py
      text: 'Repository pattern: SmtpRepository definido como classe em repository.py'
    - done: false
      test: grep -E 'crypto_state.configure' apps/api/app/main.py
      text: crypto_state.SUBKEY_SMTP inicializado via configure() no lifespan startup (idempotente)
deps:
    - TASK-012
    - TASK-013
id: TASK-015
linter: ruff check . && mypy --strict app
n45_version: 0.2.0
persona: backend
phase: Phase 3 — Backend por Domínio
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: done
tdd:
    green: false
    red: false
    refactor: false
tests: pytest tests/test_smtp.py -v
title: 'SMTP Config: GET/PUT /api/v1/smtp + POST /test, AES-GCM em username_enc/password_enc, crypto_state.SUBKEY_SMTP global no lifespan'
updated_at: "2026-05-28 10:57:09"
---

## Contexto

Esta task entrega o **slice vertical do domínio SMTP Config** — gerenciamento da configuração SMTP que será consumida pela TASK-018 (Relatórios) para enviar o PDF mensal por e-mail.

A tabela `smtp_config` é singleton (`id=1` via CHECK), com `username_enc` e `password_enc` armazenados criptografados via AES-GCM (`nonce || ciphertext || tag`, base64 url-safe). A chave AES-GCM é derivada via `HKDF-Expand(SHA-256)` da KEK com `info=b"smtp"`. Ambos os helpers existem em `app.core.crypto` desde a TASK-009.

Estado atual (fim TASK-012 + TASK-013):
- ORM `SmtpConfig` em `app/modules/smtp/model.py` com CHECK `id=1`, colunas `host`, `port`, `username_enc`, `password_enc`, `use_starttls`, `from_address`, `atualizado_em`.
- `app.core.crypto`: `ensure_kek(path)`, `derive_subkey(kek, info=b"smtp")`, `aes_gcm_encrypt(subkey, plaintext_bytes) -> str` (base64), `aes_gcm_decrypt(subkey, encoded) -> bytes`.
- `settings.kek_path` (default `./data/key.kek`) — adicionado nesta task.
- Sem service/router para SMTP ainda.

Decisões nesta task:
- A subkey `smtp` é derivada **uma vez no startup** e mantida em memória (`app.core.crypto_state.SUBKEY_SMTP`) para evitar I/O em cada request. A KEK é lida do disco em `configure_crypto_state()` chamado no `lifespan` startup do `create_app()`.
- `GET /api/v1/smtp` retorna config **sem** senha em claro: `{host, port, username, use_starttls, from_address, atualizado_em}` — `username` é descriptografado mas senha **nunca** é retornada (mesma semântica do `senha_hash`).
- `PUT /api/v1/smtp` recebe `password: SecretStr`; criptografa antes de persistir.
- "Testar conexão" SMTP: integrado em **POST `/api/v1/smtp/test`** — abre socket SMTP, faz STARTTLS se config, login com username/password, fecha. Timeout 10s. Retorna `200 {"ok": true}` ou `4xx` com erro real do servidor.

## Comportamento Esperado

| Entrada / Ação | Saída / Efeito esperado |
| --- | --- |
| `GET /api/v1/smtp` autenticado, banco sem config | `404` com `{"code":"NOT_FOUND","message":"SMTP não configurado","details":[]}` |
| `GET /api/v1/smtp` autenticado, com config | `200`, body `{"host":"smtp.example.com","port":587,"username":"user@x.com","use_starttls":true,"from_address":"noreply@x.com","atualizado_em":"<iso>"}` (sem `password`, sem `password_enc`, sem `username_enc`) |
| `PUT /api/v1/smtp` autenticado, payload válido, sem config | `200`, retorna mesmo shape do GET; persiste `SmtpConfig(id=1)` com `username_enc` e `password_enc` cifrados |
| `PUT /api/v1/smtp` autenticado, payload válido, com config existente | `200`, atualiza `host/port/username_enc/password_enc/use_starttls/from_address/atualizado_em` |
| `PUT /api/v1/smtp` com `port < 1` ou `port > 65535` | `422` com `details=[{"field":"body.port","issue":"..."}]` |
| `PUT /api/v1/smtp` com `from_address` inválido (não é email) | `422` |
| `POST /api/v1/smtp/test` autenticado, com config válida, servidor SMTP up (Mailhog em dev) | `200`, body `{"ok": true}` |
| `POST /api/v1/smtp/test` autenticado, sem config | `422` com `{"code":"SMTP_NOT_CONFIGURED","message":"...","details":[]}` |
| `POST /api/v1/smtp/test` autenticado, com config inválida (host inalcançável) | `400` com `{"code":"SMTP_TEST_FAILED","message":"<erro real do servidor>","details":[]}` |
| `decrypt(username_enc)` após PUT com `username="user@x.com"` | Retorna `b"user@x.com"` exatamente |
| `username_enc != username` (no DB) | `username_enc` é base64 url-safe blob; nunca o texto claro |
| GET/PUT/POST `/api/v1/smtp*` sem auth | `401` |

## TDD (red → green → refactor)

**Testes a escrever antes da implementação:**

### `apps/api/tests/test_smtp.py`

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
    monkeypatch.setenv("TIMESHEET_KEK_PATH", str(tmp_path / "key.kek"))
    monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
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
            trabalha_fim_de_semana=0, email_contato="u@x.com",
            senha_hash=hash_password("Senha123!"),
            criado_em=datetime.now(UTC).isoformat(), atualizado_em=datetime.now(UTC).isoformat(),
        ))
        await s.commit()
    from app.main import create_app
    app = create_app()
    # Força inicialização do crypto_state (configurado em lifespan)
    from app.core import crypto_state
    crypto_state.configure()
    yield app, sm
    await engine.dispose()


async def _login(app) -> str:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post("/api/v1/auth/login", json={"email": "u@x.com", "senha": "Senha123!"})
    return r.json()["access_token"]


def _valid_payload() -> dict:
    return {
        "host": "127.0.0.1",
        "port": 1025,
        "username": "user@example.com",
        "password": "smtp-secret-pwd",
        "use_starttls": False,
        "from_address": "noreply@example.com",
    }


@pytest.mark.asyncio
async def test_get_smtp_returns_404_when_empty(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/smtp", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 404
    assert r.json()["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_put_smtp_creates_and_get_returns_without_password(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r1 = await c.put("/api/v1/smtp", headers={"Authorization": f"Bearer {tok}"}, json=_valid_payload())
        assert r1.status_code == 200
        body = r1.json()
        assert body["host"] == "127.0.0.1"
        assert body["port"] == 1025
        assert body["username"] == "user@example.com"  # descriptografado
        assert body["from_address"] == "noreply@example.com"
        assert "password" not in body and "password_enc" not in body and "username_enc" not in body

        r2 = await c.get("/api/v1/smtp", headers={"Authorization": f"Bearer {tok}"})
        assert r2.status_code == 200
        assert r2.json()["username"] == "user@example.com"


@pytest.mark.asyncio
async def test_username_and_password_are_encrypted_on_disk(app_and_session) -> None:
    app, sm = app_and_session
    from app.models import SmtpConfig
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        await c.put("/api/v1/smtp", headers={"Authorization": f"Bearer {tok}"}, json=_valid_payload())
    async with sm() as s:
        cfg = (await s.execute(select(SmtpConfig))).scalar_one()
        # Texto claro NUNCA aparece na coluna enc
        assert cfg.username_enc != "user@example.com"
        assert "user@example.com" not in cfg.username_enc
        assert cfg.password_enc != "smtp-secret-pwd"
        assert "smtp-secret-pwd" not in cfg.password_enc
        # Decifragem funciona
        from app.core import crypto, crypto_state
        assert crypto.aes_gcm_decrypt(crypto_state.SUBKEY_SMTP, cfg.username_enc) == b"user@example.com"
        assert crypto.aes_gcm_decrypt(crypto_state.SUBKEY_SMTP, cfg.password_enc) == b"smtp-secret-pwd"


@pytest.mark.asyncio
async def test_put_smtp_updates_existing(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        await c.put("/api/v1/smtp", headers={"Authorization": f"Bearer {tok}"}, json=_valid_payload())
        new = _valid_payload() | {"host": "novo.example.com", "port": 465, "use_starttls": True}
        r = await c.put("/api/v1/smtp", headers={"Authorization": f"Bearer {tok}"}, json=new)
    assert r.status_code == 200
    body = r.json()
    assert body["host"] == "novo.example.com"
    assert body["port"] == 465
    assert body["use_starttls"] is True


@pytest.mark.asyncio
async def test_put_smtp_rejects_invalid_port(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        bad = _valid_payload() | {"port": 0}
        r = await c.put("/api/v1/smtp", headers={"Authorization": f"Bearer {tok}"}, json=bad)
    assert r.status_code == 422
    assert any("port" in d["field"] for d in r.json()["details"])


@pytest.mark.asyncio
async def test_put_smtp_rejects_invalid_email_from(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        bad = _valid_payload() | {"from_address": "not-email"}
        r = await c.put("/api/v1/smtp", headers={"Authorization": f"Bearer {tok}"}, json=bad)
    assert r.status_code == 422
    assert any("from_address" in d["field"] for d in r.json()["details"])


@pytest.mark.asyncio
async def test_post_smtp_test_without_config_returns_422_smtp_not_configured(app_and_session) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post("/api/v1/smtp/test", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 422
    assert r.json()["code"] == "SMTP_NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_post_smtp_test_unreachable_host_returns_400(app_and_session, monkeypatch) -> None:
    app, _ = app_and_session
    tok = await _login(app)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        bad = _valid_payload() | {"host": "127.0.0.2", "port": 65530}  # porta improvável
        await c.put("/api/v1/smtp", headers={"Authorization": f"Bearer {tok}"}, json=bad)
        r = await c.post("/api/v1/smtp/test", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 400
    assert r.json()["code"] == "SMTP_TEST_FAILED"


@pytest.mark.asyncio
async def test_endpoints_require_auth(app_and_session) -> None:
    app, _ = app_and_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r1 = await c.get("/api/v1/smtp")
        r2 = await c.put("/api/v1/smtp", json=_valid_payload())
        r3 = await c.post("/api/v1/smtp/test")
    assert r1.status_code == 401
    assert r2.status_code == 401
    assert r3.status_code == 401
```

**Refatoração:** Após o green, extrair `_login` para `tests/helpers.py`. Considerar mover `_valid_payload` para fixture parametrizada se mais testes precisarem.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| --- | --- | --- |
| `apps/api/.env.example` | Modificar | Garantir `TIMESHEET_KEK_PATH=./data/key.kek` presente |
| `apps/api/app/core/config.py` | Modificar | Adicionar `kek_path: str = "./data/key.kek"` |
| `apps/api/app/core/crypto_state.py` | Criar | Estado global `SUBKEY_SMTP: bytes`; `configure()` lê KEK + deriva subkey, idempotente |
| `apps/api/app/main.py` | Modificar | Chamar `crypto_state.configure()` no `_lifespan` startup |
| `apps/api/app/modules/smtp/schema.py` | Criar | `SmtpConfigRequest` (com `password: SecretStr`), `SmtpConfigResponse` (sem password) |
| `apps/api/app/modules/smtp/repository.py` | Criar | `class SmtpRepository` — `get_or_none`, `upsert(payload, subkey)`, `decrypt_username(cfg, subkey) -> str`, `decrypt_password(cfg, subkey) -> str` |
| `apps/api/app/modules/smtp/service.py` | Criar | `get_config`, `put_config`, `test_connection` (usa `smtplib.SMTP`/`SMTP_SSL` + timeout 10s) |
| `apps/api/app/modules/smtp/router.py` | Criar | `GET/PUT /api/v1/smtp`, `POST /api/v1/smtp/test` |
| `apps/api/app/modules/smtp/__init__.py` | Modificar | Vazio ou re-export — manter como está se já existe |
| `apps/api/tests/test_smtp.py` | Criar | 9 testes |

> Total: 9 arquivos. Justificável: 1 domínio, slice vertical mínimo + dependency global `crypto_state`.

### Detalhamento Técnico

**1. `apps/api/app/core/config.py`** — adicionar:

```python
    kek_path: str = Field(
        default="./data/key.kek",
        validation_alias=AliasChoices("TIMESHEET_KEK_PATH", "kek_path"),
    )
```

**2. `apps/api/app/core/crypto_state.py`:**

```python
"""Global crypto state: SMTP subkey kept in memory after KEK load."""
from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.core.crypto import derive_subkey, ensure_kek

SUBKEY_SMTP: bytes = b""


def configure() -> None:
    """Idempotent. Lê KEK do disco e deriva subkey SMTP."""
    global SUBKEY_SMTP
    if SUBKEY_SMTP:
        return
    kek = ensure_kek(Path(settings.kek_path))
    SUBKEY_SMTP = derive_subkey(kek, info=b"smtp")


def reset_for_tests() -> None:
    """Limpa estado global. Apenas para testes."""
    global SUBKEY_SMTP
    SUBKEY_SMTP = b""
```

**3. `apps/api/app/main.py`** — atualizar `_lifespan`:

```python
@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    from app.core import crypto_state
    crypto_state.configure()
    yield
    await dispose_engine()
```

**4. `apps/api/app/modules/smtp/schema.py`:**

```python
from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, SecretStr


class SmtpConfigRequest(BaseModel):
    host: str = Field(min_length=1, max_length=253)
    port: int = Field(ge=1, le=65535)
    username: str = Field(min_length=1, max_length=254)
    password: SecretStr = Field(min_length=1, max_length=512)
    use_starttls: bool = True
    from_address: EmailStr


class SmtpConfigResponse(BaseModel):
    host: str
    port: int
    username: str
    use_starttls: bool
    from_address: str
    atualizado_em: str
```

**5. `apps/api/app/modules/smtp/repository.py`:**

```python
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import aes_gcm_decrypt, aes_gcm_encrypt
from app.models import SmtpConfig


class SmtpRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_none(self) -> SmtpConfig | None:
        return (
            await self.session.execute(select(SmtpConfig).where(SmtpConfig.id == 1))
        ).scalar_one_or_none()

    async def upsert(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        use_starttls: bool,
        from_address: str,
        subkey: bytes,
    ) -> SmtpConfig:
        existing = await self.get_or_none()
        now = datetime.now(UTC).isoformat()
        username_enc = aes_gcm_encrypt(subkey, username.encode("utf-8"))
        password_enc = aes_gcm_encrypt(subkey, password.encode("utf-8"))
        if existing is None:
            cfg = SmtpConfig(
                id=1, host=host, port=port,
                username_enc=username_enc, password_enc=password_enc,
                use_starttls=1 if use_starttls else 0,
                from_address=from_address, atualizado_em=now,
            )
            self.session.add(cfg)
            return cfg
        existing.host = host
        existing.port = port
        existing.username_enc = username_enc
        existing.password_enc = password_enc
        existing.use_starttls = 1 if use_starttls else 0
        existing.from_address = from_address
        existing.atualizado_em = now
        return existing

    @staticmethod
    def decrypt_username(cfg: SmtpConfig, subkey: bytes) -> str:
        return aes_gcm_decrypt(subkey, cfg.username_enc).decode("utf-8")

    @staticmethod
    def decrypt_password(cfg: SmtpConfig, subkey: bytes) -> str:
        return aes_gcm_decrypt(subkey, cfg.password_enc).decode("utf-8")
```

**6. `apps/api/app/modules/smtp/service.py`:**

```python
from __future__ import annotations

import smtplib
import socket

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import crypto_state
from app.core.errors import DomainError
from app.modules.smtp.repository import SmtpRepository

_SMTP_TIMEOUT = 10  # seconds


async def get_config(session: AsyncSession) -> dict:
    repo = SmtpRepository(session)
    cfg = await repo.get_or_none()
    if cfg is None:
        raise DomainError(code="NOT_FOUND", message="SMTP não configurado", http_status=404)
    return {
        "host": cfg.host,
        "port": cfg.port,
        "username": repo.decrypt_username(cfg, crypto_state.SUBKEY_SMTP),
        "use_starttls": bool(cfg.use_starttls),
        "from_address": cfg.from_address,
        "atualizado_em": cfg.atualizado_em,
    }


async def put_config(session: AsyncSession, payload: dict) -> dict:
    repo = SmtpRepository(session)
    await repo.upsert(
        host=payload["host"], port=payload["port"],
        username=payload["username"], password=payload["password"].get_secret_value(),
        use_starttls=payload["use_starttls"], from_address=payload["from_address"],
        subkey=crypto_state.SUBKEY_SMTP,
    )
    await session.commit()
    return await get_config(session)


async def test_connection(session: AsyncSession) -> dict:
    repo = SmtpRepository(session)
    cfg = await repo.get_or_none()
    if cfg is None:
        raise DomainError(code="SMTP_NOT_CONFIGURED", message="SMTP não configurado", http_status=422)
    username = repo.decrypt_username(cfg, crypto_state.SUBKEY_SMTP)
    password = repo.decrypt_password(cfg, crypto_state.SUBKEY_SMTP)
    try:
        if cfg.port == 465:
            with smtplib.SMTP_SSL(cfg.host, cfg.port, timeout=_SMTP_TIMEOUT) as smtp:
                if username and password:
                    smtp.login(username, password)
        else:
            with smtplib.SMTP(cfg.host, cfg.port, timeout=_SMTP_TIMEOUT) as smtp:
                if cfg.use_starttls:
                    smtp.starttls()
                if username and password:
                    try:
                        smtp.login(username, password)
                    except smtplib.SMTPNotSupportedError:
                        # Mailhog não suporta login — aceitável em dev sem AUTH
                        pass
    except (OSError, socket.timeout, smtplib.SMTPException) as exc:
        raise DomainError(code="SMTP_TEST_FAILED", message=str(exc), http_status=400) from exc
    return {"ok": True}
```

**7. `apps/api/app/modules/smtp/router.py`:**

```python
from __future__ import annotations

from fastapi import APIRouter

from app.core.deps import CurrentTerceiroDep, SessionDep
from app.modules.smtp import service
from app.modules.smtp.schema import SmtpConfigRequest, SmtpConfigResponse

router = APIRouter(prefix="/api/v1/smtp", tags=["smtp"])


@router.get("", response_model=SmtpConfigResponse)
async def get_cfg(_t: CurrentTerceiroDep, session: SessionDep) -> SmtpConfigResponse:
    data = await service.get_config(session)
    return SmtpConfigResponse(**data)


@router.put("", response_model=SmtpConfigResponse)
async def put_cfg(body: SmtpConfigRequest, _t: CurrentTerceiroDep, session: SessionDep) -> SmtpConfigResponse:
    data = await service.put_config(session, body.model_dump())
    return SmtpConfigResponse(**data)


@router.post("/test")
async def test_cfg(_t: CurrentTerceiroDep, session: SessionDep) -> dict:
    return await service.test_connection(session)
```

**8. `apps/api/app/main.py`** — adicionar:

```python
from app.modules.smtp.router import router as smtp_router
app.include_router(smtp_router)
```

## Contratos com camadas adjacentes

```
Produz para:
  TASK-018 (relatórios + scheduler):
    - get_config(session) retorna {host, port, username, use_starttls, from_address, atualizado_em} para a função de envio SMTP.
    - SmtpRepository.decrypt_password(cfg, SUBKEY_SMTP) para autenticar no envio (nunca expor pelo HTTP).
    - DomainError code=SMTP_NOT_CONFIGURED quando ausente — TASK-018 reenvia esse erro em POST /relatorios/{mes}/enviar.

Consome de:
  TASK-009: app.core.crypto (aes_gcm_encrypt, aes_gcm_decrypt, ensure_kek, derive_subkey).
  TASK-012: SessionDep, CurrentTerceiroDep, DomainError.
  TASK-010: modelo SmtpConfig.

Erros:
  - NOT_FOUND (404) em GET quando ausente.
  - SMTP_NOT_CONFIGURED (422) em POST /test quando ausente.
  - SMTP_TEST_FAILED (400) em POST /test quando socket/login falha.
  - VALIDATION_ERROR (422) em PUT com port/email inválido.
```

## Contrato HTTP

```
GET /api/v1/smtp   (auth Bearer)
Response 200: {"host":"smtp.example.com","port":587,"username":"user@x.com","use_starttls":true,"from_address":"noreply@x.com","atualizado_em":"<iso>"}
Response 404: {"code":"NOT_FOUND","message":"SMTP não configurado","details":[]}

PUT /api/v1/smtp   (auth Bearer)
Request body:
{
  "host": "smtp.example.com",          // 1..253
  "port": 587,                         // 1..65535
  "username": "user@example.com",      // 1..254
  "password": "senha-do-smtp",         // 1..512, mascarado
  "use_starttls": true,
  "from_address": "noreply@example.com" // EmailStr
}
Response 200: SmtpConfigResponse (sem password); persiste username_enc/password_enc cifrados AES-GCM
Response 422: VALIDATION_ERROR

POST /api/v1/smtp/test   (auth Bearer)
Response 200: {"ok": true}
Response 400: {"code":"SMTP_TEST_FAILED","message":"<erro real>","details":[]}
Response 422: {"code":"SMTP_NOT_CONFIGURED","message":"SMTP não configurado","details":[]}
```

**Validação obrigatória pelo executor antes de marcar done:**

1. `cd apps/api && pip install -e ".[dev]"`.
2. `cd apps/api && TIMESHEET_ALLOW_PLAIN_KEK=1 pytest tests/test_smtp.py -v` — 9 testes passam.
3. `cd apps/api && TIMESHEET_ALLOW_PLAIN_KEK=1 pytest tests/ -v` — suite completa continua passando.
4. `cd apps/api && ruff check .` sem warnings.
5. `cd apps/api && mypy --strict app` sem erros.
6. `make smtp-up && make smoke` — Mailhog up + Phase 1 smoke continua passando.

> Executor DEVE rodar 1–6 e garantir saída 0 antes de retornar. Falha = task não concluída. Mailhog precisa estar up para teste manual de `POST /smtp/test` retornar `200`; teste automatizado usa `host: 127.0.0.2` (improvável) para garantir caminho de falha.

**Refatoração:** Após o green, considerar extrair `_SMTP_TIMEOUT` para `settings.smtp_timeout` se TASK-018 precisar de timeout diferente em envio.
