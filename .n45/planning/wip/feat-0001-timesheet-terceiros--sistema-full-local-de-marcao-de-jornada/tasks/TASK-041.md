---
checkpoint: null
complexity: M
created_at: "2026-05-29 12:37:39"
criteria:
    - done: false
      text: 'Onboarding: login + aceite de privacidade em banco semeado sem jornadas leva a /jornadas exibindo Nenhuma jornada registrada para este mes e CTA Criar jornada manual'
    - done: false
      text: 'Dia normal: jornada manual 08:00/12:00/13:00/17:00 aparece na lista com Total exatamente 08:00 e chip AJUSTADA_MANUALMENTE'
    - done: false
      test: cd apps/web && npx playwright test ajuste-manual
      text: 'Ajuste manual: editar fim 17:00->18:00 + justificativa >=5 chars vira status AJUSTADA_MANUALMENTE com Total recalculado para 09:00 (controle negativo 08:00 fica red)'
    - done: false
      text: 'Ajuste manual: accordion Historico de auditoria expandido mostra entrada com autor terceiro.e2e@example.com'
    - done: false
      text: 'Envio de relatorio: SMTP configurado para Mailhog (localhost:1025, STARTTLS off) + enviar mostra snackbar Relatorio enviado e chip SUCESSO no historico'
    - done: false
      test: cd apps/web && npx playwright test envio-relatorio
      text: 'Envio de relatorio: GET http://localhost:8025/api/v2/messages retorna total>=1 apos envio (controle negativo total 0 fica red)'
    - done: false
      text: Todas as journey specs passam com webServer real + Mailhog up (make smtp-up); sem mock de rede
deps:
    - TASK-039
    - TASK-040
id: TASK-041
linter: cd apps/web && npm run lint
n45_version: 0.2.0
persona: qa
phase: Phase 7 — E2E
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: pending
tests: cd apps/web && npx playwright test
title: 'Jornadas Completas E2E: specs Onboarding, Dia normal, Ajuste manual e Envio de relatorio (Mailhog real)'
updated_at: "2026-05-29 12:37:39"
---
## Contexto

Terceira e última task da Phase 7 — E2E. Depende da task 1 (Setup E2E: `playwright.config.ts`, `webServer`, seed, fixtures) e da task 2 (Smoke Test, que já provou o caminho crítico). Esta task escreve os **specs das jornadas completas** definidas no Quality Gate da Spec — cada uma é um fluxo contínuo de ponta a ponta exercitando navegador → Vite proxy → FastAPI → SQLite (e SMTP real via Mailhog no fluxo de relatório). Nenhum mock de rede; servidor real.

Os 4 fluxos do Quality Gate da Spec são "Onboarding completo", "Dia normal", "Ajuste manual" e "Envio de relatório". Como o cadastro do Terceiro e o registro automático das marcações são feitos pelo **Agente Desktop .NET (WPF)** — que o Playwright (browser) não consegue dirigir —, a cobertura E2E web cobre a parte web de cada fluxo:

- **Onboarding (web):** Terceiro já semeado via API (task 1) → login → aceitar privacidade → cair em `/jornadas` vazio com CTA. (A parte WPF do onboarding é coberta pelos testes xUnit do Agente, fora desta fase.)
- **Dia normal (representação web):** o "dia normal" real vem do Agente; a representação verificável na Web é a **jornada manual completa** (4 horários + atividade) aparecendo na listagem mensal com total e status corretos — equivalente ao resultado de um dia fechado.
- **Ajuste manual:** abrir o detalhe de uma jornada → editar um horário → justificar (≥5 chars) → status vira `AJUSTADA_MANUALMENTE` → entrada de auditoria visível no accordion.
- **Envio de relatório:** configurar SMTP apontando para o Mailhog → enviar relatório do mês → histórico de envios mostra `SUCESSO` → e-mail efetivamente recebido pelo Mailhog (verificado via API HTTP do Mailhog).

Estado atual relevante (fatos do código já entregue):

