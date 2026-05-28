import api from "./client";
import type { TerceiroResponse, UpdateTerceiroRequest, ChangePasswordRequest } from "@/types/contracts";

export const terceirosKeys = {
  me: ["terceiros", "me"] as const,
};

export async function getTerceiroMe(): Promise<TerceiroResponse> {
  const r = await api.get<TerceiroResponse>("/api/v1/terceiros/me");
  return r.data;
}

export async function putTerceiroMe(body: UpdateTerceiroRequest): Promise<TerceiroResponse> {
  const r = await api.put<TerceiroResponse>("/api/v1/terceiros/me", body);
  return r.data;
}

export async function putSenha(body: ChangePasswordRequest): Promise<void> {
  await api.put("/api/v1/terceiros/me/senha", body);
}
