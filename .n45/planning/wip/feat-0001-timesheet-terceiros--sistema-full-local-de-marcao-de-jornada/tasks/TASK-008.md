---
checkpoint: null
complexity: M
created_at: "2026-05-27 15:56:41"
criteria:
    - done: true
      test: cd apps/api && pytest tests/test_db.py -k test_session_executes_select_1
      text: Sessao async executa SELECT 1 com resultado 1
    - done: true
      test: cd apps/api && pytest tests/test_db.py -k test_pragma_foreign_keys_is_on
      text: PRAGMA foreign_keys=ON em toda sessao nova
    - done: true
      test: cd apps/api && pytest tests/test_db.py -k test_pragma_journal_mode_is_wal
      text: PRAGMA journal_mode=WAL aplicado no primeiro connect
    - done: true
      test: cd apps/api && pytest tests/test_db.py -k test_get_session_dependency_yields_and_closes
      text: get_session() yields AsyncSession ativa e fecha apos uso
    - done: true
      test: cd apps/api && pytest tests/test_db.py -k test_dbcheck_endpoint_only_in_dev
      text: GET /api/v1/_dbcheck retorna 200 quando TIMESHEET_DEV=true
    - done: true
      test: cd apps/api && pytest tests/test_db.py -k test_dbcheck_endpoint_absent_in_prod
      text: GET /api/v1/_dbcheck retorna 404 quando TIMESHEET_DEV=false
    - done: true
      test: cd apps/api && pytest tests/test_db.py -k test_invalid_cipher_key_rejected_at_startup
      text: TIMESHEET_DB_CIPHER_KEY com valor nao-hex64 falha no Settings() com ValidationError
    - done: true
      test: cd apps/api && pytest tests/test_db.py -k test_valid_cipher_key_accepted
      text: TIMESHEET_DB_CIPHER_KEY com 64 chars hex e aceito pelo Settings()
    - done: true
      test: cd apps/api && ruff check .
      text: ruff check sem warnings
    - done: true
      test: cd apps/api && mypy --strict app
      text: mypy --strict app sem erros
    - done: true
      text: Testes passando com cobertura >= 80%
    - done: true
      test: make smoke
      text: make smoke Phase 1 continua passando
deps:
    - TASK-006
id: TASK-008
linter: cd apps/api && ruff check . && mypy --strict app
n45_version: 0.2.0
persona: backend
phase: Phase 2 — Dados
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: done
tdd:
    green: true
    red: true
    refactor: true
tests: cd apps/api && pytest tests/test_db.py
title: SQLAlchemy 2.x async engine + sessionmaker + get_session DI + PRAGMAs WAL/FK + suporte SQLCipher opcional
updated_at: "2026-05-27 17:09:58"
---
## Contexto

Após a Phase 2 ter o schema persistido (TASK-007), os domínios da Phase 3 vão precisar abrir sessões assíncronas no SQLite a partir das rotas FastAPI. Esta task cria a infraestrutura de conexão e injeção de dependência: engine assíncrono SQLAlchemy 2.x + aiosqlite, factory de sessão por request, PRAGMAs essenciais (foreign_keys, journal_mode=WAL) e suporte opcional a SQLCipher via PRAGMA `key`.

Estado atual:
- `apps/api/app/core/config.py` carrega `dev_mode`, `port`, `host` via pydantic-settings.
- `apps/api/app/main.py` cria o `FastAPI()` e registra `sistema_router`.
- TASK-006 publicou `TIMESHEET_DB_URL`, `TIMESHEET_KEK_PATH` no `.env.example` e a pasta `data/` é criada por `make data-dir`.
- TASK-007 adicionou `sqlalchemy`, `alembic`, `aiosqlite` em `pyproject.toml` e configurou Alembic para escrever no mesmo banco.

Esta task **não** introduz ORM models — isso é a TASK-010, que depende desta e da TASK-007. Aqui apenas o engine, a session factory e a dependência FastAPI. Os testes desta task abrem conexão crua via `text("SELECT 1")` para validar o setup.

SQLCipher: o **suporte** é incluído (PRAGMA `key` é emitido após connect se a chave existir), mas a derivação efetiva da chave fica na TASK-009. Aqui aceita-se uma var `TIMESHEET_DB_CIPHER_KEY` opcional (string hex 64 chars) — quando definida, o engine emite `PRAGMA key = "x'<hex>'"` no `connect` event. Em dev/teste, a var fica ausente e o SQLite roda sem cipher (compatível com testes da TASK-007).

## Comportamento Esperado

