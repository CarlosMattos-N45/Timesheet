"""Testes de regressão para erros de importação/startup detectados no hotfix.

Cobre:
1. ImportError: email-validator não instalado (EmailStr sem dependência)
2. AssertionError: rotas com status_code=204 rejeitadas pelo FastAPI 0.115.x
   quando a anotação de retorno resolve para NoneType (com PEP 563).
"""
from __future__ import annotations

import importlib
import sys


def _reload_app_main(monkeypatch) -> None:
    """Remove módulos cacheados e importa app.main limpo."""
    to_remove = [k for k in sys.modules if k.startswith("app.")]
    for k in to_remove:
        del sys.modules[k]
    monkeypatch.setenv("TIMESHEET_DB_URL", "sqlite+aiosqlite:///./test_startup.sqlite")
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "x" * 40)
    importlib.import_module("app.main")


def test_app_main_imports_without_error(monkeypatch, tmp_path) -> None:
    """app.main deve importar sem AssertionError nem ImportError."""
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{tmp_path}/t.sqlite")
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "x" * 40)
    to_remove = [k for k in sys.modules if k.startswith("app.")]
    for k in to_remove:
        del sys.modules[k]
    # Não deve lançar nenhuma exceção
    mod = importlib.import_module("app.main")
    assert hasattr(mod, "app"), "app.main deve expor 'app' (instância FastAPI)"


def test_204_routes_registered_without_assertion_error(monkeypatch, tmp_path) -> None:
    """As 3 rotas com status_code=204 devem ser registradas sem AssertionError."""
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{tmp_path}/t.sqlite")
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "x" * 40)
    to_remove = [k for k in sys.modules if k.startswith("app.")]
    for k in to_remove:
        del sys.modules[k]
    from app.main import create_app
    fastapi_app = create_app()
    routes_204 = [
        r for r in fastapi_app.routes
        if hasattr(r, "status_code") and r.status_code == 204
    ]
    # Devem existir exatamente as 3 rotas 204 (logout, aceitar, me/senha)
    assert len(routes_204) == 3, (
        f"Esperado 3 rotas com status_code=204, encontrado {len(routes_204)}: "
        f"{[getattr(r, 'path', '?') for r in routes_204]}"
    )


def test_email_validator_available() -> None:
    """email-validator deve estar instalado (requerido por EmailStr do pydantic)."""
    import email_validator  # noqa: F401 — só testa a presença do pacote
    assert email_validator.validate_email is not None
