from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from starlette.types import ASGIApp

_CSP = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"
_VALID_HOSTS = {"127.0.0.1", "localhost"}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = _CSP
        return response


class HostHeaderValidationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, valid_hosts: set[str] | None = None) -> None:
        super().__init__(app)
        self._valid = valid_hosts or _VALID_HOSTS

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        raw_host = request.headers.get("host", "").split(":")[0]
        if raw_host and raw_host not in self._valid:
            return JSONResponse(
                status_code=400,
                content={"code": "INVALID_HOST", "message": "Host inválido", "details": []},
            )
        return await call_next(request)


def make_limiter() -> Limiter:
    return Limiter(key_func=get_remote_address, default_limits=[])
