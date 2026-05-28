from __future__ import annotations

import io
import logging


def test_redact_sensitive_fields_in_log_output() -> None:
    import structlog

    from app.core.logging import configure_logging

    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    configure_logging(extra_handlers=[handler])
    log = structlog.get_logger("test")
    log.info(
        "login_attempt",
        email="user@example.com",
        senha="MinhaSenha123!",
        password_enc="abc=",
        token_hash="ff00",
    )
    out = buf.getvalue()
    assert "MinhaSenha123!" not in out
    assert "[REDACTED]" in out
    assert "user@example.com" in out  # email não é redacted
    assert "ff00" not in out
