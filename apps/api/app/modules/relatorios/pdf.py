from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.errors import DomainError

_TEMPLATES = Path(__file__).parent / "templates"
_env = Environment(loader=FileSystemLoader(str(_TEMPLATES)), autoescape=select_autoescape(["html"]))


def _format_secs(s: int | None) -> str:
    if s is None or s == 0:
        return "—"
    h, rem = divmod(s, 3600)
    m, _ = divmod(rem, 60)
    return f"{h:02d}:{m:02d}"


def _dia_semana(data_iso: str) -> str:
    days = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    d = date.fromisoformat(data_iso)
    return days[d.weekday()]


def _build_context(
    terceiro: Any, jornadas_data: list[dict[str, Any]], mes_referencia: str
) -> dict[str, Any]:
    jornadas_view = []
    total_mes = 0
    for j in jornadas_data:
        total = j.get("total_horas_apuradas_s") or 0
        total_mes += total
        horarios: dict[str, str] = {}
        for m in j.get("marcacoes", []):
            t = (m.get("horario_efetivo") or m.get("horario_registrado") or "")[11:16]
            horarios[m["tipo"]] = t
        jornadas_view.append(
            {
                "data": j["data"],
                "dia_semana": _dia_semana(j["data"]),
                "horarios": horarios,
                "total_str": _format_secs(total),
                "status": j["status"],
                "atividade": (j.get("atividade") or {}).get("descricao"),
            }
        )
    return {
        "terceiro": terceiro,
        "mes_referencia": mes_referencia,
        "jornadas": jornadas_view,
        "total_mes_str": _format_secs(total_mes),
    }


async def render_pdf(
    terceiro: Any, jornadas_data: list[dict[str, Any]], mes_referencia: str
) -> bytes:
    if not jornadas_data:
        raise DomainError(code="NO_DATA", message="Sem jornadas no mês", http_status=422)

    def _run() -> bytes:
        from weasyprint import HTML  # type: ignore[import-untyped]  # noqa: PLC0415

        ctx = _build_context(terceiro, jornadas_data, mes_referencia)
        html = _env.get_template("mensal.html").render(**ctx)
        result: bytes = HTML(string=html).write_pdf()
        return result

    try:
        return await asyncio.wait_for(asyncio.to_thread(_run), timeout=120)
    except TimeoutError as exc:
        raise DomainError(
            code="PDF_TIMEOUT", message="Geração de PDF excedeu 120s", http_status=500
        ) from exc
