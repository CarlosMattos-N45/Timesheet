---
checkpoint: null
complexity: M
created_at: "2026-05-28 12:49:57"
criteria:
    - done: false
      test: cd apps/web && npm test -- --run src/pages/JornadaManual/JornadaManualPage.test.tsx -t "heading h1"
      text: Mount /jornadas/manual renderiza heading h1 Nova Jornada Manual com botao Salvar desabilitado por padrao
    - done: false
      test: cd apps/web && npm test -- --run src/pages/JornadaManual/JornadaManualPage.test.tsx -t "ISO UTC"
      text: Submit valido com data 2026-05-27 + 4 horarios + atividade>=10 + motivo>=5 chama POST /api/v1/jornadas/manual com data=2026-05-27, 4 marcacoes em ordem (INICIO_JORNADA, SAIDA_ALMOCO, RETORNO_ALMOCO, FIM_JORNADA), horario_efetivo em ISO UTC com offset (09:00 BRT vira T12:00:00, 18:00 vira T21:00:00), e navega para /jornadas/<id_novo>
    - done: false
      test: cd apps/web && npm test -- --run src/pages/JornadaManual/JornadaManualPage.test.tsx -t "cronologica"
      text: 'Horarios fora de ordem (ex: inicio 14:00 + saida 12:00) exibem helper text exato Os horarios devem ser em ordem cronologica. e desabilitam Salvar'
    - done: false
      test: cd apps/web && npm test -- --run src/pages/JornadaManual/JornadaManualPage.test.tsx -t "Minimo 10 caracteres"
      text: Atividade <10 chars exibe helper Minimo 10 caracteres e desabilita Salvar
    - done: false
      test: cd apps/web && npm test -- --run src/pages/JornadaManual/JornadaManualPage.test.tsx -t "CONFLICT"
      text: 409 CONFLICT exibe alert texto exato Ja existe uma jornada para este dia. Abra-a para editar. + link/botao Voltar para Jornadas
    - done: false
      test: cd apps/web && npm test -- --run src/pages/JornadaManual/JornadaManualPage.test.tsx -t "Cancelar"
      text: Cancelar navega para /jornadas (window.location.pathname=/jornadas)
    - done: false
      text: DatePicker bloqueia datas futuras (maxDate=today)
    - done: false
      test: grep -E "<JornadaManualPage ?/>" apps/web/src/routes.tsx
      text: routes.tsx substitui JornadaManualPageStub por JornadaManualPage real
    - done: false
      text: ESLint passa sem warnings e tsc strict 0 erros
    - done: false
      text: Testes passando com cobertura >= 80%
    - done: false
      text: make smoke continua passando
deps:
    - TASK-020
    - TASK-023
    - TASK-024
id: TASK-025
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
tests: cd apps/web && npm test -- --run src/pages/JornadaManual/JornadaManualPage.test.tsx
title: 'Jornada Manual (RF-007.3): pagina /jornadas/manual com DatePicker (maxDate=today), 4 TimePickers cronologicos, atividade>=10, motivo>=5, preview de total, POST /jornadas/manual, navegacao para detalhe'
updated_at: "2026-05-28 17:56:43"
worktree:
    base_sha: 81a15722cd113b86fa309ef5e318bb255d02174b
    branch: worktree-agent-475e4fba7c46665d
    path: .n45\worktree\agent-475e4fba7c46665d
---
## Contexto

Implementar a página `/jornadas/manual` (RF-007.3) — criação de jornada para dia sem eventos (data + 4 horários + atividade + justificativa). Slice: componente + zod schema + integração com `POST /api/v1/jornadas/manual` + substituição do stub em `routes.tsx`.

