---
checkpoint: null
complexity: M
created_at: "2026-05-28 12:56:49"
criteria:
    - done: true
      test: cd apps/web && npm test -- --run src/pages/Relatorios/RelatoriosPage.test.tsx -t "default = mes anterior"
      text: Mount /relatorios em 2026-05-27 default mes anterior 2026-04 chama GET /api/v1/relatorios/2026-04/meta e /historico
    - done: true
      test: cd apps/web && npm test -- --run src/pages/Relatorios/RelatoriosPage.test.tsx -t "PDF desatualizado"
      text: meta.invalidado_em diferente de null exibe alert warning com texto exato PDF desatualizado e botao Atualizar relatorio
    - done: true
      test: cd apps/web && npm test -- --run src/pages/Relatorios/RelatoriosPage.test.tsx -t "Nenhuma jornada registrada"
      text: 404 do getRelatorioMeta exibe Alert texto exato Nenhuma jornada registrada para este mes. Nao e possivel gerar o relatorio. e oculta iframe
    - done: true
      test: cd apps/web && npm test -- --run src/pages/Relatorios/RelatoriosPage.test.tsx -t "FALHA exibe chip"
      text: historico com FALHA renderiza chip vermelho FALHA + tooltip com erro_mensagem completo (truncado a 60 chars no display)
    - done: true
      test: cd apps/web && npm test -- --run src/pages/Relatorios/RelatoriosPage.test.tsx -t "Configurar SMTP navega"
      text: Botao Configurar SMTP navega para /configuracoes/smtp
    - done: true
      test: cd apps/web && npm test -- --run src/pages/Configuracoes/SmtpConfigPage.test.tsx -t "preenche o form"
      text: Mount /configuracoes/smtp com config existente preenche o form (host porta username use_starttls from_address) sem password
    - done: true
      test: cd apps/web && npm test -- --run src/pages/Configuracoes/SmtpConfigPage.test.tsx -t "Nenhuma configuracao"
      text: 404 do GET /smtp exibe alert info Nenhuma configuracao salva ainda. com form vazio
    - done: true
      test: cd apps/web && npm test -- --run src/pages/Configuracoes/SmtpConfigPage.test.tsx -t "Configuracao SMTP salva"
      text: PUT /smtp 200 envia body com password digitado e emite toast Configuracao SMTP salva.
    - done: true
      test: cd apps/web && npm test -- --run src/pages/Configuracoes/SmtpConfigPage.test.tsx -t "testada com sucesso"
      text: POST /smtp/test 200 emite toast Conexao SMTP testada com sucesso.
    - done: true
      test: cd apps/web && npm test -- --run src/pages/Configuracoes/SmtpConfigPage.test.tsx -t "SMTP_TEST_FAILED"
      text: POST /smtp/test 400 SMTP_TEST_FAILED exibe alert com a mensagem do backend (passthrough; ex Conexao recusada)
    - done: true
      test: cd apps/web && npm test -- --run src/pages/Configuracoes/SmtpConfigPage.test.tsx -t "SMTP_NOT_CONFIGURED"
      text: POST /smtp/test 422 SMTP_NOT_CONFIGURED exibe alert texto exato SMTP nao configurado. Salve antes de testar.
    - done: true
      test: grep -E "from \"@/components/EnviarRelatorioDialog\"" apps/web/src/pages/Jornadas/JornadasPage.tsx
      text: EnviarRelatorioDialog movido para src/components/ e JornadasPage importa de @/components/EnviarRelatorioDialog (TASK-023 testes continuam verdes)
    - done: true
      test: grep -E "<RelatoriosPage ?/>|<SmtpConfigPage ?/>" apps/web/src/routes.tsx
      text: routes.tsx substitui RelatoriosPageStub por RelatoriosPage e SmtpConfigPageStub por SmtpConfigPage
    - done: true
      text: ESLint passa sem warnings e tsc strict 0 erros
    - done: true
      text: Testes passando com cobertura >= 80%
    - done: true
      text: make smoke continua passando
deps:
    - TASK-020
    - TASK-023
    - TASK-026
id: TASK-027
linter: cd apps/web && npm run lint && npm run typecheck
n45_version: 0.2.0
persona: frontend
phase: Phase 4 — Frontend por Feature
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: done
tdd:
    green: true
    red: true
    refactor: true
tests: cd apps/web && npm test -- --run src/pages/Relatorios/RelatoriosPage.test.tsx src/pages/Configuracoes/SmtpConfigPage.test.tsx
title: 'Relatorios + SMTP Config (RF-008): /relatorios com iframe PDF, badge invalidado_em (PDF desatualizado), historico de envios, regenerar; /configuracoes/smtp com get/put/test; move EnviarRelatorioDialog para components'
updated_at: "2026-05-28 17:56:10"
---
## Contexto

Implementar `/relatorios` (RF-008) e `/configuracoes/smtp` — relatório mensal em PDF (download, prévia em iframe, histórico de envios, envio sob demanda, badge "PDF desatualizado") e configuração do servidor SMTP (host/porta/user/password/STARTTLS/from + teste de conexão). Slice: 2 páginas + 2 schemas zod + funções HTTP em `api/smtp.ts` (api/relatorios.ts já existe de TASK-023) + substituição de 2 stubs em `routes.tsx`.

