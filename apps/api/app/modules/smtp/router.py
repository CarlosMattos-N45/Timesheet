from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.core.deps import CurrentTerceiroDep, SessionDep
from app.modules.smtp import service
from app.modules.smtp.schema import SmtpConfigRequest, SmtpConfigResponse

router = APIRouter(prefix="/api/v1/smtp", tags=["smtp"])


@router.get("", response_model=SmtpConfigResponse)
async def get_cfg(_t: CurrentTerceiroDep, session: SessionDep) -> SmtpConfigResponse:
    data = await service.get_config(session)
    return SmtpConfigResponse(**data)


@router.put("", response_model=SmtpConfigResponse)
async def put_cfg(
    body: SmtpConfigRequest, _t: CurrentTerceiroDep, session: SessionDep
) -> SmtpConfigResponse:
    data = await service.put_config(session, body.model_dump())
    return SmtpConfigResponse(**data)


@router.post("/test")
async def test_cfg(_t: CurrentTerceiroDep, session: SessionDep) -> dict[str, Any]:
    return await service.test_connection(session)
