---
checkpoint: null
complexity: M
created_at: "2026-05-28 12:41:00"
criteria:
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Privacidade/PrivacidadePage.test.tsx -t "heading h1"
      text: Mount /privacidade renderiza heading h1 Aviso de Privacidade e bloco com textos Dados coletados, email_destinatario_relatorio e AES-GCM
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Privacidade/PrivacidadePage.test.tsx -t "aria-disabled"
      text: Botao Continuar inicia desabilitado e passa a habilitado ao marcar o checkbox (aria-checked true)
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Privacidade/PrivacidadePage.test.tsx -t "POST /api/v1/privacidade/aceitar"
      text: Clique em Continuar com checkbox marcado chama POST /api/v1/privacidade/aceitar (mock confirma)
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Privacidade/PrivacidadePage.test.tsx -t "snackbar"
      text: Erro 5xx do POST exibe snackbar com texto exato Nao foi possivel registrar o aceite. Tente novamente.
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Privacidade/PrivacidadePage.test.tsx -t "invalida o cache"
      text: Sucesso 204 invalida privacidadeKeys.status (queryClient.invalidateQueries chamado com a key correta)
    - done: false
      test: grep -E "privacidadeKeys|getStatusPrivacidade|postAceitarPrivacidade" apps/web/src/api/privacidade.ts
      text: api/privacidade.ts exporta privacidadeKeys.status com value [privacidade,status] e funcoes getStatusPrivacidade e postAceitarPrivacidade
    - done: false
      test: grep -E "from \"@/api/privacidade\"" apps/web/src/routes/PrivacyGuard.tsx
      text: PrivacyGuard.tsx importa privacidadeKeys e getStatusPrivacidade de @/api/privacidade (consolidacao da key)
    - done: false
      test: grep -E "<PrivacidadePage ?/>" apps/web/src/routes.tsx
      text: routes.tsx substitui PrivacidadePageStub por PrivacidadePage real
    - done: false
      text: ESLint passa sem warnings e tsc strict 0 erros
    - done: false
      text: Testes passando com cobertura >= 80%
    - done: false
      text: make smoke continua passando
deps:
    - TASK-020
id: TASK-022
linter: cd apps/web && npm run lint && npm run typecheck
n45_version: 0.2.0
persona: frontend
phase: Phase 4 — Frontend por Feature
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: done
tdd:
    green: false
    red: true
    refactor: false
tests: cd apps/web && npm test -- --run src/pages/Privacidade/PrivacidadePage.test.tsx
title: 'Privacidade: pagina /privacidade one-time (RF-012) com checkbox de aceite e POST /aceitar; invalida cache para PrivacyGuard redirecionar'
updated_at: "2026-05-28 17:10:41"
---

## Contexto

Implementar a página `/privacidade` (RF-012 + LGPD art. 7, VI) — modal/tela one-time exibida no primeiro acesso autenticado. Slice: componente + página + integração com `GET /api/v1/privacidade` (status) e `POST /api/v1/privacidade/aceitar` + substituição do stub em `routes.tsx`.

**State atual:** TASK-020 entregou (a) `PrivacyGuard` em `src/routes/PrivacyGuard.tsx` que consulta `GET /api/v1/privacidade` e redireciona para `/privacidade` se `accepted=false`, ou para `/jornadas` se já em `/privacidade` e `accepted=true`; (b) `PrivacidadePageStub` em `routes.tsx` dentro do `<PrivacyGuard>` (rota acessível mesmo com aceite pendente); (c) `privacyKeys.status` para query key. Esta task substitui o stub pela página real e adiciona o mutation `useAceitarPrivacidade`.

