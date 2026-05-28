import { describe, it, expect, beforeEach } from "vitest";
import MockAdapter from "axios-mock-adapter";
import api from "@/api/client";
import {
  jornadasKeys,
  getJornadasMes,
  getJornadaDetalhe,
  putAjusteJornada,
  postJornadaManual,
  postAtividade,
} from "@/api/jornadas";

const mock = new MockAdapter(api);

beforeEach(() => {
  mock.reset();
});

describe("jornadasKeys", () => {
  it("lista(mes) retorna key com mes", () => {
    expect(jornadasKeys.lista("2026-05")).toEqual(["jornadas", "lista", "2026-05"]);
  });
  it("detalhe(id) retorna key com id", () => {
    expect(jornadasKeys.detalhe("j1")).toEqual(["jornadas", "detalhe", "j1"]);
  });
});

describe("getJornadasMes", () => {
  it("faz GET /api/v1/jornadas com params mes e retorna data", async () => {
    const payload = { mes_referencia: "2026-05", total_horas_mes_s: 0, jornadas: [] };
    mock.onGet("/api/v1/jornadas").reply(200, payload);
    const result = await getJornadasMes("2026-05");
    expect(result.mes_referencia).toBe("2026-05");
    expect(result.total_horas_mes_s).toBe(0);
  });
});

describe("getJornadaDetalhe", () => {
  it("faz GET /api/v1/jornadas/:id e retorna detalhe", async () => {
    const payload = { id: "j1", data: "2026-05-27", status: "FECHADA", total_horas_apuradas_s: null, marcacoes: [], atividade: null, justificativas: [] };
    mock.onGet("/api/v1/jornadas/j1").reply(200, payload);
    const result = await getJornadaDetalhe("j1");
    expect(result.id).toBe("j1");
    expect(result.status).toBe("FECHADA");
  });
});

describe("putAjusteJornada", () => {
  it("faz PUT /api/v1/jornadas/:id e retorna detalhe atualizado", async () => {
    const payload = { id: "j1", data: "2026-05-27", status: "AJUSTADA_MANUALMENTE", total_horas_apuradas_s: 28800, marcacoes: [], atividade: null, justificativas: [] };
    mock.onPut("/api/v1/jornadas/j1").reply(200, payload);
    const result = await putAjusteJornada("j1", { marcacoes: [], motivo: "teste" });
    expect(result.status).toBe("AJUSTADA_MANUALMENTE");
  });
});

describe("postJornadaManual", () => {
  it("faz POST /api/v1/jornadas/manual e retorna jornada criada", async () => {
    const payload = { id: "j2", data: "2026-05-28", status: "FECHADA", total_horas_apuradas_s: 28800, marcacoes: [], atividade: null, justificativas: [] };
    mock.onPost("/api/v1/jornadas/manual").reply(200, payload);
    const result = await postJornadaManual({
      data: "2026-05-28",
      marcacoes: [],
      atividade: "Desenvolvimento",
      motivo: "Trabalho remoto",
    });
    expect(result.id).toBe("j2");
    expect(result.data).toBe("2026-05-28");
  });
});

describe("postAtividade", () => {
  it("faz POST /api/v1/jornadas/:id/atividade e retorna atividade criada", async () => {
    const payload = { id: "a1", jornada_id: "j1", descricao: "Trabalho", registrada_em: "2026-05-27T12:00:00Z", atualizado_em: null };
    mock.onPost("/api/v1/jornadas/j1/atividade").reply(200, payload);
    const result = await postAtividade("j1", { descricao: "Trabalho" });
    expect(result.id).toBe("a1");
    expect(result.jornada_id).toBe("j1");
  });
});
