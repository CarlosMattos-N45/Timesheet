import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MockAdapter from "axios-mock-adapter";
import api from "@/api/client";
import { renderWithProviders } from "@/test/render";
import { JornadaManualPage } from "@/pages/JornadaManual/JornadaManualPage";

const mock = new MockAdapter(api);

beforeEach(() => {
  mock.reset();
  sessionStorage.setItem("ts:access_token", "tok");
  sessionStorage.setItem("ts:refresh_token", "r");
  sessionStorage.setItem("ts:terceiro_id", "u1");
  sessionStorage.setItem("ts:expires_at", String(Date.now() + 60_000));
  vi.useFakeTimers({ shouldAdvanceTime: true });
  vi.setSystemTime(new Date("2026-05-27T15:00:00-03:00"));
});

afterEach(() => {
  vi.useRealTimers();
});

describe("JornadaManualPage", () => {
  it("renderiza heading h1 'Nova Jornada Manual' e botão Salvar desabilitado por padrão", () => {
    mock.onGet("/api/v1/jornadas").reply(200, { mes_referencia: "2026-05", total_horas_mes_s: 0, jornadas: [] });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria" });
    renderWithProviders(<JornadaManualPage />, { route: "/jornadas/manual" });
    expect(screen.getByRole("heading", { level: 1, name: /Nova Jornada Manual/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Salvar$/ })).toBeDisabled();
  });

  it("submit válido chama POST /api/v1/jornadas/manual com os 4 tipos em ISO UTC e navega para /jornadas/<id>", async () => {
    mock.onGet("/api/v1/jornadas").reply(200, { mes_referencia: "2026-05", total_horas_mes_s: 0, jornadas: [] });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria" });
    let body: unknown = null;
    mock.onPost("/api/v1/jornadas/manual").reply((c) => {
      body = JSON.parse(c.data as string);
      return [201, {
        id: "novo-id-1", data: "2026-05-27", status: "AJUSTADA_MANUALMENTE",
        total_horas_apuradas_s: 28800, marcacoes: [], atividade: null, justificativas: [],
      }];
    });
    renderWithProviders(<JornadaManualPage />, { route: "/jornadas/manual" });

    const dp = screen.getByLabelText(/Data/i) as HTMLInputElement;
    await userEvent.clear(dp);
    await userEvent.type(dp, "27/05/2026");
    await userEvent.tab();

    const tps = screen.getAllByRole("textbox", { name: /Horário/i }) as HTMLInputElement[];
    await userEvent.clear(tps[0]!);
    await userEvent.type(tps[0]!, "09:00");
    await userEvent.clear(tps[1]!);
    await userEvent.type(tps[1]!, "12:00");
    await userEvent.clear(tps[2]!);
    await userEvent.type(tps[2]!, "13:00");
    await userEvent.clear(tps[3]!);
    await userEvent.type(tps[3]!, "18:00");
    await userEvent.tab();

    await userEvent.type(screen.getByLabelText(/Atividade/i), "Trabalhei oito horas no projeto X");
    await userEvent.type(screen.getByLabelText(/Justificativa/i), "esqueci de fazer login");

    const btnSalvar = screen.getByRole("button", { name: /^Salvar$/ });
    await waitFor(() => expect(btnSalvar).not.toBeDisabled());
    await userEvent.click(btnSalvar);

    await waitFor(() => expect(body).not.toBeNull());
    const b = body as { data: string; marcacoes: { tipo: string; horario_efetivo: string }[]; atividade: string; motivo: string };
    expect(b.data).toBe("2026-05-27");
    expect(b.marcacoes).toHaveLength(4);
    const tipos = b.marcacoes.map((m) => m.tipo);
    expect(tipos).toEqual(["INICIO_JORNADA", "SAIDA_ALMOCO", "RETORNO_ALMOCO", "FIM_JORNADA"]);
    // UTC: 09:00 BRT (UTC-3) = 12:00 UTC
    expect(b.marcacoes[0]!.horario_efetivo).toMatch(/T12:00:00/);
    expect(b.marcacoes[3]!.horario_efetivo).toMatch(/T21:00:00/);
    expect(b.atividade).toBe("Trabalhei oito horas no projeto X");
    expect(b.motivo).toBe("esqueci de fazer login");
    await waitFor(() => expect(window.location.pathname).toBe("/jornadas/novo-id-1"));
  }, 30_000);

  it("horários fora de ordem exibem helper text 'Os horários devem ser em ordem cronológica.' e Salvar desabilitado", async () => {
    mock.onGet("/api/v1/jornadas").reply(200, { mes_referencia: "2026-05", total_horas_mes_s: 0, jornadas: [] });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria" });
    renderWithProviders(<JornadaManualPage />, { route: "/jornadas/manual" });
    const tps = screen.getAllByRole("textbox", { name: /Horário/i }) as HTMLInputElement[];
    await userEvent.clear(tps[0]!);
    await userEvent.type(tps[0]!, "14:00");
    await userEvent.clear(tps[1]!);
    await userEvent.type(tps[1]!, "12:00");
    await userEvent.tab();
    expect(await screen.findByText(/Os horários devem ser em ordem cronológica\./i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Salvar$/ })).toBeDisabled();
  });

  it("atividade <10 chars exibe helper 'Mínimo 10 caracteres' e desabilita Salvar", async () => {
    mock.onGet("/api/v1/jornadas").reply(200, { mes_referencia: "2026-05", total_horas_mes_s: 0, jornadas: [] });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria" });
    renderWithProviders(<JornadaManualPage />, { route: "/jornadas/manual" });
    await userEvent.type(screen.getByLabelText(/Atividade/i), "curta");
    await userEvent.tab();
    expect(await screen.findByText(/Mínimo 10 caracteres/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Salvar$/ })).toBeDisabled();
  });

  it("erro 409 CONFLICT exibe alert 'Já existe uma jornada para este dia. Abra-a para editar.' + link Voltar para Jornadas", async () => {
    mock.onGet("/api/v1/jornadas").reply(200, { mes_referencia: "2026-05", total_horas_mes_s: 0, jornadas: [] });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria" });
    mock.onPost("/api/v1/jornadas/manual").reply(409, {
      code: "CONFLICT", message: "Já existe jornada para este dia", details: [],
    });
    renderWithProviders(<JornadaManualPage />, { route: "/jornadas/manual" });

    const dp = screen.getByLabelText(/Data/i) as HTMLInputElement;
    await userEvent.clear(dp);
    await userEvent.type(dp, "27/05/2026");
    await userEvent.tab();

    const tps = screen.getAllByRole("textbox", { name: /Horário/i }) as HTMLInputElement[];
    await userEvent.clear(tps[0]!); await userEvent.type(tps[0]!, "09:00");
    await userEvent.clear(tps[1]!); await userEvent.type(tps[1]!, "12:00");
    await userEvent.clear(tps[2]!); await userEvent.type(tps[2]!, "13:00");
    await userEvent.clear(tps[3]!); await userEvent.type(tps[3]!, "18:00");
    await userEvent.tab();
    await userEvent.type(screen.getByLabelText(/Atividade/i), "Trabalhei oito horas");
    await userEvent.type(screen.getByLabelText(/Justificativa/i), "motivo válido");

    const btnSalvar = screen.getByRole("button", { name: /^Salvar$/ });
    await waitFor(() => expect(btnSalvar).not.toBeDisabled());
    await userEvent.click(btnSalvar);

    expect(await screen.findByText(/Já existe uma jornada para este dia\. Abra-a para editar\./i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Voltar para Jornadas/i })).toBeInTheDocument();
  }, 30_000);

  it("Cancelar navega para /jornadas", async () => {
    mock.onGet("/api/v1/jornadas").reply(200, { mes_referencia: "2026-05", total_horas_mes_s: 0, jornadas: [] });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria" });
    renderWithProviders(<JornadaManualPage />, { route: "/jornadas/manual" });
    await userEvent.click(screen.getByRole("button", { name: /Cancelar/i }));
    expect(window.location.pathname).toBe("/jornadas");
  });
});
