---
checkpoint: null
complexity: M
created_at: "2026-05-27 14:09:45"
criteria:
    - done: false
      test: pytest apps/api/tests/test_health.py -k test_health_returns_ok_with_version
      text: GET /api/v1/health retorna 200 com body status ok e version 0.1.0
    - done: false
      test: pytest apps/api/tests/test_health.py -k test_health_does_not_require_auth
      text: Health endpoint nao exige autenticacao
    - done: false
      test: pytest apps/api/tests/test_openapi_disabled_in_prod.py -k test_openapi_disabled_without_dev_flag
      text: OpenAPI docs desabilitado sem TIMESHEET_DEV=true
    - done: false
      test: pytest apps/api/tests/test_openapi_disabled_in_prod.py -k test_openapi_enabled_with_dev_flag
      text: OpenAPI docs habilitado com TIMESHEET_DEV=true
    - done: false
      test: ruff check apps/api
      text: Ruff lint passa sem warnings
    - done: false
      test: mypy --strict apps/api/app
      text: Mypy strict passa sem erros
    - done: false
      text: Suite pytest passando integralmente
    - done: false
      text: Testes passando com cobertura >= 80%
deps:
    - TASK-001
id: TASK-002
linter: ruff check apps/api && mypy --strict apps/api/app
n45_version: 0.2.0
persona: backend
phase: Phase 1 — Scaffold Mínimo
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: pending
tdd:
    green: false
    red: false
    refactor: false
tests: pytest apps/api/tests
title: Backend FastAPI scaffold em /apps/api com GET /api/v1/health
updated_at: "2026-05-27 14:09:45"
---
## Contexto

Backend Python do TimeSheet Terceiros: FastAPI single-worker rodando local em `127.0.0.1:8765` (porta configurável via env var). Phase 1 entrega o esqueleto mínimo que sobe e responde a um health check — sem persistência (Phase 2), sem auth (Phase 3), sem domínio (Phase 3).

Esta task cria `/apps/api` com layout em slices verticais (`app/core`, `app/modules`), instala FastAPI + Uvicorn + Pydantic + structlog, configura toolchain (ruff lint + format, mypy strict, pytest + pytest-asyncio + httpx), e expõe `GET /api/v1/health` retornando `{"status":"ok","version":"0.1.0"}`. O endpoint **não acessa banco** — é liveness puro (latência <50ms exigida pela Spec). O endpoint `/api/v1/ready` (readiness) é responsabilidade de Phase 3 (dependeria de banco + scheduler ainda inexistentes).

Padrão arquitetural definido aqui é consumido por todos os módulos backend de Phase 3: cada módulo em `app/modules/<nome>/` com `router.py` + `schema.py` + `service.py` + `model.py`. Configurações em `app/core/config.py` via Pydantic Settings. O módulo de health vive em `app/modules/sistema/` (compartilhará com `/ready` e `/config` em Phase 3).

Depende de TASK-001 (estrutura de pastas e `.gitignore` raiz precisam existir antes do scaffold do app).

## Comportamento Esperado

Após instalação das dependências e `uvicorn app.main:app --host 127.0.0.1 --port 8765`, o servidor responde imediatamente. `GET /api/v1/health` retorna 200 com body JSON contendo `status` e `version`. Endpoint não requer autenticação. Ruff lint e mypy passam sem warnings; pytest roda e o teste do health passa.

**Exemplos (entrada / ação → saída / efeito esperado)** — valores reais:

| Entrada / Ação                                                  | Saída / Efeito esperado                                                                |
| --------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| `curl -s http://127.0.0.1:8765/api/v1/health`                   | Body `{"status":"ok","version":"0.1.0"}` (JSON); status HTTP 200                        |
| Verificar latência: `curl -w "%{time_total}\n" .../health`       | Tempo < 0.050s (sem acesso a banco)                                                    |
| `curl -s -o /dev/null -w "%{http_code}" .../api/v1/health`      | `200`                                                                                  |
| `curl -s http://127.0.0.1:8765/inexistente`                     | Status HTTP 404 (FastAPI padrão)                                                       |
| `ruff check apps/api`                                           | Saída vazia; exit code 0                                                               |
| `mypy --strict apps/api/app`                                    | `Success: no issues found`; exit code 0                                                |
| `pytest apps/api/tests`                                         | `1 passed` (teste do health); exit code 0                                              |
| Variável `TIMESHEET_DEV=true` setada → `GET /docs`              | OpenAPI Swagger UI renderizada (200 com HTML)                                          |
| Sem `TIMESHEET_DEV` → `GET /docs`                               | Status HTTP 404 (docs desabilitado em produção, ver §2 da Spec)                        |

