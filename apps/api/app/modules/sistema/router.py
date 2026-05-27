from fastapi import APIRouter

from app import __version__

router = APIRouter(prefix="/api/v1", tags=["sistema"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}