**State atual:**
- TASK-020 entregou `api/client`, `parseApiError`, `AppLayout`, `renderWithProviders`, `JornadaManualPageStub` em `routes.tsx`.
- TASK-023 entregou `postJornadaManual(body)`, `jornadasKeys`, helpers `formatHoraBR`, `formatTotal`, `formatData`, `formatDiaSemana`.
- TASK-024 entregou `calculaTotalDiario(...)` em `src/lib/format/horario.ts` — esta task **consome**.

**Decisão de UX (Spec §5 — `/jornadas/manual`):**
- Cabeçalho `<h1>` "Nova Jornada Manual".
- MUI `DatePicker` (não TimePicker) para a data — `maxDate=today` (dias futuros desabilitados). **Indicação visual de "dia com jornada existente"**: backend não expõe esse meta diretamente, então a página chama `GET /api/v1/jornadas?mes={mes_da_data_selecionada}` (já em cache via `jornadasKeys.lista(mes)` se TASK-023 carregou) e marca dias presentes com `dot` no calendário via `slots.day` customizado.
- 4 MUI `TimePicker`s para os 4 horários, ordem visual: Início, Saída Almoço, Retorno Almoço, Fim. Validação cronológica em tempo real: `inicio < saida_almoco < retorno_almoco < fim`; se violado, helper text inline no campo violador "Os horários devem ser em ordem cronológica."
- Textarea "Atividade" — `descricao` min 10 chars, contador `X/2000`.
- Textarea "Justificativa" — `motivo` min 5 chars, contador `X/500`.
- Total diário (preview) usando `calculaTotalDiario` (de TASK-024) — exibido em tempo real "Total: HH:MM".
- Botão "Salvar" — desabilitado até `isValid=true` (formulário Zod) e total > 0.
- Botão "Cancelar" → `navigate("/jornadas")`.
- Sucesso 201 → invalida `jornadasKeys.lista(mes)` + navega para `/jornadas/{novo_id}` (do `Location` da response, que vem no body como `id`).
- Erro 409 CONFLICT "Já existe jornada para este dia" → alert vermelho "Já existe uma jornada para este dia. Abra-a para editar." + link "Abrir jornada existente" navega para `/jornadas` (não tem id do existente — alternativa rejeitada de chamar GET extra; usuário volta à lista).
- Erro 422 (horários fora de ordem / atividade<10 / motivo<5) → alert vermelho com `parsed.message`.

**Submissão:** o body envia **todos os 4 tipos** (não só alterados, ao contrário de TASK-024). Cada item: `{tipo, horario_efetivo: <ISO UTC>}`. Conversão local → UTC: `dayjs(dataSelecionada + horarioLocal).utc().toISOString()`.

**Dependência:** TASK-020, TASK-023 (helpers + funções HTTP), TASK-024 (`calculaTotalDiario`).

## Comportamento Esperado

| Entrada / Ação | Saída / Efeito esperado |
| -------------- | ----------------------- |
| Mount `/jornadas/manual` | Form vazio; DatePicker default = today; 4 TimePickers vazios; textareas vazias; botão "Salvar" desabilitado |
| Selecionar data 2026-05-27, preencher 09:00/12:00/13:00/18:00, atividade "Trabalhei oito horas no projeto X" (35 chars), motivo "esqueci de fazer login" (22 chars) | Total exibido "08:00"; botão "Salvar" habilitado |
| Clicar "Salvar" | Chama `POST /api/v1/jornadas/manual` com body:<br>`{data:"2026-05-27", marcacoes:[{tipo:"INICIO_JORNADA",horario_efetivo:"2026-05-27T12:00:00.000Z"}, {tipo:"SAIDA_ALMOCO",horario_efetivo:"2026-05-27T15:00:00.000Z"}, {tipo:"RETORNO_ALMOCO",horario_efetivo:"2026-05-27T16:00:00.000Z"}, {tipo:"FIM_JORNADA",horario_efetivo:"2026-05-27T21:00:00.000Z"}], atividade:"Trabalhei oito horas no projeto X", motivo:"esqueci de fazer login"}`<br>Sucesso 201 → `navigate("/jornadas/{id_novo}")` + invalida lista do mês |
| Horários fora de ordem (Início 14:00, Saída 12:00) | Helper text inline "Os horários devem ser em ordem cronológica." no Saída Almoço; botão "Salvar" desabilitado |
| Atividade < 10 chars | Helper text "Mínimo 10 caracteres"; botão "Salvar" desabilitado |
| Motivo < 5 chars | Helper text "Mínimo 5 caracteres"; botão "Salvar" desabilitado |
| Backend retorna 409 `{code:"CONFLICT", message:"Já existe jornada para este dia"}` | Alert vermelho "Já existe uma jornada para este dia. Abra-a para editar." + link "Voltar para Jornadas" navega para `/jornadas` |
| Backend retorna 422 `{code:"VALIDATION_ERROR", message:"horários devem ser cronológicos"}` | Alert vermelho com message do backend (passthrough) |
| Clicar "Cancelar" | `navigate("/jornadas")` |
| Selecionar dia futuro no DatePicker | DatePicker bloqueia (maxDate=today) |

