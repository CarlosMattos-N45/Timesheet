from __future__ import annotations

import re

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


class Settings(BaseSettings):
    dev_mode: bool = Field(
        default=False,
        validation_alias=AliasChoices("TIMESHEET_DEV", "dev_mode"),
    )
    port: int = Field(
        default=8765,
        validation_alias=AliasChoices("TIMESHEET_PORT", "port"),
    )
    host: str = Field(
        default="127.0.0.1",
        validation_alias=AliasChoices("TIMESHEET_HOST", "host"),
    )
    db_url: str = Field(
        default="sqlite+aiosqlite:///./data/timesheet.sqlite",
        validation_alias=AliasChoices("TIMESHEET_DB_URL", "db_url"),
    )
    db_cipher_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("TIMESHEET_DB_CIPHER_KEY", "db_cipher_key"),
    )

    @field_validator("db_cipher_key")
    @classmethod
    def _validate_cipher_key(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        if not _HEX64.match(v):
            raise ValueError(
                "TIMESHEET_DB_CIPHER_KEY deve ter exatamente 64 caracteres hex (256 bits)"
            )
        return v

    model_config = SettingsConfigDict(env_file=".env", populate_by_name=True)


settings = Settings()
