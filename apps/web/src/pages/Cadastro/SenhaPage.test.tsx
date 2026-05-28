import { describe, it, expect, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MockAdapter from "axios-mock-adapter";
import api from "@/api/client";
import { renderWithProviders } from "@/test/render";
import { SenhaPage } from "@/pages/Cadastro/SenhaPage";

const mock = new MockAdapter(api);

beforeEach(() => {
  mock.reset();
  sessionStorage.setItem("ts:access_token", "tok");
  sessionStorage.setItem("ts:refresh_token", "r");
  sessionStorage.setItem("ts:terceiro_id", "u1");
  sessionStorage.setItem("ts:expires_at", String(Date.now() + 60_000));
});

describe("SenhaPage", () => {
  it("renderiza heading h1 Alterar Senha e Salvar desabilitado por padrão", () => {
    renderWithProviders(<SenhaPage />, { route: "/cadastro/senha" });
    expect(screen.getByRole("heading", { level: 1, name: /Alterar Senha/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Salvar$/ })).toBeDisabled();
  });

  it("nova_senha != confirmar_senha exibe 'As senhas não coincidem' e Salvar desabilitado", async () => {
    renderWithProviders(<SenhaPage />, { route: "/cadastro/senha" });
    await userEvent.type(screen.getByLabelText(/Senha atual/i), "OldPass1");
    await userEvent.type(screen.getByLabelText(/^Nova senha$/i), "NovaSenha123");
    await userEvent.type(screen.getByLabelText(/Confirmar nova senha/i), "DifSenha123");
    await userEvent.tab();
    expect(await screen.findByText(/As senhas não coincidem/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Salvar$/ })).toBeDisabled();
  });

  it("sucesso 204 emite toast, chama logout e navega para /login", async () => {
    mock.onPut("/api/v1/terceiros/me/senha").reply(204, "");
    renderWithProviders(<SenhaPage />, { route: "/cadastro/senha" });
    await userEvent.type(screen.getByLabelText(/Senha atual/i), "OldPass1");
    await userEvent.type(screen.getByLabelText(/^Nova senha$/i), "NovaSenha123");
    await userEvent.type(screen.getByLabelText(/Confirmar nova senha/i), "NovaSenha123");
    await userEvent.click(screen.getByRole("button", { name: /^Salvar$/ }));
    expect(await screen.findByText(/Senha alterada com sucesso\./i)).toBeInTheDocument();
    await waitFor(() => expect(sessionStorage.getItem("ts:access_token")).toBeNull());
    await waitFor(() => expect(window.location.pathname).toBe("/login"));
  });

  it("401 'Senha atual incorreta' exibe alert + limpa senha_atual + foco em senha_atual", async () => {
    mock.onPost("/api/v1/auth/refresh").reply(401, { code: "UNAUTHORIZED", message: "refresh inválido", details: [] });
    mock.onPut("/api/v1/terceiros/me/senha").reply(401, {
      code: "UNAUTHORIZED", message: "Senha atual incorreta", details: [],
    });
    renderWithProviders(<SenhaPage />, { route: "/cadastro/senha" });
    const atual = screen.getByLabelText(/Senha atual/i) as HTMLInputElement;
    await userEvent.type(atual, "ErradaPass1");
    await userEvent.type(screen.getByLabelText(/^Nova senha$/i), "NovaSenha123");
    await userEvent.type(screen.getByLabelText(/Confirmar nova senha/i), "NovaSenha123");
    await userEvent.click(screen.getByRole("button", { name: /^Salvar$/ }));
    expect(await screen.findByText(/Senha atual incorreta\./i)).toBeInTheDocument();
    expect(atual.value).toBe("");
    expect(document.activeElement).toBe(atual);
  });

  it("Cancelar navega para /cadastro", async () => {
    renderWithProviders(<SenhaPage />, { route: "/cadastro/senha" });
    await userEvent.click(screen.getByRole("button", { name: /Cancelar/i }));
    expect(window.location.pathname).toBe("/cadastro");
  });
});
