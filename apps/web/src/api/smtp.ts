import api from "./client";
import type { SmtpConfigRequest, SmtpConfigResponse } from "@/types/contracts";

export const smtpKeys = {
  config: ["smtp", "config"] as const,
};

export async function getSmtpConfig(): Promise<SmtpConfigResponse> {
  const r = await api.get<SmtpConfigResponse>("/api/v1/smtp");
  return r.data;
}

export async function putSmtpConfig(body: SmtpConfigRequest): Promise<SmtpConfigResponse> {
  const r = await api.put<SmtpConfigResponse>("/api/v1/smtp", body);
  return r.data;
}

export async function postTestSmtp(): Promise<{ ok: boolean }> {
  const r = await api.post<{ ok: boolean }>("/api/v1/smtp/test");
  return r.data;
}
