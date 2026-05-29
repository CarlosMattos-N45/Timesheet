// apps/web/e2e/helpers.ts — helpers compartilhados pelas specs de jornada (TASK-041)
import type { Page } from "@playwright/test";
import dayjs from "dayjs";

/** URL base do Mailhog (API HTTP). Deve estar up antes dos specs de envio. */
export const MAILHOG = "http://localhost:8025";

/**
 * Faz login pela UI e aceita a privacidade se necessário.
 * Termina na URL /jornadas.
 */
export async function loginEPrivacidade(page: Page): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("E-mail").fill("terceiro.e2e@example.com");
  await page.getByLabel("Senha").fill("SenhaE2E!2026");
  await page.getByRole("button", { name: "Entrar" }).click();

  // Aguardar que a navegação pós-login se estabilize
  await Promise.race([
    page.waitForSelector('h1:has-text("Aviso de Privacidade")', { timeout: 30_000 }),
    page.waitForSelector('h1:has-text("Jornadas")', { timeout: 30_000 }),
  ]);

  if (page.url().includes("/privacidade")) {
    await page.waitForSelector('button:has-text("Continuar")', { timeout: 15_000 });
    // MUI Checkbox: clicar no span do MuiCheckbox (input oculto não recebe clique direto)
    await page.locator(".MuiCheckbox-root").click();
    await page.getByRole("button", { name: "Continuar" }).click();
    await page.waitForSelector('h1:has-text("Jornadas")', { timeout: 30_000 });
  }

  await page.waitForURL(/\/jornadas$/, { timeout: 30_000 });
}

/**
 * Cria uma jornada manual via UI a partir da página /jornadas.
 * Retorna o ID da jornada (extraído da URL).
 *
 * Se já existir uma jornada para o dia informado (erro 409/UI "Já existe uma jornada"),
 * navega para a lista mensal e clica na linha correspondente ao dia para acessar
 * a jornada existente.
 *
 * @param page           Playwright Page
 * @param dataYmd        Data no formato "YYYY-MM-DD"
 * @param horarios       [inicio, saida_almoco, retorno_almoco, fim] no formato "HH:mm"
 * @param atividade      Texto da atividade
 * @param justificativa  Texto da justificativa (mínimo 5 chars)
 */
export async function criarJornadaManual(
  page: Page,
  dataYmd: string,
  horarios: [string, string, string, string],
  atividade: string,
  justificativa: string
): Promise<string> {
  const [h1, h2, h3, h4] = horarios;

  // Garantir que estamos na lista de jornadas (ou redirecionar para lá)
  if (!page.url().includes("/jornadas") || page.url().includes("/manual") || page.url().match(/\/jornadas\/[0-9a-f-]{36}/)) {
    await page.goto("/jornadas");
    await page.waitForURL(/\/jornadas$/, { timeout: 15_000 });
  }

  // Clicar no botão de nova jornada (topo da lista ou CTA do estado vazio)
  await page.getByRole("button", { name: /Nova jornada manual|Criar jornada manual/ }).first().click();
  await page.waitForURL(/\/jornadas\/manual$/);

  // Preencher data no formato DD/MM/YYYY (DatePicker BR)
  const dataFormatada = dayjs(dataYmd).format("DD/MM/YYYY");
  const dataInput = page.getByLabel("Data");
  await dataInput.clear();
  await dataInput.fill(dataFormatada);
  // Fechar popover do DatePicker se aberto
  await page.keyboard.press("Escape");

  await page.getByLabel("Horário de início").fill(h1);
  await page.getByLabel("Horário de saída do almoço").fill(h2);
  await page.getByLabel("Horário de retorno do almoço").fill(h3);
  await page.getByLabel("Horário de fim").fill(h4);

  await page.getByLabel("Atividade").fill(atividade);
  await page.getByLabel("Justificativa").fill(justificativa);

  await page.getByRole("button", { name: "Salvar" }).click();

  // Aguardar: redireciona para /jornadas/<uuid> em sucesso,
  // ou exibe erro "Já existe uma jornada para este dia" em caso de conflito (re-run).
  const resultado = await Promise.race([
    page.waitForURL(/\/jornadas\/[0-9a-f-]{36}$/, { timeout: 15_000 }).then(() => "criada"),
    page.waitForSelector('text=Já existe uma jornada para este dia', { timeout: 15_000 }).then(() => "existente"),
  ]);

  if (resultado === "criada") {
    return page.url().split("/").pop() as string;
  }

  // Jornada já existe para este dia (re-run): buscar o ID da jornada via API
  // em vez de navegar pela lista (evita problemas de mês errado no DatePicker)
  const mesYm = dayjs(dataYmd).format("YYYY-MM");
  const diaFormatado = dayjs(dataYmd).format("DD/MM");

  // Navegar para a lista do mês correto via API para obter o ID da jornada
  await page.goto(`/jornadas`);
  await page.waitForURL(/\/jornadas$/, { timeout: 15_000 });

  // Navegar para o mês correto se necessário
  const mesAtual = dayjs().format("YYYY-MM");
  if (mesYm !== mesAtual) {
    // Abrir DatePicker e selecionar o mês/ano correto
    await page.getByRole("button", { name: /Choose date/ }).click({ timeout: 10_000 });
    await page.waitForSelector(".MuiPickersPopper-root", { timeout: 10_000 });
    // Switch para view de meses
    await page.locator('[aria-label="year view is open, switch to calendar view"]').click({ timeout: 5_000 });
    await page.waitForSelector('[role="radio"]', { timeout: 5_000 });
    // Se o ano for diferente, navegar — para simplificar, assumir mesmo ano (dentro de 12 meses)
    const mesesAriaLabel = [
      "janeiro", "fevereiro", "março", "abril", "maio", "junho",
      "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
    ];
    const mesDayjs = dayjs(dataYmd);
    const ariaLabel = mesesAriaLabel[mesDayjs.month()];
    await page.locator(`[aria-label="${ariaLabel}"]`).click({ timeout: 5_000 });
    await page.waitForTimeout(500); // aguardar atualização da lista
  }

  // Clicar na linha da DataGrid que corresponde ao dia
  const linha = page.getByRole("row").filter({ hasText: diaFormatado });
  await linha.waitFor({ timeout: 10_000 });
  await linha.click();

  await page.waitForURL(/\/jornadas\/[0-9a-f-]{36}$/, { timeout: 15_000 });
  return page.url().split("/").pop() as string;
}