| Entrada / Ação                                                                  | Saída / Efeito esperado                                                                                                  |
| ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `await session.execute(text("SELECT 1"))`                                       | Retorna `Result` com 1 linha `(1,)`; sessão fecha sem leak                                                               |
| `await session.execute(text("PRAGMA foreign_keys"))`                            | Retorna `1` (foreign keys ON em toda sessão)                                                                             |
| `await session.execute(text("PRAGMA journal_mode"))`                            | Retorna `'wal'` (após primeira conexão)                                                                                  |
| `async for session in get_session(): await session.execute(text("SELECT 1"))`   | Generator FastAPI cede 1 sessão; após o for, sessão é fechada                                                            |
| Endpoint FastAPI `GET /api/v1/_dbcheck` (apenas em dev)                         | Retorna `{"db": "ok", "result": 1}` quando `TIMESHEET_DEV=true`; 404 quando false                                       |
| `engine.dispose()` no shutdown                                                  | Fecha o pool sem warnings; sem conexões pendentes                                                                        |
| `TIMESHEET_DB_CIPHER_KEY` definido com 64 chars hex válidos                     | PRAGMA `key` emitido no `connect` event; conexão prossegue sem erro                                                      |
| `TIMESHEET_DB_CIPHER_KEY` ausente                                               | Nenhum PRAGMA `key` emitido; SQLite plano funciona normalmente                                                           |
| `TIMESHEET_DB_CIPHER_KEY` com tamanho ≠ 64 ou caracteres não-hex                | `Settings()` levanta `ValidationError` na startup (validator pydantic)                                                   |
| Importar `app.core.db` antes do upgrade do banco                                | Não levanta — engine é lazy; primeira query no `data/timesheet.sqlite` recém-criado dispara aplicação dos PRAGMAs       |

## TDD (red → green → refactor)

**Testes a escrever antes da implementação** (`apps/api/tests/test_db.py`):

```python
from __future__ import annotations

from pathlib import Path
from typing import AsyncIterator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_engine, get_session, get_sessionmaker


@pytest_asyncio.fixture
async def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_file = tmp_path / "t.sqlite"
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{db_file}")
    monkeypatch.delenv("TIMESHEET_DB_CIPHER_KEY", raising=False)
    # Recarrega settings + engine
    from app.core import config, db
    config.settings = config.Settings()  # type: ignore[call-arg]
    db._engine = None
    db._sessionmaker = None
    return db_file


@pytest.mark.asyncio
async def test_session_executes_select_1(db_path: Path) -> None:
    sm = get_sessionmaker()
    async with sm() as session:  # type: AsyncSession
        result = await session.execute(text("SELECT 1"))
        assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_pragma_foreign_keys_is_on(db_path: Path) -> None:
    sm = get_sessionmaker()
    async with sm() as session:
        row = (await session.execute(text("PRAGMA foreign_keys"))).scalar_one()
        assert row == 1, "foreign_keys must be ON in every session"


@pytest.mark.asyncio
async def test_pragma_journal_mode_is_wal(db_path: Path) -> None:
    sm = get_sessionmaker()
    async with sm() as session:
        mode = (await session.execute(text("PRAGMA journal_mode"))).scalar_one()
        assert str(mode).lower() == "wal"


@pytest.mark.asyncio
async def test_get_session_dependency_yields_and_closes(db_path: Path) -> None:
    seen: list[bool] = []

    async def consumer() -> AsyncIterator[AsyncSession]:
        async for s in get_session():
            seen.append(s.is_active)
            yield s

    async for s in consumer():
        await s.execute(text("SELECT 1"))
    assert seen == [True]


@pytest.mark.asyncio
async def test_dbcheck_endpoint_only_in_dev(
    db_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TIMESHEET_DEV", "true")
    from app.core import config
    from app.main import create_app

    config.settings = config.Settings()  # type: ignore[call-arg]
    app: FastAPI = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        r = await client.get("/api/v1/_dbcheck")
        assert r.status_code == 200
        assert r.json() == {"db": "ok", "result": 1}


@pytest.mark.asyncio
async def test_dbcheck_endpoint_absent_in_prod(
    db_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TIMESHEET_DEV", "false")
    from app.core import config
    from app.main import create_app

    config.settings = config.Settings()  # type: ignore[call-arg]
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        r = await client.get("/api/v1/_dbcheck")
        assert r.status_code == 404


def test_invalid_cipher_key_rejected_at_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TIMESHEET_DB_CIPHER_KEY", "naoehex")  # 7 chars, sem ser hex valido
    from pydantic import ValidationError
    from app.core import config

    with pytest.raises(ValidationError):
        config.Settings()  # type: ignore[call-arg]


def test_valid_cipher_key_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TIMESHEET_DB_CIPHER_KEY", "a" * 64)
    from app.core import config

    s = config.Settings()  # type: ignore[call-arg]
    assert s.db_cipher_key == "a" * 64
```

