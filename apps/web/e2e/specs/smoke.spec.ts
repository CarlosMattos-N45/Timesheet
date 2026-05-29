// apps/web/e2e/specs/smoke.spec.ts
// Smoke test: caminho crítico login → privacidade → criar jornada manual → ver na lista mensal
// Roda contra backend + frontend reais (webServer), sem mock de rede.
//
// Isolamento por data — garante que a data escolhida NUNCA colide com outros specs:
//   ajuste-manual: dia 10 fixo (se hoje ≥ 10) ou today-3
//   dia-normal:    dia 12 fixo (se hoje ≥ 12) ou today-2
//   envio-relatorio: dia 15 do mês ANTERIOR (sem colisão de mês)
//
// Regra de seleção de data para o smoke (hoje = d):
//   d >= 20 → dia 20
//   14 <= d < 20 → dia 14   (≠ 10, ≠ 12, ≤ d)
//   10 <= d < 14 → dia 7    (≠ 10, ≠ 12, ≠ today-2, ≠ today-3, ≤ d)
//    5 <= d < 10 → dia d-4  (= today-4 ≠ today-2 ≠ today-3, sempre ≥ 1)
//         d < 5  → dia max(d-1, 1) no mês corrente (≠ today-2 ≠ today-3, ≥ 1)
//
// Idempotência: criarJornadaManual trata 409 (jornada já existe para o dia) —
// a suíte completa passa verde em 2 execuções consecutivas.
import { test, expect } from "@playwright/test";
import dayjs from "dayjs";
import { loginEPrivacidade, criarJornadaManual } from "../helpers";

test("smoke: login -> privacidade -> cria jornada manual -> ve na lista", async ({ page }) => {
  // ---- 1. Login e privacidade via helper (tolerante a re-runs) -----------------
  await loginEPrivacidade(page);

  // ---- 2. Determinar data sem colidir com outros specs -------------------------
  const hoje = dayjs();
  const d = hoje.date();
  let dia: dayjs.Dayjs;
  if (d >= 20) {
    dia = hoje.date(20);
  } else if (d >= 14) {
    dia = hoje.date(14); // 14 ≤ d < 20; ≠ 10, ≠ 12
  } else if (d >= 10) {
    dia = hoje.date(7); // 7 ≤ d < 14; ≠ 10, ≠ 12, ≠ today-2, ≠ today-3
  } else if (d >= 5) {
    dia = hoje.date(d - 4); // today-4 ≠ today-2 e ≠ today-3; ≥ 1
  } else {
    // d <= 4: today-1 nunca iguala today-2 nem today-3; max protege contra dia 0
    dia = hoje.date(Math.max(d - 1, 1));
  }
  const dataYmd = dia.format("YYYY-MM-DD");

  // ---- 3. Criar jornada manual via helper (idempotente: trata 409) -------------
  await criarJornadaManual(
    page,
    dataYmd,
    ["08:00", "12:00", "13:00", "17:00"],
    "Desenvolvimento de feature E2E",
    "Smoke E2E"
  );

  // ---- 4. Verificar chip AJUSTADA_MANUALMENTE na página de detalhe -------------
  // POST /api/v1/jornadas/manual → 201; redireciona para /jornadas/<uuid>
  // (ou navega para jornada existente em caso de re-run)
  await expect(page.getByText("AJUSTADA_MANUALMENTE")).toBeVisible({ timeout: 15_000 });

  // ---- 5. Voltar para a lista e verificar Total = 08:00 ------------------------
  // Breadcrumb "Jornadas" na página de detalhe navega para /jornadas
  await page.getByRole("link", { name: "Jornadas" }).click();
  await page.waitForURL(/\/jornadas$/, { timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Jornadas" })).toBeVisible();

  // A coluna Data usa formatData: dayjs(yyyymmdd).format("DD/MM")
  // Ex: "20/05" para 2026-05-20
  const dataColuna = dia.format("DD/MM");

  // Localizar a linha da DataGrid pelo conteúdo da data (DD/MM)
  const linha = page.getByRole("row").filter({ hasText: dataColuna });
  await expect(linha).toBeVisible({ timeout: 15_000 });

  // Asserta a célula Total da linha (data-field="total_horas_apuradas_s").
  // A linha também tem "08:00" na coluna Início — usar data-field para ser específico.
  // Controle negativo: este assert deve ficar RED com "07:00" — trocar para verificar
  // que está realmente exercitando o valor calculado (08:00 = 4h manhã + 4h tarde).
  const celulaTotal = linha.locator('[data-field="total_horas_apuradas_s"]');
  await expect(celulaTotal).toHaveText("08:00");
});
