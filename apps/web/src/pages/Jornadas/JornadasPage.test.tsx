import { describe, it, expect, beforeEach, vi } from "vitest";
import { screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MockAdapter from "axios-mock-adapter";
import api from "@/api/client";
import { renderWithProviders } from "@/test/render";
import { JornadasPage } from "@/pages/Jornadas/JornadasPage";

const mock = new MockAdapter(api);

beforeEach(() => {
  mock.reset();
  sessionStorage.setItem("ts:access_token", "tok");
  sessionStorage.setItem("ts:refresh_token", "r");
  sessionStorage.setItem("ts:terceiro_id", "u1");
  sessionStorage.setItem("ts:expires_at", String(Date.now() + 60_000));
  vi.useFakeTimers({ shouldAdvanceTime: true });
  vi.setSystemTime(new Date("2026-05-27T12:00:00-03:00"));
});

describe("JornadasPage", () => {
  it("renderiza heading h1 Jornadas e chama GET /api/v1/jornadas?mes=2026-05", async () => {
    let urlChamada = "";
    mock.onGet("/api/v1/jornadas").reply((cfg) => {
      urlChamada = String(cfg.url) + "?" + new URLSearchParams(cfg.params as Record<string, string>).toString();
      return [200, { mes_referencia: "2026-05", total_horas_mes_s: 0, jornadas: [] }];
    });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria", email_destinatario_relatorio: "rh@acme.com" });
    renderWithProviders(<JornadasPage />, { route: "/jornadas" });
    expect(screen.getByRole("heading", { level: 1, name: /Jornadas/i })).toBeInTheDocument();
    await waitFor(() => expect(urlChamada).toContain("mes=2026-05"));
  });

  it("estado vazio: 0 jornadas exibe texto 'Nenhuma jornada registrada para este mês.' + CTA Criar", async () => {
    mock.onGet("/api/v1/jornadas").reply(200, { mes_referencia: "2026-05", total_horas_mes_s: 0, jornadas: [] });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria", email_destinatario_relatorio: null });
    renderWithProviders(<JornadasPage />, { route: "/jornadas" });
    expect(await screen.findByText(/Nenhuma jornada registrada para este mês\./i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Criar jornada manual/i })).toBeInTheDocument();
  });

  it("1 jornada FECHADA renderiza linha com Data 27/05, Total 08:00 e chip FECHADA verde", async () => {
    mock.onGet("/api/v1/jornadas").reply(200, {
      mes_referencia: "2026-05",
      total_horas_mes_s: 28800,
      jornadas: [{
        id: "j1", data: "2026-05-27", status: "FECHADA",
        total_horas_apuradas_s: 28800, tem_marcacao_pendente: false,
        horario_inicio: "2026-05-27T12:00:00+00:00",
        horario_saida_almoco: "2026-05-27T15:00:00+00:00",
        horario_retorno_almoco: "2026-05-27T16:00:00+00:00",
        horario_fim: "2026-05-27T21:00:00+00:00",
      }],
    });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria", email_destinatario_relatorio: null });
    renderWithProviders(<JornadasPage />, { route: "/jornadas" });
    expect(await screen.findByText("27/05")).toBeInTheDocument();
    // Em UTC-3, 12:00Z = 09:00 BRT
    expect(screen.getByText("09:00")).toBeInTheDocument();
    expect(screen.getByText("18:00")).toBeInTheDocument();
    // "08:00" aparece na coluna Total da linha — pode haver múltiplos, verificamos presença
    expect(screen.getAllByText("08:00").length).toBeGreaterThanOrEqual(1);
    // "Total no mês: 08:00" — texto distribuído em Typography + strong; busca pelo container
    const totalEl = screen.getByText((_content, element) => {
      return element?.tagName.toLowerCase() === "p" && /Total no mês/i.test(element.textContent ?? "");
    });
    expect(totalEl.textContent).toMatch(/08:00/);
    expect(screen.getByText("FECHADA")).toBeInTheDocument();
  });

  it("jornada com tem_marcacao_pendente=true exibe AMBOS chips status e PENDENTE", async () => {
    mock.onGet("/api/v1/jornadas").reply(200, {
      mes_referencia: "2026-05",
      total_horas_mes_s: 28800,
      jornadas: [{
        id: "j1", data: "2026-05-27", status: "FECHADA",
        total_horas_apuradas_s: 28800, tem_marcacao_pendente: true,
        horario_inicio: "2026-05-27T12:00:00+00:00",
        horario_saida_almoco: "2026-05-27T15:00:00+00:00",
        horario_retorno_almoco: "2026-05-27T16:00:00+00:00",
        horario_fim: "2026-05-27T21:00:00+00:00",
      }],
    });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria", email_destinatario_relatorio: null });
    renderWithProviders(<JornadasPage />, { route: "/jornadas" });
    expect(await screen.findByText("FECHADA")).toBeInTheDocument();
    expect(screen.getByText("PENDENTE")).toBeInTheDocument();
  });

  it("clique em linha navega para /jornadas/:id", async () => {
    mock.onGet("/api/v1/jornadas").reply(200, {
      mes_referencia: "2026-05",
      total_horas_mes_s: 28800,
      jornadas: [{
        id: "abc-123", data: "2026-05-27", status: "FECHADA",
        total_horas_apuradas_s: 28800, tem_marcacao_pendente: false,
        horario_inicio: "2026-05-27T12:00:00+00:00",
        horario_saida_almoco: "2026-05-27T15:00:00+00:00",
        horario_retorno_almoco: "2026-05-27T16:00:00+00:00",
        horario_fim: "2026-05-27T21:00:00+00:00",
      }],
    });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria", email_destinatario_relatorio: null });
    renderWithProviders(<JornadasPage />, { route: "/jornadas" });
    const linha = await screen.findByText("27/05");
    await userEvent.click(linha);
    // Asserta URL via location atual (MemoryRouter reflete)
    expect(window.location.pathname).toContain("/jornadas/abc-123");
  });

  it("Baixar PDF desabilitado quando 0 jornadas, com tooltip 'Nenhuma jornada no mês'", async () => {
    mock.onGet("/api/v1/jornadas").reply(200, { mes_referencia: "2026-05", total_horas_mes_s: 0, jornadas: [] });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria", email_destinatario_relatorio: null });
    renderWithProviders(<JornadasPage />, { route: "/jornadas" });
    const btn = await screen.findByRole("button", { name: /Baixar PDF/i });
    expect(btn).toBeDisabled();
    // O botão desabilitado tem pointer-events:none — hover no span wrapper pai
    const wrapper = btn.parentElement!;
    fireEvent.mouseOver(wrapper);
    expect(await screen.findByText(/Nenhuma jornada no mês/i)).toBeInTheDocument();
  });

  it("Enviar por e-mail abre modal com email pré-preenchido e sucesso emite toast", async () => {
    mock.onGet("/api/v1/jornadas").reply(200, {
      mes_referencia: "2026-05",
      total_horas_mes_s: 28800,
      jornadas: [{
        id: "j1", data: "2026-05-27", status: "FECHADA",
        total_horas_apuradas_s: 28800, tem_marcacao_pendente: false,
        horario_inicio: "2026-05-27T12:00:00+00:00",
        horario_saida_almoco: "2026-05-27T15:00:00+00:00",
        horario_retorno_almoco: "2026-05-27T16:00:00+00:00",
        horario_fim: "2026-05-27T21:00:00+00:00",
      }],
    });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria", email_destinatario_relatorio: "rh@acme.com" });
    mock.onPost("/api/v1/relatorios/2026-05/enviar").reply(202, { status: "SUCESSO", historico_id: "h1" });
    renderWithProviders(<JornadasPage />, { route: "/jornadas" });
    await userEvent.click(await screen.findByRole("button", { name: /Enviar por e-mail/i }));
    const inp = screen.getByLabelText(/Destinatário/i) as HTMLInputElement;
    expect(inp.value).toBe("rh@acme.com");
    await userEvent.click(screen.getByRole("button", { name: /^Enviar$/ }));
    expect(await screen.findByText(/Relatório enviado para rh@acme.com\./i)).toBeInTheDocument();
  });

  it("Enviar com SMTP_NOT_CONFIGURED mostra alert e CTA Configurar agora", async () => {
    mock.onGet("/api/v1/jornadas").reply(200, {
      mes_referencia: "2026-05",
      total_horas_mes_s: 28800,
      jornadas: [{
        id: "j1", data: "2026-05-27", status: "FECHADA",
        total_horas_apuradas_s: 28800, tem_marcacao_pendente: false,
        horario_inicio: "2026-05-27T12:00:00+00:00",
        horario_saida_almoco: "2026-05-27T15:00:00+00:00",
        horario_retorno_almoco: "2026-05-27T16:00:00+00:00",
        horario_fim: "2026-05-27T21:00:00+00:00",
      }],
    });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria", email_destinatario_relatorio: "rh@acme.com" });
    mock.onPost("/api/v1/relatorios/2026-05/enviar").reply(422, {
      code: "SMTP_NOT_CONFIGURED", message: "SMTP não configurado", details: [],
    });
    renderWithProviders(<JornadasPage />, { route: "/jornadas" });
    await userEvent.click(await screen.findByRole("button", { name: /Enviar por e-mail/i }));
    await userEvent.click(screen.getByRole("button", { name: /^Enviar$/ }));
    expect(await screen.findByText(/SMTP não configurado\./i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Configurar agora/i })).toBeInTheDocument();
  });
});
