---
checkpoint: null
complexity: M
created_at: "2026-05-28 12:44:11"
criteria:
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Jornadas/JornadasPage.test.tsx -t "mes=2026-05"
      text: Mount /jornadas em 2026-05-27 chama GET /api/v1/jornadas com query mes=2026-05
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Jornadas/JornadasPage.test.tsx -t "Nenhuma jornada"
      text: Estado vazio (jornadas=[]) renderiza texto exato Nenhuma jornada registrada para este mes. + CTA Criar jornada manual
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Jornadas/JornadasPage.test.tsx -t "FECHADA"
      text: Jornada FECHADA com horario_inicio 12:00Z (UTC) renderiza 09:00 (BRT) e total 28800s renderiza 08:00
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Jornadas/JornadasPage.test.tsx -t "tem_marcacao_pendente"
      text: Jornada com tem_marcacao_pendente=true exibe AMBOS chips status e PENDENTE simultaneos
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Jornadas/JornadasPage.test.tsx -t "navega para /jornadas"
      text: Click em linha navega para /jornadas/:id (window.location reflete)
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Jornadas/JornadasPage.test.tsx -t "desabilitado quando 0"
      text: Botoes Baixar PDF e Enviar por e-mail ficam desabilitados com tooltip Nenhuma jornada no mes quando lista vazia
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Jornadas/JornadasPage.test.tsx -t "pre-preenchido"
      text: Modal Enviar abre com input email pre-preenchido a partir de terceiro.email_destinatario_relatorio e POST /enviar 202 emite toast Relatorio enviado para <email>.
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Jornadas/JornadasPage.test.tsx -t "SMTP_NOT_CONFIGURED"
      text: 422 SMTP_NOT_CONFIGURED no POST /enviar exibe alert SMTP nao configurado. + CTA Configurar agora
    - done: false
      test: cd apps/web && npm test -- --run src/lib/format/horario.test.ts -t "formatHoraBR"
      text: formatHoraBR converte 12:00Z para 09:00 e 21:00Z para 18:00 (UTC-3)
    - done: false
      test: cd apps/web && npm test -- --run src/lib/format/horario.test.ts -t "formatTotal"
      text: formatTotal converte 28800 para 08:00 e 3661 para 01:01
    - done: false
      test: grep -E "<JornadasPage ?/>" apps/web/src/routes.tsx
      text: routes.tsx substitui JornadasPageStub por JornadasPage real
    - done: false
      text: ESLint passa sem warnings e tsc strict 0 erros
    - done: false
      text: Testes passando com cobertura >= 80%
    - done: false
      text: make smoke continua passando
deps:
    - TASK-020
id: TASK-023
linter: cd apps/web && npm run lint && npm run typecheck
n45_version: 0.2.0
persona: frontend
phase: Phase 4 — Frontend por Feature
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: pending
tdd:
    green: false
    red: false
    refactor: false
tests: cd apps/web && npm test -- --run src/pages/Jornadas/JornadasPage.test.tsx src/lib/format/horario.test.ts
title: 'Jornadas - Lista mensal (RF-007.1): DataGrid + DatePicker (mes), chips de status, badge PENDENTE, baixar/enviar PDF (TASK-018), helpers format/horario, jornadasKeys + relatoriosKeys factories'
updated_at: "2026-05-28 12:44:11"
---
## Contexto

Implementar a página `/jornadas` (RF-007.1) — lista mensal de jornadas do Terceiro autenticado. Slice: componente + página + 2 sub-componentes + hook TanStack Query + zod schema do filtro de mês + substituição do stub em `routes.tsx`.

**State atual:**
- TASK-020 entregou `api/client`, `AppLayout` (a página renderiza dentro dele), `useAuth`, `renderWithProviders`, `JornadasPageStub` em `routes.tsx` dentro de `<ProtectedRoute>` + `<PrivacyGuard>` + `<AppLayout>`.
- TASK-017 (backend) entregou `GET /api/v1/jornadas?mes=YYYY-MM` retornando `JornadasMesResponse` com `mes_referencia`, `total_horas_mes_s` e array `jornadas: JornadaResumo[]`.
- TASK-018 (backend) entregou `GET /api/v1/relatorios/{mes}` (download direto via redirect/href) e `POST /api/v1/relatorios/{mes}/enviar` (modal posterior).

**Decisão de UX (Spec §5 — `/jornadas`):**
- Cabeçalho da página: `<h1>` "Jornadas" + DatePicker MUI tipo `views={["year","month"]}` (default = mês atual, max = mês atual) — usa `@mui/x-date-pickers` v6+ (pacote adicional). **Adicionar `@mui/x-date-pickers` e `dayjs` em `package.json`**.
- Total mensal renderizado abaixo do título: "Total no mês: HH:MM" (formatado de segundos).
- Tabela MUI `DataGrid` (`@mui/x-data-grid`) com colunas:
  - Data (formato `DD/MM`)
  - Dia da semana (`Seg`, `Ter`, ...; calculado client-side de `data`)
  - Início (`HH:MM` extraído de `horario_inicio` UTC → exibido em `America/Sao_Paulo`)
  - Saída Almoço
  - Retorno Almoço
  - Fim
  - Total (`HH:MM` de `total_horas_apuradas_s`)
  - Status (chip MUI: `EM_ANDAMENTO`=cinza, `FECHADA`=verde, `AJUSTADA_MANUALMENTE`=âmbar, `PENDENTE`=vermelho com ícone `WarningIcon`)
  - Linha com `tem_marcacao_pendente=true` recebe badge vermelho PENDENTE **independente** do status da jornada
