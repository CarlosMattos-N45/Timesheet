---
checkpoint: null
complexity: M
created_at: "2026-05-28 12:47:20"
criteria:
    - done: false
      test: cd apps/web && npm test -- --run src/pages/JornadaDetalhe/JornadaDetalhePage.test.tsx -t "breadcrumb"
      text: Mount /jornadas/j1 com FECHADA renderiza breadcrumb 27/05/2026, chip FECHADA, 4 TimePickers rotulados e total 08:00
    - done: false
      test: cd apps/web && npm test -- --run src/pages/JornadaDetalhe/JornadaDetalhePage.test.tsx -t "PENDENTE"
      text: Status PENDENTE exibe banner Esta jornada possui marcacoes pendentes. Ajuste os horarios sinalizados. e TimePickers ficam disabled
    - done: false
      test: cd apps/web && npm test -- --run src/pages/JornadaDetalhe/JornadaDetalhePage.test.tsx -t "Salvar alteracoes"
      text: 'Editar horario abre modal de justificativa; <5 chars desabilita Confirmar; ao confirmar com motivo valido, PUT /jornadas/j1 inclui o motivo e o array marcacoes apenas com tipos alterados (ex: INICIO_JORNADA)'
    - done: false
      test: cd apps/web && npm test -- --run src/pages/JornadaDetalhe/JornadaDetalhePage.test.tsx -t "VALIDATION_ERROR"
      text: 422 VALIDATION_ERROR no PUT exibe alert dentro do modal com o message exato do backend (passthrough)
    - done: false
      test: cd apps/web && npm test -- --run src/pages/JornadaDetalhe/JornadaDetalhePage.test.tsx -t "POST /jornadas/j1/atividade"
      text: Editar atividade e clicar Salvar atividade chama POST /jornadas/j1/atividade com descricao igual ao novo texto
    - done: false
      test: cd apps/web && npm test -- --run src/pages/JornadaDetalhe/JornadaDetalhePage.test.tsx -t "Historico de auditoria"
      text: Expandir Accordion Historico de auditoria carrega GET /auditoria?entidade=Jornada&entidade_id=j1 lazy (so apos expandir)
    - done: false
      text: Total diario eh recalculado em tempo real conforme TimePickers mudam usando calculaTotalDiario (segundos) e formatTotal
    - done: false
      test: cd apps/web && npm test -- --run src/lib/format/horario.test.ts -t "calculaTotalDiario"
      text: calculaTotalDiario com inicio 09:00, saida 12:00, retorno 13:00, fim 18:00 retorna 28800
    - done: false
      text: atividade com <10 chars desabilita botao Salvar atividade
    - done: false
      text: 'accessibility: TimePickers com aria-label, Accordion com aria-expanded controlado, Chip status com role=status'
    - done: false
      test: grep -E "<JornadaDetalhePage ?/>" apps/web/src/routes.tsx
      text: routes.tsx substitui JornadaDetalhePageStub por JornadaDetalhePage real
    - done: false
      text: ESLint passa sem warnings e tsc strict 0 erros
    - done: false
      text: Testes passando com cobertura >= 80%
    - done: false
      text: make smoke continua passando
deps:
    - TASK-020
    - TASK-023
id: TASK-024
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
tests: cd apps/web && npm test -- --run src/pages/JornadaDetalhe/JornadaDetalhePage.test.tsx
title: 'Jornada Detalhe (RF-007.2 + RF-007.4 + RF-010): edicao de horarios com modal de justificativa, atividade inline, accordion auditoria lazy, banner PENDENTE'
updated_at: "2026-05-28 12:47:20"
---
## Contexto

Implementar a página `/jornadas/:id` (RF-007.2 + RF-007.4 + RF-010) — detalhe da jornada com edição de horários, atividade inline, accordion de histórico de auditoria e justificativas anteriores. Slice: componente + sub-componentes + zod schemas + hooks de mutation + 1 modal de justificativa + substituição do stub em `routes.tsx`.

**State atual:**
- TASK-020 entregou `api/client`, `parseApiError`, `AppLayout`, `useAuth`, `renderWithProviders`, `JornadaDetalhePageStub` em `routes.tsx`.
- TASK-023 entregou `jornadasKeys`, `getJornadaDetalhe(id)`, `putAjusteJornada(id, body)`, `postAtividade(jornadaId, body)`, helpers `formatHoraBR`, `formatTotal`, `formatData`, `formatDiaSemana`.
- Backend Phase 3:
  - TASK-017 entregou `GET /api/v1/jornadas/{id}` (retorna `JornadaDetalheResponse` com `marcacoes`, `atividade`, `justificativas`), `PUT /api/v1/jornadas/{id}` (ajuste com `marcacoes` + `motivo`), `POST /api/v1/jornadas/{id}/atividade` (upsert).
  - TASK-017 entregou também `GET /api/v1/auditoria?entidade=Jornada&entidade_id=<id>` retornando `AuditoriaItem[]` ordenado por `criado_em DESC`.

