import { describe, it, expect, vi, afterEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MockAdapter from "axios-mock-adapter";
import api from "@/api/client";
import { renderWithProviders } from "@/test/render";
import { AppLayout } from "@/components/AppLayout";

const mock = new MockAdapter(api);

const TERCEIRO_MOCK = {
  id: "uuid",
  nome: "Maria",
  empresa_nome: "Acme",
  empresa_cnpj: "00.000.000/0001-00",
  horario_inicio_jornada: "08:00:00",
  horario_saida_almoco: "12:00:00",
  horario_retorno_almoco: "13:00:00",
  horario_fim_jornada: "17:00:00",
  trabalha_fim_de_semana: false,
  email_contato: "maria@acme.com",
  email_destinatario_relatorio: null,
  criado_em: "2026-01-01T00:00:00Z",
  atualizado_em: "2026-01-01T00:00:00Z",
};

const AUTH_STATE = { accessToken: "atok", refreshToken: "rtok", terceiroId: "uuid" };

describe("AppLayout", () => {
  afterEach(() => {
    vi.useRealTimers();
    sessionStorage.clear();
    mock.reset();
  });

  it("renderiza saudação 'Bom dia' quando hora=09", () => {
    vi.useFakeTimers();
    // 09:00 no horário local — 12:00 UTC (BRT = UTC-3)
    vi.setSystemTime(new Date("2026-05-27T12:00:00.000Z"));
    mock.onGet("/api/v1/terceiros/me").reply(200, TERCEIRO_MOCK);
    renderWithProviders(<AppLayout><div>conteudo</div></AppLayout>, { authState: AUTH_STATE });
    expect(screen.getByRole("banner")).toHaveTextContent(/Bom dia/i);
    vi.useRealTimers();
  });

  it("link 'Sair' chama logout e limpa sessionStorage", async () => {
    mock.onGet("/api/v1/terceiros/me").reply(200, TERCEIRO_MOCK);
    mock.onPost("/api/v1/auth/logout").reply(204);
    renderWithProviders(<AppLayout><div>x</div></AppLayout>, { authState: AUTH_STATE });
    await userEvent.click(screen.getByRole("button", { name: /sair/i }));
    expect(sessionStorage.getItem("ts:access_token")).toBeNull();
  });

  it("botão de menu abre o Drawer", async () => {
    mock.onGet("/api/v1/terceiros/me").reply(200, TERCEIRO_MOCK);
    renderWithProviders(<AppLayout><div>x</div></AppLayout>, { authState: AUTH_STATE });
    await userEvent.click(screen.getByRole("button", { name: /abrir menu/i }));
    expect(screen.getByRole("navigation", { name: /menu principal/i })).toBeInTheDocument();
  });

  it("exibe o nome do Terceiro quando a query retorna dados", async () => {
    mock.onGet("/api/v1/terceiros/me").reply(200, TERCEIRO_MOCK);
    renderWithProviders(<AppLayout><div>x</div></AppLayout>, { authState: AUTH_STATE });
    await waitFor(() => {
      expect(screen.getByRole("banner")).toHaveTextContent(/Maria/i);
    });
  });

  it("clicar em link do Drawer fecha o drawer e navega", async () => {
    mock.onGet("/api/v1/terceiros/me").reply(200, TERCEIRO_MOCK);
    renderWithProviders(<AppLayout><div>x</div></AppLayout>, { authState: AUTH_STATE });
    await userEvent.click(screen.getByRole("button", { name: /abrir menu/i }));
    const nav = screen.getByRole("navigation", { name: /menu principal/i });
    expect(nav).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /relatórios/i }));
    // Drawer fecha após o clique — navigation element becomes hidden
    expect(screen.queryByRole("navigation", { name: /menu principal/i, hidden: false })).not.toBeInTheDocument();
  });

  it("clicar em 'Jornadas' no Drawer navega para /jornadas e fecha o drawer", async () => {
    mock.onGet("/api/v1/terceiros/me").reply(200, TERCEIRO_MOCK);
    renderWithProviders(<AppLayout><div>x</div></AppLayout>, { authState: AUTH_STATE });
    await userEvent.click(screen.getByRole("button", { name: /abrir menu/i }));
    await userEvent.click(screen.getByRole("button", { name: /^Jornadas$/i }));
    expect(window.location.pathname).toBe("/jornadas");
    expect(screen.queryByRole("navigation", { name: /menu principal/i, hidden: false })).not.toBeInTheDocument();
  });

  it("clicar em 'Nova jornada manual' navega para /jornadas/manual e fecha o drawer", async () => {
    mock.onGet("/api/v1/terceiros/me").reply(200, TERCEIRO_MOCK);
    renderWithProviders(<AppLayout><div>x</div></AppLayout>, { authState: AUTH_STATE });
    await userEvent.click(screen.getByRole("button", { name: /abrir menu/i }));
    await userEvent.click(screen.getByRole("button", { name: /nova jornada manual/i }));
    expect(window.location.pathname).toBe("/jornadas/manual");
    expect(screen.queryByRole("navigation", { name: /menu principal/i, hidden: false })).not.toBeInTheDocument();
  });

  it("clicar em 'Configurar SMTP' navega para /configuracoes/smtp e fecha o drawer", async () => {
    mock.onGet("/api/v1/terceiros/me").reply(200, TERCEIRO_MOCK);
    renderWithProviders(<AppLayout><div>x</div></AppLayout>, { authState: AUTH_STATE });
    await userEvent.click(screen.getByRole("button", { name: /abrir menu/i }));
    await userEvent.click(screen.getByRole("button", { name: /configurar smtp/i }));
    expect(window.location.pathname).toBe("/configuracoes/smtp");
    expect(screen.queryByRole("navigation", { name: /menu principal/i, hidden: false })).not.toBeInTheDocument();
  });

  it("clicar em 'Meu cadastro' navega para /cadastro e fecha o drawer", async () => {
    mock.onGet("/api/v1/terceiros/me").reply(200, TERCEIRO_MOCK);
    renderWithProviders(<AppLayout><div>x</div></AppLayout>, { authState: AUTH_STATE });
    await userEvent.click(screen.getByRole("button", { name: /abrir menu/i }));
    await userEvent.click(screen.getByRole("button", { name: /meu cadastro/i }));
    expect(window.location.pathname).toBe("/cadastro");
    expect(screen.queryByRole("navigation", { name: /menu principal/i, hidden: false })).not.toBeInTheDocument();
  });
});