**Decisão de UX (Spec §5):**
- Cabeçalho `<h1>` "Aviso de Privacidade".
- Bloco de texto scrollável (MUI `<Paper>` com `maxHeight: 50vh, overflowY: "auto"`) com o conteúdo do aviso (dados coletados — incluindo `email_destinatario_relatorio` como dado de terceiro e período de retenção do log de auditoria e que credenciais SMTP são armazenadas criptografadas localmente —, finalidade, retenção, base legal, contato DPO).
- Checkbox MUI rotulado "Li e aceito os termos de privacidade" — controlado, `aria-checked`.
- Botão "Continuar" — desabilitado até checkbox marcado.
- **Sem opção de recusar** (LGPD art. 7, VI).
- Erro 4xx/5xx do `POST /aceitar` → toast snackbar vermelho "Não foi possível registrar o aceite. Tente novamente." (não bloqueia a tela; usuário pode tentar de novo).
- Sucesso (204) → invalidar `privacyKeys.status` na TanStack Query; `PrivacyGuard` re-roda e redireciona para `/jornadas`.

**Texto do aviso (literal)** — entra no JSX, mantém formatação:

```
Aviso de Privacidade — TimeSheet Terceiros

Dados coletados:
- Cadastro do Terceiro: nome, e-mail de contato, CNPJ da empresa.
- E-mail destinatário do relatório mensal: tratado como dado de terceiro fornecido pelo Terceiro.
- Marcações de jornada: horários de início, almoço e fim do trabalho.
- Atividades diárias e justificativas de ajustes manuais.

Finalidade:
- Automatizar e auditar o registro da jornada do Terceiro.
- Gerar e enviar relatório mensal por SMTP ao endereço informado.

Retenção:
- Marcações, jornadas, atividades: enquanto o Terceiro mantiver o sistema instalado.
- Relatórios PDF: 24 meses.
- Log de auditoria: indefinido nesta versão; revisão prevista em versões futuras.

Armazenamento:
- Todos os dados ficam em banco local SQLite com criptografia em repouso (SQLCipher).
- Credenciais do servidor SMTP são armazenadas criptografadas com AES-GCM no banco local.
- Nada é enviado para servidores externos exceto o relatório mensal por SMTP, sob seu controle.

Base legal:
- Execução de contrato e legítimo interesse (art. 7, II e IX da LGPD).

Contato DPO:
- O Terceiro é o controlador dos dados desta instalação. Para dúvidas, consultar a documentação ou o canal interno da Contratante.
```

**Versão do aviso:** o backend persiste `versao_aviso = "1.0"` (TASK-014). Esta task **não** exibe a versão na UI; ela só é relevante para futuro re-prompt.

**Dependência:** TASK-020 (única).

## Comportamento Esperado

| Entrada / Ação | Saída / Efeito esperado |
| -------------- | ----------------------- |
| Mount `/privacidade` autenticado, sem aceite registrado | Renderiza heading `<h1>` "Aviso de Privacidade", bloco de texto, checkbox **desmarcado**, botão "Continuar" **desabilitado** (`aria-disabled="true"`) |
| Clicar no checkbox para marcar | Checkbox marcado (`aria-checked="true"`); botão "Continuar" passa a habilitado |
| Clicar "Continuar" com checkbox marcado | Botão entra em loading (`aria-busy="true"`); chama `POST /api/v1/privacidade/aceitar`; sucesso 204 → invalida `privacyKeys.status` |
| Após sucesso, `PrivacyGuard` re-busca status com `accepted=true` | Redireciona automaticamente para `/jornadas` |
| `POST /aceitar` retorna 5xx | Snackbar vermelho "Não foi possível registrar o aceite. Tente novamente."; botão volta a "Continuar"; checkbox permanece marcado |
| Mount `/privacidade` com aceite já em `versao_aviso="1.0"` | **Não ocorre** — `PrivacyGuard` redireciona para `/jornadas` antes do componente montar (Guard tem precedência) |
| Tab pelo teclado | Foco move: bloco de texto (`tabindex="0"` para scroll por teclado) → checkbox → botão "Continuar" |

## TDD

**Testes a escrever antes da implementação** (`apps/web/src/pages/Privacidade/PrivacidadePage.test.tsx`):