## TDD

**Testes a escrever antes da implementação** (`apps/web/src/pages/JornadaManual/JornadaManualPage.test.tsx`):

```typescript
import { describe, it, expect, beforeEach, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MockAdapter from "axios-mock-adapter";
import api from "@/api/client";
import { renderWithProviders } from "@/test/render";
import { JornadaManualPage } from "@/pages/JornadaManual/JornadaManualPage";

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

describe("JornadaManualPage", () => {
  it("renderiza heading h1 'Nova Jornada Manual' e botão Salvar desabilitado por padrão", () => {
    mock.onGet("/api/v1/jornadas").reply(200, { mes_referencia: "2026-05", total_horas_mes_s: 0, jornadas: [] });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria" });
    renderWithProviders(<JornadaManualPage />, { route: "/jornadas/manual" });
    expect(screen.getByRole("heading", { level: 1, name: /Nova Jornada Manual/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Salvar$/ })).toBeDisabled();
  });

  it("submit válido chama POST /api/v1/jornadas/manual com os 4 tipos em ISO UTC e navega para /jornadas/<id>", async () => {
    mock.onGet("/api/v1/jornadas").reply(200, { mes_referencia: "2026-05", total_horas_mes_s: 0, jornadas: [] });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria" });
    let body: any = null;
    mock.onPost("/api/v1/jornadas/manual").reply((c) => {
      body = JSON.parse(c.data as string);
      return [201, {
        id: "novo-id-1", data: "2026-05-27", status: "AJUSTADA_MANUALMENTE",
        total_horas_apuradas_s: 28800, marcacoes: [], atividade: null, justificativas: [],
      }];
    });
    renderWithProviders(<JornadaManualPage />, { route: "/jornadas/manual" });
    // DatePicker: usar typing direto no input
    const dp = screen.getByLabelText(/Data/i) as HTMLInputElement;
    await userEvent.clear(dp);
    await userEvent.type(dp, "27/05/2026");
    const tps = screen.getAllByRole("textbox", { name: /Horário/i }) as HTMLInputElement[];
    // ordem dos TimePickers: Início, Saída, Retorno, Fim
    await userEvent.type(tps[0]!, "09:00");
    await userEvent.type(tps[1]!, "12:00");
    await userEvent.type(tps[2]!, "13:00");
    await userEvent.type(tps[3]!, "18:00");
    await userEvent.type(screen.getByLabelText(/Atividade/i), "Trabalhei oito horas no projeto X");
    await userEvent.type(screen.getByLabelText(/Justificativa/i), "esqueci de fazer login");
    await userEvent.click(screen.getByRole("button", { name: /^Salvar$/ }));
    await waitFor(() => expect(body).not.toBeNull());
    expect(body.data).toBe("2026-05-27");
    expect(body.marcacoes).toHaveLength(4);
    const tipos = body.marcacoes.map((m: any) => m.tipo);
    expect(tipos).toEqual(["INICIO_JORNADA", "SAIDA_ALMOCO", "RETORNO_ALMOCO", "FIM_JORNADA"]);
    // UTC: 09:00 BRT = 12:00 UTC
    expect(body.marcacoes[0].horario_efetivo).toMatch(/T12:00:00/);
    expect(body.marcacoes[3].horario_efetivo).toMatch(/T21:00:00/);
    expect(body.atividade).toBe("Trabalhei oito horas no projeto X");
    expect(body.motivo).toBe("esqueci de fazer login");
    await waitFor(() => expect(window.location.pathname).toBe("/jornadas/novo-id-1"));
  });

  it("horários fora de ordem exibem helper text 'Os horários devem ser em ordem cronológica.' e Salvar desabilitado", async () => {
    mock.onGet("/api/v1/jornadas").reply(200, { mes_referencia: "2026-05", total_horas_mes_s: 0, jornadas: [] });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria" });
    renderWithProviders(<JornadaManualPage />, { route: "/jornadas/manual" });
    const tps = screen.getAllByRole("textbox", { name: /Horário/i }) as HTMLInputElement[];
    await userEvent.type(tps[0]!, "14:00");
    await userEvent.type(tps[1]!, "12:00");
    await userEvent.tab();
    expect(await screen.findByText(/Os horários devem ser em ordem cronológica\./i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Salvar$/ })).toBeDisabled();
  });

  it("atividade <10 chars exibe helper 'Mínimo 10 caracteres' e desabilita Salvar", async () => {
    mock.onGet("/api/v1/jornadas").reply(200, { mes_referencia: "2026-05", total_horas_mes_s: 0, jornadas: [] });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria" });
    renderWithProviders(<JornadaManualPage />, { route: "/jornadas/manual" });
    await userEvent.type(screen.getByLabelText(/Atividade/i), "curta");
    await userEvent.tab();
    expect(await screen.findByText(/Mínimo 10 caracteres/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Salvar$/ })).toBeDisabled();
  });

  it("erro 409 CONFLICT exibe alert 'Já existe uma jornada para este dia. Abra-a para editar.' + link Voltar para Jornadas", async () => {
    mock.onGet("/api/v1/jornadas").reply(200, { mes_referencia: "2026-05", total_horas_mes_s: 0, jornadas: [] });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria" });
    mock.onPost("/api/v1/jornadas/manual").reply(409, {
      code: "CONFLICT", message: "Já existe jornada para este dia", details: [],
    });
    renderWithProviders(<JornadaManualPage />, { route: "/jornadas/manual" });
    // Preencher formulário válido
    const dp = screen.getByLabelText(/Data/i) as HTMLInputElement;
    await userEvent.clear(dp); await userEvent.type(dp, "27/05/2026");
    const tps = screen.getAllByRole("textbox", { name: /Horário/i }) as HTMLInputElement[];
    await userEvent.type(tps[0]!, "09:00"); await userEvent.type(tps[1]!, "12:00");
    await userEvent.type(tps[2]!, "13:00"); await userEvent.type(tps[3]!, "18:00");
    await userEvent.type(screen.getByLabelText(/Atividade/i), "Trabalhei oito horas");
    await userEvent.type(screen.getByLabelText(/Justificativa/i), "motivo válido");
    await userEvent.click(screen.getByRole("button", { name: /^Salvar$/ }));
    expect(await screen.findByText(/Já existe uma jornada para este dia\. Abra-a para editar\./i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Voltar para Jornadas/i })).toBeInTheDocument();
  });

  it("Cancelar navega para /jornadas", async () => {
    mock.onGet("/api/v1/jornadas").reply(200, { mes_referencia: "2026-05", total_horas_mes_s: 0, jornadas: [] });
    mock.onGet("/api/v1/terceiros/me").reply(200, { id: "u1", nome: "Maria" });
    renderWithProviders(<JornadaManualPage />, { route: "/jornadas/manual" });
    await userEvent.click(screen.getByRole("button", { name: /Cancelar/i }));
    expect(window.location.pathname).toBe("/jornadas");
  });
});
```

