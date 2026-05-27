from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import db as db_mod
from app.core.base import Base
from app.models import (
    Atividade,
    HistoricoEnvioRelatorio,  # noqa: F401 — força registro da tabela no metadata
    Jornada,
    Justificativa,  # noqa: F401 — força registro da tabela no metadata
    LogAuditoria,  # noqa: F401 — força registro da tabela no metadata
    Marcacao,
    PrivacyAcceptance,
    RefreshToken,
    RelatorioGerado,  # noqa: F401 — força registro da tabela no metadata
    SmtpConfig,
    Terceiro,
)


@pytest_asyncio.fixture
async def session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):  # type: ignore[misc]
    db_file = tmp_path / "models.sqlite"
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{db_file}")
    from app.core import config

    config.settings = config.Settings()  # type: ignore[call-arg]
    db_mod._engine = None
    db_mod._sessionmaker = None
    engine = db_mod.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = db_mod.get_sessionmaker()
    async with sm() as s:
        yield s
    await engine.dispose()


def _now() -> str:
    return datetime.now(UTC).isoformat()


@pytest.mark.asyncio
async def test_all_11_tables_in_metadata() -> None:
    expected = {
        "terceiro",
        "jornada",
        "marcacao",
        "atividade",
        "justificativa",
        "log_auditoria",
        "historico_envio_relatorio",
        "refresh_token",
        "relatorio_gerado",
        "smtp_config",
        "privacy_acceptance",
    }
    assert expected.issubset(set(Base.metadata.tables.keys()))


@pytest.mark.asyncio
async def test_terceiro_roundtrip(session: AsyncSession) -> None:
    t = Terceiro(
        id=str(uuid4()),
        nome="Maria",
        empresa_nome="ACME",
        empresa_cnpj="00000000000191",
        horario_inicio_jornada="09:00:00",
        horario_saida_almoco="12:00:00",
        horario_retorno_almoco="13:00:00",
        horario_fim_jornada="18:00:00",
        trabalha_fim_de_semana=0,
        email_contato="m@a.com",
        senha_hash="hash",
        criado_em=_now(),
        atualizado_em=_now(),
    )
    session.add(t)
    await session.commit()
    fetched = (await session.execute(select(Terceiro).where(Terceiro.id == t.id))).scalar_one()
    assert fetched.nome == "Maria"
    assert fetched.empresa_cnpj == "00000000000191"


@pytest.mark.asyncio
async def test_terceiro_check_constraint(session: AsyncSession) -> None:
    t = Terceiro(
        id=str(uuid4()),
        nome="X",
        empresa_nome="Y",
        empresa_cnpj="00000000000191",
        horario_inicio_jornada="12:00:00",  # depois do almoco - viola CHECK
        horario_saida_almoco="11:00:00",
        horario_retorno_almoco="13:00:00",
        horario_fim_jornada="18:00:00",
        trabalha_fim_de_semana=0,
        email_contato="z@z.com",
        senha_hash="h",
        criado_em=_now(),
        atualizado_em=_now(),
    )
    session.add(t)
    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_jornada_marcacoes_relationship(session: AsyncSession) -> None:
    t = Terceiro(
        id="t1",
        nome="Maria",
        empresa_nome="ACME",
        empresa_cnpj="00000000000191",
        horario_inicio_jornada="09:00:00",
        horario_saida_almoco="12:00:00",
        horario_retorno_almoco="13:00:00",
        horario_fim_jornada="18:00:00",
        trabalha_fim_de_semana=0,
        email_contato="m@a.com",
        senha_hash="h",
        criado_em=_now(),
        atualizado_em=_now(),
    )
    j = Jornada(
        id="j1", terceiro_id="t1", data="2026-05-27", status="EM_ANDAMENTO", criada_em=_now()
    )
    m1 = Marcacao(
        id="m1",
        jornada_id="j1",
        tipo="INICIO_JORNADA",
        horario_registrado=_now(),
        origem="AGENTE_AUTOMATICO",
        idempotency_key="11111111-1111-1111-1111-111111111111",
        criada_em=_now(),
    )
    m2 = Marcacao(
        id="m2",
        jornada_id="j1",
        tipo="FIM_JORNADA",
        horario_registrado=_now(),
        origem="AGENTE_AUTOMATICO",
        idempotency_key="22222222-2222-2222-2222-222222222222",
        criada_em=_now(),
    )
    session.add_all([t, j, m1, m2])
    await session.commit()
    fetched = (
        await session.execute(
            select(Jornada).where(Jornada.id == "j1").options(selectinload(Jornada.marcacoes))
        )
    ).scalar_one()
    tipos = {m.tipo for m in fetched.marcacoes}
    assert tipos == {"INICIO_JORNADA", "FIM_JORNADA"}