**Decisão de UX (Spec §5 — `/jornadas/:id`):**
- Breadcrumb "Jornadas > DD/MM/YYYY" (link da primeira parte navega para `/jornadas`).
- Badge de status no cabeçalho (mesmo chip da lista).
- 4 campos de horário (MUI `TimePicker` de `@mui/x-date-pickers`), rotulados "Início", "Saída Almoço", "Retorno Almoço", "Fim".
  - **Editáveis** quando `status ∈ {FECHADA, AJUSTADA_MANUALMENTE}`.
  - **Bloqueados** (read-only) quando `status ∈ {EM_ANDAMENTO, PENDENTE}`.
  - Marcações com `status === "PENDENTE"` no array `marcacoes` recebem destaque âmbar (border, helper text "Marcação pendente — ajuste").
- Total diário calculado em tempo real conforme o usuário muda os horários (sem submeter): `total = (fim - inicio) - (retorno_almoco - saida_almoco)` em segundos; render via `formatTotal(secs)`.
- Textarea "Atividade do dia" (campo `descricao`, mínimo 10 chars, contador `X/2000`).
  - **Editável** em qualquer status exceto `EM_ANDAMENTO`.
  - Salvar via `POST /api/v1/jornadas/{id}/atividade` (upsert no backend).
- Botão "Salvar alterações" visível apenas se algo editado (form `isDirty=true`); ao clicar, abre modal "Justificativa" (textarea mínimo 5 chars + contador).
- Confirmar modal → `PUT /api/v1/jornadas/{id}` com `{marcacoes: [...alterações apenas...], motivo}` → sucesso invalida `jornadasKeys.detalhe(id)` + `jornadasKeys.lista(mes)` + `auditoriaKeys.list("Jornada", id)`; toast "Jornada atualizada com sucesso."
- Accordion colapsado "Histórico de auditoria": ao expandir, chama `GET /api/v1/auditoria?entidade=Jornada&entidade_id={id}` lazy. Lista ordem DESC: cada item exibe `criado_em` (formatado), `autor`, `motivo`, e bloco JSON colapsado com diff `antes_json` vs. `depois_json`.
- Seção "Justificativas anteriores" (acima ou abaixo do accordion): tabela com `criada_em`, `usuario_responsavel`, `motivo` para cada justificativa do array `justificativas`.
- Banner âmbar no topo se `status === "PENDENTE"`: "Esta jornada possui marcações pendentes. Ajuste os horários sinalizados."

**Acessibilidade:**
- TimePickers com `aria-label` explícito (ex.: `aria-label="Horário de início"`).
- Accordion com `aria-expanded` controlado por estado.
- Badge de status com `role="status"`.

**Dependência:** TASK-020, TASK-023 (já entregou jornadasKeys + helpers de formato + funções HTTP).

## Comportamento Esperado

| Entrada / Ação | Saída / Efeito esperado |
| -------------- | ----------------------- |
| Mount `/jornadas/j1` com jornada FECHADA, total `28800s`, 4 marcações 09:00/12:00/13:00/18:00 BRT | Breadcrumb "Jornadas > 27/05/2026"; chip verde "FECHADA"; 4 TimePickers preenchidos (não-bloqueados); total exibido "08:00"; textarea atividade preenchida |
| Mount com `status=PENDENTE` + marcação `tipo=FIM_JORNADA, status=PENDENTE` | Banner âmbar topo "Esta jornada possui marcações pendentes..."; TimePickers bloqueados (jornada PENDENTE); campo FIM destacado com border âmbar e helper text "Marcação pendente — ajuste" |
| Mudar horário Início para 08:55 BRT (jornada FECHADA) | Total recalculado em tempo real (`(18:00 - 08:55) - (13:00 - 12:00) = 8h05`); botão "Salvar alterações" aparece |
| Clicar "Salvar alterações" | Abre modal "Justificativa" com textarea (placeholder "Motivo da alteração (mínimo 5 caracteres)"), contador 0/500, botão Confirmar desabilitado até 5+ chars |
| Digitar motivo "ajuste de relógio" (16 chars) + Confirmar | Chama `PUT /api/v1/jornadas/j1` com `{marcacoes: [{tipo:"INICIO_JORNADA", horario_efetivo:"<ISO UTC>"}], motivo:"ajuste de relógio"}`; sucesso 200 → fecha modal + toast "Jornada atualizada com sucesso." + invalida cache (lista + detalhe + auditoria) |
| 422 VALIDATION_ERROR no PUT | Modal permanece; alert vermelho com `parsed.message` |
| Editar atividade de "Trabalhei X" para "Trabalhei X com sub-tarefa Y" + blur | Chama `POST /api/v1/jornadas/j1/atividade` com `{descricao:"..."}`; sucesso 201 → toast "Atividade atualizada." + invalida cache de detalhe |
| Atividade < 10 chars + tentar salvar | Helper text "Mínimo 10 caracteres"; botão "Salvar atividade" desabilitado |
| Expandir accordion "Histórico de auditoria" | Lazy: chama `GET /api/v1/auditoria?entidade=Jornada&entidade_id=j1`; renderiza N itens ordem DESC com motivo, autor, criado_em formatado |
| Voltar via breadcrumb "Jornadas" | `navigate("/jornadas")` |

## TDD

**Testes a escrever antes da implementação** (`apps/web/src/pages/JornadaDetalhe/JornadaDetalhePage.test.tsx`):