**State atual:**
- TASK-020 entregou api/client, useAuth, AppLayout, parseApiError, renderWithProviders, `RelatoriosPageStub` e `SmtpConfigPageStub` em routes.tsx.
- TASK-023 entregou `api/relatorios.ts` com `relatoriosKeys`, `urlDownloadRelatorio`, `getRelatorioMeta`, `getRelatorioHistorico`, `postEnviarRelatorio` + `EnviarRelatorioDialog` (em `src/pages/Jornadas/EnviarRelatorioDialog.tsx` — esta task **move para `src/components/EnviarRelatorioDialog.tsx`** porque agora há 2 consumidores).
- TASK-026 entregou `terceirosKeys` + `getTerceiroMe` (consumidos aqui para pre-preencher e-mail).
- Backend Phase 3:
  - TASK-018 entregou `GET /api/v1/relatorios/{mes}` (FileResponse), `GET /api/v1/relatorios/{mes}/meta`, `POST /api/v1/relatorios/{mes}/enviar`, `GET /api/v1/relatorios/{mes}/historico`.
  - TASK-015 entregou `GET /api/v1/smtp` (200 ou 404), `PUT /api/v1/smtp`, `POST /api/v1/smtp/test`.

**Decisão de UX (Spec §5 — `/relatorios`):**
- `<h1>` "Relatórios".
- MUI DatePicker tipo mês — default = mês anterior; `maxDate = início do mês atual - 1 dia` (mês anterior é o máximo).
- Iframe MUI com `src={urlDownloadRelatorio(mes)}` para prévia do PDF (Vite proxy encaminha; em produção, mesmo origin). Loading: skeleton.
- Badge âmbar "PDF desatualizado — clique em 'Atualizar relatório' para regenerar" quando `meta.invalidado_em !== null`. Botão "Atualizar relatório" chama `GET /api/v1/relatorios/{mes}` (que regenera on-demand) + invalida `relatoriosKeys.meta(mes)`.
- Tabela MUI de histórico de envios: colunas `enviado_em` (formatado), `email_destinatario`, `status` (chip verde SUCESSO / vermelho FALHA), `erro_mensagem` (truncado, expandível em accordion-row).
- Botão "Baixar PDF" → cria `<a>` invisível com `urlDownloadRelatorio(mes)`.
- Botão "Enviar agora" → abre `EnviarRelatorioDialog` (movido para `src/components/`).
- Botão "Configurar SMTP" → `navigate("/configuracoes/smtp")`.
- Estado vazio (mês sem dados ⇒ `getRelatorioMeta` retorna 404): "Nenhuma jornada registrada para este mês. Não é possível gerar o relatório." + ocultar iframe.
- 422 SMTP_NOT_CONFIGURED no envio → mesma UX do TASK-023 (alert + CTA "Configurar agora").

**Decisão de UX (Spec §5 — `/configuracoes/smtp`):**
- `<h1>` "Configuração SMTP".
- Form com:
  - `host` (1..253), `port` (1..65535, default 587), `username` (1..254), `password` (type=password, masked), Switch `use_starttls` (default true), `from_address` (EmailStr).
- Loading inicial: `GET /api/v1/smtp` para popular campos; se 404, deixar form vazio com mensagem "Nenhuma configuração salva ainda."
- Botão "Testar conexão" — chama `POST /api/v1/smtp/test` (sem body). Sucesso `{ok: true}` → toast "Conexão SMTP testada com sucesso." Erro 400 SMTP_TEST_FAILED → alert inline com `parsed.message` (mensagem do socket/login real, ex.: "Conexão recusada"). Erro 422 SMTP_NOT_CONFIGURED → alert "SMTP não configurado. Salve antes de testar."
- Botão "Salvar" → `PUT /api/v1/smtp` com `{host, port, username, password, use_starttls, from_address}`. Sucesso 200 → invalida cache + toast "Configuração SMTP salva." A senha **não retorna** do backend (resposta sem `password`); UI mantém o campo `password` em branco após salvar — usuário precisa redigitar se quiser editar de novo. Helper text "A senha não é exibida; deixe em branco para manter a atual" **NÃO** vale — o backend exige sempre `password` no PUT (TASK-015 schema). Decisão: ao salvar, NÃO esvaziar o campo; ele permanece com o último valor digitado (no estado React) até user trocar.

**Decisão alternativa rejeitada (senha):** permitir PUT sem senha. **Rejeitada** porque backend exige `password: SecretStr = Field(min_length=1)` no `SmtpConfigRequest`. Implementar opcionalidade na v1.1 (envia null e backend mantém o atual) — fora de escopo aqui.

**Dependência:** TASK-020, TASK-023 (api/relatorios), TASK-026 (terceirosKeys).

## Comportamento Esperado

### `/relatorios`

