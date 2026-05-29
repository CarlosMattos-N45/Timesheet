---
checkpoint: null
complexity: P
created_at: "2026-05-29 12:35:44"
criteria:
    - done: true
      test: cd apps/web && npx playwright test smoke
      text: Login pela UI com terceiro.e2e@example.com/SenhaE2E!2026 leva a /privacidade ou /jornadas
    - done: true
      text: Aceite de privacidade pela UI (checkbox + Continuar) leva a /jornadas com heading Jornadas visivel
    - done: true
      text: Criar jornada manual (data dia util, 08:00/12:00/13:00/17:00, atividade>=10, justificativa>=5) retorna 201 e redireciona para /jornadas/<uuid> com chip AJUSTADA_MANUALMENTE
    - done: true
      test: cd apps/web && npx playwright test smoke
      text: 'Na lista mensal a linha do dia criado exibe Total exatamente 08:00 (controle negativo: 07:00 fica red)'
    - done: true
      text: Smoke passa com banco e2e zerado antes (make web-e2e zera apps/api/data/e2e.sqlite); spec nao depende de jornada pre-existente
    - done: true
      text: Suite passando com webServer real (backend+frontend), sem mock de rede
deps:
    - TASK-039
id: TASK-040
linter: cd apps/web && npm run lint
n45_version: 0.2.0
persona: qa
phase: Phase 7 — E2E
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: pending
tests: cd apps/web && npx playwright test smoke
title: 'Smoke Test E2E: caminho critico login -> aceitar privacidade -> criar jornada manual -> ver na lista mensal com Total correto'
updated_at: "2026-05-29 13:13:09"
worktree:
    base_sha: b1cf650e1d5b0bc60356d5ce15eab1b834bd46f5
    branch: worktree-agent-aa89a8290cd22505
    path: .n45\worktree\agent-aa89a8290cd22505
---
## Contexto

Segunda task da Phase 7 — E2E. Depende da task 1 (Setup E2E), que já entregou `playwright.config.ts` com `webServer` (backend uvicorn 8765 + frontend vite 5173), o seed idempotente do Terceiro (`terceiro.e2e@example.com` / `SenhaE2E!2026`) e os fixtures/helpers em `apps/web/e2e/fixtures.ts`. Esta task escreve **1 único spec de smoke** que percorre o caminho crítico mais curto exercitando todas as camadas integradas reais: navegador → Vite proxy → FastAPI → SQLite. Nenhum mock de rede.

Estado atual relevante (fatos do código já entregue):

- O sistema é single-tenant; não há tela de cadastro do Terceiro na Web (o cadastro real é via Agente Desktop .NET, fora do alcance do Playwright). O Terceiro de teste é semeado via API pela task 1. Logo, o caminho crítico web inicia no **login** com as credenciais semeadas.
- Fluxo de rotas (de `apps/web/src/routes.tsx`): `/login` (público) → `ProtectedRoute` → `PrivacyGuard` → `/privacidade` e, dentro de `AppLayout`, `/jornadas`, `/jornadas/manual`, `/jornadas/:id`, `/relatorios`, etc.
- **Guard de privacidade:** no primeiro acesso (sem `privacy_acceptance`), o `PrivacyGuard` redireciona qualquer rota autenticada para `/privacidade`. Após `POST /api/v1/privacidade/aceitar`, o cache é invalidado e a navegação é liberada para `/jornadas`. O smoke deve aceitar a privacidade pela UI (checkbox "Li e aceito os termos de privacidade" + botão "Continuar").
- **Login** (`apps/web/src/pages/Login/LoginPage.tsx`): campos com `label` "E-mail" e "Senha" (TextField MUI), botão "Entrar" (desabilitado até o form ser válido), saudação contextual exibida acima do form. Sucesso → navega para `/jornadas`.
- **Jornada manual** (`apps/web/src/pages/JornadaManual/JornadaManualPage.tsx`): título "Nova Jornada Manual"; DatePicker "Data" (`maxDate=hoje`); 4 TextFields de horário com `aria-label` "Horário de início" / "Horário de saída do almoço" / "Horário de retorno do almoço" / "Horário de fim" e placeholder "HH:MM" (`maxLength=5`); textarea `aria-label="Atividade"` (≥10 chars); textarea `aria-label="Justificativa"` (≥5 chars); botão "Salvar" (desabilitado até válido). Sucesso → `navigate('/jornadas/:id', { replace: true })` com o id retornado pelo `POST /api/v1/jornadas/manual` (`201`, status `AJUSTADA_MANUALMENTE`).
- **Lista mensal** (`apps/web/src/pages/Jornadas/JornadasPage.tsx`): título "Jornadas"; DatePicker "Mês" (views year/month, default mês atual); DataGrid MUI com colunas Data | Dia | Início | Saída Almoço | Retorno Almoço | Fim | Total | Status; clique em linha navega para `/jornadas/:id`; estado vazio mostra "Nenhuma jornada registrada para este mês." + CTA "Criar jornada manual".

