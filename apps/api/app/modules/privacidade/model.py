from __future__ import annotations

from sqlalchemy import CheckConstraint, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class PrivacyAcceptance(Base):
    __tablename__ = "privacy_acceptance"
    __table_args__ = (CheckConstraint("id = 1", name="ck_priv_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    aceito_em: Mapped[str] = mapped_column(Text, nullable=False)
    versao_aviso: Mapped[str] = mapped_column(Text, nullable=False)
