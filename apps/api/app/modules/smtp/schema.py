from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, SecretStr


class SmtpConfigRequest(BaseModel):
    host: str = Field(min_length=1, max_length=253)
    port: int = Field(ge=1, le=65535)
    username: str = Field(min_length=1, max_length=254)
    password: SecretStr = Field(min_length=1, max_length=512)
    use_starttls: bool = True
    from_address: EmailStr


class SmtpConfigResponse(BaseModel):
    host: str
    port: int
    username: str
    use_starttls: bool
    from_address: str
    atualizado_em: str
