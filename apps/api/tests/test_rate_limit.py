from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_rate_limit_login_5_per_minute(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TIMESHEET_DEV", "true")
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "test-secret-key-min-32-chars-abcdef")
    from app.core import config
    config.settings = config.Settings()  # type: ignore[call-arg]
    from app.main import create_app
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as client:
        last = None
        for _ in range(6):
            last = await client.post(
                "/api/v1/auth/_smoke_login",
                json={"email": "x@y.com", "senha": "abc12345"},
            )
        assert last is not None
        assert last.status_code == 429
        assert last.json()["code"] == "RATE_LIMITED"
