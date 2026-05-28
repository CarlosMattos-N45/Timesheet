import { describe, it, expect, beforeEach, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MockAdapter from "axios-mock-adapter";
import api from "@/api/client";
import { renderWithProviders } from "@/test/render";
import { LoginPage } from "@/pages/Login/LoginPage";

const mock = new MockAdapter(api);

describe("LoginPage", () => {
  beforeEach(() => {
    mock.reset();
    sessionStorage.clear();
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  it("exibe heading h1 'Login' e saudação 'Bom dia.' às 09:00", () => {
    vi.setSystemTime(new Date("2026-05-27T09:00:00"));
    renderWithProviders(<LoginPage />, { route: "/login" });
    expect(screen.getByRole("heading", { level: 1, name: /Login/i })).toBeInTheDocument();
    expect(screen.getByText("Bom dia.")).toBeInTheDocument();
  });

  it("exibe 'Boa tarde.' às 14:00", () => {
    vi.setSystemTime(new Date("2026-05-27T14:00:00"));
    renderWithProviders(<LoginPage />, { route: "/login" });
    expect(screen.getByText("Boa tarde.")).toBeInTheDocument();
  });

  it("botão Entrar inicia desabilitado e fica habilitado quando ambos campos válidos", async () => {
    renderWithProviders(<LoginPage />, { route: "/login" });
    const btn = screen.getByRole("button", { name: /Entrar/i });
    expect(btn).toBeDisabled();
    await userEvent.type(screen.getByLabelText(/E-mail/i), "maria@acme.com");
    await userEvent.type(screen.getByLabelText(/Senha/i), "MinhaSenha123");
    await waitFor(() => expect(btn).toBeEnabled());
  });

  it("e-mail inválido exibe helper text 'E-mail inválido'", async () => {
    renderWithProviders(<LoginPage />, { route: "/login" });
    await userEvent.type(screen.getByLabelText(/E-mail/i), "nao-eh-email");
    await userEvent.tab();
    expect(await screen.findByText(/E-mail inválido/i)).toBeInTheDocument();
  });

  it("submit válido chama POST /auth/login e persiste tokens", async () => {
    mock.onPost("/api/v1/auth/login").reply(200, {
      access_token: "atok-1", refresh_token: "rtok-1",
      terceiro_id: "uuid-1", expires_in: 900,
    });
    renderWithProviders(<LoginPage />, { route: "/login" });
    await userEvent.type(screen.getByLabelText(/E-mail/i), "maria@acme.com");
    await userEvent.type(screen.getByLabelText(/Senha/i), "MinhaSenha123");
    await userEvent.click(screen.getByRole("button", { name: /Entrar/i }));
    await waitFor(() => expect(sessionStorage.getItem("ts:access_token")).toBe("atok-1"));
    expect(sessionStorage.getItem("ts:terceiro_id")).toBe("uuid-1");
  });

  it("401 exibe alert 'E-mail ou senha inválidos' e limpa campo senha", async () => {
    mock.onPost("/api/v1/auth/login").reply(401, {
      code: "UNAUTHORIZED", message: "E-mail ou senha inválidos", details: [],
    });
    renderWithProviders(<LoginPage />, { route: "/login" });
    await userEvent.type(screen.getByLabelText(/E-mail/i), "maria@acme.com");
    const senha = screen.getByLabelText(/Senha/i) as HTMLInputElement;
    await userEvent.type(senha, "SenhaErrada123");
    await userEvent.click(screen.getByRole("button", { name: /Entrar/i }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/E-mail ou senha inválidos\. Verifique e tente novamente\./i);
    expect(senha.value).toBe("");
    expect(document.activeElement).toBe(senha);
  });

  it("429 exibe alert 'Muitas tentativas. Aguarde alguns instantes e tente novamente.'", async () => {
    mock.onPost("/api/v1/auth/login").reply(429, {
      code: "RATE_LIMITED", message: "Muitas tentativas", details: [],
    });
    renderWithProviders(<LoginPage />, { route: "/login" });
    await userEvent.type(screen.getByLabelText(/E-mail/i), "maria@acme.com");
    await userEvent.type(screen.getByLabelText(/Senha/i), "MinhaSenha123");
    await userEvent.click(screen.getByRole("button", { name: /Entrar/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      /Muitas tentativas\. Aguarde alguns instantes e tente novamente\./i
    );
  });

  it("link 'Esqueci minha senha' está desabilitado com aria-disabled=true", () => {
    renderWithProviders(<LoginPage />, { route: "/login" });
    const link = screen.getByText(/Esqueci minha senha/i);
    expect(link).toHaveAttribute("aria-disabled", "true");
  });
});