- **Mailhog** (via `make smtp-up`, `docker-compose.dev.yml`): SMTP em `localhost:1025` (sem auth, sem TLS), API/UI HTTP em `http://localhost:8025`. A API de mensagens: `GET http://localhost:8025/api/v2/messages` retorna `{ total, items: [...] }`; `DELETE http://localhost:8025/api/v1/messages` limpa a caixa.
- **Backend SMTP send** (`apps/api/app/modules/relatorios/smtp_send.py`): usa host/port da tabela `smtp_config` (configurada via `PUT /api/v1/smtp`); quando `use_starttls=false` não chama `starttls()`; quando username/senha vazios, o login é suprimido. Mailhog aceita conexão sem auth. Logo, configurar `host=localhost, port=1025, use_starttls=false` envia com sucesso ao Mailhog.
- **`POST /api/v1/relatorios/{mes}/enviar`** retorna `202` em sucesso e grava `HistoricoEnvioRelatorio(SUCESSO)`; retorna `422 code=SMTP_NOT_CONFIGURED` se `smtp_config` ausente. O envio exige PDF gerado: `GET /relatorios/{mes}` gera o PDF on-demand se ausente; e exige ≥1 jornada no mês (senão `/relatorios/{mes}/meta` dá 404 e a página mostra "Nenhuma jornada registrada para este mês").
- **Página `/relatorios`** (`apps/web/src/pages/Relatorios/RelatoriosPage.tsx`): DatePicker "Mês" com `default = mês anterior` e `maxDate = mês anterior`. Botão "Enviar agora" → abre `EnviarRelatorioDialog`. Diálogo: campo "Destinatário" (preenchido com `email_destinatario_relatorio`), botão "Enviar". Sucesso → snackbar `role="status"` com "Relatório enviado para <email>." Há também DataGrid "Histórico de envios" (colunas Quando | Destinatário | Status | Erro), com chip "SUCESSO"/"FALHA".
- **Página `/configuracoes/smtp`** (`SmtpConfigPage.tsx`): campos `label` "Host", "Porta", "Usuário", "Senha", Switch "STARTTLS", "From address"; botões "Testar conexão" e "Salvar"; snackbar `role="status"` "Configuração SMTP salva." O Switch STARTTLS vem ligado por default — para Mailhog é preciso **desligá-lo**.
- **Página `/jornadas/manual`**: já descrita na task 2 (DatePicker "Data" `maxDate=hoje`, 4 horários por `aria-label`, "Atividade", "Justificativa", "Salvar"). Aceita datas de meses anteriores (necessário para gerar relatório do mês anterior).
- **Detalhe `/jornadas/:id`** (`JornadaDetalhePage.tsx`): horários como TextField `type="time"` com `aria-label` "Horário de início"/etc., **editáveis somente** quando status é `FECHADA` ou `AJUSTADA_MANUALMENTE`. Botão "Salvar alterações" aparece só quando há mudança. Abre `JustificativaDialog` (input ≥5 chars + botão "Confirmar alterações"). Sucesso → snackbar "Jornada atualizada com sucesso." Accordion "Histórico de auditoria" (`HistoricoAuditoria.tsx`) carrega `GET /api/v1/auditoria` lazy ao expandir; cada entrada mostra autor + "Motivo: ..." + bloco "Antes/Depois". A jornada criada via manual nasce `AJUSTADA_MANUALMENTE`, portanto é editável.

## Comportamento Esperado

Cada fluxo é um teste contínuo. Os specs assumem o Terceiro semeado (task 1) e Mailhog up (o alvo `make web-e2e` sobe o Mailhog). O fluxo de relatório limpa o Mailhog no início (`DELETE /api/v1/messages`) para asserir exatamente a mensagem enviada por ele.

**Exemplos (entrada → saída esperada)** — valores reais que os specs asseguram:

