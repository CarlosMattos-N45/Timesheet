// apps/web/e2e/specs/00-onboarding.spec.ts
// Fluxo Onboarding (web): login + aceitar privacidade → /jornadas exibe estado vazio
// com texto "Nenhuma jornada registrada para este mês." e CTA "Criar jornada manual".
//
// Para robustez em re-runs com banco acumulado (jornadas em meses correntes),
// navega para um mês passado sem jornadas (2 meses atrás) via DatePicker MUI.
//
// DatePicker MUI (views=["year","month"]) — fluxo de interação:
//   1. Clicar no ícone de calendário → abre seletor de anos
//   2. Clicar no header "↕" → muda para seletor de meses (radio buttons)
//   3. Meses têm aria-label com nome completo em pt-BR (ex: "março")
//   4. maxDate=hoje: meses futuros têm Mui-disabled; meses passados são clicáveis
import { test, expect } from "@playwright/test";
import dayjs from "dayjs";
import { loginEPrivacidade } from "../helpers";

test("onboarding: login + privacidade -> /jornadas exibe Nenhuma jornada e CTA Criar jornada manual", async ({ page }) => {
  // --- login e aceite de privacidade via UI ---
  await loginEPrivacidade(page);

  // Deve estar em /jornadas
  await expect(page).toHaveURL(/\/jornadas$/);
  await expect(page.getByRole("heading", { name: "Jornadas" })).toBeVisible();

  // Navegar para 2 meses atrás — passado, habilitado no DatePicker, nunca terá jornadas E2E.
  // (As jornadas E2E são criadas no mês corrente pelos outros specs.)
  const mesSemJornada = dayjs().subtract(2, "month");
  // aria-label dos meses em pt-BR conforme MUI + AdapterDayjs (locale pt-BR)
  const mesesAriaLabel = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
  ];
  const ariaLabelMes = mesesAriaLabel[mesSemJornada.month()]; // month() é 0-indexed

  // 1. Abrir o painel do DatePicker (abre na view de anos)
  await page.getByRole("button", { name: /Choose date/ }).click({ timeout: 10_000 });
  await page.waitForSelector(".MuiPickersPopper-root", { timeout: 10_000 });

  // 2. Mudar para view de meses (clicar no header toggle)
  await page.locator('[aria-label="year view is open, switch to calendar view"]').click({ timeout: 5_000 });
  // Aguardar o painel de meses aparecer (tem um mês com role=radio)
  await page.waitForSelector('[role="radio"]', { timeout: 5_000 });

  // 3. Clicar no mês desejado via aria-label
  // Se o mês está em um ano diferente do exibido, precisamos navegar.
  // Para simplificar: o painel começa com o ano atual; se 2 meses atrás é o mesmo ano, ok.
  // Se é ano anterior, precisamos clicar em "<" (botão de voltar) no cabeçalho do painel de meses.
  const anoAtual = dayjs().year();
  const anoMesSemJornada = mesSemJornada.year();
  if (anoMesSemJornada < anoAtual) {
    // Clicar no botão de voltar o ano (seta esquerda)
    // O header do MUI YearCalendar/MonthCalendar tem botões de navegação
    const prevBtn = page.locator(".MuiPickersPopper-root").locator('button').first();
    await prevBtn.click({ timeout: 5_000 });
    await page.waitForTimeout(300);
  }

  // 4. Clicar no mês via aria-label
  await page.locator(`[aria-label="${ariaLabelMes}"]`).click({ timeout: 5_000 });

  // 5. Aguardar a lista atualizar — o mês 2 atrás nunca terá jornadas E2E
  // Controle negativo: "Nenhuma jornada XYZ inexistente" ficaria red.
  await expect(
    page.getByText("Nenhuma jornada registrada para este mês.")
  ).toBeVisible({ timeout: 15_000 });

  // 6. CTA "Criar jornada manual" visível no estado vazio
  await expect(page.getByRole("button", { name: "Criar jornada manual" })).toBeVisible();

  // 7. Botão "Nova jornada manual" SEMPRE visível (topo da página)
  await expect(page.getByRole("button", { name: "Nova jornada manual" })).toBeVisible();
});