```typescript
import { describe, it, expect, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MockAdapter from "axios-mock-adapter";
import api from "@/api/client";
import { renderWithProviders } from "@/test/render";
import { PrivacidadePage } from "@/pages/Privacidade/PrivacidadePage";

const mock = new MockAdapter(api);

describe("PrivacidadePage", () => {
  beforeEach(() => {
    mock.reset();
    sessionStorage.clear();
  });

  it("renderiza heading h1 'Aviso de Privacidade' e bloco com termos", () => {
    renderWithProviders(<PrivacidadePage />, { route: "/privacidade" });
    expect(screen.getByRole("heading", { level: 1, name: /Aviso de Privacidade/i })).toBeInTheDocument();
    expect(screen.getByText(/Dados coletados/i)).toBeInTheDocument();
    expect(screen.getByText(/email_destinatario_relatorio/i)).toBeInTheDocument();
    expect(screen.getByText(/AES-GCM/i)).toBeInTheDocument();
  });

  it("botão Continuar inicia com aria-disabled=true e habilita ao marcar o checkbox", async () => {
    renderWithProviders(<PrivacidadePage />, { route: "/privacidade" });
    const btn = screen.getByRole("button", { name: /Continuar/i });
    expect(btn).toBeDisabled();
    const chk = screen.getByRole("checkbox", { name: /Li e aceito os termos de privacidade/i });
    await userEvent.click(chk);
    expect(chk).toBeChecked();
    expect(btn).toBeEnabled();
  });

  it("clique em Continuar chama POST /api/v1/privacidade/aceitar e invalida o cache", async () => {
    let postCalled = false;
    mock.onPost("/api/v1/privacidade/aceitar").reply(() => {
      postCalled = true;
      return [204, ""];
    });
    renderWithProviders(<PrivacidadePage />, { route: "/privacidade" });
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: /Continuar/i }));
    await waitFor(() => expect(postCalled).toBe(true));
  });

  it("erro do POST exibe snackbar com texto exato 'Não foi possível registrar o aceite. Tente novamente.'", async () => {
    mock.onPost("/api/v1/privacidade/aceitar").reply(500, {
      code: "INTERNAL_ERROR", message: "boom", details: [],
    });
    renderWithProviders(<PrivacidadePage />, { route: "/privacidade" });
    await userEvent.click(screen.getByRole("checkbox"));
    await userEvent.click(screen.getByRole("button", { name: /Continuar/i }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/Não foi possível registrar o aceite\. Tente novamente\./i);
  });

  it("checkbox tem aria-checked=true ao marcar", async () => {
    renderWithProviders(<PrivacidadePage />, { route: "/privacidade" });
    const chk = screen.getByRole("checkbox");
    expect(chk).toHaveAttribute("aria-checked", "false");
    await userEvent.click(chk);
    expect(chk).toHaveAttribute("aria-checked", "true");
  });
});
```

**Refatoração:** após green, considerar (a) extrair o texto do aviso para `src/lib/content/avisoPrivacidade.ts` se TASK-026 ou outro lugar precisar exibi-lo (improvável na v1.0); (b) extrair `useAceitarPrivacidade` para `src/hooks/usePrivacidade.ts` somente se outro componente consumir.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| ------- | ---- | --------- |
| `apps/web/src/pages/Privacidade/PrivacidadePage.tsx` | Criar | Componente da página |
| `apps/web/src/pages/Privacidade/PrivacidadePage.test.tsx` | Criar | Testes TDD acima |
| `apps/web/src/api/privacidade.ts` | Criar | Funções HTTP: `getStatusPrivacidade`, `postAceitarPrivacidade` |
| `apps/web/src/routes.tsx` | Modificar | Substituir import `PrivacidadePageStub` por `PrivacidadePage` |

> 3 criados + 1 modificado = **4 arquivos-alvo**.

### Detalhamento Técnico

**1. `src/api/privacidade.ts`**:

```typescript
import api from "./client";
import type { PrivacyStatus } from "@/types/contracts";

export const privacidadeKeys = {
  status: ["privacidade", "status"] as const,
};

export async function getStatusPrivacidade(): Promise<PrivacyStatus> {
  const r = await api.get<PrivacyStatus>("/api/v1/privacidade");
  return r.data;
}

export async function postAceitarPrivacidade(): Promise<void> {
  await api.post("/api/v1/privacidade/aceitar");
}
```

