from __future__ import annotations

from sqlalchemy import CheckConstraint, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base


class SmtpConfig(Base):
    __tablename__ = "smtp_config"
    __table_args__ = (CheckConstraint("id = 1", name="ck_smtp_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    host: Mapped[str] = mapped_column(Text, nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    username_enc: Mapped[str] = mapped_column(Text, nullable=False)
    password_enc: Mapped[str] = mapped_column(Text, nullable=False)
    use_starttls: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    from_address: Mapped[str] = mapped_column(Text, nullable=False)
    atualizado_em: Mapped[str] = mapped_column(Text, nullable=False)
