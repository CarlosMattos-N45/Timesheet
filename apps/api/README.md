# TimeSheet Terceiros — API

Backend FastAPI do sistema TimeSheet Terceiros.

## Configuração

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate  # Windows
# ou: source .venv/bin/activate  # Linux/macOS
pip install -e ".[dev]"
```

Copie o arquivo de exemplo de variáveis de ambiente:

```bash
cp .env.example .env
```

## Executar

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
```

Ou via Makefile (na raiz do projeto):

```bash
make api-dev
```

## Testar

```bash
pytest
```

Ou via Makefile:

```bash
make api-test
```

## Lint

```bash
ruff check . && mypy --strict app
```

Ou via Makefile:

```bash
make api-lint
```

## Endpoints

- `GET /api/v1/health` — liveness check (não requer autenticação)
- `GET /docs` — Swagger UI (apenas com `TIMESHEET_DEV=true`)
