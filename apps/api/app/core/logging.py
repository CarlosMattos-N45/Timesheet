from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

_SENSITIVE_FIELDS = {
    "senha",
    "senha_atual",
    "nova_senha",
    "senha_hash",
    "password",
    "password_enc",
    "username_enc",
    "jwt_access_token",
    "jwt_refresh_token",
    "access_token",
    "refresh_token",
    "token_hash",
    "kek",
}


def _redact_sensitive(
    _logger: Any, _name: str, event_dict: structlog.types.EventDict
) -> structlog.types.EventDict:
    for k in list(event_dict.keys()):
        if k.lower() in _SENSITIVE_FIELDS:
            event_dict[k] = "[REDACTED]"
    return event_dict


def configure_logging(extra_handlers: list[logging.Handler] | None = None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if extra_handlers:
        handlers.extend(extra_handlers)
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=handlers,
        force=True,
    )
    structlog.configure(
        processors=[
            _redact_sensitive,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )
