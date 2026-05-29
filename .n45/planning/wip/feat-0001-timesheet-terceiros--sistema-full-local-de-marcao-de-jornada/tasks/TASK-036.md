---
checkpoint: null
complexity: G
created_at: "2026-05-29 11:46:36"
criteria:
    - done: false
      test: cd apps/api && pytest tests/test_launcher.py -k test_derive_db_cipher_key_hex_matches_crypto
      text: derive_db_cipher_key_hex(kek) retorna hex de 64 chars igual a format_db_cipher_key(derive_subkey(kek, b'db')) e e deterministico
    - done: false
      test: cd apps/api && pytest tests/test_launcher.py -k test_prepare_runtime_sets_db_cipher_key
      text: prepare_runtime(settings) com db_cipher_key=None passa a derivar a chave da KEK (settings.db_cipher_key vira hex de 64 chars nao-nulo)
    - done: false
      test: cd apps/api && pytest tests/test_launcher.py -k test_spa_fallback_serves_index
      text: GET / e GET /jornadas (rota nao-API) servem o index.html da SPA e GET /api/v1/health mantem precedencia retornando status ok
    - done: false
      test: grep -E 'pywin32' apps/api/pyproject.toml
      text: pyproject.toml inclui pywin32 (win32) e pyinstaller; alembic/env.py aplica PRAGMA key como primeiro statement quando TIMESHEET_DB_CIPHER_KEY presente
    - done: false
      text: build-backend.ps1 copia apps/web/dist para app/static e produz apps/api/dist/timesheet-backend.exe via pyinstaller timesheet-backend.spec
    - done: false
      text: ruff e mypy --strict passam na API
deps: []
id: TASK-036
linter: cd apps/api && ruff check . && mypy --strict app
n45_version: 0.2.0
persona: devops
phase: Phase 6 — Empacotamento Windows (PyInstaller + WiX MSI)
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: pending
tests: cd apps/api && pytest tests/test_launcher.py
title: Backend launcher de producao + serve SPA estatica + bundle PyInstaller --onefile
updated_at: "2026-05-29 11:46:36"
---
## Contexto

Esta é a primeira task da Phase 6 (Empacotamento Windows). Hoje o Backend (`apps/api`) sobe **apenas em modo dev** via `uvicorn app.main:app --reload` (Makefile `api-dev`). Não existe entrypoint de produção, o React (`apps/web`) **não é servido pelo Backend** (não há mount de `StaticFiles` em `app/main.py`), e o `TIMESHEET_DB_CIPHER_KEY` precisa ser fornecido manualmente em hex — nada deriva a chave SQLCipher da KEK em runtime. O MSI da Phase 6 (TASK-038) precisa de **um único executável** que: (1) carregue a KEK (DPAPI), derive a chave do banco, rode as migrations, sirva a SPA e suba o Uvicorn em `127.0.0.1:<porta>` sem nenhum passo manual.

Estado atual relevante (fatos do código):
- `app/core/config.py`: `Settings` lê env vars prefixadas `TIMESHEET_*`. Relevantes: `TIMESHEET_PORT` (default 8765), `TIMESHEET_HOST` (default 127.0.0.1), `TIMESHEET_DB_URL` (`sqlite+aiosqlite:///./data/timesheet.sqlite`), `TIMESHEET_DB_CIPHER_KEY` (hex64 opcional — ausente = banco em claro), `TIMESHEET_KEK_PATH` (`./data/key.kek`), `TIMESHEET_PDF_DIR` (`./data/pdfs`), `TIMESHEET_SCHEDULER_JOBSTORE` (`./data/scheduler.sqlite`), `TIMESHEET_DEV` (default false → OpenAPI desabilitado), `TIMESHEET_JWT_SECRET` (mín. 32 chars, obrigatório em prod).
- `app/core/crypto.py`: `ensure_kek(path)` gera/lê a KEK (32 bytes); em Windows usa DPAPI via `win32crypt` (pywin32). `derive_subkey(kek, info=b"db")` → subkey de 32 bytes; `format_db_cipher_key(subkey)` → hex de 64 chars (igual ao formato esperado por `TIMESHEET_DB_CIPHER_KEY`). `info=b"smtp"` é a subkey do SMTP.
- `app/core/crypto_state.py`: `configure()` (chamado no lifespan) deriva **apenas** a subkey SMTP; **não** deriva a chave do banco.
- `app/core/db.py`: `_attach_pragmas` aplica `PRAGMA key = "x'<cipher_key>'"` (quando `settings.db_cipher_key` presente) + WAL/FK na conexão. A chave precisa estar em `settings.db_cipher_key` **antes** de o engine conectar.
- `apps/api/alembic/env.py`: roda migrations com driver síncrono, **sem** aplicar `PRAGMA key` — falha contra banco SQLCipher cifrado.
- `apps/api/pyproject.toml`: dependências incluem `weasyprint==62.*`, `aiosqlite==0.20.*`, mas **não** incluem `pywin32` (necessário para DPAPI) nem o instalador PyInstaller.
- `apps/web/vite.config.ts`: build padrão Vite → saída em `apps/web/dist`, `base: "/"`.