| Entrada / Ação | Saída / Efeito esperado |
| -------------- | ----------------------- |
| **Onboarding:** login + aceitar privacidade num banco recém-semeado sem jornadas | `/jornadas` exibe "Nenhuma jornada registrada para este mês." e botão "Criar jornada manual" |
| **Dia normal:** criar jornada manual no mês corrente (08:00/12:00/13:00/17:00) | Linha na DataGrid com Total `08:00` e chip "AJUSTADA_MANUALMENTE" |
| **Ajuste manual:** abrir jornada `AJUSTADA_MANUALMENTE`, mudar "Horário de fim" de `17:00` para `18:00`, "Salvar alterações" → justificar "Correcao do horario de fim" → "Confirmar alterações" | snackbar "Jornada atualizada com sucesso."; Total recalculado para `09:00` ((12−08)+(18−13)=4+5=9h); accordion "Histórico de auditoria" expandido mostra ≥1 entrada com autor `terceiro.e2e@example.com` |
| **Envio de relatório:** criar jornada no mês anterior; em `/configuracoes/smtp` preencher Host=`localhost`, Porta=`1025`, desligar STARTTLS, From=`from.e2e@example.com`, Usuário e Senha vazios, "Salvar"; ir a `/relatorios` (mês = anterior), "Enviar agora" → "Enviar" | snackbar "Relatório enviado para <email>."; DataGrid "Histórico de envios" tem linha com chip `SUCESSO`; `GET http://localhost:8025/api/v2/messages` retorna `total >= 1` com destinatário `destinatario.e2e@example.com` |

> **Totais (asserts exatos, falsificáveis):** dia normal = `08:00`; após ajuste do fim para 18:00 = `09:00`. Asserte os valores exatos, não "existe linha".

## Estratégia de Teste

> Persona QA: source-under-test (Web + Backend + SMTP) já existe; teste novo, sem red automático. Aplique **controle negativo brownfield** em pelo menos o assert numérico de cada fluxo: escreva o valor esperado **errado** primeiro (ex. Total `08:00` em vez de `09:00` no ajuste; `total: 0` no Mailhog), rode → tem que ficar **red** → corrija. Teste que nunca foi red é tautológico.

Organização: **um arquivo de spec por jornada** em `apps/web/e2e/specs/`, todos serial (a config da task 1 já força `workers: 1`, banco single-tenant compartilhado). Como os specs compartilham o mesmo Terceiro e banco, **isole por data**: cada spec cria sua jornada num dia distinto para não colidir (a `UNIQUE(terceiro_id, data)` rejeita 2 jornadas no mesmo dia com `409`). Use dias diferentes por spec (ex. ajuste usa dia 10; dia normal usa dia 12; relatório usa um dia do mês anterior).

**Skeleton canônico** (adaptar por fluxo; reusar o helper de login+privacidade do fixtures da task 1):