```typescript
import { describe, it, expect, beforeEach, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MockAdapter from "axios-mock-adapter";
import api from "@/api/client";
import { renderWithProviders } from "@/test/render";
import { JornadaDetalhePage } from "@/pages/JornadaDetalhe/JornadaDetalhePage";

const mock = new MockAdapter(api);

const J_FECHADA = {
  id: "j1", data: "2026-05-27", status: "FECHADA",
  total_horas_apuradas_s: 28800,
  marcacoes: [
    { id: "m1", tipo: "INICIO_JORNADA", horario_registrado: "2026-05-27T12:00:00+00:00", horario_efetivo: "2026-05-27T12:00:00+00:00", origem: "AGENTE_AUTOMATICO", status: "CONFIRMADA" },
    { id: "m2", tipo: "SAIDA_ALMOCO", horario_registrado: "2026-05-27T15:00:00+00:00", horario_efetivo: "2026-05-27T15:00:00+00:00", origem: "AGENTE_AUTOMATICO", status: "CONFIRMADA" },
    { id: "m3", tipo: "RETORNO_ALMOCO", horario_registrado: "2026-05-27T16:00:00+00:00", horario_efetivo: "2026-05-27T16:00:00+00:00", origem: "AGENTE_AUTOMATICO", status: "CONFIRMADA" },
    { id: "m4", tipo: "FIM_JORNADA", horario_registrado: "2026-05-27T21:00:00+00:00", horario_efetivo: "2026-05-27T21:00:00+00:00", origem: "AGENTE_CONFIRMADO", status: "CONFIRMADA" },
  ],
  atividade: { id: "a1", jornada_id: "j1", descricao: "Trabalhei no projeto X", registrada_em: "2026-05-27T21:05:00+00:00", atualizado_em: null },
  justificativas: [],
};

beforeEach(() => {
  mock.reset();
  sessionStorage.setItem("ts:access_token", "tok");
  sessionStorage.setItem("ts:refresh_token", "r");
  sessionStorage.setItem("ts:terceiro_id", "u1");
  sessionStorage.setItem("ts:expires_at", String(Date.now() + 60_000));
});

describe("JornadaDetalhePage", () => {
  it("renderiza breadcrumb, chip FECHADA verde, 4 horários e total 08:00", async () => {
    mock.onGet("/api/v1/jornadas/j1").reply(200, J_FECHADA);
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria" });
    renderWithProviders(<JornadaDetalhePage />, { route: "/jornadas/j1" });
    expect(await screen.findByText(/27\/05\/2026/)).toBeInTheDocument();
    expect(screen.getByText("FECHADA")).toBeInTheDocument();
    // Total visível
    expect(screen.getByText(/Total:\s*08:00/i)).toBeInTheDocument();
    // 4 TimePickers presentes pelo aria-label
    expect(screen.getByLabelText(/Horário de início/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Horário de saída do almoço/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Horário de retorno do almoço/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Horário de fim/i)).toBeInTheDocument();
  });

  it("status PENDENTE exibe banner topo e bloqueia TimePickers", async () => {
    mock.onGet("/api/v1/jornadas/j1").reply(200, {
      ...J_FECHADA, status: "PENDENTE",
      marcacoes: [
        ...J_FECHADA.marcacoes.slice(0, 3),
        { ...J_FECHADA.marcacoes[3], status: "PENDENTE" },
      ],
    });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria" });
    renderWithProviders(<JornadaDetalhePage />, { route: "/jornadas/j1" });
    expect(await screen.findByText(/Esta jornada possui marcações pendentes\./i)).toBeInTheDocument();
    const tp = screen.getByLabelText(/Horário de início/i) as HTMLInputElement;
    expect(tp).toBeDisabled();
  });

  it("salvar alteração abre modal de justificativa; <5 chars desabilita Confirmar; >=5 chars habilita e PUT /jornadas/j1 com motivo + 1 marcação", async () => {
    mock.onGet("/api/v1/jornadas/j1").reply(200, J_FECHADA);
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria" });
    let putBody: any = null;
    mock.onPut("/api/v1/jornadas/j1").reply((c) => {
      putBody = JSON.parse(c.data as string);
      return [200, { ...J_FECHADA, status: "AJUSTADA_MANUALMENTE" }];
    });
    renderWithProviders(<JornadaDetalhePage />, { route: "/jornadas/j1" });
    const inicio = await screen.findByLabelText(/Horário de início/i) as HTMLInputElement;
    await userEvent.clear(inicio);
    await userEvent.type(inicio, "08:55");
    await userEvent.tab();
    // Botão Salvar visível
    const btnSalvar = await screen.findByRole("button", { name: /Salvar alterações/i });
    await userEvent.click(btnSalvar);
    // Modal de justificativa aberto
    const motivo = screen.getByLabelText(/Motivo/i) as HTMLTextAreaElement;
    expect(screen.getByRole("button", { name: /Confirmar alterações/i })).toBeDisabled();
    await userEvent.type(motivo, "ajuste de relógio");
    expect(screen.getByRole("button", { name: /Confirmar alterações/i })).toBeEnabled();
    await userEvent.click(screen.getByRole("button", { name: /Confirmar alterações/i }));
    await waitFor(() => expect(putBody).not.toBeNull());
    expect(putBody.motivo).toBe("ajuste de relógio");
    expect(putBody.marcacoes).toEqual([
      expect.objectContaining({ tipo: "INICIO_JORNADA" }),
    ]);
  });

  it("422 VALIDATION_ERROR no PUT exibe alert com mensagem do backend dentro do modal", async () => {
    mock.onGet("/api/v1/jornadas/j1").reply(200, J_FECHADA);
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria" });
    mock.onPut("/api/v1/jornadas/j1").reply(422, {
      code: "VALIDATION_ERROR",
      message: "horários devem ser cronológicos",
      details: [],
    });
    renderWithProviders(<JornadaDetalhePage />, { route: "/jornadas/j1" });
    const inicio = await screen.findByLabelText(/Horário de início/i) as HTMLInputElement;
    await userEvent.clear(inicio);
    await userEvent.type(inicio, "19:00");
    await userEvent.tab();
    await userEvent.click(await screen.findByRole("button", { name: /Salvar alterações/i }));
    await userEvent.type(screen.getByLabelText(/Motivo/i), "tentando inverter");
    await userEvent.click(screen.getByRole("button", { name: /Confirmar alterações/i }));
    expect(await screen.findByText(/horários devem ser cronológicos/i)).toBeInTheDocument();
  });

  it("editar atividade e blur chama POST /jornadas/j1/atividade", async () => {
    mock.onGet("/api/v1/jornadas/j1").reply(200, J_FECHADA);
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria" });
    let postBody: any = null;
    mock.onPost("/api/v1/jornadas/j1/atividade").reply((c) => {
      postBody = JSON.parse(c.data as string);
      return [201, { id: "a1", jornada_id: "j1", descricao: postBody.descricao, registrada_em: "...", atualizado_em: "..." }];
    });
    renderWithProviders(<JornadaDetalhePage />, { route: "/jornadas/j1" });
    const ta = await screen.findByLabelText(/Atividade do dia/i) as HTMLTextAreaElement;
    await userEvent.clear(ta);
    await userEvent.type(ta, "Trabalhei no projeto X com sub-tarefa Y");
    await userEvent.click(screen.getByRole("button", { name: /Salvar atividade/i }));
    await waitFor(() => expect(postBody?.descricao).toBe("Trabalhei no projeto X com sub-tarefa Y"));
  });

  it("expandir accordion Histórico de auditoria carrega GET /auditoria lazy", async () => {
    mock.onGet("/api/v1/jornadas/j1").reply(200, J_FECHADA);
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria" });
    let auditChamado = false;
    mock.onGet("/api/v1/auditoria").reply(() => {
      auditChamado = true;
      return [200, [{
        id: "log1", entidade: "Jornada", entidade_id: "j1", autor: "maria@acme.com",
        antes_json: '{"x":1}', depois_json: '{"x":2}', motivo: "ajuste",
        criado_em: "2026-05-27T22:00:00+00:00",
      }]];
    });
    renderWithProviders(<JornadaDetalhePage />, { route: "/jornadas/j1" });
    expect(auditChamado).toBe(false);
    const acc = await screen.findByRole("button", { name: /Histórico de auditoria/i });
    expect(acc).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(acc);
    await waitFor(() => expect(auditChamado).toBe(true));
    expect(acc).toHaveAttribute("aria-expanded", "true");
    expect(await screen.findByText(/maria@acme\.com/i)).toBeInTheDocument();
  });
});
```

