from __future__ import annotations

from httpx import AsyncClient


async def login(
    client: AsyncClient,
    email: str = "user@example.com",
    senha: str = "Senha123!",
) -> str:
    """Helper para obter access_token via POST /api/v1/auth/login."""
    r = await client.post("/api/v1/auth/login", json={"email": email, "senha": senha})
    return r.json()["access_token"]
