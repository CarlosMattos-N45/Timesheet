import { describe, it, expect, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MockAdapter from "axios-mock-adapter";
import api from "@/api/client";
import { renderWithProviders } from "@/test/render";
import { SmtpConfigPage } from "@/pages/Configuracoes/SmtpConfigPage";

const mock = new MockAdapter(api);

const CFG_EXISTENTE = {
  host: "smtp.example.com", port: 587, username: "user@example.com",
  use_starttls: true, from_address: "noreply@example.com",
  atualizado_em: "2026-05-01T00:00:00Z",
};

beforeEach(() => {
  mock.reset();
  sessionStorage.setItem("ts:access_token", "tok");
  sessionStorage.setItem("ts:refresh_token", "r");
  sessionStorage.setItem("ts:terceiro_id", "u1");
  sessionStorage.setItem("ts:expires_at", String(Date.now() + 60_000));
});

describe("SmtpConfigPage", () => {
  it("preenche o form: Mount com config existente preenche o form (sem password)", async () => {
    mock.onGet("/api/v1/smtp").reply(200, CFG_EXISTENTE);
    renderWithProviders(<SmtpConfigPage />, { route: "/configuracoes/smtp" });
    expect(((await screen.findByLabelText(/Host/i)) as HTMLInputElement).value).toBe("smtp.example.com");
    expect((screen.getByLabelText(/Porta/i) as HTMLInputElement).valueAsNumber).toBe(587);
    expect((screen.getByLabelText(/Usuário/i) as HTMLInputElement).value).toBe("user@example.com");
    expect((screen.getByLabelText(/Senha/i) as HTMLInputElement).value).toBe("");
    expect((screen.getByLabelText(/From/i) as HTMLInputElement).value).toBe("noreply@example.com");
  });

  it("Nenhuma configuracao: 404 do GET /smtp deixa form vazio e mostra alerta", async () => {
    mock.onGet("/api/v1/smtp").reply(404, { code: "NOT_FOUND", message: "ausente", details: [] });
    renderWithProviders(<SmtpConfigPage />, { route: "/configuracoes/smtp" });
    expect(await screen.findByText(/Nenhuma configuração salva ainda\./i)).toBeInTheDocument();
    expect((screen.getByLabelText(/Host/i) as HTMLInputElement).value).toBe("");
  });

  it("Configuracao SMTP salva: PUT /smtp 200 emite toast", async () => {
    mock.onGet("/api/v1/smtp").reply(200, CFG_EXISTENTE);
    let putBody: unknown = null;
    mock.onPut("/api/v1/smtp").reply((c) => {
      putBody = JSON.parse(c.data as string);
      return [200, { ...CFG_EXISTENTE, atualizado_em: "2026-05-27T00:00:00Z" }];
    });
    renderWithProviders(<SmtpConfigPage />, { route: "/configuracoes/smtp" });
    const senha = await screen.findByLabelText(/Senha/i) as HTMLInputElement;
    await userEvent.type(senha, "novaSenhaSmtp");
    await userEvent.click(screen.getByRole("button", { name: /^Salvar$/ }));
    await waitFor(() => expect(putBody).not.toBeNull());
    expect((putBody as { password: string }).password).toBe("novaSenhaSmtp");
    expect(await screen.findByText(/Configuração SMTP salva\./i)).toBeInTheDocument();
  });

  it("testada com sucesso: Testar conexao 200 emite toast", async () => {
    mock.onGet("/api/v1/smtp").reply(200, CFG_EXISTENTE);
    mock.onPost("/api/v1/smtp/test").reply(200, { ok: true });
    renderWithProviders(<SmtpConfigPage />, { route: "/configuracoes/smtp" });
    await userEvent.click(await screen.findByRole("button", { name: /Testar conexão/i }));
    expect(await screen.findByText(/Conexão SMTP testada com sucesso\./i)).toBeInTheDocument();
  });

  it("SMTP_TEST_FAILED: Testar conexao 400 exibe alert com mensagem do backend", async () => {
    mock.onGet("/api/v1/smtp").reply(200, CFG_EXISTENTE);
    mock.onPost("/api/v1/smtp/test").reply(400, { code: "SMTP_TEST_FAILED", message: "Conexão recusada", details: [] });
    renderWithProviders(<SmtpConfigPage />, { route: "/configuracoes/smtp" });
    await userEvent.click(await screen.findByRole("button", { name: /Testar conexão/i }));
    expect(await screen.findByText(/Conexão recusada/i)).toBeInTheDocument();
  });

  it("SMTP_NOT_CONFIGURED: Testar conexao 422 exibe alert texto exato", async () => {
    mock.onGet("/api/v1/smtp").reply(404, { code: "NOT_FOUND", message: "ausente", details: [] });
    mock.onPost("/api/v1/smtp/test").reply(422, { code: "SMTP_NOT_CONFIGURED", message: "SMTP não configurado", details: [] });
    renderWithProviders(<SmtpConfigPage />, { route: "/configuracoes/smtp" });
    await userEvent.click(await screen.findByRole("button", { name: /Testar conexão/i }));
    expect(await screen.findByText(/SMTP não configurado\. Salve antes de testar\./i)).toBeInTheDocument();
  });
});
