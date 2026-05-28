from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore  # type: ignore[import-untyped]
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore[import-untyped]
from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-untyped]

from app.core import config as _config
from app.core.db import get_sessionmaker

logger = logging.getLogger(__name__)


async def gerar_e_enviar_mensal() -> None:
    sm = get_sessionmaker()
    async with sm() as session:
        # Mês anterior (em BRT = UTC-3)
        now = datetime.utcnow() - timedelta(hours=3)
        primeiro_dia_mes = now.replace(day=1)
        ultimo_mes = (primeiro_dia_mes - timedelta(days=1)).strftime("%Y-%m")
        try:
            from app.modules.relatorios.service import enviar_relatorio  # noqa: PLC0415

            await enviar_relatorio(session, ultimo_mes)
        except Exception as exc:
            logger.error("scheduler_envio_falhou", exc_info=exc)


async def purge_old_pdfs() -> None:
    sm = get_sessionmaker()
    cutoff = (datetime.now(UTC) - timedelta(days=24 * 30)).isoformat()  # ~24 meses
    async with sm() as session:
        from app.modules.relatorios.repository import RelatorioRepository  # noqa: PLC0415

        repo = RelatorioRepository(session)
        rows = await repo.list_to_purge(cutoff)
        for r in rows:
            try:
                p = Path(r.caminho_arquivo)
                if p.exists():
                    p.unlink()
            except OSError as exc:
                logger.warning(
                    "purge_falhou_remover_arquivo",
                    extra={"path": r.caminho_arquivo, "error": str(exc)},
                )
            await repo.delete(r)
        await session.commit()
        logger.info("purge_old_pdfs_done", extra={"removed": len(rows)})


def build_scheduler() -> AsyncIOScheduler:
    if not _config.settings.scheduler_enabled:
        # Quando desabilitado, usa jobstore em memória (sem persistência, sem jobs)
        from apscheduler.jobstores.memory import MemoryJobStore  # type: ignore[import-untyped]  # noqa: I001, PLC0415

        sched = AsyncIOScheduler(
            jobstores={"default": MemoryJobStore()},
            job_defaults={"misfire_grace_time": 3600, "coalesce": True},
            timezone="America/Sao_Paulo",
        )
        return sched
    jobstore_url = f"sqlite:///{_config.settings.scheduler_jobstore}"
    Path(_config.settings.scheduler_jobstore).parent.mkdir(parents=True, exist_ok=True)
    sched = AsyncIOScheduler(
        jobstores={"default": SQLAlchemyJobStore(url=jobstore_url)},
        job_defaults={"misfire_grace_time": 3600, "coalesce": True},
        timezone="America/Sao_Paulo",
    )
    sched.add_job(
        gerar_e_enviar_mensal,
        id="relatorios_mensal",
        trigger=CronTrigger(day=1, hour=0, minute=0),
        replace_existing=True,
    )
    sched.add_job(
        purge_old_pdfs,
        id="relatorios_purge",
        trigger=CronTrigger(day_of_week="sun", hour=2, minute=0),
        replace_existing=True,
    )
    return sched


_scheduler_instance: AsyncIOScheduler | None = None


def start_scheduler() -> None:
    global _scheduler_instance
    if _scheduler_instance is not None:
        return
    _scheduler_instance = build_scheduler()
    if _config.settings.scheduler_enabled:
        _scheduler_instance.start()


def stop_scheduler() -> None:
    global _scheduler_instance
    if _scheduler_instance is not None and _scheduler_instance.running:
        _scheduler_instance.shutdown(wait=True)
    _scheduler_instance = None


def get_scheduler() -> AsyncIOScheduler | None:
    return _scheduler_instance