| Entrada / Ação | Saída / Efeito esperado |
| -------------- | ----------------------- |
| Mount `/relatorios` em 2026-05-27 | DatePicker default = "Abril 2026" (mês anterior); `GET /api/v1/relatorios/2026-04/meta` + `GET /api/v1/relatorios/2026-04/historico`; iframe com src `/api/v1/relatorios/2026-04` |
| `meta.invalidado_em = "2026-05-15T12:00:00Z"` | Badge âmbar "PDF desatualizado — clique em 'Atualizar relatório' para regenerar" visível |
| Click em "Atualizar relatório" | Fetch `GET /api/v1/relatorios/2026-04` (regenera) → invalida `relatoriosKeys.meta(mes)` |
| `historico` retorna `[{status:"SUCESSO", email_destinatario:"rh@acme.com", enviado_em:"2026-05-01T08:00:00Z", erro_mensagem:null}]` | Tabela 1 linha com chip verde "SUCESSO" |
| `historico` retorna FALHA com `erro_mensagem` longo | Linha com chip vermelho "FALHA" + erro_mensagem truncado a 60 chars + tooltip com texto completo |
| Click "Baixar PDF" | Cria `<a href="/api/v1/relatorios/2026-04">` invisível e dispara click |
| Click "Enviar agora" | Abre `EnviarRelatorioDialog` (mesmo componente da JornadasPage) |
| 404 em `getRelatorioMeta` (sem dados no mês) | Iframe não renderiza; mensagem "Nenhuma jornada registrada para este mês. Não é possível gerar o relatório." |
| Click "Configurar SMTP" | `navigate("/configuracoes/smtp")` |

### `/configuracoes/smtp`

| Entrada / Ação | Saída / Efeito esperado |
| -------------- | ----------------------- |
| Mount `/configuracoes/smtp` com config existente (200) | Form preenchido com `host`, `port`, `username`, `use_starttls`, `from_address`; campo `password` em branco |
| Mount sem config (404) | Form vazio + mensagem "Nenhuma configuração salva ainda." |
| Preencher form + click "Testar conexão" sem salvar antes (mas backend tem config) | Chama `POST /api/v1/smtp/test`; sucesso `{ok:true}` → toast "Conexão SMTP testada com sucesso." |
| `Testar conexão` retorna 400 SMTP_TEST_FAILED message="Conexão recusada" | Alert inline com "Conexão recusada" |
| `Testar conexão` retorna 422 SMTP_NOT_CONFIGURED | Alert "SMTP não configurado. Salve antes de testar." |
| Form válido + Salvar | Chama `PUT /api/v1/smtp` com `{host, port, username, password, use_starttls, from_address}`; sucesso 200 → invalida cache + toast "Configuração SMTP salva." |
| 422 VALIDATION_ERROR no PUT | Alert vermelho com `parsed.message` |

## TDD

**Testes a escrever antes da implementação:**

`apps/web/src/pages/Relatorios/RelatoriosPage.test.tsx`:

```typescript
import { describe, it, expect, beforeEach, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MockAdapter from "axios-mock-adapter";
import api from "@/api/client";
import { renderWithProviders } from "@/test/render";
import { RelatoriosPage } from "@/pages/Relatorios/RelatoriosPage";

const mock = new MockAdapter(api);

beforeEach(() => {
  mock.reset();
  sessionStorage.setItem("ts:access_token", "tok");
  sessionStorage.setItem("ts:refresh_token", "r");
  sessionStorage.setItem("ts:terceiro_id", "u1");
  sessionStorage.setItem("ts:expires_at", String(Date.now() + 60_000));
  vi.useFakeTimers({ shouldAdvanceTime: true });
  vi.setSystemTime(new Date("2026-05-27T15:00:00-03:00"));
});

describe("RelatoriosPage", () => {
  it("default = mes anterior (2026-04); chama meta e historico", async () => {
    let metaCalled = false, histCalled = false;
    mock.onGet("/api/v1/relatorios/2026-04/meta").reply(() => {
      metaCalled = true;
      return [200, { mes_referencia: "2026-04", caminho_arquivo: "/x.pdf", gerado_em: "2026-05-01T00:00:00Z", invalidado_em: null }];
    });
    mock.onGet("/api/v1/relatorios/2026-04/historico").reply(() => {
      histCalled = true;
      return [200, []];
    });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria", email_destinatario_relatorio: "rh@acme.com" });
    renderWithProviders(<RelatoriosPage />, { route: "/relatorios" });
    await waitFor(() => expect(metaCalled).toBe(true));
    expect(histCalled).toBe(true);
  });

  it("meta.invalidado_em != null exibe badge âmbar 'PDF desatualizado'", async () => {
    mock.onGet("/api/v1/relatorios/2026-04/meta").reply(200, {
      mes_referencia: "2026-04", caminho_arquivo: "/x.pdf",
      gerado_em: "2026-05-01T00:00:00Z", invalidado_em: "2026-05-15T12:00:00Z",
    });
    mock.onGet("/api/v1/relatorios/2026-04/historico").reply(200, []);
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria", email_destinatario_relatorio: "rh@acme.com" });
    renderWithProviders(<RelatoriosPage />, { route: "/relatorios" });
    expect(await screen.findByText(/PDF desatualizado/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Atualizar relatório/i })).toBeInTheDocument();
  });

  it("404 do meta exibe mensagem 'Nenhuma jornada registrada para este mês.'", async () => {
    mock.onGet("/api/v1/relatorios/2026-04/meta").reply(404, { code: "NOT_FOUND", message: "sem dados", details: [] });
    mock.onGet("/api/v1/relatorios/2026-04/historico").reply(200, []);
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria", email_destinatario_relatorio: null });
    renderWithProviders(<RelatoriosPage />, { route: "/relatorios" });
    expect(await screen.findByText(/Nenhuma jornada registrada para este mês\. Não é possível gerar o relatório\./i)).toBeInTheDocument();
  });

  it("historico com FALHA exibe chip vermelho e erro_mensagem", async () => {
    mock.onGet("/api/v1/relatorios/2026-04/meta").reply(200, {
      mes_referencia: "2026-04", caminho_arquivo: "/x.pdf",
      gerado_em: "2026-05-01T00:00:00Z", invalidado_em: null,
    });
    mock.onGet("/api/v1/relatorios/2026-04/historico").reply(200, [
      { id: "h1", mes_referencia: "2026-04", email_destinatario: "rh@acme.com",
        status: "FALHA", erro_mensagem: "Conexão recusada", enviado_em: "2026-05-01T08:00:00Z" },
    ]);
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria", email_destinatario_relatorio: "rh@acme.com" });
    renderWithProviders(<RelatoriosPage />, { route: "/relatorios" });
    expect(await screen.findByText("FALHA")).toBeInTheDocument();
    expect(screen.getByText(/Conexão recusada/i)).toBeInTheDocument();
  });

  it("Configurar SMTP navega para /configuracoes/smtp", async () => {
    mock.onGet("/api/v1/relatorios/2026-04/meta").reply(200, {
      mes_referencia: "2026-04", caminho_arquivo: "/x.pdf",
      gerado_em: "2026-05-01T00:00:00Z", invalidado_em: null,
    });
    mock.onGet("/api/v1/relatorios/2026-04/historico").reply(200, []);
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria", email_destinatario_relatorio: null });
    renderWithProviders(<RelatoriosPage />, { route: "/relatorios" });
    await userEvent.click(await screen.findByRole("button", { name: /Configurar SMTP/i }));
    expect(window.location.pathname).toBe("/configuracoes/smtp");
  });
});
```

