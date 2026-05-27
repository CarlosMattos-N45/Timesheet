"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-27 18:50:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "terceiro",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("nome", sa.Text(), nullable=False),
        sa.Column("empresa_nome", sa.Text(), nullable=False),
        sa.Column("empresa_cnpj", sa.Text(), nullable=False),
        sa.Column("horario_inicio_jornada", sa.Text(), nullable=False),
        sa.Column("horario_saida_almoco", sa.Text(), nullable=False),
        sa.Column("horario_retorno_almoco", sa.Text(), nullable=False),
        sa.Column("horario_fim_jornada", sa.Text(), nullable=False),
        sa.Column(
            "trabalha_fim_de_semana", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("email_contato", sa.Text(), nullable=False),
        sa.Column("email_destinatario_relatorio", sa.Text(), nullable=True),
        sa.Column("senha_hash", sa.Text(), nullable=False),
        sa.Column("criado_em", sa.Text(), nullable=False),
        sa.Column("atualizado_em", sa.Text(), nullable=False),
        sa.CheckConstraint("length(nome) BETWEEN 1 AND 120", name="ck_terceiro_nome_len"),
        sa.CheckConstraint(
            "length(empresa_nome) BETWEEN 1 AND 150", name="ck_terceiro_empresa_len"
        ),
        sa.CheckConstraint("length(empresa_cnpj) = 14", name="ck_terceiro_cnpj_len"),
        sa.CheckConstraint("length(email_contato) <= 254", name="ck_terceiro_email_len"),
        sa.CheckConstraint(
            "horario_inicio_jornada < horario_saida_almoco "
            "AND horario_saida_almoco < horario_retorno_almoco "
            "AND horario_retorno_almoco < horario_fim_jornada",
            name="ck_terceiro_horarios_crono",
        ),
        sa.UniqueConstraint("email_contato", name="uq_terceiro_email"),
    )

    op.create_table(
        "jornada",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("terceiro_id", sa.Text(), nullable=False),
        sa.Column("data", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("total_horas_apuradas_s", sa.Integer(), nullable=True),
        sa.Column("criada_em", sa.Text(), nullable=False),
        sa.Column("fechada_em", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('EM_ANDAMENTO','FECHADA','AJUSTADA_MANUALMENTE','PENDENTE')",
            name="ck_jornada_status",
        ),
        sa.ForeignKeyConstraint(
            ["terceiro_id"], ["terceiro.id"], ondelete="CASCADE", name="fk_jornada_terceiro"
        ),
        sa.UniqueConstraint("terceiro_id", "data", name="uq_jornada_terceiro_data"),
    )
    op.create_index("idx_jornada_terceiro_data", "jornada", ["terceiro_id", "data"])

    op.create_table(
        "marcacao",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("jornada_id", sa.Text(), nullable=False),
        sa.Column("tipo", sa.Text(), nullable=False),
        sa.Column("horario_registrado", sa.Text(), nullable=False),
        sa.Column("horario_efetivo", sa.Text(), nullable=True),
        sa.Column("origem", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'CONFIRMADA'")),
        sa.Column(
            "confirmado_pelo_usuario", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("criada_em", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "tipo IN ('INICIO_JORNADA','SAIDA_ALMOCO','RETORNO_ALMOCO','FIM_JORNADA')",
            name="ck_marcacao_tipo",
        ),
        sa.CheckConstraint(
            "origem IN ('AGENTE_AUTOMATICO','AGENTE_CONFIRMADO','AJUSTE_WEB')",
            name="ck_marcacao_origem",
        ),
        sa.CheckConstraint(
            "status IN ('CONFIRMADA','PENDENTE','AJUSTADA')",
            name="ck_marcacao_status",
        ),
        sa.CheckConstraint("length(idempotency_key) = 36", name="ck_marcacao_idem_len"),
        sa.ForeignKeyConstraint(["jornada_id"], ["jornada.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("idempotency_key", name="uq_marcacao_idem"),
        sa.UniqueConstraint("jornada_id", "tipo", name="uq_marcacao_jornada_tipo"),
    )
    op.create_index("idx_marcacao_jornada", "marcacao", ["jornada_id"])

    op.create_table(
        "atividade",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("jornada_id", sa.Text(), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("registrada_em", sa.Text(), nullable=False),
        sa.Column("atualizado_em", sa.Text(), nullable=True),
        sa.CheckConstraint("length(descricao) >= 10", name="ck_atividade_desc_len"),
        sa.ForeignKeyConstraint(["jornada_id"], ["jornada.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("jornada_id", name="uq_atividade_jornada"),
    )

    op.create_table(
        "justificativa",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("jornada_id", sa.Text(), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("usuario_responsavel", sa.Text(), nullable=False),
        sa.Column("criada_em", sa.Text(), nullable=False),
        sa.CheckConstraint("length(motivo) >= 5", name="ck_justif_motivo_len"),
        sa.ForeignKeyConstraint(["jornada_id"], ["jornada.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_justificativa_jornada", "justificativa", ["jornada_id"])

    op.create_table(
        "log_auditoria",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("entidade", sa.Text(), nullable=False),
        sa.Column("entidade_id", sa.Text(), nullable=False),
        sa.Column("autor", sa.Text(), nullable=False),
        sa.Column("antes_json", sa.Text(), nullable=True),
        sa.Column("depois_json", sa.Text(), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.Text(), nullable=False),
        sa.Column("expira_em", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "entidade IN ('Jornada','Marcacao','Terceiro','Atividade')",
            name="ck_audit_entidade",
        ),
    )
    op.create_index("idx_audit_entidade", "log_auditoria", ["entidade", "entidade_id"])
    op.create_index("idx_audit_criado_em", "log_auditoria", ["criado_em"])

    op.create_table(
        "historico_envio_relatorio",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("mes_referencia", sa.Text(), nullable=False),
        sa.Column("email_destinatario", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("erro_mensagem", sa.Text(), nullable=True),
        sa.Column("enviado_em", sa.Text(), nullable=False),
        sa.CheckConstraint("length(mes_referencia) = 7", name="ck_hist_mes_len"),
        sa.CheckConstraint("status IN ('SUCESSO','FALHA')", name="ck_hist_status"),
    )
    op.create_index("idx_hist_envio_mes", "historico_envio_relatorio", ["mes_referencia"])

    op.create_table(
        "refresh_token",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("terceiro_id", sa.Text(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expira_em", sa.Text(), nullable=False),
        sa.Column("revogado_em", sa.Text(), nullable=True),
        sa.Column("criado_em", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["terceiro_id"], ["terceiro.id"], ondelete="CASCADE"),
    )
    op.create_index("idx_refresh_token_hash", "refresh_token", ["token_hash"])
    op.create_index("idx_refresh_token_exp", "refresh_token", ["expira_em"])

    op.create_table(
        "relatorio_gerado",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("mes_referencia", sa.Text(), nullable=False),
        sa.Column("caminho_arquivo", sa.Text(), nullable=False),
        sa.Column("gerado_em", sa.Text(), nullable=False),
        sa.Column("invalidado_em", sa.Text(), nullable=True),
        sa.CheckConstraint("length(mes_referencia) = 7", name="ck_relat_mes_len"),
        sa.UniqueConstraint("mes_referencia", name="uq_relat_mes"),
    )

    op.create_table(
        "smtp_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("host", sa.Text(), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("username_enc", sa.Text(), nullable=False),
        sa.Column("password_enc", sa.Text(), nullable=False),
        sa.Column("use_starttls", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("from_address", sa.Text(), nullable=False),
        sa.Column("atualizado_em", sa.Text(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_smtp_singleton"),
    )

    op.create_table(
        "privacy_acceptance",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("aceito_em", sa.Text(), nullable=False),
        sa.Column("versao_aviso", sa.Text(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_priv_singleton"),
    )


def downgrade() -> None:
    op.drop_table("privacy_acceptance")
    op.drop_table("smtp_config")
    op.drop_table("relatorio_gerado")
    op.drop_index("idx_refresh_token_exp", table_name="refresh_token")
    op.drop_index("idx_refresh_token_hash", table_name="refresh_token")
    op.drop_table("refresh_token")
    op.drop_index("idx_hist_envio_mes", table_name="historico_envio_relatorio")
    op.drop_table("historico_envio_relatorio")
    op.drop_index("idx_audit_criado_em", table_name="log_auditoria")
    op.drop_index("idx_audit_entidade", table_name="log_auditoria")
    op.drop_table("log_auditoria")
    op.drop_index("idx_justificativa_jornada", table_name="justificativa")
    op.drop_table("justificativa")
    op.drop_table("atividade")
    op.drop_index("idx_marcacao_jornada", table_name="marcacao")
    op.drop_table("marcacao")
    op.drop_index("idx_jornada_terceiro_data", table_name="jornada")
    op.drop_table("jornada")
    op.drop_table("terceiro")
