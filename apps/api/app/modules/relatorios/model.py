from __future__ import annotations

from sqlalchemy import CheckConstraint, Index, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class RelatorioGerado(Base):
    __tablename__ = "relatorio_gerado"
    __table_args__ = (
        CheckConstraint("length(mes_referencia) = 7", name="ck_relat_mes_len"),
        UniqueConstraint("mes_referencia", name="uq_relat_mes"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    mes_referencia: Mapped[str] = mapped_column(Text, nullable=False)
    caminho_arquivo: Mapped[str] = mapped_column(Text, nullable=False)
    gerado_em: Mapped[str] = mapped_column(Text, nullable=False)
    invalidado_em: Mapped[str | None] = mapped_column(Text, nullable=True)


class HistoricoEnvioRelatorio(Base):
    __tablename__ = "historico_envio_relatorio"
    __table_args__ = (
        CheckConstraint("length(mes_referencia) = 7", name="ck_hist_mes_len"),
        CheckConstraint("status IN ('SUCESSO','FALHA')", name="ck_hist_status"),
        Index("idx_hist_envio_mes", "mes_referencia"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    mes_referencia: Mapped[str] = mapped_column(Text, nullable=False)
    email_destinatario: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    erro_mensagem: Mapped[str | None] = mapped_column(Text, nullable=True)
    enviado_em: Mapped[str] = mapped_column(Text, nullable=False)