> **Quirk MUI DatePicker/TimePicker em jsdom**: usar `screen.getByLabelText` é mais robusto que `getByRole("textbox")` — funciona porque MUI `slotProps.textField.label` define o `aria-label` via `<TextField label="..."/>`. Em testes pesados de DatePicker, considere usar `userEvent.type(input, "27/05/2026")` direto no input (formato pt-BR via `dayjs.locale("pt-br")` configurado no helper de TASK-023).

**Refatoração:** após green, considerar (a) extrair função `dataHorarioLocalParaUtc(data, horario)` para `src/lib/format/horario.ts` (TASK-023) — TASK-026 (cadastro) pode usar para horários de jornada padrão.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| ------- | ---- | --------- |
| `apps/web/src/pages/JornadaManual/JornadaManualPage.tsx` | Criar | Componente principal |
| `apps/web/src/pages/JornadaManual/JornadaManualPage.test.tsx` | Criar | TDD acima |
| `apps/web/src/lib/schemas/jornadaManual.ts` | Criar | Zod schema `jornadaManualSchema` com validação cronológica |
| `apps/web/src/routes.tsx` | Modificar | Substituir `JornadaManualPageStub` por `JornadaManualPage` |

> 3 criados + 1 modificado = **4 arquivos-alvo**.

