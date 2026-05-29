.PHONY: help smoke api-smoke web-smoke agent-smoke api-dev api-test api-lint web-dev web-build web-test web-lint agent-build agent-test agent-format smtp-up smtp-down smtp-status data-dir build build-backend publish-agent installer-validate release setup

API_DIR := apps/api
WEB_DIR := apps/web
AGENT_DIR := apps/agent
INSTALLER_DIR := apps/installer

help:
	@echo Comandos disponiveis:
	@echo   help          - mostra esta mensagem
	@echo   smoke         - executa os 3 smoke verifiers em sequencia: api + web + agent
	@echo   api-smoke     - valida que o backend sobe e /api/v1/health responde 200
	@echo   web-smoke     - valida que o build de producao do frontend passa
	@echo   agent-smoke   - valida que a solution .NET compila e testes passam
	@echo   api-dev       - inicia servidor de desenvolvimento da API
	@echo   api-test      - executa testes da API
	@echo   api-lint      - executa ruff e mypy na API
	@echo   web-dev       - inicia servidor de desenvolvimento do frontend
	@echo   web-build     - build de producao do frontend
	@echo   web-test      - executa testes do frontend
	@echo   web-lint      - executa eslint e typecheck no frontend
	@echo   agent-build   - compila a solution do agente .NET
	@echo   agent-test    - executa testes do agente .NET
	@echo   agent-format  - verifica formatacao do agente .NET
	@echo   smtp-up       - sobe Mailhog (SMTP fake) via docker compose
	@echo   smtp-down     - derruba Mailhog
	@echo   smtp-status   - estado do servico Mailhog
	@echo   data-dir      - cria diretorio data/ local (SQLite + key.kek dev)
	@echo   build         - compila backend + agente + gera MSI em dist/
	@echo   build-backend - compila apenas o backend (PyInstaller)
	@echo   publish-agent - publica apenas o agente .NET (self-contained)
	@echo   installer-validate - valida o MSI WiX sem subir app (CI)
	@echo   release       - build + assina MSI com signtool (SIGN_CERT obrigatorio)
	@echo   setup         - prepara ambiente dev local sem subir app

smoke: api-smoke web-smoke agent-smoke
	@echo "[SMOKE OK] api + web + agent ok"

api-smoke:
	powershell -ExecutionPolicy Bypass -File scripts/api_smoke.ps1

web-smoke:
	powershell -ExecutionPolicy Bypass -File scripts/web_smoke.ps1

agent-smoke:
	powershell -ExecutionPolicy Bypass -File scripts/agent_smoke.ps1

api-dev:
	cd $(API_DIR) && uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload

api-test:
	cd $(API_DIR) && pytest

api-lint:
	cd $(API_DIR) && ruff check . && mypy --strict app

web-dev:
	cd $(WEB_DIR) && npm run dev

web-build:
	cd $(WEB_DIR) && npm run build

web-test:
	cd $(WEB_DIR) && npm test -- --run

web-lint:
	cd $(WEB_DIR) && npm run lint && npm run typecheck

agent-build:
	cd $(AGENT_DIR) && dotnet build Timesheet.Agent.sln -c Debug

agent-test:
	cd $(AGENT_DIR) && dotnet test Timesheet.Agent.sln -c Debug --no-restore

agent-format:
	cd $(AGENT_DIR) && dotnet format Timesheet.Agent.sln --verify-no-changes

data-dir:
	@powershell -NoProfile -Command "if (-not (Test-Path data)) { New-Item -ItemType Directory data | Out-Null }"

# -----------------------------------------------------------------------
# Build de producao
# -----------------------------------------------------------------------

build-backend:
	powershell -ExecutionPolicy Bypass -File $(API_DIR)/scripts/build-backend.ps1

publish-agent:
	powershell -ExecutionPolicy Bypass -File $(AGENT_DIR)/scripts/publish-agent.ps1

installer-validate:
	@powershell -NoProfile -Command "if (-not (Test-Path dist)) { New-Item -ItemType Directory dist | Out-Null }"
	wix build $(INSTALLER_DIR)/Product.wxs $(INSTALLER_DIR)/Components.wxs -ext WixToolset.Util.wixext -ext WixToolset.UI.wixext -o dist/TimesheetTerceiros.msi

build: build-backend publish-agent installer-validate

release: build
	powershell -NoProfile -Command "if ($$env:SIGN_CERT) { signtool sign /f $$env:SIGN_CERT /fd SHA256 /t http://timestamp.digicert.com dist/TimesheetTerceiros.msi; Write-Host '[release] MSI assinado.' } else { Write-Host '[release] SIGN_CERT ausente -- MSI nao assinado (dev).' }"

setup: data-dir
	@powershell -NoProfile -Command "Write-Host '[setup] Ambiente dev preparado (data/). Producao via MSI.'"

smtp-up:
	docker compose -f docker-compose.dev.yml up -d mailhog
	@powershell -NoProfile -Command "$$max = 30; for ($$i = 1; $$i -le $$max; $$i++) { $$state = (docker inspect -f '{{.State.Health.Status}}' timesheet-mailhog 2>$$null); if ($$state -eq 'healthy') { Write-Host '[mailhog] healthy'; exit 0 }; Start-Sleep -Seconds 1 }; Write-Error '[mailhog] nao ficou healthy em 30s'; exit 1"

smtp-down:
	docker compose -f docker-compose.dev.yml down -v

smtp-status:
	docker compose -f docker-compose.dev.yml ps mailhog