```ts
import { test, expect } from "../fixtures";
import dayjs from "dayjs";

const MAILHOG = "http://localhost:8025";

async function loginEPrivacidade(page) {
  await page.goto("/login");
  await page.getByLabel("E-mail").fill("terceiro.e2e@example.com");
  await page.getByLabel("Senha").fill("SenhaE2E!2026");
  await page.getByRole("button", { name: "Entrar" }).click();
  await page.waitForURL(/\/(privacidade|jornadas)/);
  if (page.url().includes("/privacidade")) {
    await page.getByLabel("Li e aceito os termos de privacidade").check();
    await page.getByRole("button", { name: "Continuar" }).click();
  }
  await page.waitForURL(/\/jornadas$/);
}

async function criarJornadaManual(page, dataYmd, [h1, h2, h3, h4], atividade, motivo) {
  await page.getByRole("button", { name: /Nova jornada manual|Criar jornada manual/ }).click();
  await page.waitForURL(/\/jornadas\/manual$/);
  await page.getByLabel("Data").fill(dayjs(dataYmd).format("DD/MM/YYYY"));
  await page.getByLabel("Horário de início").fill(h1);
  await page.getByLabel("Horário de saída do almoço").fill(h2);
  await page.getByLabel("Horário de retorno do almoço").fill(h3);
  await page.getByLabel("Horário de fim").fill(h4);
  await page.getByLabel("Atividade").fill(atividade);
  await page.getByLabel("Justificativa").fill(motivo);
  await page.getByRole("button", { name: "Salvar" }).click();
  await page.waitForURL(/\/jornadas\/[0-9a-f-]{36}$/);
  return page.url().split("/").pop();
}

// Exemplo — fluxo Ajuste manual (controle negativo: trocar 09:00 -> 08:00 deve ficar red)
test("ajuste manual: edita fim, justifica, vira AJUSTADA + auditoria", async ({ page }) => {
  await loginEPrivacidade(page);
  const dia = dayjs().date() >= 10 ? dayjs().date(10) : dayjs().subtract(2, "day");
  await criarJornadaManual(page, dia.format("YYYY-MM-DD"),
    ["08:00", "12:00", "13:00", "17:00"], "Atividade do dia E2E", "Criacao E2E");
  // já está no detalhe (AJUSTADA_MANUALMENTE → editável)
  await page.getByLabel("Horário de fim").fill("18:00");
  await page.getByRole("button", { name: "Salvar alterações" }).click();
  await page.getByRole("textbox").last().fill("Correcao do horario de fim"); // input do JustificativaDialog
  await page.getByRole("button", { name: "Confirmar alterações" }).click();
  await expect(page.getByText("Jornada atualizada com sucesso.")).toBeVisible();
  await expect(page.getByText(/Total: 09:00/)).toBeVisible();
  // auditoria
  await page.getByText("Histórico de auditoria").click();
  await expect(page.getByText("terceiro.e2e@example.com").first()).toBeVisible();
});

// Exemplo — fluxo Envio de relatório (controle negativo: total Mailhog 0 deve ficar red)
test("envio de relatorio: SMTP Mailhog -> enviar -> SUCESSO + email recebido", async ({ page, request }) => {
  await request.delete(`${MAILHOG}/api/v1/messages`); // limpa caixa
  await loginEPrivacidade(page);
  const diaAnterior = dayjs().subtract(1, "month").date(15);
  await criarJornadaManual(page, diaAnterior.format("YYYY-MM-DD"),
    ["08:00", "12:00", "13:00", "17:00"], "Atividade mes anterior E2E", "Criacao relatorio E2E");
  // configurar SMTP -> Mailhog
  await page.goto("/configuracoes/smtp");
  await page.getByLabel("Host").fill("localhost");
  await page.getByLabel("Porta").fill("1025");
  // STARTTLS vem ligado: desligar
  const starttls = page.getByRole("checkbox", { name: "STARTTLS" });
  if (await starttls.isChecked()) await starttls.uncheck();
  await page.getByLabel("From address").fill("from.e2e@example.com");
  await page.getByRole("button", { name: "Salvar" }).click();
  await expect(page.getByText("Configuração SMTP salva.")).toBeVisible();
  // enviar relatorio do mes anterior
  await page.goto("/relatorios");
  await page.getByRole("button", { name: "Enviar agora" }).click();
  await page.getByRole("button", { name: "Enviar" }).click();
  await expect(page.getByText(/Relatório enviado para/)).toBeVisible();
  // historico SUCESSO
  await expect(page.getByText("SUCESSO").first()).toBeVisible();
  // Mailhog recebeu
  const res = await request.get(`${MAILHOG}/api/v2/messages`);
  const body = await res.json();
  expect(body.total).toBeGreaterThanOrEqual(1);
});
```