### Detalhamento Técnico

**1. `src/lib/schemas/jornadaManual.ts`:**

```typescript
import { z } from "zod";
import dayjs from "dayjs";

const horarioRegex = /^([01]\d|2[0-3]):[0-5]\d$/;

const horarioField = z.string().regex(horarioRegex, "Horário inválido (use HH:MM)");

export const jornadaManualSchema = z
  .object({
    data: z.string().min(1, "Data obrigatória").refine(
      (v) => {
        const d = dayjs(v, "YYYY-MM-DD", true);
        return d.isValid() && !d.isAfter(dayjs(), "day");
      },
      { message: "Data inválida ou futura" }
    ),
    inicio: horarioField,
    saidaAlmoco: horarioField,
    retornoAlmoco: horarioField,
    fim: horarioField,
    atividade: z.string().min(10, "Mínimo 10 caracteres").max(2000, "Máximo 2000 caracteres"),
    motivo: z.string().min(5, "Mínimo 5 caracteres").max(500, "Máximo 500 caracteres"),
  })
  .refine(
    (v) => v.inicio < v.saidaAlmoco && v.saidaAlmoco < v.retornoAlmoco && v.retornoAlmoco < v.fim,
    { message: "Os horários devem ser em ordem cronológica.", path: ["saidaAlmoco"] }
  );

export type JornadaManualFormValues = z.infer<typeof jornadaManualSchema>;
```

> **Quirk Zod path em refine**: `path: ["saidaAlmoco"]` anexa o erro ao campo Saída Almoço — escolha pragmática para destacar o primeiro campo violado. Helper text aparecerá nele; outros campos sem ponto de erro.

**2. `src/pages/JornadaManual/JornadaManualPage.tsx`:**