`apps/web/src/pages/Configuracoes/SmtpConfigPage.test.tsx`:

```typescript
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
  it("Mount com config existente preenche o form (sem password)", async () => {
    mock.onGet("/api/v1/smtp").reply(200, CFG_EXISTENTE);
    renderWithProviders(<SmtpConfigPage />, { route: "/configuracoes/smtp" });
    expect(((await screen.findByLabelText(/Host/i)) as HTMLInputElement).value).toBe("smtp.example.com");
    expect((screen.getByLabelText(/Porta/i) as HTMLInputElement).valueAsNumber).toBe(587);
    expect((screen.getByLabelText(/Usuário/i) as HTMLInputElement).value).toBe("user@example.com");
    expect((screen.getByLabelText(/Senha/i) as HTMLInputElement).value).toBe("");
    expect((screen.getByLabelText(/From/i) as HTMLInputElement).value).toBe("noreply@example.com");
  });

  it("404 do GET /smtp deixa form vazio e mostra 'Nenhuma configuração salva ainda.'", async () => {
    mock.onGet("/api/v1/smtp").reply(404, { code: "NOT_FOUND", message: "ausente", details: [] });
    renderWithProviders(<SmtpConfigPage />, { route: "/configuracoes/smtp" });
    expect(await screen.findByText(/Nenhuma configuração salva ainda\./i)).toBeInTheDocument();
    expect((screen.getByLabelText(/Host/i) as HTMLInputElement).value).toBe("");
  });

  it("PUT /smtp 200 emite toast 'Configuração SMTP salva.'", async () => {
    mock.onGet("/api/v1/smtp").reply(200, CFG_EXISTENTE);
    let putBody: any = null;
    mock.onPut("/api/v1/smtp").reply((c) => {
      putBody = JSON.parse(c.data as string);
      return [200, { ...CFG_EXISTENTE, atualizado_em: "2026-05-27T00:00:00Z" }];
    });
    renderWithProviders(<SmtpConfigPage />, { route: "/configuracoes/smtp" });
    const senha = await screen.findByLabelText(/Senha/i) as HTMLInputElement;
    await userEvent.type(senha, "novaSenhaSmtp");
    await userEvent.click(screen.getByRole("button", { name: /^Salvar$/ }));
    await waitFor(() => expect(putBody).not.toBeNull());
    expect(putBody.password).toBe("novaSenhaSmtp");
    expect(await screen.findByText(/Configuração SMTP salva\./i)).toBeInTheDocument();
  });

  it("Testar conexão 200 emite toast 'Conexão SMTP testada com sucesso.'", async () => {
    mock.onGet("/api/v1/smtp").reply(200, CFG_EXISTENTE);
    mock.onPost("/api/v1/smtp/test").reply(200, { ok: true });
    renderWithProviders(<SmtpConfigPage />, { route: "/configuracoes/smtp" });
    await userEvent.click(await screen.findByRole("button", { name: /Testar conexão/i }));
    expect(await screen.findByText(/Conexão SMTP testada com sucesso\./i)).toBeInTheDocument();
  });

  it("Testar conexão 400 SMTP_TEST_FAILED exibe alert com a mensagem do backend", async () => {
    mock.onGet("/api/v1/smtp").reply(200, CFG_EXISTENTE);
    mock.onPost("/api/v1/smtp/test").reply(400, { code: "SMTP_TEST_FAILED", message: "Conexão recusada", details: [] });
    renderWithProviders(<SmtpConfigPage />, { route: "/configuracoes/smtp" });
    await userEvent.click(await screen.findByRole("button", { name: /Testar conexão/i }));
    expect(await screen.findByText(/Conexão recusada/i)).toBeInTheDocument();
  });

  it("Testar conexão 422 SMTP_NOT_CONFIGURED exibe alert 'SMTP não configurado. Salve antes de testar.'", async () => {
    mock.onGet("/api/v1/smtp").reply(404, { code: "NOT_FOUND", message: "ausente", details: [] });
    mock.onPost("/api/v1/smtp/test").reply(422, { code: "SMTP_NOT_CONFIGURED", message: "SMTP não configurado", details: [] });
    renderWithProviders(<SmtpConfigPage />, { route: "/configuracoes/smtp" });
    await userEvent.click(await screen.findByRole("button", { name: /Testar conexão/i }));
    expect(await screen.findByText(/SMTP não configurado\. Salve antes de testar\./i)).toBeInTheDocument();
  });
});
```