Como cobre auth + persistência + UI, o smoke segue o caminho da matriz "Auth + persistência + UI" adaptado (não há signup web): **login → aceitar privacidade → criar recurso (jornada manual) → ver na listagem**.

## Comportamento Esperado

O smoke roda contra backend + frontend reais (subidos pelo `webServer`) e dados semeados (task 1). Como a primeira execução do dia já pode ter aceito a privacidade num run anterior, o spec deve ser tolerante: se cair direto em `/jornadas` (privacidade já aceita), pula a etapa de aceite; senão, aceita.

**Exemplos (entrada → saída esperada)** — valores reais que o spec asserta:

| Entrada / Ação | Saída / Efeito esperado |
| -------------- | ----------------------- |
| Navegar para `/login`, preencher "E-mail"=`terceiro.e2e@example.com`, "Senha"=`SenhaE2E!2026`, clicar "Entrar" | URL passa a conter `/privacidade` (1º acesso) **ou** `/jornadas` (já aceito) |
| Em `/privacidade`: marcar checkbox "Li e aceito os termos de privacidade", clicar "Continuar" | URL passa a `/jornadas`; título "Jornadas" visível |
| Em `/jornadas`, clicar "Nova jornada manual" (ou CTA "Criar jornada manual" no estado vazio) | URL = `/jornadas/manual`; título "Nova Jornada Manual" visível |
| Preencher Data (um dia útil do mês corrente, ex. dia 15), horários `08:00`/`12:00`/`13:00`/`17:00`, Atividade="Desenvolvimento de feature E2E", Justificativa="Smoke E2E", clicar "Salvar" | `POST /api/v1/jornadas/manual` → `201`; URL passa a `/jornadas/<uuid>`; chip de status "AJUSTADA_MANUALMENTE" visível |
| Voltar para `/jornadas` (breadcrumb/navegação) com o mês = mês corrente | A DataGrid lista **≥1** linha; a linha do dia 15 exibe Total "08:00" (8h = início→fim menos 1h de almoço = 17:00−08:00−01:00 = 08:00) e o chip "AJUSTADA_MANUALMENTE" |

> **Cálculo do total:** (12:00−08:00) + (17:00−13:00) = 4h + 4h = 8h → `formatTotal` exibe `"08:00"`. Asserte exatamente `08:00` na célula Total da linha criada (não apenas "existe linha").

## Estratégia de Teste

> Persona QA: source-under-test (Web + Backend) já existe; o teste é novo, sem red automático. Use o **controle negativo brownfield**: antes de fixar o assert final, escreva temporariamente o Total esperado **errado** (ex. `"07:00"`) e rode → tem que ficar **red** → corrija para `"08:00"`. Isso prova que o assert exercita o valor real, não passa por acaso.

**Skeleton canônico** (`apps/web/e2e/specs/smoke.spec.ts`):