```typescript
import { useState, useMemo } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate, Link as RouterLink } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import dayjs from "dayjs";
import {
  Container, Typography, Box, Button, Stack, TextField, Alert, Link,
} from "@mui/material";
import { DatePicker, LocalizationProvider, TimePicker } from "@mui/x-date-pickers";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { postJornadaManual, jornadasKeys } from "@/api/jornadas";
import { calculaTotalDiario, formatTotal } from "@/lib/format/horario";
import { parseApiError } from "@/lib/errors";
import { jornadaManualSchema, type JornadaManualFormValues } from "@/lib/schemas/jornadaManual";

function horarioParaIsoUtc(data: string, horarioHHmm: string): string {
  // data: "YYYY-MM-DD", horario: "HH:MM" interpretado em America/Sao_Paulo
  return dayjs(`${data}T${horarioHHmm}:00`).utc().toISOString();
}

export function JornadaManualPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [serverError, setServerError] = useState<{ code: string; message: string } | null>(null);

  const {
    control, register, handleSubmit, watch,
    formState: { errors, isValid, isSubmitting },
  } = useForm<JornadaManualFormValues>({
    mode: "onBlur",
    resolver: zodResolver(jornadaManualSchema),
    defaultValues: {
      data: dayjs().format("YYYY-MM-DD"),
      inicio: "", saidaAlmoco: "", retornoAlmoco: "", fim: "",
      atividade: "", motivo: "",
    },
  });

  const inicio = watch("inicio");
  const saidaAlmoco = watch("saidaAlmoco");
  const retornoAlmoco = watch("retornoAlmoco");
  const fim = watch("fim");
  const dataSel = watch("data");

  const totalPreview = useMemo(() => {
    if (!inicio || !saidaAlmoco || !retornoAlmoco || !fim || !dataSel) return null;
    return calculaTotalDiario(
      horarioParaIsoUtc(dataSel, inicio),
      horarioParaIsoUtc(dataSel, saidaAlmoco),
      horarioParaIsoUtc(dataSel, retornoAlmoco),
      horarioParaIsoUtc(dataSel, fim)
    );
  }, [dataSel, inicio, saidaAlmoco, retornoAlmoco, fim]);

  const mutation = useMutation({
    mutationFn: async (values: JornadaManualFormValues) => {
      return postJornadaManual({
        data: values.data,
        marcacoes: [
          { tipo: "INICIO_JORNADA", horario_efetivo: horarioParaIsoUtc(values.data, values.inicio) },
          { tipo: "SAIDA_ALMOCO", horario_efetivo: horarioParaIsoUtc(values.data, values.saidaAlmoco) },
          { tipo: "RETORNO_ALMOCO", horario_efetivo: horarioParaIsoUtc(values.data, values.retornoAlmoco) },
          { tipo: "FIM_JORNADA", horario_efetivo: horarioParaIsoUtc(values.data, values.fim) },
        ],
        atividade: values.atividade,
        motivo: values.motivo,
      });
    },
    onSuccess: (resp) => {
      const mesNovo = resp.data.slice(0, 7);
      void qc.invalidateQueries({ queryKey: jornadasKeys.lista(mesNovo) });
      void qc.invalidateQueries({ queryKey: jornadasKeys.all });
      navigate(`/jornadas/${resp.id}`, { replace: true });
    },
    onError: (err) => {
      setServerError(parseApiError(err));
    },
  });

  return (
    <Container maxWidth="md" sx={{ mt: 2 }}>
      <Typography variant="h4" component="h1" gutterBottom>Nova Jornada Manual</Typography>
      <Box component="form" onSubmit={handleSubmit((v) => { setServerError(null); mutation.mutate(v); })}>
        <LocalizationProvider dateAdapter={AdapterDayjs}>
          <Controller
            name="data"
            control={control}
            render={({ field }) => (
              <DatePicker
                label="Data"
                value={field.value ? dayjs(field.value) : null}
                onChange={(v) => field.onChange(v ? v.format("YYYY-MM-DD") : "")}
                maxDate={dayjs()}
                slotProps={{
                  textField: {
                    fullWidth: true,
                    margin: "normal",
                    error: Boolean(errors.data),
                    helperText: errors.data?.message ?? " ",
                  },
                }}
              />
            )}
          />
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
            {([
              ["inicio", "Horário de início"],
              ["saidaAlmoco", "Horário de saída do almoço"],
              ["retornoAlmoco", "Horário de retorno do almoço"],
              ["fim", "Horário de fim"],
            ] as const).map(([fname, label]) => (
              <Controller
                key={fname}
                name={fname}
                control={control}
                render={({ field }) => (
                  <TimePicker
                    label={label}
                    value={field.value ? dayjs(`2020-01-01T${field.value}:00`) : null}
                    onChange={(v) => field.onChange(v ? v.format("HH:mm") : "")}
                    slotProps={{
                      textField: {
                        "aria-label": label,
                        error: Boolean(errors[fname]),
                        helperText: errors[fname]?.message ?? " ",
                      },
                    }}
                  />
                )}
              />
            ))}
          </Stack>
        </LocalizationProvider>

        <Typography variant="body1" mt={2}>
          Total: <strong>{formatTotal(totalPreview)}</strong>
        </Typography>

        <TextField
          label="Atividade"
          multiline minRows={3} fullWidth margin="normal"
          {...register("atividade")}
          error={Boolean(errors.atividade)}
          helperText={(errors.atividade?.message ?? `${watch("atividade").length}/2000`)}
        />
        <TextField
          label="Justificativa"
          multiline minRows={2} fullWidth margin="normal"
          {...register("motivo")}
          error={Boolean(errors.motivo)}
          helperText={(errors.motivo?.message ?? `${watch("motivo").length}/500`)}
        />

        {serverError && (
          <Alert severity="error" role="alert" sx={{ mt: 2 }} action={
            serverError.code === "CONFLICT" ? (
              <Button color="inherit" size="small" component={RouterLink} to="/jornadas">
                Voltar para Jornadas
              </Button>
            ) : undefined
          }>
            {serverError.code === "CONFLICT"
              ? "Já existe uma jornada para este dia. Abra-a para editar."
              : serverError.message}
            {serverError.code === "CONFLICT" && (
              <Link component={RouterLink} to="/jornadas" sx={{ ml: 1 }}>
                Voltar para Jornadas
              </Link>
            )}
          </Alert>
        )}

        <Stack direction="row" spacing={2} mt={3}>
          <Button onClick={() => navigate("/jornadas")}>Cancelar</Button>
          <Button
            type="submit"
            variant="contained"
            disabled={!isValid || isSubmitting || mutation.isPending}
          >
            {mutation.isPending ? "Salvando..." : "Salvar"}
          </Button>
        </Stack>
      </Box>
    </Container>
  );
}
```

