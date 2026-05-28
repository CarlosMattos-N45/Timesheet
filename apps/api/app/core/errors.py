from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorDetail(BaseModel):
    field: str
    issue: str


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = []


class DomainError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        http_status: int = 400,
        details: list[ErrorDetail] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or []


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_handler(_req: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content={
                "code": exc.code,
                "message": exc.message,
                "details": [d.model_dump() for d in exc.details],
            },
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_req: Request, exc: RequestValidationError) -> JSONResponse:
        details: list[dict[str, Any]] = []
        for err in exc.errors():
            # Check if the ValueError carries a structured dict with loc/msg
            ctx_error = (err.get("ctx") or {}).get("error")
            first_arg = ctx_error.args[0] if (ctx_error and ctx_error.args) else None
            if isinstance(ctx_error, ValueError) and isinstance(first_arg, dict):
                structured = first_arg
                inner_loc = structured.get("loc") or ()
                issue = structured.get("msg", "")
                # Combine outer loc (e.g. "body") with inner loc fields
                outer_parts = [str(p) for p in err.get("loc", []) if p not in ("", "body")]
                inner_parts = [str(p) for p in inner_loc]
                all_parts = outer_parts + inner_parts
                prefix = "body." if all_parts else "body"
                field = prefix + ".".join(all_parts) if all_parts else "body"
                details.append({"field": field, "issue": issue})
            else:
                loc_parts = [str(p) for p in err.get("loc", []) if p != ""]
                loc = ".".join(loc_parts)
                details.append({"field": loc, "issue": err.get("msg", "")})
        return JSONResponse(
            status_code=422,
            content={
                "code": "VALIDATION_ERROR",
                "message": "Erro de validação",
                "details": details,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_handler(_req: Request, exc: StarletteHTTPException) -> JSONResponse:
        code_map = {
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            409: "CONFLICT",
            429: "RATE_LIMITED",
        }
        code = code_map.get(exc.status_code, "INTERNAL_ERROR")
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": code, "message": str(exc.detail), "details": []},
        )