**Refatoração:** após green, considerar (a) extrair cálculo de total para `src/lib/format/horario.ts` como `calculaTotalDiario(inicio, saidaAlmoco, retornoAlmoco, fim): number` — TASK-025 (jornada manual) também usa o mesmo cálculo.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| ------- | ---- | --------- |
| `apps/web/src/pages/JornadaDetalhe/JornadaDetalhePage.tsx` | Criar | Componente principal |
| `apps/web/src/pages/JornadaDetalhe/JustificativaDialog.tsx` | Criar | Modal de motivo |
| `apps/web/src/pages/JornadaDetalhe/HistoricoAuditoria.tsx` | Criar | Accordion com chamada lazy |
| `apps/web/src/pages/JornadaDetalhe/JornadaDetalhePage.test.tsx` | Criar | TDD acima |
| `apps/web/src/api/auditoria.ts` | Criar | `auditoriaKeys` + `getAuditoria(entidade, entidadeId)` |
| `apps/web/src/lib/schemas/jornada.ts` | Criar | Zod schemas: `ajusteSchema` (motivo>=5), `atividadeSchema` (descricao>=10) |
| `apps/web/src/lib/format/horario.ts` | Modificar | Adicionar `calculaTotalDiario(inicio, saidaAlmoco, retornoAlmoco, fim)` |
| `apps/web/src/routes.tsx` | Modificar | Substituir `JornadaDetalhePageStub` por `JornadaDetalhePage` |

> 6 criados + 2 modificados = **8 arquivos-alvo**. Dentro do teto.

### Detalhamento Técnico