Gap crítico de criptografia: para o banco cifrado funcionar em produção, o entrypoint deve, **antes** de qualquer acesso ao banco: carregar a KEK → derivar a subkey `db` → setar `settings.db_cipher_key = format_db_cipher_key(subkey)` (ou env `TIMESHEET_DB_CIPHER_KEY`) → rodar migrations com a chave aplicada → só então criar o app/engine. SQLCipher também exige um binário `sqlite3` com SQLCipher; o bundle PyInstaller deve incluí-lo (ver Detalhamento).

## Comportamento Esperado

O alvo testável é o **módulo de produção** `app/launcher.py` (código novo, puro o suficiente para teste): preparar o ambiente cripto + migrations + mount de estáticos. O `serve()` que chama `uvicorn.run` em si é orquestração fina (fora da cobertura, como adaptadores). Os testes usam KEK em arquivo temporário com `TIMESHEET_ALLOW_PLAIN_KEK=1` e banco SQLite em diretório temporário.

**Exemplos (entrada → saída esperada)** — valores reais:

| Entrada / Ação | Saída / Efeito esperado |
| -------------- | ----------------------- |
| `derive_db_cipher_key_hex(kek_path)` com KEK de 32 bytes em arquivo | string hex de **64 chars** igual a `format_db_cipher_key(derive_subkey(kek, b"db"))` |
| `prepare_runtime(settings)` com `kek_path` válido e `db_cipher_key=None` | `settings.db_cipher_key` passa a ser a hex de 64 chars derivada da KEK (não-`None`) |
| `prepare_runtime` chamado 2× sobre a mesma KEK | mesma hex nas duas chamadas (KEK imutável → derivação determinística) |
| `static_dir_for_bundle()` quando rodando como bundle PyInstaller (`sys.frozen=True`) | caminho `<_MEIPASS>/static` |
| `static_dir_for_bundle()` em execução normal (não-frozen) | caminho `apps/api/app/static` (relativo ao módulo) |
| `create_app()` com `app/static/index.html` presente | rota `GET /` responde `200` e content-type `text/html`; rota `GET /assets/<arquivo>` serve o asset; rota desconhecida `GET /jornadas` (não-API) responde o `index.html` (SPA fallback) |
| `GET /api/v1/health` no app de produção | `200 {"status":"ok","version":"<v>"}` (rota da API tem precedência sobre o SPA fallback) |
| `run_migrations()` contra banco SQLite simples (sem cipher) | tabelas `terceiro`, `jornada`, `marcacao` (e demais 11) existem; `alembic_version` na head |

## EstratégiaDeTeste (launcher = código novo → TDD red→green; mount de SPA + uvicorn = orquestração fina, fora da meta de cobertura)

> O módulo `app/launcher.py` é **código novo** — TDD red→green. As funções puras (`derive_db_cipher_key_hex`, `prepare_runtime`, `static_dir_for_bundle`) têm teste direto. O mount de `StaticFiles` é validável via `TestClient`. `serve()` (uvicorn.run) e o `.spec` PyInstaller ficam fora da meta de cobertura (orquestração/build).

**Testes a escrever antes da implementação** (`apps/api/tests/test_launcher.py`):

