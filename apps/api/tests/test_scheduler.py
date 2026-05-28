from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


def test_scheduler_jobs_registered_when_enabled(monkeypatch) -> None:
    monkeypatch.setenv("TIMESHEET_SCHEDULER_ENABLED", "true")
    from app.core import config

    config.settings = config.Settings()  # type: ignore[call-arg]
    from app.modules.relatorios import scheduler

    sched = scheduler.build_scheduler()
    job_ids = {j.id for j in sched.get_jobs()}
    assert "relatorios_mensal" in job_ids
    assert "relatorios_purge" in job_ids


def test_scheduler_disabled_when_flag_false(monkeypatch) -> None:
    monkeypatch.setenv("TIMESHEET_SCHEDULER_ENABLED", "false")
    from app.core import config

    config.settings = config.Settings()  # type: ignore[call-arg]
    from app.modules.relatorios import scheduler

    sched = scheduler.build_scheduler()
    # Quando desabilitado, scheduler é construído mas sem jobs
    assert len(sched.get_jobs()) == 0


@pytest.mark.asyncio
async def test_purge_remove_arquivos_e_relatorios_antigos(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{tmp_path}/t.sqlite")
    monkeypatch.setenv("TIMESHEET_PDF_DIR", str(tmp_path / "pdf"))
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "x" * 40)
    from sqlalchemy import select  # noqa: PLC0415

    from app.core import config
    from app.core import db as db_mod
    from app.core.base import Base
    from app.models import RelatorioGerado

    config.settings = config.Settings()  # type: ignore[call-arg]
    db_mod._engine = None
    db_mod._sessionmaker = None
    engine = db_mod.get_engine()
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    sm = db_mod.get_sessionmaker()
    pdf_dir = tmp_path / "pdf"
    pdf_dir.mkdir()
    old_file = pdf_dir / "2023-01.pdf"
    old_file.write_bytes(b"%PDF-fake")
    recent_file = pdf_dir / "2026-05.pdf"
    recent_file.write_bytes(b"%PDF-fake")
    async with sm() as s:
        s.add(
            RelatorioGerado(
                id="r-old",
                mes_referencia="2023-01",
                caminho_arquivo=str(old_file),
                gerado_em="2023-01-01T00:00:00+00:00",
            )
        )
        s.add(
            RelatorioGerado(
                id="r-recent",
                mes_referencia="2026-05",
                caminho_arquivo=str(recent_file),
                gerado_em="2026-05-01T00:00:00+00:00",
            )
        )
        await s.commit()

    from app.modules.relatorios.scheduler import purge_old_pdfs

    await purge_old_pdfs()

    async with sm() as s:
        rows = (await s.execute(select(RelatorioGerado))).scalars().all()
        ids = {r.id for r in rows}
        assert "r-old" not in ids  # removido
        assert "r-recent" in ids  # mantido
    assert not old_file.exists()
    assert recent_file.exists()
    await engine.dispose()


def test_start_stop_get_scheduler(monkeypatch) -> None:
    """Cobre start_scheduler, stop_scheduler e get_scheduler."""
    monkeypatch.setenv("TIMESHEET_SCHEDULER_ENABLED", "false")
    from app.core import config

    config.settings = config.Settings()  # type: ignore[call-arg]
    from app.modules.relatorios import scheduler

    # Garante estado limpo
    scheduler._scheduler_instance = None

    scheduler.start_scheduler()
    assert scheduler.get_scheduler() is not None

    # Segunda chamada não deve criar outro
    first = scheduler.get_scheduler()
    scheduler.start_scheduler()
    assert scheduler.get_scheduler() is first

    scheduler.stop_scheduler()
    assert scheduler._scheduler_instance is None

    # Stop idempotente
    scheduler.stop_scheduler()


@pytest.mark.asyncio
async def test_gerar_e_enviar_mensal_loga_erro_e_nao_propaga(tmp_path, monkeypatch) -> None:
    """Cobre gerar_e_enviar_mensal: garante que exceção é capturada e não propagada."""
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{tmp_path}/t.sqlite")
    monkeypatch.setenv("TIMESHEET_JWT_SECRET", "x" * 40)
    from app.core import config
    from app.core import db as db_mod
    from app.core.base import Base

    config.settings = config.Settings()  # type: ignore[call-arg]
    db_mod._engine = None
    db_mod._sessionmaker = None
    engine = db_mod.get_engine()
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.create_all)

    from app.modules.relatorios import scheduler

    # gerar_e_enviar_mensal faz import local de enviar_relatorio; patcheia no módulo service
    with patch(
        "app.modules.relatorios.service.enviar_relatorio",
        new=AsyncMock(side_effect=RuntimeError("boom")),
    ):
        # Não deve propagar exceção
        await scheduler.gerar_e_enviar_mensal()
    await engine.dispose()
