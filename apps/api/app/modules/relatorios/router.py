from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi import Path as FastPath
from fastapi.responses import FileResponse

from app.core.deps import CurrentTerceiroDep, SessionDep
from app.modules.relatorios import service
from app.modules.relatorios.repository import RelatorioRepository
from app.modules.relatorios.schema import (
    EnviarRelatorioRequest,
    EnviarResponse,
    HistoricoEnvioItem,
    RelatorioMesResponse,
)

router = APIRouter(prefix="/api/v1/relatorios", tags=["relatorios"])

_MES_PATTERN = r"^\d{4}-\d{2}$"


@router.get("/{mes}")
async def download(
    mes: str = FastPath(pattern=_MES_PATTERN),
    _t: CurrentTerceiroDep = None,  # type: ignore[assignment]
    session: SessionDep = None,  # type: ignore[assignment]
) -> FileResponse:
    rel_repo = RelatorioRepository(session)
    r = await rel_repo.get_by_mes(mes)
    if r is None or r.invalidado_em is not None or not Path(r.caminho_arquivo).exists():
        await service.gerar_pdf(session, mes)
        r = await rel_repo.get_by_mes(mes)
    assert r is not None
    return FileResponse(
        r.caminho_arquivo,
        media_type="application/pdf",
        filename=f"relatorio-{mes}.pdf",
    )


@router.get("/{mes}/meta", response_model=RelatorioMesResponse)
async def meta(
    mes: str = FastPath(pattern=_MES_PATTERN),
    _t: CurrentTerceiroDep = None,  # type: ignore[assignment]
    session: SessionDep = None,  # type: ignore[assignment]
) -> RelatorioMesResponse:
    data = await service.get_meta(session, mes)
    return RelatorioMesResponse(**data)


@router.post("/{mes}/enviar", status_code=202, response_model=EnviarResponse)
async def enviar(
    mes: str = FastPath(pattern=_MES_PATTERN),
    body: EnviarRelatorioRequest | None = None,
    _t: CurrentTerceiroDep = None,  # type: ignore[assignment]
    session: SessionDep = None,  # type: ignore[assignment]
) -> EnviarResponse:
    override = body.email if body else None
    data = await service.enviar_relatorio(session, mes, email_override=override)
    return EnviarResponse(**data)


@router.get("/{mes}/historico", response_model=list[HistoricoEnvioItem])
async def historico(
    mes: str = FastPath(pattern=_MES_PATTERN),
    _t: CurrentTerceiroDep = None,  # type: ignore[assignment]
    session: SessionDep = None,  # type: ignore[assignment]
) -> list[HistoricoEnvioItem]:
    rows = await service.listar_historico(session, mes)
    return [HistoricoEnvioItem(**r) for r in rows]
