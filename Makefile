.PHONY: help api-dev api-test api-lint web-dev web-build web-test web-lint

API_DIR := apps/api
WEB_DIR := apps/web

help:
	@echo Comandos disponiveis:
	@echo   help       - mostra esta mensagem
	@echo   api-dev    - inicia servidor de desenvolvimento da API
	@echo   api-test   - executa testes da API
	@echo   api-lint   - executa ruff e mypy na API
	@echo   web-dev    - inicia servidor de desenvolvimento do frontend
	@echo   web-build  - build de producao do frontend
	@echo   web-test   - executa testes do frontend
	@echo   web-lint   - executa eslint e typecheck no frontend

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
