from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app import __version__
from app.core import config as _config
from app.core.db import dispose_engine
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import (
    HostHeaderValidationMiddleware,
    SecurityHeadersMiddleware,
    make_limiter,
)
from app.modules.sistema.router import router as sistema_router
from app.modules.sistema.router import router_dev as sistema_router_dev


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    configure_logging()
    from app.core import crypto_state

    crypto_state.configure()
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title="TimeSheet Terceiros API",
        version=__version__,
        lifespan=_lifespan,
        docs_url="/docs" if _config.settings.dev_mode else None,
        redoc_url="/redoc" if _config.settings.dev_mode else None,
        openapi_url="/openapi.json" if _config.settings.dev_mode else None,
    )
    app.state.limiter = make_limiter()
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(HostHeaderValidationMiddleware)
    install_error_handlers(app)

    @app.exception_handler(RateLimitExceeded)
    async def _rl(_req: FastAPI, _exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={
                "code": "RATE_LIMITED",
                "message": "Muitas tentativas. Tente novamente em alguns instantes.",
                "details": [],
            },
        )

    from app.modules.atividades.router import router as atividades_router
    from app.modules.auditoria.router import router as auditoria_router
    from app.modules.auth.router import router as auth_router
    from app.modules.jornadas.router import router as jornadas_router
    from app.modules.marcacoes.router import router as marcacoes_router
    from app.modules.privacidade.router import router as privacidade_router
    from app.modules.smtp.router import router as smtp_router
    from app.modules.terceiros.router import router as terceiros_router

    app.include_router(sistema_router)
    app.include_router(terceiros_router)
    app.include_router(auth_router)
    app.include_router(privacidade_router)
    app.include_router(smtp_router)
    app.include_router(marcacoes_router)
    app.include_router(jornadas_router)
    app.include_router(atividades_router)
    app.include_router(auditoria_router)

    # Apply rate limits to auth endpoints
    limiter = app.state.limiter
    for route in app.routes:
        p = getattr(route, "path", "")
        if p == "/api/v1/auth/login":
            route.endpoint = limiter.limit(_config.settings.rate_limit_login)(route.endpoint)  # type: ignore[attr-defined]
            route.dependant.call = route.endpoint  # type: ignore[attr-defined]
        elif p == "/api/v1/auth/refresh":
            route.endpoint = limiter.limit(_config.settings.rate_limit_refresh)(route.endpoint)  # type: ignore[attr-defined]
            route.dependant.call = route.endpoint  # type: ignore[attr-defined]

    if _config.settings.dev_mode:
        app.include_router(sistema_router_dev)
        from app.modules.sistema.router import bind_smoke_rate_limit

        bind_smoke_rate_limit(app)

    return app


app = create_app()