```python
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.crypto import ensure_kek, derive_subkey, format_db_cipher_key


def test_derive_db_cipher_key_hex_matches_crypto(tmp_path, monkeypatch):
    monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    kek_path = tmp_path / "key.kek"
    kek = ensure_kek(kek_path)
    from app.launcher import derive_db_cipher_key_hex
    expected = format_db_cipher_key(derive_subkey(kek, info=b"db"))
    got = derive_db_cipher_key_hex(kek_path)
    assert got == expected
    assert len(got) == 64
    assert derive_db_cipher_key_hex(kek_path) == got  # determinístico (KEK imutável)


def test_prepare_runtime_sets_db_cipher_key(tmp_path, monkeypatch):
    monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    from app.core.config import Settings
    s = Settings(kek_path=str(tmp_path / "key.kek"), db_cipher_key=None)
    from app.launcher import prepare_runtime
    prepare_runtime(s)
    assert s.db_cipher_key is not None
    assert len(s.db_cipher_key) == 64


def test_spa_fallback_serves_index(tmp_path, monkeypatch):
    # static dir com index.html mínimo
    from app import launcher
    static = launcher.static_dir_for_bundle()
    Path(static).mkdir(parents=True, exist_ok=True)
    (Path(static) / "index.html").write_text("<!doctype html><title>app</title>", encoding="utf-8")
    from app.main import create_app
    client = TestClient(create_app())
    assert client.get("/").status_code == 200
    # rota não-API desconhecida → SPA fallback (index.html)
    r = client.get("/jornadas")
    assert r.status_code == 200
    assert "<title>app</title>" in r.text
    # rota da API tem precedência
    assert client.get("/api/v1/health").json()["status"] == "ok"
```

**Controle negativo (red brownfield):** N/A — `launcher.py` e o mount de SPA são código novo; o red vem natural.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| ------- | ---- | --------- |
| `apps/api/app/launcher.py` | Criar | Entrypoint de produção: `prepare_runtime(settings)` (KEK→db cipher key→env), `derive_db_cipher_key_hex(path)`, `static_dir_for_bundle()`, `run_migrations()`, `serve()` (uvicorn single-worker) e `main()` |
| `apps/api/app/main.py` | Modificar | Em `create_app()`: após registrar routers, montar a SPA — `StaticFiles` para `/assets` e demais arquivos do `static_dir_for_bundle()`, e um **SPA fallback** que serve `index.html` para rotas GET não-API (qualquer caminho que **não** comece com `/api`). API mantém precedência |
| `apps/api/pyproject.toml` | Modificar | Adicionar `pywin32==306; sys_platform == 'win32'` às `dependencies` (DPAPI) e `pyinstaller==6.*` ao grupo `[project.optional-dependencies].dev` (ou novo grupo `build`) |
| `apps/api/timesheet-backend.spec` | Criar | Spec PyInstaller `--onefile`: entrypoint `app/launcher.py` → `main()`; `datas` inclui `app/static/**`, `app/pdf/templates/**` (Jinja2), `alembic/**` e `alembic.ini`; `binaries`/`collect` para WeasyPrint (libpango/libcairo/libgobject e dependências GTK) e a DLL SQLCipher; `hiddenimports` para `aiosqlite`, `app.modules.*`, `apscheduler.jobstores.sqlalchemy`, `passlib.handlers.argon2` |
| `apps/api/scripts/build-backend.ps1` | Criar | Roda `web-build` (copia `apps/web/dist/**` → `apps/api/app/static/`), depois `pyinstaller timesheet-backend.spec`, produzindo `apps/api/dist/timesheet-backend.exe` |
| `apps/api/alembic/env.py` | Modificar | Em `run_migrations_online`, no listener `connect`, aplicar `PRAGMA key = "x'<cipher>'"` como **primeiro** statement quando `TIMESHEET_DB_CIPHER_KEY` presente (antes de `PRAGMA foreign_keys`) — para migrar banco SQLCipher cifrado |
| `apps/api/.dockerignore` | Não criar | N/A — projeto full-local, sem Docker para a app |

### Detalhamento Técnico

1. **`launcher.py` — `derive_db_cipher_key_hex(kek_path)`**: `kek = ensure_kek(Path(kek_path))`; `return format_db_cipher_key(derive_subkey(kek, info=b"db"))`. (Reusa `app.core.crypto` — não reimplementar HKDF/DPAPI.)

2. **`prepare_runtime(settings)`**: se `settings.db_cipher_key` é `None` e `settings.kek_path` aponta para arquivo (ou pode ser criado), setar `settings.db_cipher_key = derive_db_cipher_key_hex(settings.kek_path)`. Também propagar para `os.environ["TIMESHEET_DB_CIPHER_KEY"]` (para o subprocesso/ambiente do alembic). Idempotente. Chamar **antes** de `get_engine()` e antes de `run_migrations()`.

3. **`static_dir_for_bundle()`**: se `getattr(sys, "frozen", False)` → `Path(sys._MEIPASS) / "static"`; senão `Path(__file__).resolve().parent / "static"`. Garantir `mkdir(parents=True, exist_ok=True)` em desenvolvimento (modo não-frozen) para o caso de o build do web ainda não ter sido copiado (evita crash do mount).

