from __future__ import annotations

from httpx import ASGITransport, AsyncClient


async def login(
    client: AsyncClient,
    email: str = "user@example.com",
    senha: str = "Senha123!",
) -> str:
    """Helper para obter access_token via POST /api/v1/auth/login."""
    r = await client.post("/api/v1/auth/login", json={"email": email, "senha": senha})
    return r.json()["access_token"]


async def login_with_app(
    app: object,
    email: str = "u@x.com",
    senha: str = "Senha123!",
) -> str:
    """Helper para obter access_token criando client interno com ASGITransport."""
    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://127.0.0.1") as c:
        r = await c.post("/api/v1/auth/login", json={"email": email, "senha": senha})
    return r.json()["access_token"]