> **Quirk dayjs UTC**: `dayjs("2026-05-27T09:00:00").utc().toISOString()` — sem o `tz()`, dayjs assume o fuso local do navegador (que em testes Vitest jsdom é UTC por default a menos que `TZ=America/Sao_Paulo` esteja setado). **Decisão de testes**: setar `process.env.TZ = "America/Sao_Paulo"` em `vitest.config.ts` ou nos testes via `vi.stubGlobal`. Mais simples: usar `dayjs.tz` com plugin já carregado em TASK-023 — substituir por `dayjs.tz(\`${data}T${horario}:00\`, "America/Sao_Paulo").utc().toISOString()`. Reescrever helper inline para usar `dayjs.tz`:

```typescript
import "@/lib/format/horario"; // garante plugins carregados

function horarioParaIsoUtc(data: string, horarioHHmm: string): string {
  return dayjs.tz(`${data}T${horarioHHmm}:00`, "America/Sao_Paulo").utc().toISOString();
}
```

> **Edição em `src/lib/format/horario.ts`**: exportar `dayjs` como `export default dayjs` (após `extend(utc); extend(timezone);`) para garantir que outros módulos importando dayjs daqui herdem os plugins. **Edição cirúrgica de 1 linha** em arquivo da TASK-023 — aceitável pela mesma justificativa de TASK-022 (refactor de extração compartilhada).

**3. `src/routes.tsx` — diff:**

