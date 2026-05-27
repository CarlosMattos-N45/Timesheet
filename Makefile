.PHONY: help api-dev api-test api-lint

API_DIR := apps/api

help:
	@echo Comandos disponiveis:
	@echo   help      - mostra esta mensagem
	@echo   api-dev   - inicia servidor de desenvolvimento da API
	@echo   api-test  - executa testes da API
	@echo   api-lint  - executa ruff e mypy na API

api-dev:
	cd $(API_DIR) && uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload

api-test:
	cd $(API_DIR) && pytest

api-lint:
	cd $(API_DIR) && ruff check . && mypy --strict app
