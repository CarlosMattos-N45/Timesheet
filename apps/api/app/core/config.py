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
    jwt_secret: str = Field(
        default="dev-only-jwt-secret-min-32-chars-aaaaaaaaaaa",
        validation_alias=AliasChoices("TIMESHEET_JWT_SECRET", "jwt_secret"),
    )
    jwt_algorithm: str = Field(default="HS256")
    access_token_ttl_seconds: int = Field(default=900)
    refresh_token_ttl_seconds: int = Field(default=2592000)
    rate_limit_login: str = Field(
        default="5/minute",
        validation_alias=AliasChoices("TIMESHEET_RATE_LIMIT_LOGIN", "rate_limit_login"),
    )
    rate_limit_refresh: str = Field(
        default="10/minute",
        validation_alias=AliasChoices("TIMESHEET_RATE_LIMIT_REFRESH", "rate_limit_refresh"),
    )
    kek_path: str = Field(
        default="./data/key.kek",
        validation_alias=AliasChoices("TIMESHEET_KEK_PATH", "kek_path"),
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

    @field_validator("jwt_secret")
    @classmethod
    def _validate_jwt_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("TIMESHEET_JWT_SECRET deve ter pelo menos 32 caracteres")
        return v

    model_config = SettingsConfigDict(env_file=".env", populate_by_name=True)


settings = Settings()