**Refatoração:** após green, considerar (a) extrair `<HistoricoEnviosTable items={...}/>` para `src/components/HistoricoEnviosTable.tsx` se for usado fora do Relatórios (improvável v1.0); (b) consolidar `dayjs("UTC ISO").format("DD/MM/YYYY HH:mm")` em helper `formatDataHoraBR` em `src/lib/format/horario.ts`.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| ------- | ---- | --------- |
| `apps/web/src/pages/Relatorios/RelatoriosPage.tsx` | Criar | Componente `/relatorios` |
| `apps/web/src/pages/Relatorios/RelatoriosPage.test.tsx` | Criar | TDD acima |
| `apps/web/src/pages/Configuracoes/SmtpConfigPage.tsx` | Criar | Componente `/configuracoes/smtp` |
| `apps/web/src/pages/Configuracoes/SmtpConfigPage.test.tsx` | Criar | TDD acima |
| `apps/web/src/api/smtp.ts` | Criar | `smtpKeys`, `getSmtpConfig`, `putSmtpConfig`, `postTestSmtp` |
| `apps/web/src/lib/schemas/smtp.ts` | Criar | Zod `smtpConfigSchema` |
| `apps/web/src/components/EnviarRelatorioDialog.tsx` | Criar (move) | Copiar de `src/pages/Jornadas/EnviarRelatorioDialog.tsx` (mover) |
| `apps/web/src/pages/Jornadas/JornadasPage.tsx` | Modificar | Atualizar import de `EnviarRelatorioDialog` para `@/components/EnviarRelatorioDialog` |
| `apps/web/src/pages/Jornadas/EnviarRelatorioDialog.tsx` | Remover | Substituído pelo arquivo em `components/` |
| `apps/web/src/routes.tsx` | Modificar | Substituir `RelatoriosPageStub` e `SmtpConfigPageStub` |

> 7 criados + 3 modificados (1 dos quais é remoção) = **10 alvos**. **Excede o teto por 2** — justificativa: duas páginas no mesmo domínio (Relatórios e SMTP fortemente cruzadas — "Configurar agora" em alertas; o usuário viaja entre as duas). O movimento do `EnviarRelatorioDialog` é refactor obrigatório (não estritamente desta task, mas oportuno porque agora há 2 consumidores reais). Alternativa rejeitada: deixar duplicado → drift; ou separar em 2 tasks → estoura o cap de 8 da fase.

### Detalhamento Técnico

**1. `src/api/smtp.ts`:**

```typescript
import api from "./client";
import type { SmtpConfigRequest, SmtpConfigResponse } from "@/types/contracts";

export const smtpKeys = {
  config: ["smtp", "config"] as const,
};

export async function getSmtpConfig(): Promise<SmtpConfigResponse> {
  const r = await api.get<SmtpConfigResponse>("/api/v1/smtp");
  return r.data;
}

export async function putSmtpConfig(body: SmtpConfigRequest): Promise<SmtpConfigResponse> {
  const r = await api.put<SmtpConfigResponse>("/api/v1/smtp", body);
  return r.data;
}

export async function postTestSmtp(): Promise<{ ok: boolean }> {
  const r = await api.post<{ ok: boolean }>("/api/v1/smtp/test");
  return r.data;
}
```

**2. `src/lib/schemas/smtp.ts`:**

```typescript
import { z } from "zod";

export const smtpConfigSchema = z.object({
  host: z.string().min(1, "Host obrigatório").max(253, "Máximo 253 caracteres"),
  port: z.coerce.number().int().min(1, "Porta inválida").max(65535, "Porta inválida"),
  username: z.string().min(1, "Usuário obrigatório").max(254, "Máximo 254 caracteres"),
  password: z.string().min(1, "Senha obrigatória").max(512, "Máximo 512 caracteres"),
  use_starttls: z.boolean(),
  from_address: z.string().email("E-mail inválido"),
});

export type SmtpConfigFormValues = z.infer<typeof smtpConfigSchema>;
```

**3. `src/components/EnviarRelatorioDialog.tsx`** — mover de `src/pages/Jornadas/EnviarRelatorioDialog.tsx`:

```typescript
// Conteúdo idêntico ao original em src/pages/Jornadas/EnviarRelatorioDialog.tsx
// (TASK-023 criou esse componente lá; esta task move sem mudar comportamento).
```

> **Após mover**, atualizar import em `apps/web/src/pages/Jornadas/JornadasPage.tsx`:
> ```typescript
> // de:
> import { EnviarRelatorioDialog } from "./EnviarRelatorioDialog";
> // para:
> import { EnviarRelatorioDialog } from "@/components/EnviarRelatorioDialog";
> ```
> E remover o arquivo antigo (`Remover` na tabela acima). Validação: `npm test` da TASK-023 (`src/pages/Jornadas/JornadasPage.test.tsx`) deve continuar verde com o novo path.

**4. `src/pages/Relatorios/RelatoriosPage.tsx`:**