> **Seletores incertos a confirmar no source ao implementar:** (a) o input do `JustificativaDialog` (`apps/web/src/pages/JornadaDetalhe/JustificativaDialog.tsx` — ler para achar o label/role exato; o skeleton usa `getByRole("textbox").last()` como fallback); (b) o Switch STARTTLS é renderizado como `role="checkbox"` (MUI Switch) com label "STARTTLS" — confirme; (c) o campo total no detalhe é renderizado como `Total: <hh:mm>` num `<Typography>` — confirme o texto. Ajuste os seletores ao que existe; não invente.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| ------- | ---- | --------- |
| `apps/web/e2e/specs/onboarding.spec.ts` | Criar | Login + aceitar privacidade → `/jornadas` vazio com CTA "Criar jornada manual" |
| `apps/web/e2e/specs/dia-normal.spec.ts` | Criar | Criar jornada manual completa → aparece na lista com Total `08:00` e chip `AJUSTADA_MANUALMENTE` |
| `apps/web/e2e/specs/ajuste-manual.spec.ts` | Criar | Editar fim 17:00→18:00, justificar, status `AJUSTADA_MANUALMENTE`, Total `09:00`, auditoria com autor |
| `apps/web/e2e/specs/envio-relatorio.spec.ts` | Criar | Jornada no mês anterior → configurar SMTP (Mailhog, STARTTLS off) → enviar → histórico `SUCESSO` + e-mail no Mailhog |
| `apps/web/e2e/helpers.ts` | Criar | Helpers compartilhados `loginEPrivacidade`, `criarJornadaManual`, constante `MAILHOG` (extrair do skeleton para evitar duplicação) |

> Se os helpers já couberem em `apps/web/e2e/fixtures.ts` (task 1), colocá-los lá em vez de criar `helpers.ts` — uma fonte única. Decida e documente.

### Detalhamento Técnico

1. **Isolamento por data entre specs:** cada spec cria a jornada num dia distinto (`onboarding` não cria; `dia-normal` dia 12; `ajuste-manual` dia 10; `envio-relatorio` dia 15 do mês anterior). Se um dia escolhido for futuro (não há nesse esquema) ou já existir jornada (re-run sem zerar banco), o `POST manual` retorna `409`; o alvo `make web-e2e` zera `apps/api/data/e2e.sqlite` antes de rodar a suíte, então em CI o banco está limpo. Não escreva spec que dependa de jornada pré-existente de outro spec.
2. **Ajuste manual — Total recalculado:** (12:00−08:00)+(18:00−13:00) = 4h+5h = 9h → `formatTotal` exibe `09:00`. Assert exato em `Total: 09:00` na tela de detalhe após o save.
3. **Auditoria:** o `PUT /api/v1/jornadas/{id}` grava `log_auditoria` com `autor = email_contato` do Terceiro (`terceiro.e2e@example.com`). Após salvar, expandir o accordion "Histórico de auditoria" e asserir que o autor aparece. O accordion carrega lazy ao expandir — aguarde o texto aparecer (`getByText("terceiro.e2e@example.com")`).
4. **Envio de relatório — Mailhog:**
   - Limpar Mailhog no início: `request.delete("http://localhost:8025/api/v1/messages")`.
   - Configurar SMTP via UI: Host `localhost`, Porta `1025`, STARTTLS **off**, From `from.e2e@example.com`, Usuário/Senha vazios. Salvar e aguardar "Configuração SMTP salva."
   - A página `/relatorios` usa `mês = anterior` por default — a jornada criada no dia 15 do mês anterior garante que `/relatorios/{mês}/meta` não dê 404 e o "Enviar agora" funcione.
   - Após enviar: asserir snackbar "Relatório enviado para ...", chip `SUCESSO` no histórico, e `GET http://localhost:8025/api/v2/messages` com `total >= 1`. Opcionalmente asserir que o destinatário (`destinatario.e2e@example.com`, vindo do `email_destinatario_relatorio` do Terceiro semeado) está em `items[0].Content.Headers.To` ou `items[0].To`.
   - Pré-condição da fase: cada spec faz pre-flight implícito porque o `webServer` só libera após `/api/v1/ready` 200; o Mailhog é exigência do alvo `make web-e2e`. Se o Mailhog não estiver up, o spec de envio falha com erro de conexão SMTP (histórico FALHA) — isso é o comportamento esperado de ambiente; documente no retorno que `make smtp-up` (ou `make web-e2e`) é obrigatório.
5. **Executor DEVE rodar os testes e garantir que todos passam antes de retornar. Teste falhando = task não concluída.** Rode `cd apps/web && npx playwright test` com o Mailhog up (`make smtp-up`) e o banco e2e zerado.

**Refatoração:** Nenhuma no código de produção — os specs se adaptam à UI existente.
