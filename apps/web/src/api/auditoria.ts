import api from "./client";
import type { AuditoriaItem } from "@/types/contracts";

export const auditoriaKeys = {
  list: (entidade: string, entidadeId: string) => ["auditoria", entidade, entidadeId] as const,
};

export async function getAuditoria(
  entidade: AuditoriaItem["entidade"],
  entidadeId: string
): Promise<AuditoriaItem[]> {
  const r = await api.get<AuditoriaItem[]>("/api/v1/auditoria", {
    params: { entidade, entidade_id: entidadeId },
  });
  return r.data;
}