> **Nota:** TASK-020 já criou `privacyKeys.status` em `routes/PrivacyGuard.tsx`. Para evitar duplicação, reexportar a mesma chave aqui: `export { privacyKeys as privacidadeKeys } from "@/routes/PrivacyGuard"` **ou** mover a definição para `src/api/privacidade.ts` (canônico) e atualizar `PrivacyGuard.tsx` para importar. **Decisão:** mover a definição para `src/api/privacidade.ts` (canônico — keys vivem com a API) e atualizar `PrivacyGuard.tsx` para importar. Isso é uma **edição cirúrgica em arquivo da TASK-020** — aceitável porque é o refactor previsto na regra "extrair quando 2+ consomem" e não muda comportamento.

**2. `src/pages/Privacidade/PrivacidadePage.tsx`**:

```typescript
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Container, Paper, Typography, Box, FormControlLabel, Checkbox, Button,
  Snackbar, Alert,
} from "@mui/material";
import { postAceitarPrivacidade, privacidadeKeys } from "@/api/privacidade";

const TEXTO_AVISO = `Dados coletados:
- Cadastro do Terceiro: nome, e-mail de contato, CNPJ da empresa.
- E-mail destinatário do relatório mensal (email_destinatario_relatorio): tratado como dado de terceiro fornecido pelo Terceiro.
- Marcações de jornada: horários de início, almoço e fim do trabalho.
- Atividades diárias e justificativas de ajustes manuais.

Finalidade:
- Automatizar e auditar o registro da jornada do Terceiro.
- Gerar e enviar relatório mensal por SMTP ao endereço informado.

Retenção:
- Marcações, jornadas, atividades: enquanto o Terceiro mantiver o sistema instalado.
- Relatórios PDF: 24 meses.
- Log de auditoria: indefinido nesta versão; revisão prevista em versões futuras.

Armazenamento:
- Todos os dados ficam em banco local SQLite com criptografia em repouso (SQLCipher).
- Credenciais do servidor SMTP são armazenadas criptografadas com AES-GCM no banco local.
- Nada é enviado para servidores externos exceto o relatório mensal por SMTP, sob seu controle.

Base legal:
- Execução de contrato e legítimo interesse (art. 7, II e IX da LGPD).

Contato DPO:
- O Terceiro é o controlador dos dados desta instalação. Para dúvidas, consultar a documentação ou o canal interno da Contratante.`;

export function PrivacidadePage() {
  const [aceito, setAceito] = useState(false);
  const [snackbar, setSnackbar] = useState<string | null>(null);
  const qc = useQueryClient();

  const mutation = useMutation({
    mutationFn: postAceitarPrivacidade,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: privacidadeKeys.status });
    },
    onError: () => {
      setSnackbar("Não foi possível registrar o aceite. Tente novamente.");
    },
  });

  return (
    <Container maxWidth="md" sx={{ mt: 4 }}>
      <Paper sx={{ p: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Aviso de Privacidade
        </Typography>
        <Box
          tabIndex={0}
          sx={{
            maxHeight: "50vh",
            overflowY: "auto",
            p: 2,
            border: 1,
            borderColor: "divider",
            borderRadius: 1,
            whiteSpace: "pre-wrap",
            fontFamily: "monospace",
            fontSize: 14,
          }}
        >
          {TEXTO_AVISO}
        </Box>
        <FormControlLabel
          sx={{ mt: 3 }}
          control={
            <Checkbox
              checked={aceito}
              onChange={(e) => setAceito(e.target.checked)}
              inputProps={{ "aria-label": "Li e aceito os termos de privacidade" }}
            />
          }
          label="Li e aceito os termos de privacidade"
        />
        <Box display="flex" justifyContent="flex-end" mt={2}>
          <Button
            variant="contained"
            disabled={!aceito || mutation.isPending}
            aria-busy={mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? "Registrando..." : "Continuar"}
          </Button>
        </Box>
      </Paper>
      <Snackbar
        open={Boolean(snackbar)}
        autoHideDuration={5000}
        onClose={() => setSnackbar(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert severity="error" role="alert" onClose={() => setSnackbar(null)}>
          {snackbar}
        </Alert>
      </Snackbar>
    </Container>
  );
}
```

