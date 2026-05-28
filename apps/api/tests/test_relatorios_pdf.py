from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

_FAKE_PDF = b"%PDF-fake"


# ---------------------------------------------------------------------------
# Testes unitários dos helpers internos de pdf.py (não exigem WeasyPrint)
# ---------------------------------------------------------------------------


def test_format_secs_none_returns_dash() -> None:
    from app.modules.relatorios.pdf import _format_secs  # noqa: PLC0415

    assert _format_secs(None) == "—"


def test_format_secs_zero_returns_dash() -> None:
    from app.modules.relatorios.pdf import _format_secs  # noqa: PLC0415

    assert _format_secs(0) == "—"


def test_format_secs_positive() -> None:
    from app.modules.relatorios.pdf import _format_secs  # noqa: PLC0415

    assert _format_secs(3661) == "01:01"


def test_dia_semana_segunda() -> None:
    from app.modules.relatorios.pdf import _dia_semana  # noqa: PLC0415

    assert _dia_semana("2026-05-25") == "Seg"


def test_dia_semana_domingo() -> None:
    from app.modules.relatorios.pdf import _dia_semana  # noqa: PLC0415

    assert _dia_semana("2026-05-31") == "Dom"


def test_build_context_structure() -> None:
    from app.modules.relatorios.pdf import _build_context  # noqa: PLC0415

    terceiro = object()
    jornadas = [
        {
            "data": "2026-05-27",
            "status": "FECHADA",
            "total_horas_apuradas_s": 28800,
            "marcacoes": [
                {"tipo": "INICIO_JORNADA", "horario_efetivo": "2026-05-27T09:00:00+00:00"},
            ],
            "atividade": {"descricao": "Desenvolvimento"},
        }
    ]
    ctx = _build_context(terceiro, jornadas, "2026-05")
    assert ctx["mes_referencia"] == "2026-05"
    assert ctx["terceiro"] is terceiro
    assert len(ctx["jornadas"]) == 1
    j = ctx["jornadas"][0]
    assert j["data"] == "2026-05-27"
    assert j["dia_semana"] == "Qua"
    assert j["total_str"] == "08:00"
    assert j["atividade"] == "Desenvolvimento"
    assert j["horarios"]["INICIO_JORNADA"] == "09:00"


@pytest.mark.asyncio
async def test_render_pdf_raises_no_data_when_empty() -> None:
    from app.core.errors import DomainError  # noqa: PLC0415
    from app.modules.relatorios.pdf import render_pdf  # noqa: PLC0415

    with pytest.raises(DomainError) as exc:
        await render_pdf(object(), [], "2026-05")
    assert exc.value.code == "NO_DATA"


@pytest_asyncio.fixture
async def session_with_jornada(tmp_path, monkeypatch):
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{tmp_path}/t.sqlite")
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "x" * 40)
    monkeypatch.setenv("TIMESHEET_KEK_PATH", str(tmp_path / "key.kek"))
    monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    monkeypatch.setenv("TIMESHEET_PDF_DIR", str(tmp_path / "pdf"))
    from app.core import config
    from app.core import db as db_mod
    from app.core.base import Base
    from app.core.security import hash_password
    from app.models import Jornada, Marcacao, Terceiro

    config.settings = config.Settings()  # type: ignore[call-arg]
    db_mod._engine = None
    db_mod._sessionmaker = None

    engine = db_mod.get_engine()
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    sm = db_mod.get_sessionmaker()
    now = datetime.now(UTC).isoformat()
    async with sm() as s:
        t = Terceiro(
            id="t-1",
            nome="Maria Silva",
            empresa_nome="ACME LTDA",
            empresa_cnpj="00000000000191",
            horario_inicio_jornada="09:00:00",
            horario_saida_almoco="12:00:00",
            horario_retorno_almoco="13:00:00",
            horario_fim_jornada="18:00:00",
            trabalha_fim_de_semana=0,
            email_contato="u@x.com",
            senha_hash=hash_password("Senha123!"),
            criado_em=now,
            atualizado_em=now,
        )
        s.add(t)
        s.add(
            Jornada(
                id="j-1",
                terceiro_id="t-1",
                data="2026-05-27",
                status="FECHADA",
                total_horas_apuradas_s=28800,
                criada_em=now,
            )
        )
        for i, (tipo, h) in enumerate(
            [
                ("INICIO_JORNADA", "2026-05-27T09:00:00+00:00"),
                ("SAIDA_ALMOCO", "2026-05-27T12:00:00+00:00"),
                ("RETORNO_ALMOCO", "2026-05-27T13:00:00+00:00"),
                ("FIM_JORNADA", "2026-05-27T18:00:00+00:00"),
            ]
        ):
            s.add(
                Marcacao(
                    id=f"m-{i}",
                    jornada_id="j-1",
                    tipo=tipo,
                    horario_registrado=h,
                    horario_efetivo=h,
                    origem="AGENTE_AUTOMATICO",
                    status="CONFIRMADA",
                    idempotency_key=f"idem-{i}-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"[:36],
                    criada_em=now,
                )
            )
        await s.commit()
    yield sm, t
    await engine.dispose()


@pytest.mark.asyncio
async def test_gerar_pdf_cria_arquivo_e_relatorio_gerado(
    session_with_jornada, tmp_path, monkeypatch
) -> None:
    sm, _t = session_with_jornada
    from sqlalchemy import select  # noqa: PLC0415

    from app.models import RelatorioGerado
    from app.modules.relatorios import service as svc_mod

    monkeypatch.setattr(svc_mod, "render_pdf", AsyncMock(return_value=_FAKE_PDF))
    from app.modules.relatorios.service import gerar_pdf

    async with sm() as s:
        await gerar_pdf(s, "2026-05")
    async with sm() as s:
        r = (await s.execute(select(RelatorioGerado))).scalar_one()
        assert r.mes_referencia == "2026-05"
        assert Path(r.caminho_arquivo).exists()
        assert Path(r.caminho_arquivo).read_bytes().startswith(b"%PDF")
        assert r.invalidado_em is None


@pytest.mark.asyncio
async def test_gerar_pdf_sem_jornadas_levanta_no_data(session_with_jornada) -> None:
    sm, _t = session_with_jornada
    from app.core.errors import DomainError
    from app.modules.relatorios.service import gerar_pdf

    async with sm() as s:
        with pytest.raises(DomainError) as exc:
            await gerar_pdf(s, "2026-04")
        assert exc.value.code == "NO_DATA"


@pytest.mark.asyncio
async def test_invalidacao_seta_invalidado_em_ao_mutar_jornada(
    session_with_jornada, monkeypatch
) -> None:
    sm, _t = session_with_jornada
    from sqlalchemy import select  # noqa: PLC0415

    from app.models import Jornada, RelatorioGerado
    from app.modules.relatorios import service as svc_mod

    monkeypatch.setattr(svc_mod, "render_pdf", AsyncMock(return_value=_FAKE_PDF))
    from app.modules.relatorios.service import gerar_pdf

    async with sm() as s:
        await gerar_pdf(s, "2026-05")
    # Mutar jornada
    async with sm() as s:
        j = (await s.execute(select(Jornada).where(Jornada.id == "j-1"))).scalar_one()
        j.status = "AJUSTADA_MANUALMENTE"
        await s.commit()
    async with sm() as s:
        r = (
            await s.execute(
                select(RelatorioGerado).where(RelatorioGerado.mes_referencia == "2026-05")
            )
        ).scalar_one()
        assert r.invalidado_em is not None
