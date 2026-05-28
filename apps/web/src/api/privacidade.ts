import api from "./client";
import type { PrivacyStatus } from "@/types/contracts";

export const privacidadeKeys = {
  status: ["privacidade", "status"] as const,
};

export async function getStatusPrivacidade(): Promise<PrivacyStatus> {
  const r = await api.get<PrivacyStatus>("/api/v1/privacidade");
  return r.data;
}

export async function postAceitarPrivacidade(): Promise<void> {
  await api.post("/api/v1/privacidade/aceitar");
}