```typescript
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query";
import dayjs, { type Dayjs } from "dayjs";
import {
  Container, Typography, Box, Button, Stack, Chip, Alert, Snackbar, Skeleton, Tooltip,
} from "@mui/material";
import { DataGrid, type GridColDef } from "@mui/x-data-grid";
import { DatePicker, LocalizationProvider } from "@mui/x-date-pickers";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { getRelatorioMeta, getRelatorioHistorico, urlDownloadRelatorio, relatoriosKeys } from "@/api/relatorios";
import api from "@/api/client";
import { terceirosKeys, getTerceiroMe } from "@/api/terceiros";
import { EnviarRelatorioDialog } from "@/components/EnviarRelatorioDialog";
import type { HistoricoEnvioItem } from "@/types/contracts";

export function RelatoriosPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [mesSel, setMesSel] = useState<Dayjs>(() => dayjs().subtract(1, "month"));
  const [dialogOpen, setDialogOpen] = useState(false);
  const [snackbar, setSnackbar] = useState<{ msg: string; severity: "success" | "error" | "info" } | null>(null);
  const mes = mesSel.format("YYYY-MM");

  const { data: meta, isLoading: loadingMeta, isError: errMeta } = useQuery({
    queryKey: relatoriosKeys.meta(mes), queryFn: () => getRelatorioMeta(mes), retry: false,
  });
  const { data: historico = [] } = useQuery({
    queryKey: relatoriosKeys.historico(mes), queryFn: () => getRelatorioHistorico(mes),
  });
  const { data: terceiro } = useQuery({ queryKey: terceirosKeys.me, queryFn: getTerceiroMe });

  const regenerar = useMutation({
    mutationFn: async () => api.get(urlDownloadRelatorio(mes), { responseType: "blob" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: relatoriosKeys.meta(mes) });
      setSnackbar({ msg: "Relatório regenerado.", severity: "success" });
    },
    onError: () => setSnackbar({ msg: "Falha ao regenerar relatório.", severity: "error" }),
  });

  function baixarPdf() {
    const a = document.createElement("a");
    a.href = urlDownloadRelatorio(mes);
    a.target = "_self";
    document.body.appendChild(a); a.click(); a.remove();
  }

  const semDados = errMeta;

  const histColunas: GridColDef<HistoricoEnvioItem>[] = [
    {
      field: "enviado_em", headerName: "Quando", width: 170,
      valueFormatter: (v: string) => dayjs(v).format("DD/MM/YYYY HH:mm"),
    },
    { field: "email_destinatario", headerName: "Destinatário", flex: 1 },
    {
      field: "status", headerName: "Status", width: 110,
      renderCell: (p) => <Chip label={p.row.status} color={p.row.status === "SUCESSO" ? "success" : "error"} size="small" />,
    },
    {
      field: "erro_mensagem", headerName: "Erro", flex: 1,
      renderCell: (p) => p.row.erro_mensagem ? (
        <Tooltip title={p.row.erro_mensagem}>
          <Typography variant="body2" noWrap>{p.row.erro_mensagem.slice(0, 60)}</Typography>
        </Tooltip>
      ) : "—",
    },
  ];

  return (
    <Container maxWidth="lg" sx={{ mt: 2 }}>
      <Typography variant="h4" component="h1" gutterBottom>Relatórios</Typography>
      <Stack direction="row" spacing={2} alignItems="center" mb={2}>
        <LocalizationProvider dateAdapter={AdapterDayjs}>
          <DatePicker
            views={["year", "month"]} label="Mês"
            value={mesSel} onChange={(v) => v && setMesSel(v)}
            maxDate={dayjs().subtract(1, "month")}
          />
        </LocalizationProvider>
      </Stack>

      {semDados ? (
        <Alert severity="info" sx={{ mt: 2 }}>
          Nenhuma jornada registrada para este mês. Não é possível gerar o relatório.
        </Alert>
      ) : (
        <>
          {meta?.invalidado_em && (
            <Alert
              severity="warning" sx={{ mb: 2 }}
              action={
                <Button color="inherit" size="small" disabled={regenerar.isPending} onClick={() => regenerar.mutate()}>
                  Atualizar relatório
                </Button>
              }
            >
              PDF desatualizado — clique em "Atualizar relatório" para regenerar.
            </Alert>
          )}
          <Box mb={2}>
            {loadingMeta ? <Skeleton variant="rectangular" height={500} /> : (
              <iframe
                title={`Relatório ${mes}`}
                src={urlDownloadRelatorio(mes)}
                style={{ width: "100%", height: 500, border: "1px solid #ccc" }}
              />
            )}
          </Box>
          <Stack direction="row" spacing={1} mb={2}>
            <Button variant="outlined" onClick={baixarPdf}>Baixar PDF</Button>
            <Button variant="contained" onClick={() => setDialogOpen(true)}>Enviar agora</Button>
            <Button onClick={() => navigate("/configuracoes/smtp")}>Configurar SMTP</Button>
          </Stack>
          <Typography variant="h6">Histórico de envios</Typography>
          <DataGrid<HistoricoEnvioItem>
            rows={historico} columns={histColunas} getRowId={(r) => r.id}
            autoHeight density="compact" pageSizeOptions={[10, 25]}
            initialState={{ pagination: { paginationModel: { pageSize: 10, page: 0 } } }}
          />
        </>
      )}

      <EnviarRelatorioDialog
        open={dialogOpen} onClose={() => setDialogOpen(false)}
        mes={mes} emailDefault={terceiro?.email_destinatario_relatorio ?? ""}
        onSuccess={(email) => { setDialogOpen(false); setSnackbar({ msg: `Relatório enviado para ${email}.`, severity: "success" }); }}
      />
      <Snackbar open={Boolean(snackbar)} autoHideDuration={5000} onClose={() => setSnackbar(null)}>
        <Alert severity={snackbar?.severity ?? "info"} onClose={() => setSnackbar(null)}
          role={snackbar?.severity === "error" ? "alert" : "status"}>
          {snackbar?.msg}
        </Alert>
      </Snackbar>
    </Container>
  );
}
```

