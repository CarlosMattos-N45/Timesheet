import { describe, it, expect, beforeEach } from "vitest";
import MockAdapter from "axios-mock-adapter";
import api from "@/api/client";

const mock = new MockAdapter(api);

describe("api client interceptors", () => {
  beforeEach(() => {
    sessionStorage.clear();
    mock.reset();
  });

  it("injeta Authorization Bearer quando access_token presente", async () => {
    sessionStorage.setItem("ts:access_token", "atok-123");
    mock.onGet("/api/v1/jornadas").reply((config) => {
      expect(config.headers?.Authorization).toBe("Bearer atok-123");
      return [200, { mes_referencia: "2026-05", total_horas_mes_s: 0, jornadas: [] }];
    });
    await api.get("/api/v1/jornadas", { params: { mes: "2026-05" } });
  });

  it("em 401 chama /auth/refresh, persiste novos tokens e refaz request", async () => {
    sessionStorage.setItem("ts:access_token", "atok-velho");
    sessionStorage.setItem("ts:refresh_token", "rtok-velho");
    let primeiraChamada = true;
    mock.onGet("/api/v1/jornadas").reply(() => {
      if (primeiraChamada) {
        primeiraChamada = false;
        return [401, { code: "UNAUTHORIZED", message: "expirado", details: [] }];
      }
      return [200, { mes_referencia: "2026-05", total_horas_mes_s: 0, jornadas: [] }];
    });
    mock.onPost("/api/v1/auth/refresh").reply(200, {
      access_token: "atok-novo",
      refresh_token: "rtok-novo",
      expires_in: 900,
    });
    const r = await api.get("/api/v1/jornadas", { params: { mes: "2026-05" } });
    expect(r.status).toBe(200);
    expect(sessionStorage.getItem("ts:access_token")).toBe("atok-novo");
    expect(sessionStorage.getItem("ts:refresh_token")).toBe("rtok-novo");
  });

  it("em refresh falhando, limpa sessão e propaga 401", async () => {
    sessionStorage.setItem("ts:access_token", "atok");
    sessionStorage.setItem("ts:refresh_token", "rtok-revogado");
    mock.onGet("/api/v1/jornadas").reply(401, { code: "UNAUTHORIZED", message: "expirado", details: [] });
    mock.onPost("/api/v1/auth/refresh").reply(401, { code: "UNAUTHORIZED", message: "revogado", details: [] });
    await expect(api.get("/api/v1/jornadas", { params: { mes: "2026-05" } })).rejects.toThrow();
    expect(sessionStorage.getItem("ts:access_token")).toBeNull();
  });
});
