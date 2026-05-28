import api from "./client";
import type {
  EnviarResponse,
  RelatorioMesResponse,
  HistoricoEnvioItem,
} from "@/types/contracts";

export const relatoriosKeys = {
  meta: (mes: string) => ["relatorios", "meta", mes] as const,
  historico: (mes: string) => ["relatorios", "historico", mes] as const,
};

export function urlDownloadRelatorio(mes: string): string {
  return `/api/v1/relatorios/${mes}`;
}

export async function getRelatorioMeta(mes: string): Promise<RelatorioMesResponse> {
  const r = await api.get<RelatorioMesResponse>(`/api/v1/relatorios/${mes}/meta`);
  return r.data;
}

export async function getRelatorioHistorico(mes: string): Promise<HistoricoEnvioItem[]> {
  const r = await api.get<HistoricoEnvioItem[]>(`/api/v1/relatorios/${mes}/historico`);
  return r.data;
}

export async function postEnviarRelatorio(mes: string, email?: string): Promise<EnviarResponse> {
  const r = await api.post<EnviarResponse>(
    `/api/v1/relatorios/${mes}/enviar`,
    email ? { email } : undefined
  );
  return r.data;
}
