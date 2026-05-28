import axios, { AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from "axios";

export const STORAGE = {
  accessToken: "ts:access_token",
  refreshToken: "ts:refresh_token",
  terceiroId: "ts:terceiro_id",
  expiresAt: "ts:expires_at",
} as const;

const api = axios.create({
  baseURL: "",
  timeout: 15_000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const tok = sessionStorage.getItem(STORAGE.accessToken);
  if (tok && config.headers) {
    config.headers.Authorization = `Bearer ${tok}`;
  }
  return config;
});

type RetriableConfig = InternalAxiosRequestConfig & { _retry?: boolean };

let refreshPromise: Promise<string> | null = null;

async function doRefresh(): Promise<string> {
  const rtok = sessionStorage.getItem(STORAGE.refreshToken);
  if (!rtok) throw new Error("no refresh token");
  // isAuthEndpoint no response interceptor evita loop — url inclui /auth/refresh
  const r = await api.post<{ access_token: string; refresh_token: string; expires_in: number }>(
    "/api/v1/auth/refresh",
    { refresh_token: rtok }
  );
  sessionStorage.setItem(STORAGE.accessToken, r.data.access_token);
  sessionStorage.setItem(STORAGE.refreshToken, r.data.refresh_token);
  sessionStorage.setItem(STORAGE.expiresAt, String(Date.now() + r.data.expires_in * 1000));
  return r.data.access_token;
}

function clearSession() {
  sessionStorage.removeItem(STORAGE.accessToken);
  sessionStorage.removeItem(STORAGE.refreshToken);
  sessionStorage.removeItem(STORAGE.terceiroId);
  sessionStorage.removeItem(STORAGE.expiresAt);
}

api.interceptors.response.use(
  (r: AxiosResponse) => r,
  async (error: AxiosError) => {
    const status = error.response?.status;
    const cfg = error.config as RetriableConfig | undefined;
    const url = cfg?.url ?? "";

    // Sem retry para os próprios endpoints de auth ou se já tentou
    const isAuthEndpoint =
      url.includes("/api/v1/auth/login") ||
      url.includes("/api/v1/auth/refresh") ||
      url.includes("/api/v1/auth/logout");

    if (status === 401 && cfg && !cfg._retry && !isAuthEndpoint) {
      cfg._retry = true;
      try {
        const novoToken = await (refreshPromise ?? (refreshPromise = doRefresh()));
        cfg.headers = cfg.headers ?? {};
        cfg.headers.Authorization = `Bearer ${novoToken}`;
        return api(cfg);
      } catch {
        clearSession();
        // Disparar evento custom para AuthProvider sincronizar e router redirecionar
        window.dispatchEvent(new CustomEvent("ts:auth-logout"));
        throw error;
      } finally {
        refreshPromise = null;
      }
    }
    return Promise.reject(error);
  }
);

export default api;
