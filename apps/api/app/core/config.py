from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    model_config = SettingsConfigDict(
        env_file=".env",
        populate_by_name=True,
    )


settings = Settings()
