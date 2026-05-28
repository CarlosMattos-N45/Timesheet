import { describe, it, expect, beforeEach, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MockAdapter from "axios-mock-adapter";
import api from "@/api/client";
import { renderWithProviders } from "@/test/render";
import { RelatoriosPage } from "@/pages/Relatorios/RelatoriosPage";

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

describe("RelatoriosPage", () => {
  it("default = mes anterior (2026-04); chama meta e historico", async () => {
    let metaCalled = false, histCalled = false;
    mock.onGet("/api/v1/relatorios/2026-04/meta").reply(() => {
      metaCalled = true;
      return [200, { mes_referencia: "2026-04", caminho_arquivo: "/x.pdf", gerado_em: "2026-05-01T00:00:00Z", invalidado_em: null }];
    });
    mock.onGet("/api/v1/relatorios/2026-04/historico").reply(() => {
      histCalled = true;
      return [200, []];
    });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria", email_destinatario_relatorio: "rh@acme.com" });
    renderWithProviders(<RelatoriosPage />, { route: "/relatorios" });
    await waitFor(() => expect(metaCalled).toBe(true));
    expect(histCalled).toBe(true);
  });

  it("PDF desatualizado: meta.invalidado_em != null exibe badge ambar e botao Atualizar relatorio", async () => {
    mock.onGet("/api/v1/relatorios/2026-04/meta").reply(200, {
      mes_referencia: "2026-04", caminho_arquivo: "/x.pdf",
      gerado_em: "2026-05-01T00:00:00Z", invalidado_em: "2026-05-15T12:00:00Z",
    });
    mock.onGet("/api/v1/relatorios/2026-04/historico").reply(200, []);
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria", email_destinatario_relatorio: "rh@acme.com" });
    renderWithProviders(<RelatoriosPage />, { route: "/relatorios" });
    expect(await screen.findByText(/PDF desatualizado/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Atualizar relatório/i })).toBeInTheDocument();
  });

  it("Nenhuma jornada registrada: 404 do meta exibe mensagem e oculta iframe", async () => {
    mock.onGet("/api/v1/relatorios/2026-04/meta").reply(404, { code: "NOT_FOUND", message: "sem dados", details: [] });
    mock.onGet("/api/v1/relatorios/2026-04/historico").reply(200, []);
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria", email_destinatario_relatorio: null });
    renderWithProviders(<RelatoriosPage />, { route: "/relatorios" });
    expect(await screen.findByText(/Nenhuma jornada registrada para este mês\. Não é possível gerar o relatório\./i)).toBeInTheDocument();
    expect(document.querySelector("iframe")).toBeNull();
  });

  it("FALHA exibe chip vermelho e erro_mensagem", async () => {
    mock.onGet("/api/v1/relatorios/2026-04/meta").reply(200, {
      mes_referencia: "2026-04", caminho_arquivo: "/x.pdf",
      gerado_em: "2026-05-01T00:00:00Z", invalidado_em: null,
    });
    mock.onGet("/api/v1/relatorios/2026-04/historico").reply(200, [
      { id: "h1", mes_referencia: "2026-04", email_destinatario: "rh@acme.com",
        status: "FALHA", erro_mensagem: "Conexão recusada", enviado_em: "2026-05-01T08:00:00Z" },
    ]);
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria", email_destinatario_relatorio: "rh@acme.com" });
    renderWithProviders(<RelatoriosPage />, { route: "/relatorios" });
    expect(await screen.findByText("FALHA")).toBeInTheDocument();
    expect(screen.getByText(/Conexão recusada/i)).toBeInTheDocument();
  });

  it("Configurar SMTP navega para /configuracoes/smtp", async () => {
    mock.onGet("/api/v1/relatorios/2026-04/meta").reply(200, {
      mes_referencia: "2026-04", caminho_arquivo: "/x.pdf",
      gerado_em: "2026-05-01T00:00:00Z", invalidado_em: null,
    });
    mock.onGet("/api/v1/relatorios/2026-04/historico").reply(200, []);
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria", email_destinatario_relatorio: null });
    renderWithProviders(<RelatoriosPage />, { route: "/relatorios" });
    await userEvent.click(await screen.findByRole("button", { name: /Configurar SMTP/i }));
    expect(window.location.pathname).toBe("/configuracoes/smtp");
  });
});