**1. `src/api/auditoria.ts`:**

```typescript
import api from "./client";
import type { AuditoriaItem } from "@/types/contracts";

export const auditoriaKeys = {
  list: (entidade: string, entidadeId: string) => ["auditoria", entidade, entidadeId] as const,
};

export async function getAuditoria(entidade: AuditoriaItem["entidade"], entidadeId: string): Promise<AuditoriaItem[]> {
  const r = await api.get<AuditoriaItem[]>("/api/v1/auditoria", { params: { entidade, entidade_id: entidadeId } });
  return r.data;
}
```

**2. `src/lib/schemas/jornada.ts`:**

```typescript
import { z } from "zod";

export const ajusteSchema = z.object({
  motivo: z.string().min(5, "Mínimo 5 caracteres").max(500, "Máximo 500 caracteres"),
});
export type AjusteFormValues = z.infer<typeof ajusteSchema>;

export const atividadeSchema = z.object({
  descricao: z.string().min(10, "Mínimo 10 caracteres").max(2000, "Máximo 2000 caracteres"),
});
export type AtividadeFormValues = z.infer<typeof atividadeSchema>;
```

**3. `src/lib/format/horario.ts` — adição:**

```typescript
import dayjs from "dayjs";

export function calculaTotalDiario(
  inicio: string | null,
  saidaAlmoco: string | null,
  retornoAlmoco: string | null,
  fim: string | null
): number | null {
  if (!inicio || !fim) return null;
  const ini = dayjs(inicio).valueOf();
  const f = dayjs(fim).valueOf();
  if (Number.isNaN(ini) || Number.isNaN(f) || f <= ini) return null;
  let totalMs = f - ini;
  if (saidaAlmoco && retornoAlmoco) {
    const sa = dayjs(saidaAlmoco).valueOf();
    const ra = dayjs(retornoAlmoco).valueOf();
    if (!Number.isNaN(sa) && !Number.isNaN(ra) && ra > sa) {
      totalMs -= ra - sa;
    }
  }
  return Math.floor(totalMs / 1000);
}
```

> **Quirk dayjs `.valueOf()`**: retorna ms; conversão final divide por 1000 para devolver segundos (formato do backend).

**4. `src/pages/JornadaDetalhe/JornadaDetalhePage.tsx`** (resumo — partes-chave):