> Os testes usam `pytest-asyncio` em modo auto (já configurado no pyproject) e `httpx.ASGITransport` (já em deps de dev). Não é necessário tocar `pyproject.toml`.

**Refatoração:** Após o green, garantir que helpers de teste compartilhados (criar app limpa por test) estejam em `conftest.py` se a duplicação ficar grande. Caso contrário, nenhuma.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo                                  | Ação      | Descrição                                                                                                            |
| ---------------------------------------- | --------- | -------------------------------------------------------------------------------------------------------------------- |
| `apps/api/app/core/config.py`            | Modificar | Adicionar `db_url`, `db_cipher_key` (opcional) com validator                                                         |
| `apps/api/app/core/db.py`                | Criar     | Engine async + sessionmaker + `get_session` (DI) + listener `connect` que aplica PRAGMAs e opcional `PRAGMA key`     |
| `apps/api/app/main.py`                   | Modificar | Refatorar para `create_app()` factory + registrar router de `_dbcheck` apenas se `dev_mode` true + `shutdown` event  |
| `apps/api/app/modules/sistema/router.py` | Modificar | Adicionar `GET /api/v1/_dbcheck` (incluído pela `create_app` somente em dev)                                         |
| `apps/api/tests/test_db.py`              | Criar     | Suite acima (8 testes)                                                                                               |

### Detalhamento Técnico

**1. `apps/api/app/core/config.py`** — substituir o conteúdo atual (mantendo as 3 vars existentes):

```python
from __future__ import annotations

import re

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


class Settings(BaseSettings):
    dev_mode: bool = Field(
        default=False,
        validation_alias=AliasChoices("TIMESHEET_DEV", "dev_mode"),
    )
    port: int = Field(
        default=8765,
        validation_alias=AliasChoices("TIMESHEET_PORT", "port"),
    )
    host: str = Field(
        default="127.0.0.1",
        validation_alias=AliasChoices("TIMESHEET_HOST", "host"),
    )
    db_url: str = Field(
        default="sqlite+aiosqlite:///./data/timesheet.sqlite",
        validation_alias=AliasChoices("TIMESHEET_DB_URL", "db_url"),
    )
    db_cipher_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("TIMESHEET_DB_CIPHER_KEY", "db_cipher_key"),
    )

    @field_validator("db_cipher_key")
    @classmethod
    def _validate_cipher_key(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        if not _HEX64.match(v):
            raise ValueError(
                "TIMESHEET_DB_CIPHER_KEY deve ter exatamente 64 caracteres hex (256 bits)"
            )
        return v

    model_config = SettingsConfigDict(env_file=".env", populate_by_name=True)


settings = Settings()
```

**2. `apps/api/app/core/db.py`** — criar do zero:

```python
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Lazy singleton engine. Aceita reset em teste via `_engine = None`."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.db_url,
            echo=False,
            future=True,
            connect_args={"check_same_thread": False},
        )
        _attach_pragmas(_engine)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency. Use: session = Depends(get_session)."""
    sm = get_sessionmaker()
    async with sm() as session:
        yield session


def _attach_pragmas(engine: AsyncEngine) -> None:
    """Registra listener no engine sincrono subjacente. Roda em toda nova conexao."""
    sync_engine = engine.sync_engine
    cipher_key = settings.db_cipher_key

    @event.listens_for(sync_engine, "connect")
    def _on_connect(dbapi_conn: Any, _record: Any) -> None:  # noqa: ARG001
        cursor = dbapi_conn.cursor()
        try:
            # PRAGMA key DEVE ser o primeiro statement em uma conexao SQLCipher.
            # No dialeto aiosqlite com sqlite plano, o PRAGMA e' simplesmente ignorado
            # (banco nao cifrado retorna 0 rows). Em SQLCipher, ativa a chave.
            if cipher_key:
                cursor.execute(f"PRAGMA key = \"x'{cipher_key}'\"")
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("PRAGMA journal_mode = WAL")
            cursor.execute("PRAGMA synchronous = NORMAL")
            cursor.execute("PRAGMA busy_timeout = 5000")
        finally:
            cursor.close()


async def dispose_engine() -> None:
    """Chamado no shutdown da aplicacao."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None
```

