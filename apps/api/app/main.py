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
from app.modules.atividades.router import router as atividades_router
from app.modules.auditoria.router import router as auditoria_router
from app.modules.auth.router import router as auth_router
from app.modules.jornadas.router import router as jornadas_router
from app.modules.marcacoes.router import router as marcacoes_router
from app.modules.privacidade.router import router as privacidade_router
from app.modules.relatorios.router import router as relatorios_router
from app.modules.sistema.router import bind_smoke_rate_limit
from app.modules.sistema.router import router as sistema_router
from app.modules.sistema.router import router_dev as sistema_router_dev
from app.modules.smtp.router import router as smtp_router
from app.modules.terceiros.router import router as terceiros_router


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    configure_logging()
    from app.core import crypto_state  # noqa: PLC0415

    crypto_state.configure()
    from app.modules.relatorios.invalidation import register_invalidation_listener  # noqa: PLC0415

    register_invalidation_listener()
    from app.modules.relatorios.scheduler import start_scheduler, stop_scheduler  # noqa: PLC0415

    start_scheduler()
    yield
    stop_scheduler()
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

    # Middlewares + limiter (ordem importa: SlowAPI dentro, security headers fora)
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

    # ROUTERS — ordem canônica
    app.include_router(sistema_router)      # /health /config /ready
    app.include_router(auth_router)         # /auth/*
    app.include_router(terceiros_router)    # /terceiros/*
    app.include_router(privacidade_router)  # /privacidade/*
    app.include_router(smtp_router)         # /smtp/*
    app.include_router(marcacoes_router)    # /marcacoes/*
    app.include_router(jornadas_router)     # /jornadas/*
    app.include_router(atividades_router)   # /jornadas/{id}/atividade
    app.include_router(auditoria_router)    # /auditoria
    app.include_router(relatorios_router)   # /relatorios/*

    # Rate limit aplicado aos endpoints reais de auth
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
        bind_smoke_rate_limit(app)

    # SPA mount — routers /api/* registered above keep precedence.
    # The catch-all is added LAST so specific routes always win.
    from fastapi import HTTPException  # noqa: PLC0415
    from fastapi.responses import FileResponse  # noqa: PLC0415
    from fastapi.staticfiles import StaticFiles  # noqa: PLC0415

    from app.launcher import static_dir_for_bundle  # noqa: PLC0415

    static_dir = static_dir_for_bundle()
    assets = static_dir / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="assets")

    # Paths that belong to the framework but are disabled in prod (docs/openapi).
    _RESERVED_PREFIXES = ("api", "docs", "redoc", "openapi.json")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _spa_fallback(full_path: str) -> FileResponse:
        # Paths under /api/ are API territory — if they reach this catch-all it
        # means no router handled them, so return 404 rather than index.html.
        # Also preserve 404 behaviour for framework paths (/docs etc.) that are
        # disabled in production.
        if any(full_path.startswith(p) for p in _RESERVED_PREFIXES):
            raise HTTPException(status_code=404)
        return FileResponse(str(static_dir / "index.html"))

    return app


app = create_app()