```typescript
import { useState, useMemo } from "react";
import { useParams, useNavigate, Link as RouterLink } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import dayjs, { type Dayjs } from "dayjs";
import {
  Container, Breadcrumbs, Link, Typography, Box, Chip, Stack, Button,
  TextField, Snackbar, Alert,
} from "@mui/material";
import { TimePicker, LocalizationProvider } from "@mui/x-date-pickers";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { getJornadaDetalhe, putAjusteJornada, postAtividade, jornadasKeys } from "@/api/jornadas";
import { auditoriaKeys } from "@/api/auditoria";
import { formatData, formatTotal, calculaTotalDiario } from "@/lib/format/horario";
import { parseApiError } from "@/lib/errors";
import { JustificativaDialog } from "./JustificativaDialog";
import { HistoricoAuditoria } from "./HistoricoAuditoria";
import type { JornadaDetalheResponse, MarcacaoDetalhe, TipoMarcacao, StatusJornada } from "@/types/contracts";

const STATUS_COLOR: Record<StatusJornada, "default" | "success" | "warning" | "error"> = {
  EM_ANDAMENTO: "default", FECHADA: "success", AJUSTADA_MANUALMENTE: "warning", PENDENTE: "error",
};

const TIPO_LABEL: Record<TipoMarcacao, string> = {
  INICIO_JORNADA: "Horário de início",
  SAIDA_ALMOCO: "Horário de saída do almoço",
  RETORNO_ALMOCO: "Horário de retorno do almoço",
  FIM_JORNADA: "Horário de fim",
};

const TIPOS_ORDEM: TipoMarcacao[] = ["INICIO_JORNADA", "SAIDA_ALMOCO", "RETORNO_ALMOCO", "FIM_JORNADA"];

export function JornadaDetalhePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [editado, setEditado] = useState<Record<TipoMarcacao, Dayjs | null>>({
    INICIO_JORNADA: null, SAIDA_ALMOCO: null, RETORNO_ALMOCO: null, FIM_JORNADA: null,
  });
  const [atividadeTxt, setAtividadeTxt] = useState("");
  const [atividadeDirty, setAtividadeDirty] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [snackbar, setSnackbar] = useState<{ msg: string; severity: "success" | "error" } | null>(null);

  const { data: jornada, isLoading } = useQuery({
    queryKey: jornadasKeys.detalhe(id!),
    queryFn: () => getJornadaDetalhe(id!),
    enabled: Boolean(id),
  });

  // Sincronizar estado local com fetch
  useMemo(() => {
    if (jornada) {
      const map: Record<TipoMarcacao, Dayjs | null> = {
        INICIO_JORNADA: null, SAIDA_ALMOCO: null, RETORNO_ALMOCO: null, FIM_JORNADA: null,
      };
      for (const m of jornada.marcacoes) {
        const h = m.horario_efetivo ?? m.horario_registrado;
        map[m.tipo as TipoMarcacao] = dayjs(h);
      }
      // Apenas resetar se ainda não editado
      setEditado((prev) => {
        const algumEditado = TIPOS_ORDEM.some((t) => prev[t] !== null);
        return algumEditado ? prev : map;
      });
      setAtividadeTxt(jornada.atividade?.descricao ?? "");
    }
  }, [jornada]);

  const editavel = jornada ? (jornada.status === "FECHADA" || jornada.status === "AJUSTADA_MANUALMENTE") : false;
  const atividadeEditavel = jornada ? jornada.status !== "EM_ANDAMENTO" : false;

  const marcacoesAlteradas = useMemo<{ tipo: TipoMarcacao; horario_efetivo: string }[]>(() => {
    if (!jornada) return [];
    const alts: { tipo: TipoMarcacao; horario_efetivo: string }[] = [];
    for (const m of jornada.marcacoes) {
      const tipo = m.tipo as TipoMarcacao;
      const original = dayjs(m.horario_efetivo ?? m.horario_registrado);
      const atual = editado[tipo];
      if (atual && !atual.isSame(original, "minute")) {
        alts.push({ tipo, horario_efetivo: atual.utc().toISOString() });
      }
    }
    return alts;
  }, [jornada, editado]);

  const isDirty = marcacoesAlteradas.length > 0;

  const totalAtual = useMemo(() => {
    return calculaTotalDiario(
      editado.INICIO_JORNADA?.toISOString() ?? null,
      editado.SAIDA_ALMOCO?.toISOString() ?? null,
      editado.RETORNO_ALMOCO?.toISOString() ?? null,
      editado.FIM_JORNADA?.toISOString() ?? null,
    );
  }, [editado]);

  const mutationAjuste = useMutation({
    mutationFn: (motivo: string) => putAjusteJornada(id!, { marcacoes: marcacoesAlteradas, motivo }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: jornadasKeys.detalhe(id!) });
      void qc.invalidateQueries({ queryKey: jornadasKeys.all });
      void qc.invalidateQueries({ queryKey: auditoriaKeys.list("Jornada", id!) });
      setDialogOpen(false);
      setSnackbar({ msg: "Jornada atualizada com sucesso.", severity: "success" });
    },
  });

  const mutationAtividade = useMutation({
    mutationFn: () => postAtividade(id!, { descricao: atividadeTxt }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: jornadasKeys.detalhe(id!) });
      void qc.invalidateQueries({ queryKey: auditoriaKeys.list("Atividade", id!) });
      setAtividadeDirty(false);
      setSnackbar({ msg: "Atividade atualizada.", severity: "success" });
    },
    onError: (e) => {
      const p = parseApiError(e);
      setSnackbar({ msg: p.message, severity: "error" });
    },
  });

  if (isLoading || !jornada) return <Container sx={{ mt: 3 }}>Carregando...</Container>;

  return (
    <Container maxWidth="lg" sx={{ mt: 2 }}>
      <Breadcrumbs>
        <Link component={RouterLink} to="/jornadas">Jornadas</Link>
        <Typography color="text.primary">{formatData(jornada.data).replace("/", "/")}/{dayjs(jornada.data).format("YYYY")}</Typography>
      </Breadcrumbs>
      <Box display="flex" alignItems="center" gap={2} mt={2}>
        <Typography variant="h4" component="h1">{dayjs(jornada.data).format("DD/MM/YYYY")}</Typography>
        <Chip
          label={jornada.status}
          color={STATUS_COLOR[jornada.status]}
          role="status"
          aria-label={`Status: ${jornada.status}`}
        />
      </Box>

      {jornada.status === "PENDENTE" && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          Esta jornada possui marcações pendentes. Ajuste os horários sinalizados.
        </Alert>
      )}

      <LocalizationProvider dateAdapter={AdapterDayjs}>
        <Stack direction="row" spacing={2} mt={3} flexWrap="wrap">
          {TIPOS_ORDEM.map((tipo) => {
            const marc = jornada.marcacoes.find((m) => m.tipo === tipo);
            const pendente = marc?.status === "PENDENTE";
            return (
              <TimePicker
                key={tipo}
                label={TIPO_LABEL[tipo]}
                value={editado[tipo]}
                onChange={(v) => setEditado((prev) => ({ ...prev, [tipo]: v }))}
                disabled={!editavel}
                slotProps={{
                  textField: {
                    "aria-label": TIPO_LABEL[tipo],
                    error: pendente,
                    helperText: pendente ? "Marcação pendente — ajuste" : undefined,
                    sx: pendente ? { "& .MuiOutlinedInput-root": { borderColor: "warning.main" } } : undefined,
                  },
                }}
              />
            );
          })}
        </Stack>
      </LocalizationProvider>

      <Box mt={2}>
        <Typography variant="body1">Total: <strong>{formatTotal(totalAtual)}</strong></Typography>
      </Box>

      <Box mt={3}>
        <TextField
          label="Atividade do dia"
          multiline
          minRows={3}
          fullWidth
          value={atividadeTxt}
          disabled={!atividadeEditavel}
          onChange={(e) => { setAtividadeTxt(e.target.value); setAtividadeDirty(true); }}
          helperText={`${atividadeTxt.length}/2000` + (atividadeTxt.length < 10 ? " — Mínimo 10 caracteres" : "")}
          error={atividadeDirty && atividadeTxt.length < 10}
        />
        <Box mt={1}>
          <Button
            variant="outlined"
            disabled={!atividadeDirty || atividadeTxt.length < 10 || mutationAtividade.isPending}
            onClick={() => mutationAtividade.mutate()}
          >
            Salvar atividade
          </Button>
        </Box>
      </Box>

      {isDirty && (
        <Box mt={3}>
          <Button variant="contained" onClick={() => setDialogOpen(true)}>
            Salvar alterações
          </Button>
        </Box>
      )}

      <Box mt={4}>
        <Typography variant="h6" gutterBottom>Justificativas anteriores</Typography>
        {jornada.justificativas.length === 0 ? (
          <Typography color="text.secondary">Nenhuma.</Typography>
        ) : (
          <Stack spacing={1}>
            {jornada.justificativas.map((j) => (
              <Box key={j.id} p={1} border={1} borderColor="divider" borderRadius={1}>
                <Typography variant="caption">{dayjs(j.criada_em).format("DD/MM/YYYY HH:mm")} — {j.usuario_responsavel}</Typography>
                <Typography>{j.motivo}</Typography>
              </Box>
            ))}
          </Stack>
        )}
      </Box>

      <Box mt={4}>
        <HistoricoAuditoria jornadaId={jornada.id} />
      </Box>

      <JustificativaDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onConfirm={(motivo) => mutationAjuste.mutate(motivo)}
        loading={mutationAjuste.isPending}
        error={mutationAjuste.error ? parseApiError(mutationAjuste.error).message : null}
      />

      <Snackbar
        open={Boolean(snackbar)}
        autoHideDuration={5000}
        onClose={() => setSnackbar(null)}
      >
        <Alert severity={snackbar?.severity ?? "info"} onClose={() => setSnackbar(null)} role={snackbar?.severity === "error" ? "alert" : "status"}>
          {snackbar?.msg}
        </Alert>
      </Snackbar>
    </Container>
  );
}
```