```ts
import { test, expect } from "../fixtures"; // test estendido da task 1
import dayjs from "dayjs";

test("smoke: login -> privacidade -> cria jornada manual -> ve na lista", async ({ page }) => {
  // 1. Login pela UI
  await page.goto("/login");
  await page.getByLabel("E-mail").fill("terceiro.e2e@example.com");
  await page.getByLabel("Senha").fill("SenhaE2E!2026");
  await page.getByRole("button", { name: "Entrar" }).click();

  // 2. Privacidade (tolerante: pode já estar aceita)
  await page.waitForURL(/\/(privacidade|jornadas)/);
  if (page.url().includes("/privacidade")) {
    await page.getByLabel("Li e aceito os termos de privacidade").check();
    await page.getByRole("button", { name: "Continuar" }).click();
    await page.waitForURL(/\/jornadas$/);
  }
  await expect(page.getByRole("heading", { name: "Jornadas" })).toBeVisible();

  // 3. Criar jornada manual
  await page.getByRole("button", { name: /Nova jornada manual|Criar jornada manual/ }).click();
  await page.waitForURL(/\/jornadas\/manual$/);
  await expect(page.getByRole("heading", { name: "Nova Jornada Manual" })).toBeVisible();

  // data: dia 15 do mes corrente (sempre <= hoje se hoje>=15; senao escolher dia <= hoje)
  const dia = dayjs().date() >= 15 ? dayjs().date(15) : dayjs().subtract(1, "day");
  // Preencher DatePicker: abrir e digitar, ou usar o input textual do MUI DatePicker
  await page.getByLabel("Data").fill(dia.format("DD/MM/YYYY"));

  await page.getByLabel("Horário de início").fill("08:00");
  await page.getByLabel("Horário de saída do almoço").fill("12:00");
  await page.getByLabel("Horário de retorno do almoço").fill("13:00");
  await page.getByLabel("Horário de fim").fill("17:00");
  await page.getByLabel("Atividade").fill("Desenvolvimento de feature E2E");
  await page.getByLabel("Justificativa").fill("Smoke E2E");

  await page.getByRole("button", { name: "Salvar" }).click();

  // 4. Redireciona para o detalhe da jornada criada
  await page.waitForURL(/\/jornadas\/[0-9a-f-]{36}$/);
  await expect(page.getByText("AJUSTADA_MANUALMENTE")).toBeVisible();

  // 5. Voltar para a lista e ver a jornada com Total 08:00
  await page.getByRole("link", { name: "Jornadas" }).click();
  await page.waitForURL(/\/jornadas$/);
  const linha = page.getByRole("row", { name: new RegExp(dia.format("DD/MM/YYYY")) });
  await expect(linha).toBeVisible();
  await expect(linha.getByText("08:00")).toBeVisible(); // controle negativo: trocar p/ "07:00" deve ficar red
});
```

> **DatePicker MUI:** o input aceita texto via `fill` no campo com `aria-label="Data"` (formato `DD/MM/YYYY`). Se o `fill` não disparar o `onChange` do DatePicker de forma confiável, abra o popup do calendário (`page.getByLabel("Data")` → ícone) e selecione o dia via `page.getByRole("gridcell", { name: String(dia.date()) })`. Escolha a abordagem que ficar verde de forma estável e documente no retorno.

> **`docker compose down -v` antes do smoke:** o critério da fase exige que o smoke passe começando de um estado limpo. Como o backend usa o banco SQLite e2e (não Mailhog) e o Mailhog não é usado neste smoke, "estado limpo" aqui = banco e2e zerado + Terceiro semeado. O alvo `make web-e2e` (task 1) já zera `apps/api/data/e2e.sqlite` antes de rodar. Garanta que o spec **não** depende de jornadas pré-existentes — ele cria a própria jornada.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| ------- | ---- | --------- |
| `apps/web/e2e/specs/smoke.spec.ts` | Criar | 1 spec do caminho crítico login → privacidade → criar jornada manual → ver na lista, com assert do Total `08:00` |

> Se a task 1 deixou um `infra.spec.ts` de controle, ele permanece — não removê-lo.

### Detalhamento Técnico

1. Importar `test`/`expect` do fixtures estendido criado na task 1 (`../fixtures`). Se o fixture `seededPage` (login+privacidade prontos) já existir e for estável, o spec pode usá-lo para encurtar — mas como **este é o smoke**, prefira exercitar login e privacidade **pela UI** explicitamente (o smoke deve cobrir essas camadas de ponta a ponta, não atalhar por API).
2. Selecionar a data com um dia ≤ hoje (o DatePicker tem `maxDate=hoje`). Use dia 15 quando `hoje >= 15`; senão um dia anterior a hoje — garanta que o dia escolhido **não** caia em fim de semana só se isso afetar a criação (o endpoint manual aceita qualquer dia; sem restrição de fim de semana no manual). Não precisa evitar fim de semana.
3. Asserts mínimos obrigatórios (cada um falsificável):
   - URL chega em `/jornadas` após login+privacidade.
   - Após salvar, URL casa `/jornadas/<uuid>` e chip "AJUSTADA_MANUALMENTE" visível.
   - Na lista, a linha do dia criado exibe Total exatamente `08:00`.
4. Rodar `cd apps/web && npx playwright test smoke` e confirmar verde com o `webServer` real subindo backend+frontend e o banco e2e zerado.

**Refatoração:** Nenhuma no código de produção — o spec se adapta à UI existente.
