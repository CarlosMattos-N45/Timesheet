// apps/web/e2e/specs/ajuste-manual.spec.ts
// Fluxo Ajuste manual:
//   1. Criar jornada 08:00/12:00/13:00/17:00 → Total 08:00
//   2. Fazer o ajuste de FIM_JORNADA de 17:00 para 18:00 via UI
//      (acionar handler React via __reactProps$.onChange → Salvar alterações →
//       JustificativaDialog → Confirmar alterações)
//   3. Verificar: snackbar sucesso, campo 18:00, Total 09:00, auditoria com autor
//
// Nota técnica — input type="time" + React:
// A JornadaDetalhePage usa inputs type="time" (controlled pelo React state).
// O Playwright fill() em campos com valor pré-existente não aciona o React onChange.
// Solução: acessar __reactProps$.onChange diretamente via evaluate.
//
// Idempotência: usa a API para resetar FIM_JORNADA para 17:00 antes de cada run.
// Verificação pós-salvar: navega para outra rota e volta para forçar estado fresco
// (evita cache stale do react-query que pode mostrar dado antigo).
//
// Isolamento: dia 10 do mês corrente.
import { test, expect } from "@playwright/test";
import dayjs from "dayjs";
import { loginEPrivacidade, criarJornadaManual } from "../helpers";

test("ajuste manual: edita fim 17:00->18:00, Total 09:00, auditoria com autor", async ({ page, request }) => {
  await loginEPrivacidade(page);

  const hoje = dayjs();
  const dia = hoje.date() >= 10 ? hoje.date(10) : hoje.subtract(3, "day");
  const dataYmd = dia.format("YYYY-MM-DD");

  // Criar ou navegar para jornada existente no dia 10
  await criarJornadaManual(
    page,
    dataYmd,
    ["08:00", "12:00", "13:00", "17:00"],
    "Atividade ajuste manual E2E",
    "Criacao ajuste E2E"
  );

  const jornadaId = page.url().split("/").pop()!;

  // Login via API para obter token (necessário para o reset de idempotência)
  const loginRes = await request.post("/api/v1/auth/login", {
    data: { email: "terceiro.e2e@example.com", senha: "SenhaE2E!2026" },
  });
  const { access_token } = await loginRes.json() as { access_token: string };

  // Resetar o FIM_JORNADA para 17:00 (idempotência em re-runs: garante ponto de partida fixo)
  const jornadaRes = await request.get(`/api/v1/jornadas/${jornadaId}`, {
    headers: { Authorization: `Bearer ${access_token}` },
  });
  const jornada = await jornadaRes.json() as { data: string };
  const horario17h = dayjs(jornada.data).hour(17).minute(0).second(0).millisecond(0).toISOString();
  await request.put(`/api/v1/jornadas/${jornadaId}`, {
    headers: { Authorization: `Bearer ${access_token}`, "Content-Type": "application/json" },
    data: { marcacoes: [{ tipo: "FIM_JORNADA", horario_efetivo: horario17h }], motivo: "Reset idempotente E2E" },
  });

  // Navegar para a jornada com estado fresco (após reset, garante que o React carrega 17:00)
  await page.goto(`/jornadas/${jornadaId}`);
  await page.waitForURL(/\/jornadas\/[0-9a-f-]{36}$/, { timeout: 15_000 });
  const campoFim = page.getByLabel("Horário de fim");
  await expect(campoFim).toBeEnabled({ timeout: 10_000 });
  await expect(campoFim).toHaveValue("17:00", { timeout: 5_000 });
  await expect(page.getByText(/Total: 08:00/)).toBeVisible({ timeout: 5_000 });

  // Acionar o handler onChange do React diretamente via __reactProps$
  // (método confiável para controlled inputs type="time" — fill() não aciona onChange
  //  quando o campo tem valor pré-existente)
  await campoFim.evaluate((el: HTMLInputElement) => {
    const propsKey = Object.keys(el).find(k => k.startsWith("__reactProps$"));
    if (!propsKey) throw new Error("__reactProps$ não encontrado no elemento");
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const props = (el as any)[propsKey];
    if (typeof props?.onChange !== "function") throw new Error("onChange não encontrado");
    props.onChange({ target: { value: "18:00" } });
  });

  // Aguardar o React re-renderizar: Total deve atualizar para 09:00
  // Controle negativo (brownfield): antes de fixar "09:00" foi verificado que "08:00" fica red.
  await expect(page.getByText(/Total: 09:00/)).toBeVisible({ timeout: 5_000 });

  // Verificar estado estável antes de clicar: campo fim = 18:00
  await expect(campoFim).toHaveValue("18:00", { timeout: 2_000 });

  // Botão "Salvar alterações" deve aparecer (isDirty=true: marcacoesAlteradas.length > 0)
  const btnSalvar = page.getByRole("button", { name: "Salvar alterações" });
  await expect(btnSalvar).toBeVisible({ timeout: 5_000 });
  await btnSalvar.click();

  // JustificativaDialog: preencher motivo (≥5 chars)
  const inputMotivo = page.getByRole("textbox", { name: "Motivo da alteração" });
  await expect(inputMotivo).toBeVisible({ timeout: 5_000 });
  await inputMotivo.fill("Correcao do horario de fim");
  await page.getByRole("button", { name: "Confirmar alterações" }).click();

  // Snackbar de sucesso
  await expect(
    page.getByText("Jornada atualizada com sucesso.")
  ).toBeVisible({ timeout: 15_000 });

  // Navegar para a lista e voltar para verificar com estado fresco do react-query
  // (o cache stale pode mostrar dados antigos; navegar força um re-mount)
  const jornadaUrl = page.url();
  await page.goto("/jornadas");
  await page.waitForURL(/\/jornadas$/, { timeout: 10_000 });
  await page.goto(jornadaUrl);
  await page.waitForURL(/\/jornadas\/[0-9a-f-]{36}$/, { timeout: 10_000 });

  // Campo fim deve mostrar 18:00 (dado persistido no banco)
  // Controle negativo: "17:00" ficaria red após o ajuste para 18:00.
  const campoFimFresco = page.getByLabel("Horário de fim");
  await expect(campoFimFresco).toBeEnabled({ timeout: 10_000 });
  await expect(campoFimFresco).toHaveValue("18:00", { timeout: 5_000 });

  // Total 09:00 = (12-08) + (18-13) = 4h + 5h = 9h
  // Controle negativo: "Total: 08:00" ficaria red (valor antes do ajuste).
  await expect(page.getByText(/Total: 09:00/)).toBeVisible({ timeout: 5_000 });

  // Abrir accordion "Histórico de auditoria" (lazy ao expandir)
  await page.getByText("Histórico de auditoria").click();

  // Verificar o autor no log de auditoria (email do Terceiro E2E semeado pelo global-setup)
  await expect(
    page.getByText("terceiro.e2e@example.com").first()
  ).toBeVisible({ timeout: 15_000 });
});
