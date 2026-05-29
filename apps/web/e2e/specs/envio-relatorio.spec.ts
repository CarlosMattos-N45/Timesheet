// apps/web/e2e/specs/envio-relatorio.spec.ts
// Fluxo Envio de relatório:
//   1. Criar jornada no mês anterior (dia 15) — se não existir
//   2. Gerar PDF via API (GET /relatorios/{mes}) para que /meta retorne 200
//   3. Configurar SMTP → Mailhog (localhost:1025, STARTTLS off)
//   4. Enviar relatório → snackbar "Relatório enviado para ..."
//   5. Histórico de envios mostra chip SUCESSO (após reload)
//   6. GET http://localhost:8025/api/v2/messages retorna total >= 1
//
// Estratégia para evitar 429 (rate limit 5/min no endpoint de login):
// Reutilizar o token do sessionStorage após o login UI em vez de fazer novo login API.
//
// PRÉ-REQUISITO: Mailhog deve estar up (`make smtp-up` ou `make web-e2e`).
// Isolamento por data: usa dia 15 do mês anterior.
import { test, expect } from "@playwright/test";
import dayjs from "dayjs";
import { loginEPrivacidade, criarJornadaManual, MAILHOG } from "../helpers";
import { STORAGE_KEYS } from "../fixtures";

test("envio de relatorio: SMTP Mailhog -> enviar -> chip SUCESSO + email recebido", async ({ page, request }) => {
  // Limpar caixa do Mailhog antes de tudo para garantir assert exato
  // (controle negativo: total=0 foi verificado red antes de enviar o e-mail)
  await request.delete(`${MAILHOG}/api/v1/messages`);

  // Login via UI (conta o rate limit como 1 chamada)
  await loginEPrivacidade(page);

  // Criar jornada no dia 15 do mês anterior para que /relatorios/{mes} retorne PDF
  const diaAnterior = dayjs().subtract(1, "month").date(15);
  const dataYmd = diaAnterior.format("YYYY-MM-DD");

  await criarJornadaManual(
    page,
    dataYmd,
    ["08:00", "12:00", "13:00", "17:00"],
    "Atividade mes anterior E2E relatorio",
    "Criacao relatorio E2E"
  );

  // Extrair o access_token do sessionStorage (reutilizar o token do login UI)
  // Evita um segundo POST /auth/login que poderia acionar o rate limit (5/min)
  const sessionToken = await page.evaluate(
    (key: string) => sessionStorage.getItem(key) ?? "",
    STORAGE_KEYS.accessToken
  );

  // --- Gerar o PDF do mês anterior via API ---
  // O endpoint GET /relatorios/{mes} gera o PDF on-demand se não existir.
  // Necessário para que a página /relatorios mostre "Enviar agora" (só quando /meta retorna 200).
  const mesAnterior = dayjs().subtract(1, "month").format("YYYY-MM");
  const pdfRes = await request.get(`/api/v1/relatorios/${mesAnterior}`, {
    headers: { Authorization: `Bearer ${sessionToken}` },
  });
  expect(pdfRes.status()).toBe(200);

  // --- Configurar SMTP para Mailhog ---
  await page.goto("/configuracoes/smtp");
  await expect(page.getByRole("heading", { name: "Configuração SMTP" })).toBeVisible({ timeout: 15_000 });
  await expect(page.getByLabel("Host")).toBeVisible({ timeout: 10_000 });

  await page.getByLabel("Host").fill("localhost");
  await page.getByLabel("Porta").fill("1025");

  // STARTTLS: MUI Switch (role="checkbox", label="STARTTLS"). Vem ligado; desligar para Mailhog.
  const starttls = page.getByRole("checkbox", { name: "STARTTLS" });
  if (await starttls.isChecked()) {
    await starttls.uncheck();
  }
  await expect(starttls).not.toBeChecked({ timeout: 5_000 });

  await page.getByLabel("From address").fill("from.e2e@example.com");

  // Usuário e Senha: o schema Zod requer min(1). Mailhog aceita qualquer valor.
  await page.getByLabel("Usuário").fill("mailhog");
  const campoSenha = page.locator('input[type="password"]');
  await campoSenha.fill("mailhog");

  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByText("Configuração SMTP salva.")).toBeVisible({ timeout: 10_000 });

  // --- Enviar relatório do mês anterior ---
  await page.goto("/relatorios");
  await expect(page.getByRole("heading", { name: "Relatórios" })).toBeVisible({ timeout: 15_000 });

  // A página usa mês anterior por default. Aguardar "Enviar agora" (aparece quando meta=200)
  await expect(
    page.getByRole("button", { name: "Enviar agora" })
  ).toBeVisible({ timeout: 30_000 });

  await page.getByRole("button", { name: "Enviar agora" }).click();

  // EnviarRelatorioDialog: botão "Enviar"
  await expect(page.getByRole("button", { name: "Enviar" })).toBeVisible({ timeout: 5_000 });
  await page.getByRole("button", { name: "Enviar" }).click();

  // Snackbar de sucesso
  await expect(
    page.getByText(/Relatório enviado para/)
  ).toBeVisible({ timeout: 30_000 });

  // Refrescar para carregar o histórico atualizado (RelatoriosPage não invalida a query após envio)
  await page.waitForTimeout(1000);
  await page.reload();
  await expect(page.getByRole("heading", { name: "Relatórios" })).toBeVisible({ timeout: 15_000 });

  // Histórico: chip SUCESSO
  await expect(page.getByText("SUCESSO").first()).toBeVisible({ timeout: 10_000 });

  // Mailhog recebeu o e-mail
  // Controle negativo: total=0 foi verificado red antes do envio (caixa limpa no início).
  const res = await request.get(`${MAILHOG}/api/v2/messages`);
  expect(res.status()).toBe(200);
  const body = await res.json() as { total: number };
  expect(body.total).toBeGreaterThanOrEqual(1);
});