- Tabela ordenada por `data` ascendente; linhas clicáveis → `navigate("/jornadas/:id")`.
- Barra de ações acima da tabela: botão "Nova jornada manual" (→ `/jornadas/manual`), botão "Baixar PDF", botão "Enviar por e-mail".
  - "Baixar PDF": cria `<a href={"/api/v1/relatorios/" + mes}>` invisível, programaticamente clicado; **desabilitado com tooltip "Nenhuma jornada no mês"** quando `jornadas.length === 0`.
  - "Enviar por e-mail": abre modal de confirmação com campo "Destinatário" preenchido com `terceiro.email_destinatario_relatorio` (editável). Submit → `POST /api/v1/relatorios/{mes}/enviar` com `{email}`. Sucesso 202 → toast "Relatório enviado para <email>". Erro 422 `SMTP_NOT_CONFIGURED` → toast "SMTP não configurado." + CTA "Configurar agora" navega para `/configuracoes/smtp`. **Desabilitado com tooltip "Nenhuma jornada no mês"** quando vazio.

**Decisão sobre DatePicker:** usar `@mui/x-date-pickers/DatePicker` com adapter `dayjs`. Para evitar bloat, **NÃO** habilitar localização específica (já é pt-BR via `dayjs/locale/pt-br` import).

**Decisão sobre formatação UTC → BRT:** o backend envia `horario_*` como `+00:00` (UTC ISO 8601). O frontend converte para `America/Sao_Paulo` usando `dayjs.tz` (plugin `timezone` + `utc`). Helper `formatHora(isoUtc)` em `src/lib/format/horario.ts`.

**Dependência:** TASK-020.

## Comportamento Esperado

| Entrada / Ação | Saída / Efeito esperado |
| -------------- | ----------------------- |
| Mount `/jornadas` em 2026-05-27 | DatePicker default = "Maio 2026"; chama `GET /api/v1/jornadas?mes=2026-05`; loading → skeleton de 5 linhas |
| Backend responde 200 com 0 jornadas | Tabela vazia com estado vazio: "Nenhuma jornada registrada para este mês." + CTA "Criar jornada manual"; "Baixar PDF" e "Enviar por e-mail" desabilitados com tooltip |
| Backend responde 200 com 1 jornada `{id:"j1", data:"2026-05-27", status:"FECHADA", total_horas_apuradas_s:28800, tem_marcacao_pendente:false, horario_inicio:"2026-05-27T12:00:00+00:00", horario_saida_almoco:"2026-05-27T15:00:00+00:00", horario_retorno_almoco:"2026-05-27T16:00:00+00:00", horario_fim:"2026-05-27T21:00:00+00:00"}` | Tabela 1 linha: Data "27/05", Dia "Qua", Início "09:00", Saída Almoço "12:00", Retorno "13:00", Fim "18:00", Total "08:00", Chip verde "FECHADA"; `total_horas_mes_s=28800` → "Total no mês: 08:00" |
| Linha com `tem_marcacao_pendente=true` + `status:"FECHADA"` | **Dois chips**: verde "FECHADA" + vermelho "PENDENTE" com ícone WarningIcon |
| Click em linha | `navigate("/jornadas/j1")` |
| Click em "Nova jornada manual" | `navigate("/jornadas/manual")` |
| Click em "Baixar PDF" com 1+ jornadas | Cria `<a>` invisível com `href="/api/v1/relatorios/2026-05"` e `click()`; navegador inicia download (proxy Vite encaminha; produção mesmo origin) |
| Click em "Enviar por e-mail" com 1+ jornadas | Abre modal com TextField "Destinatário" pré-preenchido com `terceiro.email_destinatario_relatorio` |
| Modal envio: clicar "Enviar" | Chama `POST /api/v1/relatorios/2026-05/enviar` com `{email:"..."}`; sucesso 202 → fecha modal + toast "Relatório enviado para <email>." |
| Erro 422 `SMTP_NOT_CONFIGURED` | Modal fica aberto; alert inline "SMTP não configurado." com link "Configurar agora" → `navigate("/configuracoes/smtp")` |
| Erro 500 | Toast vermelho com `parseApiError(err).message` |
| Trocar mês para 2026-04 | Chama `GET /api/v1/jornadas?mes=2026-04` (nova queryKey); tabela re-renderiza |
| Tentar selecionar mês futuro (2026-06) | DatePicker bloqueia (`maxDate=today`) |

## TDD

**Testes a escrever antes da implementação** (`apps/web/src/pages/Jornadas/JornadasPage.test.tsx`):

