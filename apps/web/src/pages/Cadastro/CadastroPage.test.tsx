import { describe, it, expect, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MockAdapter from "axios-mock-adapter";
import api from "@/api/client";
import { renderWithProviders } from "@/test/render";
import { CadastroPage } from "@/pages/Cadastro/CadastroPage";

const mock = new MockAdapter(api);

const T_BASE = {
  id: "u1", nome: "Maria", empresa_nome: "ACME LTDA",
  empresa_cnpj: "00000000000191",
  horario_inicio_jornada: "09:00:00", horario_saida_almoco: "12:00:00",
  horario_retorno_almoco: "13:00:00", horario_fim_jornada: "18:00:00",
  trabalha_fim_de_semana: false,
  email_contato: "maria@acme.com",
  email_destinatario_relatorio: "rh@acme.com",
  criado_em: "2026-01-01T00:00:00Z", atualizado_em: "2026-05-27T00:00:00Z",
};

beforeEach(() => {
  mock.reset();
  sessionStorage.setItem("ts:access_token", "tok");
  sessionStorage.setItem("ts:refresh_token", "r");
  sessionStorage.setItem("ts:terceiro_id", "u1");
  sessionStorage.setItem("ts:expires_at", String(Date.now() + 60_000));
});

describe("CadastroPage", () => {
  it("carrega GET /terceiros/me e preenche o form", async () => {
    mock.onGet("/api/v1/terceiros/me").reply(200, T_BASE);
    renderWithProviders(<CadastroPage />, { route: "/cadastro" });
    const nome = await screen.findByLabelText(/Nome/i) as HTMLInputElement;
    expect(nome.value).toBe("Maria");
    expect((screen.getByLabelText(/CNPJ/i) as HTMLInputElement).value).toMatch(/00\.000\.000\/0001-91/);
  });

  it("Salvar fica desabilitado por padrão e habilita ao tornar o form dirty + valid", async () => {
    mock.onGet("/api/v1/terceiros/me").reply(200, T_BASE);
    renderWithProviders(<CadastroPage />, { route: "/cadastro" });
    const btn = await screen.findByRole("button", { name: /^Salvar$/ });
    expect(btn).toBeDisabled();
    const nome = screen.getByLabelText(/Nome/i) as HTMLInputElement;
    await userEvent.clear(nome);
    await userEvent.type(nome, "Maria Silva");
    await waitFor(() => expect(btn).toBeEnabled());
  });

  it("CNPJ inválido client-side exibe helper text e bloqueia Salvar", async () => {
    mock.onGet("/api/v1/terceiros/me").reply(200, T_BASE);
    renderWithProviders(<CadastroPage />, { route: "/cadastro" });
    const cnpj = await screen.findByLabelText(/CNPJ/i) as HTMLInputElement;
    await userEvent.clear(cnpj);
    await userEvent.type(cnpj, "00.000.000/0000-99"); // DV errado
    await userEvent.tab();
    expect(await screen.findByText(/CNPJ inválido \(dígito verificador incorreto\)\./i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Salvar$/ })).toBeDisabled();
  });

  it("PUT /terceiros/me sucesso invalida cache e mostra toast", async () => {
    mock.onGet("/api/v1/terceiros/me").reply(200, T_BASE);
    mock.onPut("/api/v1/terceiros/me").reply(200, { ...T_BASE, nome: "Maria Silva" });
    renderWithProviders(<CadastroPage />, { route: "/cadastro" });
    const nome = await screen.findByLabelText(/Nome/i) as HTMLInputElement;
    await userEvent.clear(nome);
    await userEvent.type(nome, "Maria Silva");
    await userEvent.click(screen.getByRole("button", { name: /^Salvar$/ }));
    expect(await screen.findByText(/Cadastro atualizado com sucesso\./i)).toBeInTheDocument();
  });

  it("422 do PUT com field body.empresa_cnpj exibe alert", async () => {
    mock.onGet("/api/v1/terceiros/me").reply(200, T_BASE);
    mock.onPut("/api/v1/terceiros/me").reply(422, {
      code: "VALIDATION_ERROR",
      message: "Erro de validação",
      details: [{ field: "body.empresa_cnpj", issue: "CNPJ inválido (dígito verificador incorreto)" }],
    });
    renderWithProviders(<CadastroPage />, { route: "/cadastro" });
    const nome = await screen.findByLabelText(/Nome/i) as HTMLInputElement;
    await userEvent.clear(nome); await userEvent.type(nome, "X");
    await userEvent.click(screen.getByRole("button", { name: /^Salvar$/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/Erro de validação/i);
  });

  it("Alterar senha navega para /cadastro/senha", async () => {
    mock.onGet("/api/v1/terceiros/me").reply(200, T_BASE);
    renderWithProviders(<CadastroPage />, { route: "/cadastro" });
    await userEvent.click(await screen.findByRole("button", { name: /Alterar senha/i }));
    expect(window.location.pathname).toBe("/cadastro/senha");
  });
});