**5. `src/pages/JornadaDetalhe/JustificativaDialog.tsx`:**

```typescript
import { useEffect, useState } from "react";
import {
  Dialog, DialogTitle, DialogContent, DialogActions, TextField, Button, Alert,
} from "@mui/material";

interface Props {
  open: boolean;
  onClose: () => void;
  onConfirm: (motivo: string) => void;
  loading: boolean;
  error: string | null;
}

export function JustificativaDialog({ open, onClose, onConfirm, loading, error }: Props) {
  const [motivo, setMotivo] = useState("");
  useEffect(() => { if (open) setMotivo(""); }, [open]);
  const ok = motivo.trim().length >= 5;
  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Justificativa do ajuste</DialogTitle>
      <DialogContent>
        <TextField
          label="Motivo"
          multiline
          minRows={3}
          fullWidth
          margin="normal"
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
          helperText={`${motivo.length}/500` + (motivo.length < 5 ? " — Mínimo 5 caracteres" : "")}
          inputProps={{ maxLength: 500, "aria-label": "Motivo da alteração" }}
        />
        {error && <Alert severity="error" role="alert">{error}</Alert>}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancelar</Button>
        <Button variant="contained" disabled={!ok || loading} onClick={() => onConfirm(motivo)}>
          {loading ? "Salvando..." : "Confirmar alterações"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
```

**6. `src/pages/JornadaDetalhe/HistoricoAuditoria.tsx`:**

```typescript
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Accordion, AccordionSummary, AccordionDetails, Stack, Box, Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import dayjs from "dayjs";
import { getAuditoria, auditoriaKeys } from "@/api/auditoria";

interface Props { jornadaId: string; }

export function HistoricoAuditoria({ jornadaId }: Props) {
  const [expanded, setExpanded] = useState(false);
  const { data, isLoading } = useQuery({
    queryKey: auditoriaKeys.list("Jornada", jornadaId),
    queryFn: () => getAuditoria("Jornada", jornadaId),
    enabled: expanded, // lazy
  });

  return (
    <Accordion expanded={expanded} onChange={(_e, v) => setExpanded(v)}>
      <AccordionSummary expandIcon={<ExpandMoreIcon />} aria-controls="audit-content">
        <Typography>Histórico de auditoria</Typography>
      </AccordionSummary>
      <AccordionDetails>
        {isLoading && <Typography>Carregando...</Typography>}
        {data && data.length === 0 && <Typography color="text.secondary">Nenhum registro.</Typography>}
        <Stack spacing={1}>
          {data?.map((log) => (
            <Box key={log.id} p={1} border={1} borderColor="divider" borderRadius={1}>
              <Typography variant="caption">
                {dayjs(log.criado_em).format("DD/MM/YYYY HH:mm")} — {log.autor}
              </Typography>
              <Typography>Motivo: {log.motivo ?? "—"}</Typography>
              <Box mt={1} component="pre" sx={{ fontSize: 12, bgcolor: "grey.100", p: 1, borderRadius: 1, whiteSpace: "pre-wrap" }}>
                Antes: {log.antes_json ?? "—"}
                {"\n"}Depois: {log.depois_json}
              </Box>
            </Box>
          ))}
        </Stack>
      </AccordionDetails>
    </Accordion>
  );
}
```