```typescript
import { describe, it, expect, beforeEach, vi } from "vitest";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MockAdapter from "axios-mock-adapter";
import api from "@/api/client";
import { renderWithProviders } from "@/test/render";
import { JornadasPage } from "@/pages/Jornadas/JornadasPage";

const mock = new MockAdapter(api);

beforeEach(() => {
  mock.reset();
  sessionStorage.setItem("ts:access_token", "tok");
  sessionStorage.setItem("ts:refresh_token", "r");
  sessionStorage.setItem("ts:terceiro_id", "u1");
  sessionStorage.setItem("ts:expires_at", String(Date.now() + 60_000));
  vi.useFakeTimers({ shouldAdvanceTime: true });
  vi.setSystemTime(new Date("2026-05-27T12:00:00-03:00"));
});

describe("JornadasPage", () => {
  it("renderiza heading h1 Jornadas e chama GET /api/v1/jornadas?mes=2026-05", async () => {
    let urlChamada = "";
    mock.onGet("/api/v1/jornadas").reply((cfg) => {
      urlChamada = String(cfg.url) + "?" + new URLSearchParams(cfg.params).toString();
      return [200, { mes_referencia: "2026-05", total_horas_mes_s: 0, jornadas: [] }];
    });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria", email_destinatario_relatorio: "rh@acme.com" });
    renderWithProviders(<JornadasPage />, { route: "/jornadas" });
    expect(screen.getByRole("heading", { level: 1, name: /Jornadas/i })).toBeInTheDocument();
    await waitFor(() => expect(urlChamada).toContain("mes=2026-05"));
  });

  it("estado vazio: 0 jornadas exibe texto 'Nenhuma jornada registrada para este mês.' + CTA Criar", async () => {
    mock.onGet("/api/v1/jornadas").reply(200, { mes_referencia: "2026-05", total_horas_mes_s: 0, jornadas: [] });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria", email_destinatario_relatorio: null });
    renderWithProviders(<JornadasPage />, { route: "/jornadas" });
    expect(await screen.findByText(/Nenhuma jornada registrada para este mês\./i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Criar jornada manual/i })).toBeInTheDocument();
  });

  it("1 jornada FECHADA renderiza linha com Data 27/05, Total 08:00 e chip FECHADA verde", async () => {
    mock.onGet("/api/v1/jornadas").reply(200, {
      mes_referencia: "2026-05",
      total_horas_mes_s: 28800,
      jornadas: [{
        id: "j1", data: "2026-05-27", status: "FECHADA",
        total_horas_apuradas_s: 28800, tem_marcacao_pendente: false,
        horario_inicio: "2026-05-27T12:00:00+00:00",
        horario_saida_almoco: "2026-05-27T15:00:00+00:00",
        horario_retorno_almoco: "2026-05-27T16:00:00+00:00",
        horario_fim: "2026-05-27T21:00:00+00:00",
      }],
    });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria", email_destinatario_relatorio: null });
    renderWithProviders(<JornadasPage />, { route: "/jornadas" });
    expect(await screen.findByText("27/05")).toBeInTheDocument();
    // Em UTC-3, 12:00Z = 09:00 BRT
    expect(screen.getByText("09:00")).toBeInTheDocument();
    expect(screen.getByText("18:00")).toBeInTheDocument();
    expect(screen.getByText("08:00")).toBeInTheDocument();
    expect(screen.getByText(/Total no mês:\s*08:00/i)).toBeInTheDocument();
    expect(screen.getByText("FECHADA")).toBeInTheDocument();
  });

  it("jornada com tem_marcacao_pendente=true exibe AMBOS chips status e PENDENTE", async () => {
    mock.onGet("/api/v1/jornadas").reply(200, {
      mes_referencia: "2026-05",
      total_horas_mes_s: 28800,
      jornadas: [{
        id: "j1", data: "2026-05-27", status: "FECHADA",
        total_horas_apuradas_s: 28800, tem_marcacao_pendente: true,
        horario_inicio: "2026-05-27T12:00:00+00:00",
        horario_saida_almoco: "2026-05-27T15:00:00+00:00",
        horario_retorno_almoco: "2026-05-27T16:00:00+00:00",
        horario_fim: "2026-05-27T21:00:00+00:00",
      }],
    });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria", email_destinatario_relatorio: null });
    renderWithProviders(<JornadasPage />, { route: "/jornadas" });
    expect(await screen.findByText("FECHADA")).toBeInTheDocument();
    expect(screen.getByText("PENDENTE")).toBeInTheDocument();
  });

  it("clique em linha navega para /jornadas/:id", async () => {
    mock.onGet("/api/v1/jornadas").reply(200, {
      mes_referencia: "2026-05",
      total_horas_mes_s: 28800,
      jornadas: [{
        id: "abc-123", data: "2026-05-27", status: "FECHADA",
        total_horas_apuradas_s: 28800, tem_marcacao_pendente: false,
        horario_inicio: "2026-05-27T12:00:00+00:00",
        horario_saida_almoco: "2026-05-27T15:00:00+00:00",
        horario_retorno_almoco: "2026-05-27T16:00:00+00:00",
        horario_fim: "2026-05-27T21:00:00+00:00",
      }],
    });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria", email_destinatario_relatorio: null });
    const { container } = renderWithProviders(<JornadasPage />, { route: "/jornadas" });
    const linha = await screen.findByText("27/05");
    await userEvent.click(linha);
    // Asserta URL via location atual (MemoryRouter reflete)
    expect(window.location.pathname).toContain("/jornadas/abc-123");
  });

  it("Baixar PDF desabilitado quando 0 jornadas, com tooltip 'Nenhuma jornada no mês'", async () => {
    mock.onGet("/api/v1/jornadas").reply(200, { mes_referencia: "2026-05", total_horas_mes_s: 0, jornadas: [] });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria", email_destinatario_relatorio: null });
    renderWithProviders(<JornadasPage />, { route: "/jornadas" });
    const btn = await screen.findByRole("button", { name: /Baixar PDF/i });
    expect(btn).toBeDisabled();
    await userEvent.hover(btn);
    expect(await screen.findByText(/Nenhuma jornada no mês/i)).toBeInTheDocument();
  });

  it("Enviar por e-mail abre modal com email pré-preenchido e sucesso emite toast", async () => {
    mock.onGet("/api/v1/jornadas").reply(200, {
      mes_referencia: "2026-05",
      total_horas_mes_s: 28800,
      jornadas: [{
        id: "j1", data: "2026-05-27", status: "FECHADA",
        total_horas_apuradas_s: 28800, tem_marcacao_pendente: false,
        horario_inicio: "2026-05-27T12:00:00+00:00",
        horario_saida_almoco: "2026-05-27T15:00:00+00:00",
        horario_retorno_almoco: "2026-05-27T16:00:00+00:00",
        horario_fim: "2026-05-27T21:00:00+00:00",
      }],
    });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria", email_destinatario_relatorio: "rh@acme.com" });
    mock.onPost("/api/v1/relatorios/2026-05/enviar").reply(202, { status: "SUCESSO", historico_id: "h1" });
    renderWithProviders(<JornadasPage />, { route: "/jornadas" });
    await userEvent.click(await screen.findByRole("button", { name: /Enviar por e-mail/i }));
    const inp = screen.getByLabelText(/Destinatário/i) as HTMLInputElement;
    expect(inp.value).toBe("rh@acme.com");
    await userEvent.click(screen.getByRole("button", { name: /^Enviar$/ }));
    expect(await screen.findByText(/Relatório enviado para rh@acme.com\./i)).toBeInTheDocument();
  });

  it("Enviar com SMTP_NOT_CONFIGURED mostra alert e CTA Configurar agora", async () => {
    mock.onGet("/api/v1/jornadas").reply(200, {
      mes_referencia: "2026-05",
      total_horas_mes_s: 28800,
      jornadas: [{
        id: "j1", data: "2026-05-27", status: "FECHADA",
        total_horas_apuradas_s: 28800, tem_marcacao_pendente: false,
        horario_inicio: "2026-05-27T12:00:00+00:00",
        horario_saida_almoco: "2026-05-27T15:00:00+00:00",
        horario_retorno_almoco: "2026-05-27T16:00:00+00:00",
        horario_fim: "2026-05-27T21:00:00+00:00",
      }],
    });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria", email_destinatario_relatorio: "rh@acme.com" });
    mock.onPost("/api/v1/relatorios/2026-05/enviar").reply(422, {
      code: "SMTP_NOT_CONFIGURED", message: "SMTP não configurado", details: [],
    });
    renderWithProviders(<JornadasPage />, { route: "/jornadas" });
    await userEvent.click(await screen.findByRole("button", { name: /Enviar por e-mail/i }));
    await userEvent.click(screen.getByRole("button", { name: /^Enviar$/ }));
    expect(await screen.findByText(/SMTP não configurado\./i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Configurar agora/i })).toBeInTheDocument();
  });
});
```

