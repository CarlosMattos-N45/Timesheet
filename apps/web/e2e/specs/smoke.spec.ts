// apps/web/e2e/specs/smoke.spec.ts
// Smoke test: caminho crítico login → privacidade → criar jornada manual → ver na lista mensal
// Roda contra backend + frontend reais (webServer), sem mock de rede.
import { test, expect } from "../fixtures";
import dayjs from "dayjs";

test("smoke: login -> privacidade -> cria jornada manual -> ve na lista", async ({ page }) => {
  // ---- 1. Login pela UI -------------------------------------------------------
  await page.goto("/login");
  await page.getByLabel("E-mail").fill("terceiro.e2e@example.com");
  await page.getByLabel("Senha").fill("SenhaE2E!2026");
  await page.getByRole("button", { name: "Entrar" }).click();

  // ---- 2. Privacidade (tolerante: pode já estar aceita) -----------------------
  // O LoginPage navega para /jornadas, mas o PrivacyGuard pode redirecionar para /privacidade.
  // Aguardar que a URL se estabilize: esperar o heading de Privacidade OU o heading de Jornadas.
  // Usar waitForSelector para garantir que a página estabilizou (não apenas a URL).
  await Promise.race([
    page.waitForSelector('h1:has-text("Aviso de Privacidade")', { timeout: 30_000 }),
    page.waitForSelector('h1:has-text("Jornadas")', { timeout: 30_000 }),
  ]);

  if (page.url().includes("/privacidade")) {
    // Aguardar o componente renderizar completamente (spinner de loading do PrivacyGuard terminado)
    await page.waitForSelector('button:has-text("Continuar")', { timeout: 15_000 });
    // MUI Checkbox: clicar no span interativo do MuiCheckbox (não no <input> oculto)
    await page.locator(".MuiCheckbox-root").click();
    // Verificar que o checkbox foi marcado (botão Continuar habilitado)
    await expect(page.locator('input[type="checkbox"]')).toBeChecked({ timeout: 5_000 });
    await page.getByRole("button", { name: "Continuar" }).click();
    // Aguardar o PrivacyGuard redirecionar após a query retornar accepted=true
    await page.waitForSelector('h1:has-text("Jornadas")', { timeout: 30_000 });
  }
  // Esperar o heading da lista de jornadas estar visível
  await expect(page.getByRole("heading", { name: "Jornadas" })).toBeVisible({ timeout: 15_000 });

  // ---- 3. Navegar para criação de jornada manual ------------------------------
  // Preferir o botão "Nova jornada manual" sempre visível no topo da lista.
  // Fallback: CTA "Criar jornada manual" no estado vazio (se ainda não há jornadas).
  await page.getByRole("button", { name: /Nova jornada manual|Criar jornada manual/ }).first().click();
  await page.waitForURL(/\/jornadas\/manual$/);
  await expect(page.getByRole("heading", { name: "Nova Jornada Manual" })).toBeVisible();

  // ---- 4. Preencher formulário da jornada manual ------------------------------
  // Data: dia 15 do mês corrente quando hoje >= 15; senão antepenúltimo dia (sempre <= maxDate=hoje)
  const dia = dayjs().date() >= 15 ? dayjs().date(15) : dayjs().subtract(2, "day");
  const dataFormatada = dia.format("DD/MM/YYYY"); // formato esperado pelo DatePicker BR

  // O MUI DatePicker expõe um <input> com aria-label="Data".
  // Limpar o valor atual antes de digitar (pode ter default preenchido).
  const dataInput = page.getByLabel("Data");
  await dataInput.clear();
  await dataInput.fill(dataFormatada);
  // Fechar o popover do DatePicker pressionando Escape, se aberto
  await page.keyboard.press("Escape");

  await page.getByLabel("Horário de início").fill("08:00");
  await page.getByLabel("Horário de saída do almoço").fill("12:00");
  await page.getByLabel("Horário de retorno do almoço").fill("13:00");
  await page.getByLabel("Horário de fim").fill("17:00");

  await page.getByLabel("Atividade").fill("Desenvolvimento de feature E2E");
  await page.getByLabel("Justificativa").fill("Smoke E2E");

  // ---- 5. Salvar e verificar redirecionamento para detalhe -------------------
  await page.getByRole("button", { name: "Salvar" }).click();

  // POST /api/v1/jornadas/manual → 201; redireciona para /jornadas/<uuid>
  await page.waitForURL(/\/jornadas\/[0-9a-f-]{36}$/);
  // Chip de status renderizado com label="AJUSTADA_MANUALMENTE"
  await expect(page.getByText("AJUSTADA_MANUALMENTE")).toBeVisible();

  // ---- 6. Voltar para a lista e verificar Total = 08:00 ----------------------
  // Breadcrumb "Jornadas" na página de detalhe navega para /jornadas
  await page.getByRole("link", { name: "Jornadas" }).click();
  await page.waitForURL(/\/jornadas$/);
  await expect(page.getByRole("heading", { name: "Jornadas" })).toBeVisible();

  // A coluna Data usa formatData: dayjs(yyyymmdd).format("DD/MM")
  // Ex: "15/05" para 2026-05-15
  const dataColuna = dia.format("DD/MM");

  // Localizar a linha da DataGrid pelo conteúdo da data (DD/MM)
  const linha = page.getByRole("row").filter({ hasText: dataColuna });
  await expect(linha).toBeVisible();

  // Asserta a célula Total da linha (data-field="total_horas_apuradas_s").
  // A linha também tem "08:00" na coluna Início — usar data-field para ser específico.
  // Controle negativo: este assert deve ficar RED com "07:00" — trocar para verificar
  // que está realmente exercitando o valor calculado (08:00 = 4h manhã + 4h tarde).
  const celulaTotal = linha.locator('[data-field="total_horas_apuradas_s"]');
  await expect(celulaTotal).toHaveText("08:00");
});