```typescript
import { JornadaManualPage } from "@/pages/JornadaManual/JornadaManualPage";
// Substituir:
// { path: "/jornadas/manual", element: <JornadaManualPageStub /> },
// Por:
// { path: "/jornadas/manual", element: <JornadaManualPage /> },
```

## Contratos com camadas adjacentes

```
Produz para:
  - jornadaManualSchema: padrão Zod de form complexo com refine cross-field; TASK-026 (cadastro) reusa o padrão para validar horários cronológicos do Terceiro.

Consome de:
  TASK-020: api/client, parseApiError, renderWithProviders.
  TASK-023: postJornadaManual, jornadasKeys, formatTotal, formatHoraBR (indireto via dayjs em testes).
  TASK-024: calculaTotalDiario (reuso).
  Backend Phase 3 TASK-017: POST /api/v1/jornadas/manual.

Erros:
  - 409 CONFLICT: alert "Já existe uma jornada para este dia. Abra-a para editar." + CTA.
  - 422 VALIDATION_ERROR: passthrough do message do backend (horários fora de ordem, atividade<10, motivo<5).
  - 401: tratado pelo interceptor.
```

## Contrato HTTP

```
POST /api/v1/jornadas/manual   (auth Bearer)
Content-Type: application/json

Request body:
{
  "data": "2026-05-27",                                       // YYYY-MM-DD, dia <= hoje
  "marcacoes": [                                              // exatamente 4 itens, tipos distintos, cronológicos
    {"tipo": "INICIO_JORNADA",  "horario_efetivo": "2026-05-27T12:00:00.000Z"},
    {"tipo": "SAIDA_ALMOCO",    "horario_efetivo": "2026-05-27T15:00:00.000Z"},
    {"tipo": "RETORNO_ALMOCO",  "horario_efetivo": "2026-05-27T16:00:00.000Z"},
    {"tipo": "FIM_JORNADA",     "horario_efetivo": "2026-05-27T21:00:00.000Z"}
  ],
  "atividade": "Trabalhei oito horas no projeto X",           // min 10, max 2000
  "motivo": "esqueci de fazer login"                          // min 5, max 500
}

Response 201: JornadaDetalheResponse criada (status=AJUSTADA_MANUALMENTE; 4 marcações origem=AJUSTE_WEB; 1 atividade; 1 justificativa; +1 LogAuditoria(Jornada))
{
  "id": "<uuid_novo>",
  "data": "2026-05-27",
  "status": "AJUSTADA_MANUALMENTE",
  "total_horas_apuradas_s": 28800,
  "marcacoes": [...4 marcações com origem=AJUSTE_WEB...],
  "atividade": {...},
  "justificativas": [{ "motivo": "...", "usuario_responsavel": "...", "criada_em": "<ISO>" }]
}

Response 409: {"code":"CONFLICT","message":"Já existe jornada para este dia","details":[]}
Response 422: {"code":"VALIDATION_ERROR","message":"horários devem ser cronológicos" | "as 4 marcações de tipos distintos são obrigatórias" | "motivo<5" | "atividade<10",...}
Response 401: {"code":"UNAUTHORIZED",...}
```

**Validação obrigatória pelo executor antes de marcar done:**

1. `cd apps/web && npm test -- --run src/pages/JornadaManual/JornadaManualPage.test.tsx` — 6 testes passam.
2. `cd apps/web && npm test -- --run` — toda a suite continua verde; coverage >= 80.
3. `cd apps/web && npm run typecheck` — 0 erros.
4. `cd apps/web && npm run lint` — 0 warnings.
5. `cd apps/web && npm run build` — `dist/` gerado sem erros.
6. `make smoke` (raiz) — Phase 1 smoke continua passando.

> Executor DEVE rodar 1–6 e garantir saída 0 antes de retornar.

**Refatoração:** após green, mover `horarioParaIsoUtc` para `src/lib/format/horario.ts` (helper compartilhado) — TASK-026 pode usar para horários do Terceiro.