**Refatoração:** após green, considerar extrair `formatHoraBR(isoUtc)` e `formatTotal(secs)` para `src/lib/format/horario.ts` (já criados nesta task) — **já fazem parte dos alvos**, mover de inline para módulo central garante reuso por TASK-024/025.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| ------- | ---- | --------- |
| `apps/web/package.json` | Modificar | Adicionar deps: `@mui/x-data-grid` `^7.x`, `@mui/x-date-pickers` `^7.x`, `dayjs` `^1.11.x` |
| `apps/web/src/api/jornadas.ts` | Criar | `jornadasKeys` (factory) + `getJornadasMes(mes)` + tipos |
| `apps/web/src/api/relatorios.ts` | Criar | `relatoriosKeys` + `postEnviarRelatorio(mes, email?)` + função para URL de download |
| `apps/web/src/pages/Jornadas/JornadasPage.tsx` | Criar | Componente principal |
| `apps/web/src/pages/Jornadas/EnviarRelatorioDialog.tsx` | Criar | Modal de envio |
| `apps/web/src/pages/Jornadas/JornadasPage.test.tsx` | Criar | TDD acima |
| `apps/web/src/lib/format/horario.ts` | Criar | `formatHoraBR(isoUtc)`, `formatTotal(secs)`, `formatData(yyyymmdd)`, `formatDiaSemana(yyyymmdd)` |
| `apps/web/src/lib/format/horario.test.ts` | Criar | Testes do helper |
| `apps/web/src/routes.tsx` | Modificar | Substituir `JornadasPageStub` por `JornadasPage` |

