from __future__ import annotations

import contextlib
import smtplib
import time
from email.message import EmailMessage

from app.core.config import settings
from app.core.errors import DomainError


def send_pdf_sync(
    *,
    host: str,
    port: int,
    username: str,
    password: str,
    use_starttls: bool,
    from_address: str,
    to_email: str,
    pdf_bytes: bytes,
    mes_referencia: str,
) -> None:
    """Envia o PDF anexado. Retry 3x backoff linear 5s. Levanta DomainError em falha final."""
    msg = EmailMessage()
    msg["Subject"] = f"Relatório de jornada — {mes_referencia}"
    msg["From"] = from_address
    msg["To"] = to_email
    msg.set_content(f"Segue em anexo o relatório de jornada do mês {mes_referencia}.")
    msg.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=f"relatorio-{mes_referencia}.pdf",
    )
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            if port == 465:
                with smtplib.SMTP_SSL(host, port, timeout=settings.smtp_timeout) as s:
                    if username and password:
                        with contextlib.suppress(smtplib.SMTPNotSupportedError):
                            s.login(username, password)
                    s.send_message(msg)
            else:
                with smtplib.SMTP(host, port, timeout=settings.smtp_timeout) as s:
                    if use_starttls:
                        s.starttls()
                    if username and password:
                        with contextlib.suppress(smtplib.SMTPNotSupportedError):
                            s.login(username, password)
                    s.send_message(msg)
            return
        except (OSError, smtplib.SMTPException) as exc:
            last_err = exc
            if attempt < 2:
                time.sleep(5)
    raise DomainError(
        code="SMTP_SEND_FAILED",
        message=f"Envio SMTP falhou após 3 tentativas: {last_err}",
        http_status=500,
    )
