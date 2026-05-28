import importlib
import sys

import pytest
from httpx import ASGITransport, AsyncClient


def _reload_app() -> object:
    """Reload config and main modules to pick up env changes."""
    config_mod = sys.modules.get("app.core.config")
    if config_mod is not None:
        importlib.reload(config_mod)
    main_mod = sys.modules.get("app.main")
    if main_mod is not None:
        importlib.reload(main_mod)
    import app.main as main  # noqa: PLC0415

    return main.app


@pytest.mark.asyncio
async def test_openapi_disabled_without_dev_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TIMESHEET_DEV", raising=False)
    reloaded_app = _reload_app()
    transport = ASGITransport(app=reloaded_app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
        response = await client.get("/docs")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_openapi_enabled_with_dev_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TIMESHEET_DEV", "true")
    reloaded_app = _reload_app()
    transport = ASGITransport(app=reloaded_app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
        response = await client.get("/docs")
    assert response.status_code == 200