> 7 criados + 2 modificados = **9 arquivos-alvo**. **Excede** o teto por 1 — justificativa: o slice exige helpers de formatação compartilhados (`formatHoraBR`, `formatTotal`, `formatData`, `formatDiaSemana`) que TASK-024 e TASK-025 também consomem. Criá-los aqui (primeiro consumidor) com **teste unitário próprio** é coesão; alternativa rejeitada: spalhar os helpers nas tasks consumidoras → duplicação garantida.

### Detalhamento Técnico

**1. `package.json` — adições:**

```jsonc
"dependencies": {
  // ... existentes ...
  "@mui/x-data-grid": "^7.22.0",
  "@mui/x-date-pickers": "^7.22.0",
  "dayjs": "^1.11.13"
}
```

**2. `src/lib/format/horario.ts`** (helpers compartilhados):

```typescript
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import timezone from "dayjs/plugin/timezone";
import "dayjs/locale/pt-br";

dayjs.extend(utc);
dayjs.extend(timezone);
dayjs.locale("pt-br");

const TZ_BR = "America/Sao_Paulo";

export function formatHoraBR(isoUtc: string | null): string {
  if (!isoUtc) return "—";
  return dayjs(isoUtc).tz(TZ_BR).format("HH:mm");
}

export function formatTotal(segundos: number | null): string {
  if (segundos == null || segundos < 0) return "—";
  const h = Math.floor(segundos / 3600);
  const m = Math.floor((segundos % 3600) / 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

export function formatData(yyyymmdd: string): string {
  return dayjs(yyyymmdd).format("DD/MM");
}

const DIAS_SEMANA = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sab"] as const;
export function formatDiaSemana(yyyymmdd: string): string {
  const d = dayjs(yyyymmdd).day(); // 0..6
  return DIAS_SEMANA[d] ?? "—";
}
```

**3. `src/lib/format/horario.test.ts`**:

```typescript
import { describe, it, expect } from "vitest";
import { formatHoraBR, formatTotal, formatData, formatDiaSemana } from "@/lib/format/horario";

describe("format/horario", () => {
  describe("formatHoraBR", () => {
    it("12:00Z UTC → 09:00 (UTC-3)", () => {
      expect(formatHoraBR("2026-05-27T12:00:00+00:00")).toBe("09:00");
    });
    it("21:00Z UTC → 18:00 (UTC-3)", () => {
      expect(formatHoraBR("2026-05-27T21:00:00+00:00")).toBe("18:00");
    });
    it("null → '—'", () => {
      expect(formatHoraBR(null)).toBe("—");
    });
  });
  describe("formatTotal", () => {
    it("28800 → '08:00'", () => expect(formatTotal(28800)).toBe("08:00"));
    it("3661 → '01:01'", () => expect(formatTotal(3661)).toBe("01:01"));
    it("null → '—'", () => expect(formatTotal(null)).toBe("—"));
    it("0 → '00:00'", () => expect(formatTotal(0)).toBe("00:00"));
  });
  describe("formatData", () => {
    it("'2026-05-27' → '27/05'", () => expect(formatData("2026-05-27")).toBe("27/05"));
  });
  describe("formatDiaSemana", () => {
    it("'2026-05-27' (quarta) → 'Qua'", () => expect(formatDiaSemana("2026-05-27")).toBe("Qua"));
    it("'2026-05-30' (sábado) → 'Sab'", () => expect(formatDiaSemana("2026-05-30")).toBe("Sab"));
  });
});
```

**4. `src/api/jornadas.ts`**:

```typescript
import api from "./client";
import type { JornadasMesResponse, JornadaDetalheResponse, AjusteJornadaRequest, JornadaManualRequest, AtividadeRequest, AtividadeDetalhe } from "@/types/contracts";

export const jornadasKeys = {
  all: ["jornadas"] as const,
  lista: (mes: string) => ["jornadas", "lista", mes] as const,
  detalhe: (id: string) => ["jornadas", "detalhe", id] as const,
};

export async function getJornadasMes(mes: string): Promise<JornadasMesResponse> {
  const r = await api.get<JornadasMesResponse>("/api/v1/jornadas", { params: { mes } });
  return r.data;
}

// Os abaixo serão usados por TASK-024/025; declarados agora porque a key factory está aqui.
export async function getJornadaDetalhe(id: string): Promise<JornadaDetalheResponse> {
  const r = await api.get<JornadaDetalheResponse>(`/api/v1/jornadas/${id}`);
  return r.data;
}
export async function putAjusteJornada(id: string, body: AjusteJornadaRequest): Promise<JornadaDetalheResponse> {
  const r = await api.put<JornadaDetalheResponse>(`/api/v1/jornadas/${id}`, body);
  return r.data;
}
export async function postJornadaManual(body: JornadaManualRequest): Promise<JornadaDetalheResponse> {
  const r = await api.post<JornadaDetalheResponse>("/api/v1/jornadas/manual", body);
  return r.data;
}
export async function postAtividade(jornadaId: string, body: AtividadeRequest): Promise<AtividadeDetalhe> {
  const r = await api.post<AtividadeDetalhe>(`/api/v1/jornadas/${jornadaId}/atividade`, body);
  return r.data;
}
```

