from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, Field

from app.core.errors import DomainError, install_error_handlers


class BodyIn(BaseModel):
    senha: str = Field(min_length=8)


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()
    install_error_handlers(app)

    @app.post("/v")
    async def v(b: BodyIn) -> dict[str, str]:
        return {"ok": "1"}

    @app.get("/boom")
    async def boom() -> None:
        raise DomainError(code="CONFLICT", message="Conflito", http_status=409)

    return app


@pytest.mark.asyncio
async def test_validation_error_returns_padronizado(app: FastAPI) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        r = await client.post("/v", json={"senha": "abc"})
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["message"] == "Erro de validação"
    assert isinstance(body["details"], list) and len(body["details"]) >= 1
    assert "field" in body["details"][0] and "issue" in body["details"][0]


@pytest.mark.asyncio
async def test_domain_error_serializes_padronizado(app: FastAPI) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        r = await client.get("/boom")
    assert r.status_code == 409
    assert r.json() == {"code": "CONFLICT", "message": "Conflito", "details": []}
