from __future__ import annotations

from fastapi import APIRouter, status

from app.core.deps import CurrentTerceiroDep, SessionDep
from app.modules.privacidade import service
from app.modules.privacidade.schema import PrivacyStatus

router = APIRouter(prefix="/api/v1/privacidade", tags=["privacidade"])


@router.get("", response_model=PrivacyStatus)
async def get_status(_t: CurrentTerceiroDep, session: SessionDep) -> PrivacyStatus:
    return await service.get_status(session)


@router.post("/aceitar", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def aceitar(_t: CurrentTerceiroDep, session: SessionDep) -> None:
    await service.aceitar(session)
