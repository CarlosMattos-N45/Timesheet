import api from "./client";
import type { LoginResponse, RefreshResponse } from "@/types/contracts";

export async function postLogin(email: string, senha: string): Promise<LoginResponse> {
  const r = await api.post<LoginResponse>("/api/v1/auth/login", { email, senha });
  return r.data;
}

export async function postRefresh(refresh_token: string): Promise<RefreshResponse> {
  const r = await api.post<RefreshResponse>("/api/v1/auth/refresh", { refresh_token });
  return r.data;
}

export async function postLogout(refresh_token: string): Promise<void> {
  await api.post("/api/v1/auth/logout", { refresh_token });
}
