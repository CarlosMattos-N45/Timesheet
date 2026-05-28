import { describe, it, expect, beforeEach } from "vitest";
import MockAdapter from "axios-mock-adapter";
import api from "@/api/client";
import {
  relatoriosKeys,
  urlDownloadRelatorio,
  getRelatorioMeta,
  getRelatorioHistorico,
  postEnviarRelatorio,
} from "@/api/relatorios";

const mock = new MockAdapter(api);

beforeEach(() => {
  mock.reset();
});

describe("relatoriosKeys", () => {
  it("meta(mes) retorna key correta", () => {
    expect(relatoriosKeys.meta("2026-05")).toEqual(["relatorios", "meta", "2026-05"]);
  });
  it("historico(mes) retorna key correta", () => {
    expect(relatoriosKeys.historico("2026-05")).toEqual(["relatorios", "historico", "2026-05"]);
  });
});

describe("urlDownloadRelatorio", () => {
  it("retorna URL com mes correto", () => {
    expect(urlDownloadRelatorio("2026-05")).toBe("/api/v1/relatorios/2026-05");
  });
});

describe("getRelatorioMeta", () => {
  it("faz GET /api/v1/relatorios/:mes/meta e retorna meta", async () => {
    const payload = { mes_referencia: "2026-05", caminho_arquivo: "/tmp/r.pdf", gerado_em: "2026-05-27T12:00:00Z", invalidado_em: null };
    mock.onGet("/api/v1/relatorios/2026-05/meta").reply(200, payload);
    const result = await getRelatorioMeta("2026-05");
    expect(result.mes_referencia).toBe("2026-05");
    expect(result.caminho_arquivo).toBe("/tmp/r.pdf");
  });
});

describe("getRelatorioHistorico", () => {
  it("faz GET /api/v1/relatorios/:mes/historico e retorna lista", async () => {
    const payload = [{ id: "h1", mes_referencia: "2026-05", email_destinatario: "rh@acme.com", status: "SUCESSO", erro_mensagem: null, enviado_em: "2026-05-27T12:00:00Z" }];
    mock.onGet("/api/v1/relatorios/2026-05/historico").reply(200, payload);
    const result = await getRelatorioHistorico("2026-05");
    expect(result).toHaveLength(1);
    expect(result.at(0)?.id).toBe("h1");
  });
});

describe("postEnviarRelatorio", () => {
  it("faz POST /api/v1/relatorios/:mes/enviar com email e retorna resposta 202", async () => {
    const payload = { status: "SUCESSO", historico_id: "h1" };
    mock.onPost("/api/v1/relatorios/2026-05/enviar").reply(202, payload);
    const result = await postEnviarRelatorio("2026-05", "rh@acme.com");
    expect(result.status).toBe("SUCESSO");
    expect(result.historico_id).toBe("h1");
  });

  it("faz POST sem email quando email não informado", async () => {
    const payload = { status: "SUCESSO", historico_id: "h2" };
    mock.onPost("/api/v1/relatorios/2026-05/enviar").reply(202, payload);
    const result = await postEnviarRelatorio("2026-05");
    expect(result.historico_id).toBe("h2");
  });
});
