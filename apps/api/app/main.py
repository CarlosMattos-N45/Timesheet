from fastapi import FastAPI

from app import __version__
from app.core.config import settings
from app.modules.sistema.router import router as sistema_router

app = FastAPI(
    title="TimeSheet Terceiros API",
    version=__version__,
    docs_url="/docs" if settings.dev_mode else None,
    redoc_url="/redoc" if settings.dev_mode else None,
    openapi_url="/openapi.json" if settings.dev_mode else None,
)
app.include_router(sistema_router)