**5. `src/pages/Configuracoes/SmtpConfigPage.tsx`:**

```typescript
import { useEffect, useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Container, Typography, Box, Stack, TextField, Switch, FormControlLabel, Button, Alert, Snackbar, Skeleton,
} from "@mui/material";
import { getSmtpConfig, putSmtpConfig, postTestSmtp, smtpKeys } from "@/api/smtp";
import { parseApiError } from "@/lib/errors";
import { smtpConfigSchema, type SmtpConfigFormValues } from "@/lib/schemas/smtp";

const MENSAGENS: Record<string, string> = {
  SMTP_NOT_CONFIGURED: "SMTP não configurado. Salve antes de testar.",
  SMTP_TEST_FAILED: "", // passthrough mensagem real do backend
};

export function SmtpConfigPage() {
  const qc = useQueryClient();
  const [snackbar, setSnackbar] = useState<{ msg: string; severity: "success" | "error" | "info" } | null>(null);
  const [testError, setTestError] = useState<string | null>(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: smtpKeys.config, queryFn: getSmtpConfig, retry: false,
  });

  const {
    control, register, handleSubmit, reset,
    formState: { errors, isValid, isSubmitting },
  } = useForm<SmtpConfigFormValues>({
    mode: "onBlur",
    resolver: zodResolver(smtpConfigSchema),
    defaultValues: {
      host: "", port: 587, username: "", password: "",
      use_starttls: true, from_address: "",
    },
  });

  useEffect(() => {
    if (data) {
      reset({
        host: data.host, port: data.port, username: data.username,
        password: "", // não vem do backend
        use_starttls: data.use_starttls, from_address: data.from_address,
      });
    }
  }, [data, reset]);

  const putMut = useMutation({
    mutationFn: (v: SmtpConfigFormValues) => putSmtpConfig({
      host: v.host, port: v.port, username: v.username, password: v.password,
      use_starttls: v.use_starttls, from_address: v.from_address,
    }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: smtpKeys.config });
      setSnackbar({ msg: "Configuração SMTP salva.", severity: "success" });
    },
    onError: (e) => {
      setSnackbar({ msg: parseApiError(e).message, severity: "error" });
    },
  });

  const testMut = useMutation({
    mutationFn: postTestSmtp,
    onSuccess: () => {
      setTestError(null);
      setSnackbar({ msg: "Conexão SMTP testada com sucesso.", severity: "success" });
    },
    onError: (e) => {
      const p = parseApiError(e);
      const m = MENSAGENS[p.code] || p.message;
      setTestError(m);
    },
  });

  return (
    <Container maxWidth="md" sx={{ mt: 2 }}>
      <Typography variant="h4" component="h1" gutterBottom>Configuração SMTP</Typography>
      {isError && (
        <Alert severity="info" sx={{ mb: 2 }}>Nenhuma configuração salva ainda.</Alert>
      )}
      {isLoading ? <Skeleton variant="rectangular" height={400} /> : (
        <Box component="form" onSubmit={handleSubmit((v) => putMut.mutate(v))}>
          <TextField label="Host" fullWidth margin="normal"
            {...register("host")} error={Boolean(errors.host)} helperText={errors.host?.message ?? " "} />
          <TextField label="Porta" type="number" fullWidth margin="normal"
            inputProps={{ min: 1, max: 65535 }}
            {...register("port", { valueAsNumber: true })}
            error={Boolean(errors.port)} helperText={errors.port?.message ?? " "} />
          <TextField label="Usuário" fullWidth margin="normal"
            {...register("username")} error={Boolean(errors.username)} helperText={errors.username?.message ?? " "} />
          <TextField label="Senha" type="password" fullWidth margin="normal"
            {...register("password")} error={Boolean(errors.password)} helperText={errors.password?.message ?? " "} />
          <Controller
            control={control} name="use_starttls"
            render={({ field }) => (
              <FormControlLabel
                control={<Switch checked={field.value} onChange={(_e, c) => field.onChange(c)} />}
                label="STARTTLS"
              />
            )}
          />
          <TextField label="From address" type="email" fullWidth margin="normal"
            {...register("from_address")} error={Boolean(errors.from_address)} helperText={errors.from_address?.message ?? " "} />

          {testError && <Alert severity="error" role="alert" sx={{ mt: 2 }}>{testError}</Alert>}

          <Stack direction="row" spacing={2} mt={3}>
            <Button onClick={() => testMut.mutate()} disabled={testMut.isPending}>
              {testMut.isPending ? "Testando..." : "Testar conexão"}
            </Button>
            <Button
              type="submit" variant="contained"
              disabled={!isValid || isSubmitting || putMut.isPending}
            >
              {putMut.isPending ? "Salvando..." : "Salvar"}
            </Button>
          </Stack>
        </Box>
      )}
      <Snackbar open={Boolean(snackbar)} autoHideDuration={5000} onClose={() => setSnackbar(null)}>
        <Alert severity={snackbar?.severity ?? "info"} onClose={() => setSnackbar(null)}
          role={snackbar?.severity === "error" ? "alert" : "status"}>
          {snackbar?.msg}
        </Alert>
      </Snackbar>
    </Container>
  );
}
```