@pytest.mark.asyncio
async def test_marcacao_tipo_check_constraint(session: AsyncSession) -> None:
    t = Terceiro(
        id="t1",
        nome="Maria",
        empresa_nome="ACME",
        empresa_cnpj="00000000000191",
        horario_inicio_jornada="09:00:00",
        horario_saida_almoco="12:00:00",
        horario_retorno_almoco="13:00:00",
        horario_fim_jornada="18:00:00",
        trabalha_fim_de_semana=0,
        email_contato="m@a.com",
        senha_hash="h",
        criado_em=_now(),
        atualizado_em=_now(),
    )
    j = Jornada(
        id="j1", terceiro_id="t1", data="2026-05-27", status="EM_ANDAMENTO", criada_em=_now()
    )
    session.add_all([t, j])
    await session.commit()
    m = Marcacao(
        id="m_bad",
        jornada_id="j1",
        tipo="TIPO_INVALIDO",  # nao existe
        horario_registrado=_now(),
        origem="AGENTE_AUTOMATICO",
        idempotency_key="33333333-3333-3333-3333-333333333333",
        criada_em=_now(),
    )
    session.add(m)
    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_atividade_one_to_one_with_jornada(session: AsyncSession) -> None:
    t = Terceiro(
        id="t1",
        nome="X",
        empresa_nome="Y",
        empresa_cnpj="00000000000191",
        horario_inicio_jornada="09:00:00",
        horario_saida_almoco="12:00:00",
        horario_retorno_almoco="13:00:00",
        horario_fim_jornada="18:00:00",
        trabalha_fim_de_semana=0,
        email_contato="m@a.com",
        senha_hash="h",
        criado_em=_now(),
        atualizado_em=_now(),
    )
    j = Jornada(id="j1", terceiro_id="t1", data="2026-05-27", status="FECHADA", criada_em=_now())
    a = Atividade(id="a1", jornada_id="j1", descricao="trabalhei dez horas", registrada_em=_now())
    session.add_all([t, j, a])
    await session.commit()
    fetched_j = (
        await session.execute(
            select(Jornada).where(Jornada.id == "j1").options(selectinload(Jornada.atividade))
        )
    ).scalar_one()
    assert fetched_j.atividade is not None
    assert fetched_j.atividade.descricao == "trabalhei dez horas"


@pytest.mark.asyncio
async def test_smtp_config_singleton_check(session: AsyncSession) -> None:
    cfg = SmtpConfig(
        id=2,  # viola CHECK id=1
        host="smtp.example.com",
        port=587,
        username_enc="ENC1",
        password_enc="ENC2",
        use_starttls=1,
        from_address="noreply@example.com",
        atualizado_em=_now(),
    )
    session.add(cfg)
    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_privacy_acceptance_singleton(session: AsyncSession) -> None:
    p = PrivacyAcceptance(id=1, aceito_em=_now(), versao_aviso="1.0")
    session.add(p)
    await session.commit()
    fetched = (await session.execute(select(PrivacyAcceptance))).scalar_one()
    assert fetched.versao_aviso == "1.0"


@pytest.mark.asyncio
async def test_refresh_token_cascade_on_terceiro_delete(session: AsyncSession) -> None:
    t = Terceiro(
        id="t1",
        nome="X",
        empresa_nome="Y",
        empresa_cnpj="00000000000191",
        horario_inicio_jornada="09:00:00",
        horario_saida_almoco="12:00:00",
        horario_retorno_almoco="13:00:00",
        horario_fim_jornada="18:00:00",
        trabalha_fim_de_semana=0,
        email_contato="m@a.com",
        senha_hash="h",
        criado_em=_now(),
        atualizado_em=_now(),
    )
    rt = RefreshToken(
        id="rt1",
        terceiro_id="t1",
        token_hash="hashvalue",
        expira_em=_now(),
        criado_em=_now(),
    )
    session.add_all([t, rt])
    await session.commit()
    await session.delete(t)
    await session.commit()
    rows = (await session.execute(select(RefreshToken))).scalars().all()
    assert rows == []


def test_alembic_env_uses_base_metadata() -> None:
    # Smoke estatico: env.py importa Base e seta target_metadata = Base.metadata
    env_path = Path(__file__).parent.parent / "alembic" / "env.py"
    content = env_path.read_text(encoding="utf-8")
    assert "from app.core.base import Base" in content
    assert "target_metadata = Base.metadata" in content
    # Garante que models foram importados antes (autogenerate enxerga as tabelas)
    assert "from app import models" in content or "import app.models" in content
