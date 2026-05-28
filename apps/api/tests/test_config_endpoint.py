from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.mark.asyncio
async def test_config_returns_settings_snapshot(monkeypatch) -> None:
    monkeypatch.setenv("TIMESHEET_PORT", "8765")
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "x" * 40)
    monkeypatch.setenv("TIMESHEET_DEV", "false")
    from app.core import config
    config.settings = config.Settings()  # type: ignore[call-arg]
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/config")
    assert r.status_code == 200
    body = r.json()
    assert body["port"] == 8765
    assert body["timezone"] == "America/Sao_Paulo"
    assert body["dev_mode"] is False
    assert body["version"]


@pytest.mark.asyncio
async def test_config_no_auth_required(monkeypatch) -> None:
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "x" * 40)
    from app.core import config
    config.settings = config.Settings()  # type: ignore[call-arg]
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.get("/api/v1/config")
    assert r.status_code == 200
