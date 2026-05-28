import api from "./client";
import type {
  JornadasMesResponse,
  JornadaDetalheResponse,
  AjusteJornadaRequest,
  JornadaManualRequest,
  AtividadeRequest,
  AtividadeDetalhe,
} from "@/types/contracts";

export const jornadasKeys = {
  all: ["jornadas"] as const,
  lista: (mes: string) => ["jornadas", "lista", mes] as const,
  detalhe: (id: string) => ["jornadas", "detalhe", id] as const,
};

export async function getJornadasMes(mes: string): Promise<JornadasMesResponse> {
  const r = await api.get<JornadasMesResponse>("/api/v1/jornadas", { params: { mes } });
  return r.data;
}

export async function getJornadaDetalhe(id: string): Promise<JornadaDetalheResponse> {
  const r = await api.get<JornadaDetalheResponse>(`/api/v1/jornadas/${id}`);
  return r.data;
}

export async function putAjusteJornada(
  id: string,
  body: AjusteJornadaRequest
): Promise<JornadaDetalheResponse> {
  const r = await api.put<JornadaDetalheResponse>(`/api/v1/jornadas/${id}`, body);
  return r.data;
}

export async function postJornadaManual(body: JornadaManualRequest): Promise<JornadaDetalheResponse> {
  const r = await api.post<JornadaDetalheResponse>("/api/v1/jornadas/manual", body);
  return r.data;
}

export async function postAtividade(
  jornadaId: string,
  body: AtividadeRequest
): Promise<AtividadeDetalhe> {
  const r = await api.post<AtividadeDetalhe>(`/api/v1/jornadas/${jornadaId}/atividade`, body);
  return r.data;
}