> **Quirk MUI Checkbox + aria-checked**: o input nativo de fato seta `aria-checked` em `role="checkbox"` apenas quando MUI usa `inputProps={{role: "checkbox"}}` implicitamente. Testar com `screen.getByRole("checkbox")` é o padrão correto; o atributo `aria-checked` é setado pelo MUI quando o checkbox está checked.

> **Quirk Snackbar + role="alert"**: o `<Alert>` MUI já vem com `role="alert"`. Não precisa passar manualmente.

**3. `src/routes/PrivacyGuard.tsx` — diff (mover a definição da key):**

```typescript
// Substituir:
// export const privacyKeys = { status: ["privacidade", "status"] as const };
// const { data, isLoading } = useQuery({ queryKey: privacyKeys.status, ... });

// Por:
import { privacidadeKeys, getStatusPrivacidade } from "@/api/privacidade";
// ...
const { data, isLoading } = useQuery({
  queryKey: privacidadeKeys.status,
  queryFn: getStatusPrivacidade,
  staleTime: 60_000,
});
```

> **Justificativa de edição em arquivo da TASK-020**: é exatamente o refactor de extração previsto ("extrair se 2+ consomem"). PrivacyGuard e PrivacidadePage agora compartilham `privacidadeKeys.status`. Aceitável porque é micro-edição cirúrgica que **não muda comportamento** (mesma chave, mesma URL). Alternativa rejeitada: duplicar a chave em dois lugares → drift.

**4. `src/routes.tsx` — diff:**

```typescript
// Adicionar:
import { PrivacidadePage } from "@/pages/Privacidade/PrivacidadePage";

// E substituir:
// { path: "/privacidade", element: <PrivacidadePageStub /> },
// Por:
// { path: "/privacidade", element: <PrivacidadePage /> },
```

## Contratos com camadas adjacentes

```
Produz para:
  - privacidadeKeys.status (em src/api/privacidade.ts): chave canônica reusada pelo PrivacyGuard
  - Phase 6 E2E: fluxo "Onboarding completo" inclui esta tela.

Consome de:
  TASK-020: api/client, renderWithProviders (testes), PrivacyGuard (re-roda após invalidate).
  Backend Phase 3 (TASK-014): GET /api/v1/privacidade, POST /api/v1/privacidade/aceitar.

Erros:
  - 500/qualquer 5xx: snackbar vermelho "Não foi possível registrar o aceite. Tente novamente."
  - 401: tratado pelo interceptor TASK-020 (refresh + retry; falha → logout + redirect /login).
```

## Contrato HTTP

```
GET /api/v1/privacidade   (auth Bearer)
Response 200: {
  "accepted": false|true,
  "versao_aviso": "1.0"|null,
  "aceito_em": "<iso utc>"|null
}
Response 401: {"code":"UNAUTHORIZED",...}

POST /api/v1/privacidade/aceitar   (auth Bearer)
Sem body
Response 204: vazio; backend cria/atualiza PrivacyAcceptance(id=1, versao_aviso="1.0", aceito_em=now); idempotente (re-chamadas viram no-op)
Response 401: {"code":"UNAUTHORIZED",...}
Response 5xx: {"code":"INTERNAL_ERROR",...}
```

**Validação obrigatória pelo executor antes de marcar done:**

1. `cd apps/web && npm test -- --run src/pages/Privacidade/PrivacidadePage.test.tsx` — 5 testes passam.
2. `cd apps/web && npm test -- --run` — toda a suite continua verde; coverage >= 80.
3. `cd apps/web && npm run typecheck` — 0 erros.
4. `cd apps/web && npm run lint` — 0 warnings.
5. `cd apps/web && npm run build` — `dist/` gerado sem erros.
6. `make smoke` (raiz) — Phase 1 smoke continua passando.

> Executor DEVE rodar 1–6 e garantir saída 0 antes de retornar. Falha = task não concluída.

**Refatoração:** após green, considerar extrair o texto do aviso para `src/lib/content/avisoPrivacidade.ts` somente se outro local exibir; por ora, manter inline.
