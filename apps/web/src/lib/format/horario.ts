import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import timezone from "dayjs/plugin/timezone";
import "dayjs/locale/pt-br";

dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.locale("pt-br");

const TZ_BR = "America/Sao_Paulo";

export function formatHoraBR(isoUtc: string | null): string {
  if (!isoUtc) return "—";
  return dayjs(isoUtc).tz(TZ_BR).format("HH:mm");
}

export function formatTotal(segundos: number | null): string {
  if (segundos == null || segundos < 0) return "—";
  const h = Math.floor(segundos / 3600);
  const m = Math.floor((segundos % 3600) / 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

export function formatData(yyyymmdd: string): string {
  return dayjs(yyyymmdd).format("DD/MM");
}

const DIAS_SEMANA = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sab"] as const;
export function formatDiaSemana(yyyymmdd: string): string {
  const d = dayjs(yyyymmdd).day(); // 0..6
  return DIAS_SEMANA[d] ?? "—";
}

/**
 * Calcula o total diário em segundos.
 * total = (fim - inicio) - (retornoAlmoco - saidaAlmoco)
 * Retorna null se inicio ou fim não informados ou se fim <= inicio.
 */
export function calculaTotalDiario(
  inicio: string | null,
  saidaAlmoco: string | null,
  retornoAlmoco: string | null,
  fim: string | null
): number | null {
  if (!inicio || !fim) return null;
  const ini = dayjs(inicio).valueOf();
  const f = dayjs(fim).valueOf();
  if (Number.isNaN(ini) || Number.isNaN(f) || f <= ini) return null;
  let totalMs = f - ini;
  if (saidaAlmoco && retornoAlmoco) {
    const sa = dayjs(saidaAlmoco).valueOf();
    const ra = dayjs(retornoAlmoco).valueOf();
    if (!Number.isNaN(sa) && !Number.isNaN(ra) && ra > sa) {
      totalMs -= ra - sa;
    }
  }
  return Math.floor(totalMs / 1000);
}