4. **`run_migrations()`**: invocar Alembic programaticamente — `from alembic.config import Config; from alembic import command; cfg = Config(str(<alembic.ini resolvido>)); command.upgrade(cfg, "head")`. Resolver o caminho do `alembic.ini` e do diretório `alembic/` tanto frozen (em `_MEIPASS`) quanto não-frozen. `TIMESHEET_DB_CIPHER_KEY` já deve estar no env (passo 2) para o `env.py` aplicar o `PRAGMA key`.

5. **`serve()`**: `import uvicorn; uvicorn.run(create_app(), host=settings.host, port=settings.port, workers=1, log_config=None)` (single-worker — Spec §2). Sem `--reload`.

6. **`main()`** (entrypoint do .exe): `configure_logging()` → `prepare_runtime(settings)` → `run_migrations()` → `serve()`. Tratar exceção de bootstrap com log estruturado e exit code ≠ 0.

7. **`main.py` — mount da SPA**: ao fim de `create_app()`, após os `include_router`:
   ```python
   from fastapi.staticfiles import StaticFiles
   from fastapi.responses import FileResponse
   from app.launcher import static_dir_for_bundle

   static_dir = static_dir_for_bundle()
   assets = static_dir / "assets"
   if assets.is_dir():
       app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

   @app.get("/{full_path:path}", include_in_schema=False)
   async def _spa(full_path: str) -> FileResponse:
       # API tem precedência: rotas /api/* já registradas acima nunca caem aqui.
       index = static_dir / "index.html"
       return FileResponse(str(index))
   ```
   A rota catch-all é registrada **por último** → routers `/api/v1/*` mantêm precedência. Não aplicar a rotas que comecem com `/api` (FastAPI resolve as rotas específicas antes do catch-all).

8. **`alembic/env.py`** — no `set_sqlite_pragma`:
   ```python
   cipher = os.environ.get("TIMESHEET_DB_CIPHER_KEY")
   if cipher:
       cursor.execute(f"PRAGMA key = \"x'{cipher}'\"")  # PRIMEIRO statement
   cursor.execute("PRAGMA foreign_keys=ON")
   ```

9. **PyInstaller `.spec`** — WeasyPrint exige libpango/libcairo/libgobject/libfontconfig nativas no bundle (Spec §7 "WeasyPrint quirk"); usar `from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files` para `weasyprint`, `cffi`, `gi`/GTK runtime. SQLCipher: incluir a DLL `sqlite3` com SQLCipher como binário (substitui o `sqlite3.dll` padrão). `datas`: `('app/static', 'static')`, `('app/pdf/templates', 'app/pdf/templates')`, `('alembic', 'alembic')`, `('alembic.ini', '.')`. `hiddenimports`: `['aiosqlite','apscheduler.jobstores.sqlalchemy','apscheduler.triggers.cron','passlib.handlers.argon2','app.modules.auth.router', ...]` (todos os routers importados em `main.py`).

> **Nota de fronteira (produzido para TASK-038):** o artefato final é `apps/api/dist/timesheet-backend.exe`. Ele lê os caminhos de produção via env vars que o MSI define no Service `TimesheetBackend`: `TIMESHEET_KEK_PATH=%APPDATA%\TimesheetTerceiros\key.kek`, `TIMESHEET_DB_URL=sqlite+aiosqlite:///%APPDATA%\TimesheetTerceiros\timesheet.sqlite`, `TIMESHEET_PDF_DIR=%APPDATA%\TimesheetTerceiros\pdfs`, `TIMESHEET_SCHEDULER_JOBSTORE=%APPDATA%\TimesheetTerceiros\scheduler.sqlite`, `TIMESHEET_PORT` (configurável na instalação), `TIMESHEET_JWT_SECRET` (gerado na instalação), `TIMESHEET_DEV` ausente (OpenAPI off). O exe roda migrations e serve a SPA + API na mesma porta.

**Contrato HTTP** (já existente, consumido pela SPA servida aqui):

```
GET /api/v1/health        → 200 {"status":"ok","version":"<v>"}   (sem auth)
GET /api/v1/ready         → 200 {"status":"ready"} | 503          (sem auth; usado pelo MSI/tray)
GET /                      → 200 text/html (index.html da SPA)
GET /assets/<arquivo>      → 200 (asset estático Vite)
GET /<rota-spa>            → 200 index.html (fallback de client-side routing)
```