**6. `src/routes.tsx` — diff:**

```typescript
import { RelatoriosPage } from "@/pages/Relatorios/RelatoriosPage";
import { SmtpConfigPage } from "@/pages/Configuracoes/SmtpConfigPage";
// Substituir:
// { path: "/relatorios", element: <RelatoriosPageStub /> },
// { path: "/configuracoes/smtp", element: <SmtpConfigPageStub /> },
// Por:
// { path: "/relatorios", element: <RelatoriosPage /> },
// { path: "/configuracoes/smtp", element: <SmtpConfigPage /> },
```

## Contratos com camadas adjacentes

```
Produz para:
  - Phase 6 (E2E): fluxo "Envio de relatório" termina aqui.

Consome de:
  TASK-020: api/client, parseApiError, renderWithProviders.
  TASK-023: relatoriosKeys, urlDownloadRelatorio, getRelatorioMeta, getRelatorioHistorico, postEnviarRelatorio.
  TASK-026: terceirosKeys, getTerceiroMe.
  Backend Phase 3 TASK-015: GET/PUT /smtp, POST /smtp/test.
  Backend Phase 3 TASK-018: GET /relatorios/{mes}, GET /{mes}/meta, POST /{mes}/enviar, GET /{mes}/historico.

Erros:
  - 401: tratado pelo interceptor.
  - 404 em /smtp: mensagem "Nenhuma configuração salva ainda."; form vazio.
  - 404 em /relatorios/{mes}/meta: bloqueia render do iframe; mensagem "Nenhuma jornada... Não é possível gerar..."
  - 422 SMTP_NOT_CONFIGURED no /smtp/test: alert "SMTP não configurado. Salve antes de testar."
  - 400 SMTP_TEST_FAILED: alert com mensagem real do backend (passthrough).
  - 422 VALIDATION_ERROR no PUT /smtp: snackbar com message do backend.
```

## Contrato HTTP

```
GET /api/v1/relatorios/{mes}/meta   (auth Bearer)
Response 200: {"mes_referencia":"2026-04","caminho_arquivo":"<path>","gerado_em":"<iso>","invalidado_em":null|"<iso>"}
Response 404: relatório ainda não gerado para o mês

GET /api/v1/relatorios/{mes}/historico   (auth Bearer)
Response 200: [HistoricoEnvioItem, ...] ordenado por enviado_em DESC

GET /api/v1/relatorios/{mes}   (auth Bearer)
Response 200: application/pdf (FileResponse) — gera on-demand se ausente/invalidado

POST /api/v1/relatorios/{mes}/enviar   (auth Bearer)  ← consumido via EnviarRelatorioDialog
Request body (opcional): {"email":"destino@example.com"}
Response 202: {"status":"SUCESSO","historico_id":"<uuid>"}
Response 422: {"code":"SMTP_NOT_CONFIGURED",...}
Response 500: {"code":"SMTP_SEND_FAILED","message":"...","details":[]}

GET /api/v1/smtp   (auth Bearer)
Response 200: SmtpConfigResponse (sem password)
Response 404: {"code":"NOT_FOUND","message":"SMTP não configurado","details":[]}

PUT /api/v1/smtp   (auth Bearer)
Request body:
{
  "host": "smtp.example.com",                          // 1..253
  "port": 587,                                         // 1..65535
  "username": "user@example.com",                      // 1..254
  "password": "senha-do-smtp",                         // 1..512; SecretStr; persiste cifrada (AES-GCM)
  "use_starttls": true,
  "from_address": "noreply@example.com"                // EmailStr
}
Response 200: SmtpConfigResponse atualizada (sem password)
Response 422: {"code":"VALIDATION_ERROR",...}

POST /api/v1/smtp/test   (auth Bearer; sem body)
Response 200: {"ok": true}
Response 400: {"code":"SMTP_TEST_FAILED","message":"<erro real>","details":[]}
Response 422: {"code":"SMTP_NOT_CONFIGURED","message":"SMTP não configurado","details":[]}
```

**Validação obrigatória pelo executor antes de marcar done:**

1. `cd apps/web && npm test -- --run src/pages/Relatorios/RelatoriosPage.test.tsx src/pages/Configuracoes/SmtpConfigPage.test.tsx` — 11+ testes passam.
2. `cd apps/web && npm test -- --run` — toda a suite (incluindo JornadasPage com o novo path do dialog) continua verde; coverage >= 80.
3. `cd apps/web && npm run typecheck` — 0 erros.
4. `cd apps/web && npm run lint` — 0 warnings.
5. `cd apps/web && npm run build` — `dist/` gerado sem erros.
6. `make smoke` (raiz) — Phase 1 smoke continua passando.

> Executor DEVE rodar 1–6 e garantir saída 0 antes de retornar.

**Refatoração:** após green, considerar (a) extrair `<HistoricoEnviosTable>` e `<PdfPreviewIframe>` para `src/components/` se necessário em futuro; (b) consolidar `dayjs(...).format("DD/MM/YYYY HH:mm")` em `formatDataHoraBR` em `src/lib/format/horario.ts`.