## TDD

**Testes a escrever antes da implementação:**

`apps/api/tests/test_health.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_returns_ok_with_version():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {"status": "ok", "version": "0.1.0"}


@pytest.mark.asyncio
async def test_health_does_not_require_auth():
    # Sem Authorization header — não deve retornar 401
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    assert response.status_code != 401
    assert response.status_code != 403
```

`apps/api/tests/test_openapi_disabled_in_prod.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_openapi_disabled_without_dev_flag(monkeypatch):
    monkeypatch.delenv("TIMESHEET_DEV", raising=False)
    # Re-importa app para pegar settings atualizado
    import importlib
    from app import main
    importlib.reload(main)
    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_openapi_enabled_with_dev_flag(monkeypatch):
    monkeypatch.setenv("TIMESHEET_DEV", "true")
    import importlib
    from app import main
    importlib.reload(main)
    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/docs")
    assert response.status_code == 200
```

**Refatoração:** após green, extrair criação do `AsyncClient` para fixture em `conftest.py` se houver duplicação ≥ 2x (não há nesta task — manter inline).

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo                                            | Ação      | Descrição                                                                                                                                                                                                                                                                          |
| -------------------------------------------------- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `apps/api/pyproject.toml`                          | Criar     | Projeto Python 3.12. Deps: `fastapi==0.115.*`, `uvicorn[standard]==0.32.*`, `pydantic==2.9.*`, `pydantic-settings==2.6.*`, `structlog==24.4.*`. Dev: `pytest==8.3.*`, `pytest-asyncio==0.24.*`, `httpx==0.27.*`, `ruff==0.7.*`, `mypy==1.13.*`. Configs `[tool.ruff]` line-length 100; `[tool.mypy]` strict=true; `[tool.pytest.ini_options]` asyncio_mode="auto" |
| `apps/api/app/__init__.py`                         | Criar     | Vazio — só marca pacote                                                                                                                                                                                                                                                            |
| `apps/api/app/main.py`                             | Criar     | Cria `app = FastAPI(...)` com `title="TimeSheet Terceiros API"`, version do `app/__version__`, `docs_url`/`redoc_url`/`openapi_url` baseado em `settings.dev_mode`. Registra `sistema_router`. `__version__ = "0.1.0"`                                                              |
| `apps/api/app/core/__init__.py`                    | Criar     | Vazio                                                                                                                                                                                                                                                                              |
| `apps/api/app/core/config.py`                      | Criar     | `Settings(BaseSettings)` Pydantic com campos `dev_mode: bool = False` (env `TIMESHEET_DEV`), `port: int = 8765` (env `TIMESHEET_PORT`), `host: str = "127.0.0.1"`. `model_config = SettingsConfigDict(env_prefix="TIMESHEET_", env_file=".env")`. Instância singleton `settings = Settings()` |
| `apps/api/app/modules/__init__.py`                 | Criar     | Vazio                                                                                                                                                                                                                                                                              |
| `apps/api/app/modules/sistema/__init__.py`         | Criar     | Vazio                                                                                                                                                                                                                                                                              |
| `apps/api/app/modules/sistema/router.py`           | Criar     | `APIRouter(prefix="/api/v1", tags=["sistema"])` com `GET /health` retornando `{"status":"ok","version":__version__}`. Função `async def health() -> dict[str, str]`                                                                                                                |
| `apps/api/tests/__init__.py`                       | Criar     | Vazio                                                                                                                                                                                                                                                                              |
| `apps/api/tests/conftest.py`                       | Criar     | Configura `pytest_plugins = []` (asyncio_mode auto pega de pyproject)                                                                                                                                                                                                              |
| `apps/api/tests/test_health.py`                    | Criar     | Conforme TDD acima                                                                                                                                                                                                                                                                 |
| `apps/api/tests/test_openapi_disabled_in_prod.py`  | Criar     | Conforme TDD acima                                                                                                                                                                                                                                                                 |
| `apps/api/.env.example`                            | Criar     | `TIMESHEET_DEV=false` e `TIMESHEET_PORT=8765` comentados                                                                                                                                                                                                                            |
| `apps/api/README.md`                               | Criar     | Como criar venv, instalar (`pip install -e .[dev]`), rodar (`uvicorn app.main:app --reload`), testar (`pytest`)                                                                                                                                                                    |
| `Makefile` (raiz)                                  | Modificar | Adicionar target `api-dev` que ativa venv e roda uvicorn; target `api-test` que roda pytest em `apps/api`; target `api-lint` que roda ruff + mypy. Atualizar `help` para listá-los                                                                                                  |