**5. `src/api/relatorios.ts`**:

```typescript
import api from "./client";
import type { EnviarResponse, RelatorioMesResponse, HistoricoEnvioItem } from "@/types/contracts";

export const relatoriosKeys = {
  meta: (mes: string) => ["relatorios", "meta", mes] as const,
  historico: (mes: string) => ["relatorios", "historico", mes] as const,
};

export function urlDownloadRelatorio(mes: string): string {
  return `/api/v1/relatorios/${mes}`;
}

export async function getRelatorioMeta(mes: string): Promise<RelatorioMesResponse> {
  const r = await api.get<RelatorioMesResponse>(`/api/v1/relatorios/${mes}/meta`);
  return r.data;
}

export async function getRelatorioHistorico(mes: string): Promise<HistoricoEnvioItem[]> {
  const r = await api.get<HistoricoEnvioItem[]>(`/api/v1/relatorios/${mes}/historico`);
  return r.data;
}

export async function postEnviarRelatorio(mes: string, email?: string): Promise<EnviarResponse> {
  const r = await api.post<EnviarResponse>(`/api/v1/relatorios/${mes}/enviar`, email ? { email } : undefined);
  return r.data;
}
```

**6. `src/pages/Jornadas/JornadasPage.tsx`** — componente principal (resumo):