Decisões:
- Estado global (`_engine`, `_sessionmaker`) é necessário para testes que recarregam `settings` (monkeypatch troca env vars). A função `get_engine()` é lazy e respeita reset.
- `check_same_thread=False` é exigido pelo `aiosqlite` quando usado dentro de event loop.
- Listener `connect` aplica todos os PRAGMAs em ordem: `key` (se houver) → `foreign_keys` → `journal_mode=WAL` → `synchronous=NORMAL` (recomendado com WAL) → `busy_timeout` (evita "database is locked").
- `dispose_engine()` é exposto para o `shutdown` event do FastAPI.

**3. `apps/api/app/main.py`** — refatorar para `create_app()`:

```python
from __future__ import annotations

from fastapi import FastAPI

from app import __version__
from app.core.config import settings
from app.core.db import dispose_engine
from app.modules.sistema.router import router as sistema_router
from app.modules.sistema.router import router_dev as sistema_router_dev


def create_app() -> FastAPI:
    app = FastAPI(
        title="TimeSheet Terceiros API",
        version=__version__,
        docs_url="/docs" if settings.dev_mode else None,
        redoc_url="/redoc" if settings.dev_mode else None,
        openapi_url="/openapi.json" if settings.dev_mode else None,
    )
    app.include_router(sistema_router)
    if settings.dev_mode:
        app.include_router(sistema_router_dev)

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        await dispose_engine()

    return app


app = create_app()
```

Razão para a factory: testes precisam construir a app **após** mudar env vars (o `dbcheck_endpoint_only_in_dev` depende disso). Manter `app = create_app()` no módulo preserva o uso atual com `uvicorn app.main:app`.

**4. `apps/api/app/modules/sistema/router.py`** — adicionar router dev separado:

```python
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.core.db import get_session

router = APIRouter(prefix="/api/v1", tags=["sistema"])
router_dev = APIRouter(prefix="/api/v1", tags=["sistema-dev"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


@router_dev.get("/_dbcheck")
async def dbcheck(session: AsyncSession = Depends(get_session)) -> dict[str, object]:
    result = (await session.execute(text("SELECT 1"))).scalar_one()
    return {"db": "ok", "result": result}
```

`router_dev` só é registrado pelo `create_app()` quando `settings.dev_mode=True`. Em prod, `/api/v1/_dbcheck` retorna 404 — sem expor superfície interna.

## Contratos com camadas adjacentes

```
Produz para:
  - TASK-010 (ORM models): get_engine(), get_sessionmaker(), get_session(); ORM models criam Base e binds em sessions.
  - Phase 3 (dominio backend): get_session() como FastAPI Dependency padrao em todos os endpoints que tocam banco.

Consome de:
  - TASK-006: settings.db_url default sqlite+aiosqlite:///./data/timesheet.sqlite; settings.dev_mode controla expor /api/v1/_dbcheck.
  - TASK-007 (deps): sqlalchemy 2.0, aiosqlite 0.20 declarados em pyproject.toml. Importa-se diretamente.

Erros:
  - Conexao falha (arquivo SQLite inacessivel): SQLAlchemy levanta OperationalError; deixa propagar (Phase 3 trata com handler global).
  - cipher_key invalida: Settings() levanta ValidationError no startup; FastAPI nem sobe.
```

**Validação obrigatória pelo executor antes de marcar done:**

1. `cd apps/api && pip install -e ".[dev]"`.
2. `cd apps/api && TIMESHEET_DB_URL=sqlite+aiosqlite:///./data/test.sqlite alembic upgrade head` (ou usar `make data-dir` antes). O banco precisa existir para os testes que inspecionam PRAGMAs.
3. `cd apps/api && pytest tests/test_db.py -v` — 8 testes passam.
4. `cd apps/api && pytest tests/ -v` — toda a suite (incluindo testes prévios da Phase 1) continua passando.
5. `cd apps/api && ruff check .` sem warnings.
6. `cd apps/api && mypy --strict app` sem erros.
7. `cd apps/api && uvicorn app.main:app --host 127.0.0.1 --port 8765 &` → `curl http://127.0.0.1:8765/api/v1/health` → 200; com `TIMESHEET_DEV=true`, `curl http://127.0.0.1:8765/api/v1/_dbcheck` → 200; sem flag, → 404.
8. `make smoke` (Phase 1) continua passando sem regressão.

> Executor DEVE rodar 1–8 e garantir saída 0 antes de retornar. Falha = task não concluída.

**Refatoração:** Caso `expire_on_commit=False` cause comportamento inesperado em testes que fazem `session.commit()` e reusam objetos, considerar mudar para padrão. Por ora, manter False (padrão da maior parte das stacks async).
