import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command


@pytest.fixture
def alembic_cfg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Config:
    db_path = tmp_path / "test_migration.sqlite"
    sync_url = f"sqlite:///{db_path}"  # Alembic usa driver sincrono; ORM async fica fora desta task
    monkeypatch.setenv("TIMESHEET_DB_URL", f"sqlite+aiosqlite:///{db_path}")
    cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", sync_url)
    return cfg


def test_upgrade_creates_all_11_tables(alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    url = alembic_cfg.get_main_option("sqlalchemy.url")
    assert url is not None
    db_path = url.replace("sqlite:///", "")
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    names = {r[0] for r in rows}
    expected = {
        "alembic_version",
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
    assert expected.issubset(names), f"Faltando: {expected - names}"


def test_downgrade_to_base_removes_all_domain_tables(alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")
    url = alembic_cfg.get_main_option("sqlalchemy.url")
    assert url is not None
    db_path = url.replace("sqlite:///", "")
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    names = {r[0] for r in rows}
    # alembic_version pode permanecer (vazia); demais tabelas removidas
    domain_tables = names - {"alembic_version"}
    assert domain_tables == set(), f"Tabelas remanescentes: {domain_tables}"


def test_terceiro_horario_check_constraint(alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    url = alembic_cfg.get_main_option("sqlalchemy.url")
    assert url is not None
    db_path = url.replace("sqlite:///", "")
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
            conn.execute(
                "INSERT INTO terceiro (id, nome, empresa_nome, empresa_cnpj, "
                "horario_inicio_jornada, horario_saida_almoco, horario_retorno_almoco, "
                "horario_fim_jornada, trabalha_fim_de_semana, email_contato, senha_hash, "
                "criado_em, atualizado_em) VALUES "
                "('00000000-0000-0000-0000-000000000001', 'Maria', 'ACME', "
                "'00000000000191', '12:00:00', '11:00:00', '13:00:00', '18:00:00', "
                "0, 'a@a.com', 'hash', '2026-05-27T12:00:00Z', '2026-05-27T12:00:00Z')"
            )


def test_marcacao_idempotency_key_unique(alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    url = alembic_cfg.get_main_option("sqlalchemy.url")
    assert url is not None
    db_path = url.replace("sqlite:///", "")
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        _seed_terceiro_e_jornada(conn)
        conn.execute(
            "INSERT INTO marcacao (id, jornada_id, tipo, horario_registrado, origem, "
            "idempotency_key, criada_em) VALUES "
            "('m1', 'j1', 'INICIO_JORNADA', '2026-05-27T12:00:00Z', 'AGENTE_AUTOMATICO', "
            "'11111111-1111-1111-1111-111111111111', '2026-05-27T12:00:00Z')"
        )
        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
            conn.execute(
                "INSERT INTO marcacao (id, jornada_id, tipo, horario_registrado, origem, "
                "idempotency_key, criada_em) VALUES "
                "('m2', 'j1', 'SAIDA_ALMOCO', '2026-05-27T12:00:00Z', 'AGENTE_AUTOMATICO', "
                "'11111111-1111-1111-1111-111111111111', '2026-05-27T12:00:00Z')"
            )


def test_marcacao_jornada_tipo_unique(alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    url = alembic_cfg.get_main_option("sqlalchemy.url")
    assert url is not None
    db_path = url.replace("sqlite:///", "")
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        _seed_terceiro_e_jornada(conn)
        conn.execute(
            "INSERT INTO marcacao (id, jornada_id, tipo, horario_registrado, origem, "
            "idempotency_key, criada_em) VALUES "
            "('m1', 'j1', 'INICIO_JORNADA', '2026-05-27T12:00:00Z', 'AGENTE_AUTOMATICO', "
            "'11111111-1111-1111-1111-111111111111', '2026-05-27T12:00:00Z')"
        )
        with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
            conn.execute(
                "INSERT INTO marcacao (id, jornada_id, tipo, horario_registrado, origem, "
                "idempotency_key, criada_em) VALUES "
                "('m2', 'j1', 'INICIO_JORNADA', '2026-05-27T12:30:00Z', 'AGENTE_AUTOMATICO', "
                "'22222222-2222-2222-2222-222222222222', '2026-05-27T12:00:00Z')"
            )


def test_jornada_status_check(alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    url = alembic_cfg.get_main_option("sqlalchemy.url")
    assert url is not None
    db_path = url.replace("sqlite:///", "")
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        _seed_terceiro(conn)
        with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
            conn.execute(
                "INSERT INTO jornada (id, terceiro_id, data, status, criada_em) VALUES "
                "('j1', 't1', '2026-05-27', 'INVALIDO', '2026-05-27T12:00:00Z')"
            )


def test_idempotency_key_length_check(alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    url = alembic_cfg.get_main_option("sqlalchemy.url")
    assert url is not None
    db_path = url.replace("sqlite:///", "")
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        _seed_terceiro_e_jornada(conn)
        with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
            conn.execute(
                "INSERT INTO marcacao (id, jornada_id, tipo, horario_registrado, origem, "
                "idempotency_key, criada_em) VALUES "
                "('m1', 'j1', 'INICIO_JORNADA', '2026-05-27T12:00:00Z', 'AGENTE_AUTOMATICO', "
                "'curto', '2026-05-27T12:00:00Z')"
            )


def test_cascade_delete_terceiro(alembic_cfg: Config) -> None:
    command.upgrade(alembic_cfg, "head")
    url = alembic_cfg.get_main_option("sqlalchemy.url")
    assert url is not None
    db_path = url.replace("sqlite:///", "")
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        _seed_terceiro_e_jornada(conn)
        conn.execute(
            "INSERT INTO marcacao (id, jornada_id, tipo, horario_registrado, origem, "
            "idempotency_key, criada_em) VALUES "
            "('m1', 'j1', 'INICIO_JORNADA', '2026-05-27T12:00:00Z', 'AGENTE_AUTOMATICO', "
            "'11111111-1111-1111-1111-111111111111', '2026-05-27T12:00:00Z')"
        )
        conn.execute("DELETE FROM terceiro WHERE id = 't1'")
        conn.commit()
        assert conn.execute("SELECT COUNT(*) FROM jornada").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM marcacao").fetchone()[0] == 0


# Helpers
def _seed_terceiro(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO terceiro (id, nome, empresa_nome, empresa_cnpj, "
        "horario_inicio_jornada, horario_saida_almoco, horario_retorno_almoco, "
        "horario_fim_jornada, trabalha_fim_de_semana, email_contato, senha_hash, "
        "criado_em, atualizado_em) VALUES "
        "('t1', 'Maria', 'ACME', '00000000000191', '09:00:00', '12:00:00', "
        "'13:00:00', '18:00:00', 0, 'a@a.com', 'hash', "
        "'2026-05-27T12:00:00Z', '2026-05-27T12:00:00Z')"
    )


def _seed_terceiro_e_jornada(conn: sqlite3.Connection) -> None:
    _seed_terceiro(conn)
    conn.execute(
        "INSERT INTO jornada (id, terceiro_id, data, status, criada_em) VALUES "
        "('j1', 't1', '2026-05-27', 'EM_ANDAMENTO', '2026-05-27T12:00:00Z')"
    )