```typescript
import { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import dayjs, { type Dayjs } from "dayjs";
import {
  Container, Typography, Box, Button, Stack, Chip, Tooltip, Snackbar, Alert,
} from "@mui/material";
import WarningIcon from "@mui/icons-material/Warning";
import { DataGrid, type GridColDef, type GridRenderCellParams } from "@mui/x-data-grid";
import { DatePicker, LocalizationProvider } from "@mui/x-date-pickers";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { getJornadasMes, jornadasKeys } from "@/api/jornadas";
import { urlDownloadRelatorio } from "@/api/relatorios";
import { terceiroKeys } from "@/components/AppLayout";
import api from "@/api/client";
import type { TerceiroResponse, JornadaResumo } from "@/types/contracts";
import { formatHoraBR, formatTotal, formatData, formatDiaSemana } from "@/lib/format/horario";
import { EnviarRelatorioDialog } from "./EnviarRelatorioDialog";

const STATUS_COLOR: Record<JornadaResumo["status"], "default" | "success" | "warning" | "error"> = {
  EM_ANDAMENTO: "default",
  FECHADA: "success",
  AJUSTADA_MANUALMENTE: "warning",
  PENDENTE: "error",
};

export function JornadasPage() {
  const navigate = useNavigate();
  const [mesSel, setMesSel] = useState<Dayjs>(dayjs());
  const [dialogOpen, setDialogOpen] = useState(false);
  const [snackbar, setSnackbar] = useState<{ msg: string; severity: "success" | "error" } | null>(null);

  const mes = mesSel.format("YYYY-MM");

  const { data, isLoading } = useQuery({
    queryKey: jornadasKeys.lista(mes),
    queryFn: () => getJornadasMes(mes),
  });

  const { data: terceiro } = useQuery({
    queryKey: terceiroKeys.me,
    queryFn: async (): Promise<TerceiroResponse> => {
      const r = await api.get<TerceiroResponse>("/api/v1/terceiros/me");
      return r.data;
    },
  });

  const vazio = !data || data.jornadas.length === 0;

  const colunas: GridColDef<JornadaResumo>[] = useMemo(
    () => [
      { field: "data", headerName: "Data", width: 90, valueFormatter: (v: string) => formatData(v) },
      { field: "diaSemana", headerName: "Dia", width: 70, valueGetter: (_v, row) => formatDiaSemana(row.data) },
      { field: "horario_inicio", headerName: "Início", width: 90, valueFormatter: (v: string | null) => formatHoraBR(v) },
      { field: "horario_saida_almoco", headerName: "Saída Almoço", width: 120, valueFormatter: (v: string | null) => formatHoraBR(v) },
      { field: "horario_retorno_almoco", headerName: "Retorno Almoço", width: 130, valueFormatter: (v: string | null) => formatHoraBR(v) },
      { field: "horario_fim", headerName: "Fim", width: 90, valueFormatter: (v: string | null) => formatHoraBR(v) },
      { field: "total_horas_apuradas_s", headerName: "Total", width: 90, valueFormatter: (v: number | null) => formatTotal(v) },
      {
        field: "status", headerName: "Status", width: 240,
        renderCell: (p: GridRenderCellParams<JornadaResumo>) => (
          <Stack direction="row" spacing={1} alignItems="center">
            <Chip label={p.row.status} color={STATUS_COLOR[p.row.status]} size="small" />
            {p.row.tem_marcacao_pendente && (
              <Chip
                label="PENDENTE"
                color="error"
                size="small"
                icon={<WarningIcon />}
              />
            )}
          </Stack>
        ),
      },
    ],
    []
  );

  function baixarPdf() {
    const a = document.createElement("a");
    a.href = urlDownloadRelatorio(mes);
    a.target = "_self";
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 2 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Jornadas
      </Typography>
      <Stack direction="row" spacing={2} alignItems="center" mb={2}>
        <LocalizationProvider dateAdapter={AdapterDayjs}>
          <DatePicker
            views={["year", "month"]}
            label="Mês"
            value={mesSel}
            onChange={(v) => v && setMesSel(v)}
            maxDate={dayjs()}
          />
        </LocalizationProvider>
        <Typography variant="body1">
          Total no mês: <strong>{formatTotal(data?.total_horas_mes_s ?? null)}</strong>
        </Typography>
      </Stack>
      <Stack direction="row" spacing={1} mb={2}>
        <Button variant="contained" onClick={() => navigate("/jornadas/manual")}>
          Nova jornada manual
        </Button>
        <Tooltip title={vazio ? "Nenhuma jornada no mês" : ""}>
          <span>
            <Button variant="outlined" disabled={vazio} onClick={baixarPdf}>
              Baixar PDF
            </Button>
          </span>
        </Tooltip>
        <Tooltip title={vazio ? "Nenhuma jornada no mês" : ""}>
          <span>
            <Button variant="outlined" disabled={vazio} onClick={() => setDialogOpen(true)}>
              Enviar por e-mail
            </Button>
          </span>
        </Tooltip>
      </Stack>

      {vazio && !isLoading ? (
        <Box textAlign="center" py={6}>
          <Typography color="text.secondary" mb={2}>
            Nenhuma jornada registrada para este mês.
          </Typography>
          <Button variant="contained" onClick={() => navigate("/jornadas/manual")}>
            Criar jornada manual
          </Button>
        </Box>
      ) : (
        <DataGrid<JornadaResumo>
          rows={data?.jornadas ?? []}
          columns={colunas}
          loading={isLoading}
          getRowId={(r) => r.id}
          onRowClick={(p) => navigate(`/jornadas/${p.id}`)}
          autoHeight
          disableRowSelectionOnClick
          initialState={{ pagination: { paginationModel: { pageSize: 31, page: 0 } } }}
          pageSizeOptions={[31]}
        />
      )}

      <EnviarRelatorioDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        mes={mes}
        emailDefault={terceiro?.email_destinatario_relatorio ?? ""}
        onSuccess={(email) => {
          setDialogOpen(false);
          setSnackbar({ msg: `Relatório enviado para ${email}.`, severity: "success" });
        }}
      />

      <Snackbar
        open={Boolean(snackbar)}
        autoHideDuration={5000}
        onClose={() => setSnackbar(null)}
      >
        <Alert
          severity={snackbar?.severity ?? "info"}
          onClose={() => setSnackbar(null)}
          role="status"
        >
          {snackbar?.msg}
        </Alert>
      </Snackbar>
    </Container>
  );
}
```

**7. `src/pages/Jornadas/EnviarRelatorioDialog.tsx`**:

```typescript
import { useState, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  Dialog, DialogTitle, DialogContent, DialogActions, TextField, Button, Alert, Box,
} from "@mui/material";
import { postEnviarRelatorio } from "@/api/relatorios";
import { parseApiError } from "@/lib/errors";

interface Props {
  open: boolean;
  onClose: () => void;
  mes: string;
  emailDefault: string;
  onSuccess: (email: string) => void;
}

export function EnviarRelatorioDialog({ open, onClose, mes, emailDefault, onSuccess }: Props) {
  const [email, setEmail] = useState(emailDefault);
  const [erro, setErro] = useState<{ code: string; message: string } | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (open) {
      setEmail(emailDefault);
      setErro(null);
    }
  }, [open, emailDefault]);

  const mutation = useMutation({
    mutationFn: async () => postEnviarRelatorio(mes, email || undefined),
    onSuccess: () => onSuccess(email),
    onError: (err) => {
      const p = parseApiError(err);
      setErro({ code: p.code, message: p.message });
    },
  });

  const isSmtpMissing = erro?.code === "SMTP_NOT_CONFIGURED";

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Enviar relatório do mês {mes}</DialogTitle>
      <DialogContent>
        <TextField
          label="Destinatário"
          fullWidth
          margin="normal"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        {erro && (
          <Alert
            severity={isSmtpMissing ? "warning" : "error"}
            role="alert"
            action={
              isSmtpMissing ? (
                <Button color="inherit" size="small" onClick={() => navigate("/configuracoes/smtp")}>
                  Configurar agora
                </Button>
              ) : undefined
            }
            sx={{ mt: 2 }}
          >
            {isSmtpMissing ? "SMTP não configurado." : erro.message}
          </Alert>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancelar</Button>
        <Button
          variant="contained"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending || !email}
        >
          {mutation.isPending ? "Enviando..." : "Enviar"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
```