**7. `src/routes.tsx` — diff:**

```typescript
import { JornadaDetalhePage } from "@/pages/JornadaDetalhe/JornadaDetalhePage";
// Substituir:
// { path: "/jornadas/:id", element: <JornadaDetalhePageStub /> },
// Por:
// { path: "/jornadas/:id", element: <JornadaDetalhePage /> },
```

## Contratos com camadas adjacentes

```
Produz para:
  - auditoriaKeys e getAuditoria: também consumidos por TASK-026 (cadastro: auditoria de "Terceiro").
  - calculaTotalDiario: também consumido por TASK-025 (jornada manual com preview de total).
  - JustificativaDialog: padrão de modal de motivo; TASK-025 também usa motivo>=5.

Consome de:
  TASK-020: api/client, parseApiError, renderWithProviders.
  TASK-023: jornadasKeys, getJornadaDetalhe, putAjusteJornada, postAtividade, formatHoraBR, formatTotal, formatData.
  Backend Phase 3 TASK-017: GET/PUT /jornadas/{id}, POST /jornadas/{id}/atividade, GET /auditoria.

Erros:
  - 401: tratado pelo interceptor.
  - 404 jornada: redirect /jornadas (banner "Jornada não encontrada"); fallback no useQuery.error.
  - 422 motivo<5 / atividade<10: bloqueio client-side antes do PUT; redundância no backend.
  - 422 horários fora de ordem (PUT): alert no modal com message do backend (passthrough).
```

## Contrato HTTP

```
GET /api/v1/jornadas/{id}   (auth Bearer)
Response 200:
{
  "id": "<uuid>",
  "data": "2026-05-27",
  "status": "FECHADA" | "EM_ANDAMENTO" | "AJUSTADA_MANUALMENTE" | "PENDENTE",
  "total_horas_apuradas_s": 28800 | null,
  "marcacoes": [
    {
      "id": "<uuid>",
      "tipo": "INICIO_JORNADA" | "SAIDA_ALMOCO" | "RETORNO_ALMOCO" | "FIM_JORNADA",
      "horario_registrado": "<ISO UTC>",
      "horario_efetivo": "<ISO UTC>" | null,
      "origem": "AGENTE_AUTOMATICO" | "AGENTE_CONFIRMADO" | "AJUSTE_WEB",
      "status": "CONFIRMADA" | "PENDENTE" | "AJUSTADA"
    }
  ],
  "atividade": { "id":"...", "jornada_id":"...", "descricao":"...", "registrada_em":"<ISO>", "atualizado_em":"<ISO>"|null } | null,
  "justificativas": [{ "id":"...", "motivo":"...", "usuario_responsavel":"...", "criada_em":"<ISO>" }]
}
Response 404: jornada inexistente / de outro terceiro

PUT /api/v1/jornadas/{id}   (auth Bearer)
Request body:
{
  "marcacoes": [
    { "tipo": "INICIO_JORNADA", "horario_efetivo": "2026-05-27T11:55:00Z" }  // ISO UTC; 1..4 itens (somente alterações)
  ],
  "motivo": "ajuste de relógio interno"   // min 5 chars
}
Response 200: JornadaDetalheResponse atualizada (status=AJUSTADA_MANUALMENTE)
Response 422: {"code":"VALIDATION_ERROR","message":"motivo<5"|"horários devem ser cronológicos",...}
Response 404: jornada inexistente

POST /api/v1/jornadas/{id}/atividade   (auth Bearer)
Request body: { "descricao": "trabalhei oito horas no projeto X" }  // min 10, max 2000
Response 201: AtividadeDetalhe (id, jornada_id, descricao, registrada_em, atualizado_em); +1 LogAuditoria(Atividade)
Response 404: jornada inexistente
Response 422: descricao<10

GET /api/v1/auditoria?entidade=Jornada&entidade_id=<id>   (auth Bearer)
Response 200: [AuditoriaItem, ...] ordenado por criado_em DESC
Response 422: entidade fora de {Jornada,Marcacao,Terceiro,Atividade}
```

**Validação obrigatória pelo executor antes de marcar done:**

1. `cd apps/web && npm test -- --run src/pages/JornadaDetalhe/JornadaDetalhePage.test.tsx` — 6 testes passam.
2. `cd apps/web && npm test -- --run` — toda a suite continua verde; coverage >= 80.
3. `cd apps/web && npm run typecheck` — 0 erros.
4. `cd apps/web && npm run lint` — 0 warnings.
5. `cd apps/web && npm run build` — `dist/` gerado sem erros.
6. `make smoke` (raiz) — Phase 1 smoke continua passando.

> Executor DEVE rodar 1–6 e garantir saída 0 antes de retornar.

**Refatoração:** após green, considerar extrair `STATUS_COLOR` e `TIPO_LABEL` para `src/lib/labels.ts` se TASK-025 também usar. Mover `JustificativaDialog` para `src/components/` se TASK-025 reusar.