### Detalhamento Técnico

1. **Layout em slices verticais:** `app/modules/<dominio>/` é o padrão para todo o backend (Phase 3 cria `auth`, `terceiros`, `jornadas`, `marcacoes`, `atividades`, `justificativas`, `auditoria`, `relatorios`, `historico_envio`, `privacidade`). Cada slice terá `router.py`, `schema.py`, `service.py`, `model.py`. Nesta task, só `sistema/router.py` existe — não criar arquivos vazios dos outros domínios (eles nascem com a task que os implementa).

2. **`app/core/config.py`** estabelece o padrão de settings via Pydantic. Todas as env vars do projeto usam prefixo `TIMESHEET_`. Tasks de Phase 2/3 estenderão `Settings` com novos campos (sqlite path, KEK path, JWT secret, SMTP, etc) — esta task **não** os adiciona ainda. Manter mínimo.

3. **`app/main.py`** lógica condicional para OpenAPI:

   ```python
   from fastapi import FastAPI
   from app.core.config import settings
   from app.modules.sistema.router import router as sistema_router

   __version__ = "0.1.0"

   docs_kwargs = (
       {}
       if settings.dev_mode
       else {"docs_url": None, "redoc_url": None, "openapi_url": None}
   )

   app = FastAPI(
       title="TimeSheet Terceiros API",
       version=__version__,
       **docs_kwargs,
   )
   app.include_router(sistema_router)
   ```

4. **`app/modules/sistema/router.py`:**

   ```python
   from fastapi import APIRouter
   from app.main import __version__  # cuidado com circular — preferir mover __version__ para app/__init__.py

   router = APIRouter(prefix="/api/v1", tags=["sistema"])

   @router.get("/health")
   async def health() -> dict[str, str]:
       return {"status": "ok", "version": __version__}
   ```

   Para evitar import circular: mover `__version__ = "0.1.0"` para `app/__init__.py` e importar de lá.

5. **`pyproject.toml` (chave):**

   ```toml
   [project]
   name = "timesheet-api"
   version = "0.1.0"
   requires-python = ">=3.12"
   dependencies = [
     "fastapi==0.115.*",
     "uvicorn[standard]==0.32.*",
     "pydantic==2.9.*",
     "pydantic-settings==2.6.*",
     "structlog==24.4.*",
   ]
   [project.optional-dependencies]
   dev = [
     "pytest==8.3.*",
     "pytest-asyncio==0.24.*",
     "httpx==0.27.*",
     "ruff==0.7.*",
     "mypy==1.13.*",
   ]

   [tool.ruff]
   line-length = 100
   target-version = "py312"

   [tool.ruff.lint]
   select = ["E","F","W","I","UP","B","SIM"]

   [tool.mypy]
   strict = true
   python_version = "3.12"

   [tool.pytest.ini_options]
   asyncio_mode = "auto"
   testpaths = ["tests"]

   [build-system]
   requires = ["setuptools>=68"]
   build-backend = "setuptools.build_meta"

   [tool.setuptools.packages.find]
   include = ["app*"]
   ```

6. **Makefile (adições):**

   ```makefile
   .PHONY: help api-dev api-test api-lint

   API_DIR := apps/api

   api-dev:
   	cd $(API_DIR) && uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload

   api-test:
   	cd $(API_DIR) && pytest

   api-lint:
   	cd $(API_DIR) && ruff check . && mypy --strict app
   ```

7. **Pasta `tests/` ao nível de `apps/api/tests/`** (não dentro de `app/`) para não empacotar tests no build.

**Refatoração:** Nenhuma — código novo, sem duplicação a remover além da fixture sugerida no bloco TDD.