**8. `src/routes.tsx` — diff:**

```typescript
import { JornadasPage } from "@/pages/Jornadas/JornadasPage";
// substituir:
// { path: "/jornadas", element: <JornadasPageStub /> },
// por:
// { path: "/jornadas", element: <JornadasPage /> },
```

## Contratos com camadas adjacentes

```
Produz para (TASK-024, 025, 027 reutilizam):
  - jornadasKeys (factory): jornadasKeys.lista(mes), jornadasKeys.detalhe(id)
  - relatoriosKeys (factory): relatoriosKeys.meta(mes), relatoriosKeys.historico(mes)
  - urlDownloadRelatorio(mes): também usada na página /relatorios (TASK-027)
  - formatHoraBR, formatTotal, formatData, formatDiaSemana: helpers compartilhados (TASK-024/025)
  - getJornadaDetalhe, putAjusteJornada, postJornadaManual, postAtividade: funções HTTP que TASK-024 e TASK-025 importam diretamente

Consome de:
  TASK-020: api/client, parseApiError, renderWithProviders, terceiroKeys.me (de AppLayout).
  Backend Phase 3 TASK-017: GET /api/v1/jornadas?mes=YYYY-MM.
  Backend Phase 3 TASK-018: GET /api/v1/relatorios/{mes}, POST /api/v1/relatorios/{mes}/enviar.

Erros:
  - 401: tratado pelo interceptor (refresh + retry).
  - 422 SMTP_NOT_CONFIGURED: alert warning com CTA "Configurar agora" no modal de envio.
  - 422 NO_DATA: backend não chega aqui se buttons "Baixar/Enviar" estiverem desabilitados (vazio=true).
  - 500 SMTP_SEND_FAILED: parsed.message no alert do modal.
```

## Contrato HTTP

```
GET /api/v1/jornadas?mes=YYYY-MM   (auth Bearer)
Response 200:
{
  "mes_referencia": "2026-05",
  "total_horas_mes_s": 28800,
  "jornadas": [
    {
      "id": "<uuid>",
      "data": "2026-05-27",
      "status": "FECHADA" | "EM_ANDAMENTO" | "AJUSTADA_MANUALMENTE" | "PENDENTE",
      "total_horas_apuradas_s": 28800 | null,
      "tem_marcacao_pendente": false | true,
      "horario_inicio": "2026-05-27T12:00:00+00:00" | null,
      "horario_saida_almoco": "..." | null,
      "horario_retorno_almoco": "..." | null,
      "horario_fim": "..." | null
    }
  ]
}
Response 422: mes inválido (formato fora de YYYY-MM)

GET /api/v1/relatorios/{mes}   (auth Bearer)
Response 200: application/pdf (FileResponse) — gera on-demand se ausente/invalidado
Response 422: NO_DATA (sem jornadas)

POST /api/v1/relatorios/{mes}/enviar   (auth Bearer)
Request body (opcional): {"email": "destino@example.com"}
Response 202: {"status": "SUCESSO", "historico_id": "<uuid>"}
Response 422: {"code": "SMTP_NOT_CONFIGURED", ...}
Response 500: {"code": "SMTP_SEND_FAILED", "message": "Envio SMTP falhou após 3 tentativas: <erro>", ...}

GET /api/v1/terceiros/me   (auth Bearer; já consumido pelo AppLayout para nome — re-uso de cache)
Response 200: TerceiroResponse com email_destinatario_relatorio (string | null) — usado para pre-preencher modal
```

**Validação obrigatória pelo executor antes de marcar done:**

1. `cd apps/web && npm install` — novas deps `@mui/x-data-grid`, `@mui/x-date-pickers`, `dayjs` instaladas.
2. `cd apps/web && npm test -- --run src/pages/Jornadas/JornadasPage.test.tsx src/lib/format/horario.test.ts` — 7+ testes passam.
3. `cd apps/web && npm test -- --run` — toda a suite continua verde; coverage >= 80.
4. `cd apps/web && npm run typecheck` — 0 erros.
5. `cd apps/web && npm run lint` — 0 warnings.
6. `cd apps/web && npm run build` — `dist/` gerado sem erros.
7. `make smoke` (raiz) — Phase 1 smoke continua passando.

> Executor DEVE rodar 1–7 e garantir saída 0 antes de retornar. Falha = task não concluída.

**Refatoração:** após green, considerar (a) extrair `EnviarRelatorioDialog` para `src/components/EnviarRelatorioDialog.tsx` se TASK-027 (página `/relatorios`) reusar — provavelmente sim, mover então para `src/components/`. Por ora, manter em `pages/Jornadas/` (primeiro consumidor); TASK-027 pode mover.
