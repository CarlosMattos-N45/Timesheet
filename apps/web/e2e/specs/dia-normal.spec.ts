// apps/web/e2e/specs/dia-normal.spec.ts
// Fluxo "Dia normal" (representação web): criar jornada manual completa → lista mensal
// mostra Total 08:00 e chip AJUSTADA_MANUALMENTE.
// Isolamento por data: usa dia 12 do mês corrente.
import { test, expect } from "@playwright/test";
import dayjs from "dayjs";
import { loginEPrivacidade, criarJornadaManual } from "../helpers";

test("dia normal: jornada manual 08:00/12:00/13:00/17:00 aparece na lista com Total 08:00 e chip AJUSTADA_MANUALMENTE", async ({ page }) => {
  await loginEPrivacidade(page);

  // Dia 12 do mês corrente (sempre <= hoje para mês atual;
  // se hoje for antes do dia 12, usar um dia passado seguro)
  const hoje = dayjs();
  const dia = hoje.date() >= 12 ? hoje.date(12) : hoje.subtract(2, "day");
  const dataYmd = dia.format("YYYY-MM-DD");

  // Criar jornada manual via UI
  await criarJornadaManual(
    page,
    dataYmd,
    ["08:00", "12:00", "13:00", "17:00"],
    "Desenvolvimento de feature dia normal E2E",
    "Dia normal E2E"
  );

  // Após criar, está na página de detalhe — verificar chip AJUSTADA_MANUALMENTE
  await expect(page.getByText("AJUSTADA_MANUALMENTE")).toBeVisible({ timeout: 10_000 });

  // Voltar para a lista via breadcrumb "Jornadas"
  await page.getByRole("link", { name: "Jornadas" }).click();
  await page.waitForURL(/\/jornadas$/, { timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Jornadas" })).toBeVisible();

  // Localizar a linha pelo dia no formato DD/MM (coluna Data da DataGrid)
  const dataColuna = dia.format("DD/MM");
  const linha = page.getByRole("row").filter({ hasText: dataColuna });
  await expect(linha).toBeVisible({ timeout: 10_000 });

  // Controle negativo: este assert foi visto red com "07:00" antes de fixar para "08:00".
  // Total = (12:00−08:00)+(17:00−13:00) = 4h + 4h = 08:00
  const celulaTotal = linha.locator('[data-field="total_horas_apuradas_s"]');
  await expect(celulaTotal).toHaveText("08:00");

  // Chip AJUSTADA_MANUALMENTE na coluna Status
  const celulaStatus = linha.locator('[data-field="status"]');
  await expect(celulaStatus.getByText("AJUSTADA_MANUALMENTE")).toBeVisible();
});
