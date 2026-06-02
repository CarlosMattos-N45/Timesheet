---
checkpoint: null
complexity: P
created_at: "2026-06-02 16:45:05"
criteria:
    - done: false
      test: grep -E "win32serviceutil|win32service|win32event|servicemanager|win32api" apps/api/timesheet-backend.spec
      text: timesheet-backend.spec lista win32serviceutil, win32service, win32event, servicemanager e win32api em hiddenimports
    - done: false
      test: grep -E "aiosqlite|app.models|passlib.handlers.argon2" apps/api/timesheet-backend.spec
      text: 'Nenhum import preexistente removido: aiosqlite, app.models, passlib.handlers.argon2 ainda presentes'
    - done: false
      test: '! grep -E "win32gui|win32con|pythoncom" apps/api/timesheet-backend.spec'
      text: 'Nenhum modulo pywin32 alem dos 5 adicionado: win32gui/win32con/pythoncom ausentes'
    - done: false
      test: python -c "import ast; ast.parse(open(apps/api/timesheet-backend.spec).read())"
      text: O spec continua sendo Python valido (parseia sem erro)
deps: []
id: TASK-002
n45_version: 0.2.0
persona: devops
phase: Phase 1 — Handshake SCM do Backend
roadmap: fix-0002-backend-nao-roda-como-windows-service-handshake-scm-ausente
status: pending
tests: python -c "import ast; ast.parse(open('apps/api/timesheet-backend.spec').read())"
title: Hidden imports do pywin32 service no timesheet-backend.spec
updated_at: "2026-06-02 16:45:05"
---
## Contexto

O `timesheet-backend.exe` é empacotado via PyInstaller (onefile) usando `apps/api/timesheet-backend.spec`. A correção do handshake do Windows Service (feita em outra task no `launcher.py`) usa os módulos do `pywin32`: `win32serviceutil`, `win32service`, `win32event`, `servicemanager` e `win32api`. Esses módulos são importados **lazy** (dentro de função / atrás de `sys.platform == "win32"`) no `launcher.py` — e é exatamente por isso que o PyInstaller, que faz análise estática de imports, **não os detecta automaticamente**. Sem declará-los como `hiddenimports`, o bundle congelado não os incluirá e o modo serviço quebrará em runtime na instalação de produção (`ImportError`), mesmo com o código correto.

Estado atual do spec: a lista `hiddenimports` (linhas ~38-66) já contém `aiosqlite`, jobstores/triggers do APScheduler, `passlib.handlers.argon2`, os routers da app, `app.models`, `app.core.base` e dialetos SQLAlchemy, seguida de `hiddenimports += collect_submodules("sqlalchemy")`. `pywin32==306` já é dependência declarada (`pyproject.toml`, `sys_platform == 'win32'`) e já participa do ambiente de build — esta task **não adiciona dependência**, apenas garante que os 5 módulos entrem no bundle. **Escopo mínimo:** adicionar somente esses 5 módulos, nenhum outro módulo pywin32 (não ampliar a superfície do bundle), e não remover nenhum import preexistente.

## Comportamento Esperado

Os 5 módulos do pywin32 service passam a constar em `hiddenimports`; todos os imports preexistentes permanecem; nenhum módulo pywin32 adicional é incluído.

**Exemplos (entrada / verificação → saída esperada)** — valores reais:

| Verificação | Resultado esperado |
| ----------- | ------------------ |
| `"win32serviceutil" in hiddenimports` | `True` |
| `"win32service" in hiddenimports` | `True` |
| `"win32event" in hiddenimports` | `True` |
| `"servicemanager" in hiddenimports` | `True` |
| `"win32api" in hiddenimports` | `True` |
| `"aiosqlite" in hiddenimports` (preexistente) | `True` (inalterado) |
| `"app.models" in hiddenimports` (preexistente) | `True` (inalterado) |
| outros módulos pywin32 (ex.: `win32gui`, `win32con`, `pythoncom`) em `hiddenimports` | ausentes (não incluídos) |

## O que Implementar

Persona `devops` (PyInstaller spec). Acrescentar os 5 módulos à lista `hiddenimports` existente em `apps/api/timesheet-backend.spec`, antes da linha `hiddenimports += collect_submodules("sqlalchemy")`. Não reordenar nem remover entradas existentes.

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| ------- | ---- | --------- |
| `apps/api/timesheet-backend.spec` | Modificar | Adicionar `"win32serviceutil"`, `"win32service"`, `"win32event"`, `"servicemanager"`, `"win32api"` à lista `hiddenimports` |

### Detalhamento Técnico

1. Localizar o bloco `hiddenimports = [ ... ]` (atualmente termina com `"sqlalchemy.dialects.sqlite",` antes do `]`).
2. Adicionar, dentro do literal da lista, um grupo comentado com os 5 módulos do pywin32 service. Manter a vírgula final em cada entrada (estilo do arquivo).
3. **Não** adicionar `win32gui`, `win32con`, `pythoncom`, `pywintypes` ou qualquer outro módulo pywin32 — escopo restrito aos 5.
4. **Não** alterar `datas`, `binaries`, a chamada `Analysis(...)`, `EXE(...)`, nem `collect_submodules("sqlalchemy")`.

**Exemplo de implementação (trecho do literal `hiddenimports`):**

```python
    # SQLAlchemy dialects used at runtime
    "sqlalchemy.dialects.sqlite",
    # pywin32 service modules — imported lazily in launcher.py (Windows Service mode),
    # invisible to PyInstaller's static analysis; declared here so the frozen bundle
    # ships them. Scope limited to the 5 modules strictly required for the SCM handshake.
    "win32serviceutil",
    "win32service",
    "win32event",
    "servicemanager",
    "win32api",
]
hiddenimports += collect_submodules("sqlalchemy")
```

**Refatoração:** Nenhuma.

> **Validação (devops):** o spec é um arquivo Python — `python -c "import ast; ast.parse(open('apps/api/timesheet-backend.spec').read())"` deve parsear sem erro. A verificação de presença/ausência dos módulos é feita por inspeção da lista (grep/import do AST). `docker build` não se aplica (não há Dockerfile envolvido nesta mudança); o build real do bundle (`pyinstaller`) roda no CI Windows — não executável em CI Linux, então o critério mecânico aqui é a presença textual no spec, não o build do exe.
