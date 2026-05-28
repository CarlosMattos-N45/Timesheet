---
checkpoint: null
complexity: M
created_at: "2026-05-28 12:39:11"
criteria:
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Login/LoginPage.test.tsx -t "exibe heading h1"
      text: Mount /login as 09h renderiza heading h1 Login e Typography Bom dia.
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Login/LoginPage.test.tsx -t "Boa tarde"
      text: Mount /login as 14h renderiza Boa tarde.
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Login/LoginPage.test.tsx -t "inicia desabilitado"
      text: Botao Entrar inicia desabilitado e habilita quando email e senha (>=8) validos
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Login/LoginPage.test.tsx -t "E-mail invalido"
      text: Email invalido exibe helper text exato E-mail invalido com aria-invalid=true
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Login/LoginPage.test.tsx -t "persiste tokens"
      text: Submit valido chama POST /api/v1/auth/login e persiste tokens no sessionStorage (ts:access_token, ts:terceiro_id)
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Login/LoginPage.test.tsx -t "limpa campo senha"
      text: Resposta 401 UNAUTHORIZED renderiza alert role=alert com texto exato E-mail ou senha invalidos. Verifique e tente novamente. + limpa campo senha + foco em senha
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Login/LoginPage.test.tsx -t "Muitas tentativas"
      text: Resposta 429 RATE_LIMITED renderiza alert com texto exato Muitas tentativas. Aguarde alguns instantes e tente novamente.
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Login/LoginPage.test.tsx -t "aria-disabled"
      text: Link Esqueci minha senha tem aria-disabled=true e tooltip Recuperacao de senha disponivel em breve
    - done: false
      test: grep -E "<LoginPage ?/>" apps/web/src/routes.tsx
      text: routes.tsx substitui LoginPageStub por LoginPage real (import e element)
    - done: false
      text: ESLint passa sem warnings e tsc strict 0 erros
    - done: false
      text: Testes passando com cobertura >= 80%
    - done: false
      text: 'acessibilidade: form com inputs rotulados (TextField label), aria-invalid em erro, role=alert no server error'
    - done: false
      text: make smoke continua passando
deps:
    - TASK-020
id: TASK-021
linter: cd apps/web && npm run lint && npm run typecheck
n45_version: 0.2.0
persona: frontend
phase: Phase 4 — Frontend por Feature
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: pending
tdd:
    green: false
    red: true
    refactor: false
tests: cd apps/web && npm test -- --run src/pages/Login/LoginPage.test.tsx
title: 'Login: pagina /login com saudacao contextual (RF-001), form RHF+Zod, integracao useAuth().login, erros 401/429/network, link ''Esqueci minha senha'' desabilitado'
updated_at: "2026-05-28 13:30:15"
worktree:
    base_sha: 4322b5e75dde3e6501c193d809631f12a065fa49
    branch: worktree-agent-20365e98da71ffeb
    path: .n45\worktree\agent-20365e98da71ffeb
---
## Contexto

Implementar a página `/login` da Web SPA (RF-009 + RF-001 — saudação contextual). Slice vertical: componente + página + zod schema + integração com `useAuth().login()` + substituição do stub em `src/routes.tsx`. A página é a porta de entrada pós-instalação (o cadastro do Terceiro acontece no Agente Desktop; aqui só login).

**State atual:** TASK-020 entregou (a) `useAuth().login(email, senha)` chamando `POST /api/v1/auth/login` e persistindo tokens em `sessionStorage`; (b) `LoginPageStub` registrado em `src/routes.tsx` como `path: "/login"` fora do `<ProtectedRoute>`; (c) `parseApiError()` para extrair `{code, message, fields}` do erro padronizado; (d) `saudacaoAgora()` em `@/lib/saudacao`. Esta task substitui o stub pela página real.

**Decisão de UX (Spec §5):** form com 2 campos (e-mail + senha), botão "Entrar" desabilitado enquanto ambos vazios, link "Esqueci minha senha" **desabilitado/cinza** com tooltip "Recuperação de senha disponível em breve". Erro 401 → alert MUI inline abaixo do form com texto "E-mail ou senha inválidos. Verifique e tente novamente." + limpa campo senha + foco retorna a ele. Erro 429 (rate-limit) → alert "Muitas tentativas. Aguarde alguns instantes e tente novamente." Sucesso → `navigate("/jornadas")` (PrivacyGuard redireciona para `/privacidade` se aceite pendente).

**Saudação:** acima do form, MUI Typography `variant="h5"` exibindo apenas a saudação (sem nome, porque ainda não autenticado) — "Bom dia.", "Boa tarde.", "Boa noite." Conforme faixa horária local.

**Validação client-side** (Zod + RHF): `email` formato e-mail; `senha` mínimo 8 chars. Erro de validação → helper text inline por campo; botão "Entrar" desabilitado enquanto `isValid=false`.

**Acessibilidade:** form com `noValidate` (RHF cuida); inputs com `aria-invalid` + helper text; alert de erro com `role="alert"`; botão "Entrar" tem `aria-busy="true"` durante submit; tabindex padrão.

**Dependência:** TASK-020 (única).

## Comportamento Esperado

| Entrada / Ação | Saída / Efeito esperado |
| -------------- | ----------------------- |
| Mount `/login` às 10h | Renderiza heading `<h1>` "Login", `<h5>` "Bom dia.", form com campos "E-mail" + "Senha" + botão "Entrar" (desabilitado) |
| Mount `/login` às 14h | Saudação "Boa tarde." |
| Digitar `e-mail-invalido` em e-mail | helper text "E-mail inválido"; campo com `aria-invalid="true"`; botão "Entrar" continua desabilitado |
| Preencher `maria@acme.com` + `MinhaSenha123` e clicar "Entrar" | Botão entra em loading (`aria-busy="true"`); chama `useAuth().login(...)`; sucesso → `navigate("/jornadas")` |
| Backend retorna 401 `{code:"UNAUTHORIZED", message:"E-mail ou senha inválidos"}` | Alert `role="alert"` exibe "E-mail ou senha inválidos. Verifique e tente novamente."; campo `senha` zerado; foco em `senha` |
| Backend retorna 429 `{code:"RATE_LIMITED"}` | Alert "Muitas tentativas. Aguarde alguns instantes e tente novamente." |
| Backend retorna erro de rede (sem response) | Alert "Falha de conexão. Verifique o serviço local." |
| Clicar "Esqueci minha senha" | Nenhuma navegação (link desabilitado); tooltip "Recuperação de senha disponível em breve" no hover |

## TDD

**Testes a escrever antes da implementação** (`apps/web/src/pages/Login/LoginPage.test.tsx`):

```typescript
import { describe, it, expect, beforeEach, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MockAdapter from "axios-mock-adapter";
import api from "@/api/client";
import { renderWithProviders } from "@/test/render";
import { LoginPage } from "@/pages/Login/LoginPage";

const mock = new MockAdapter(api);

describe("LoginPage", () => {
  beforeEach(() => {
    mock.reset();
    sessionStorage.clear();
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  it("exibe heading h1 'Login' e saudação 'Bom dia.' às 09:00", () => {
    vi.setSystemTime(new Date("2026-05-27T09:00:00"));
    renderWithProviders(<LoginPage />, { route: "/login" });
    expect(screen.getByRole("heading", { level: 1, name: /Login/i })).toBeInTheDocument();
    expect(screen.getByText("Bom dia.")).toBeInTheDocument();
  });

  it("exibe 'Boa tarde.' às 14:00", () => {
    vi.setSystemTime(new Date("2026-05-27T14:00:00"));
    renderWithProviders(<LoginPage />, { route: "/login" });
    expect(screen.getByText("Boa tarde.")).toBeInTheDocument();
  });

  it("botão Entrar inicia desabilitado e fica habilitado quando ambos campos válidos", async () => {
    renderWithProviders(<LoginPage />, { route: "/login" });
    const btn = screen.getByRole("button", { name: /Entrar/i });
    expect(btn).toBeDisabled();
    await userEvent.type(screen.getByLabelText(/E-mail/i), "maria@acme.com");
    await userEvent.type(screen.getByLabelText(/Senha/i), "MinhaSenha123");
    await waitFor(() => expect(btn).toBeEnabled());
  });

  it("e-mail inválido exibe helper text 'E-mail inválido'", async () => {
    renderWithProviders(<LoginPage />, { route: "/login" });
    await userEvent.type(screen.getByLabelText(/E-mail/i), "nao-eh-email");
    await userEvent.tab();
    expect(await screen.findByText(/E-mail inválido/i)).toBeInTheDocument();
  });

  it("submit válido chama POST /auth/login e persiste tokens", async () => {
    mock.onPost("/api/v1/auth/login").reply(200, {
      access_token: "atok-1", refresh_token: "rtok-1",
      terceiro_id: "uuid-1", expires_in: 900,
    });
    renderWithProviders(<LoginPage />, { route: "/login" });
    await userEvent.type(screen.getByLabelText(/E-mail/i), "maria@acme.com");
    await userEvent.type(screen.getByLabelText(/Senha/i), "MinhaSenha123");
    await userEvent.click(screen.getByRole("button", { name: /Entrar/i }));
    await waitFor(() => expect(sessionStorage.getItem("ts:access_token")).toBe("atok-1"));
    expect(sessionStorage.getItem("ts:terceiro_id")).toBe("uuid-1");
  });

  it("401 exibe alert 'E-mail ou senha inválidos' e limpa campo senha", async () => {
    mock.onPost("/api/v1/auth/login").reply(401, {
      code: "UNAUTHORIZED", message: "E-mail ou senha inválidos", details: [],
    });
    renderWithProviders(<LoginPage />, { route: "/login" });
    await userEvent.type(screen.getByLabelText(/E-mail/i), "maria@acme.com");
    const senha = screen.getByLabelText(/Senha/i) as HTMLInputElement;
    await userEvent.type(senha, "SenhaErrada123");
    await userEvent.click(screen.getByRole("button", { name: /Entrar/i }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(/E-mail ou senha inválidos\. Verifique e tente novamente\./i);
    expect(senha.value).toBe("");
    expect(document.activeElement).toBe(senha);
  });

  it("429 exibe alert 'Muitas tentativas. Aguarde alguns instantes e tente novamente.'", async () => {
    mock.onPost("/api/v1/auth/login").reply(429, {
      code: "RATE_LIMITED", message: "Muitas tentativas", details: [],
    });
    renderWithProviders(<LoginPage />, { route: "/login" });
    await userEvent.type(screen.getByLabelText(/E-mail/i), "maria@acme.com");
    await userEvent.type(screen.getByLabelText(/Senha/i), "MinhaSenha123");
    await userEvent.click(screen.getByRole("button", { name: /Entrar/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      /Muitas tentativas\. Aguarde alguns instantes e tente novamente\./i
    );
  });

  it("link 'Esqueci minha senha' está desabilitado com aria-disabled=true", () => {
    renderWithProviders(<LoginPage />, { route: "/login" });
    const link = screen.getByText(/Esqueci minha senha/i);
    expect(link).toHaveAttribute("aria-disabled", "true");
  });
});
```

> **Quirk userEvent + RHF**: usar `userEvent.tab()` para acionar `onBlur` que dispara validação Zod com `mode: "onBlur"`. Caso queira `onChange` immediate, usar `mode: "onChange"` mas custa mais re-renders.

**Refatoração:** após green, considerar extrair `<SaudacaoHeader />` para `src/components/SaudacaoHeader.tsx` se TASK-022 (Privacidade) também precisar — por ora, inline no `LoginPage`.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| ------- | ---- | --------- |
| `apps/web/src/pages/Login/LoginPage.tsx` | Criar | Componente da página `/login` |
| `apps/web/src/pages/Login/LoginPage.test.tsx` | Criar | Testes TDD acima |
| `apps/web/src/lib/schemas/login.ts` | Criar | Zod schema `loginSchema` + tipo `LoginFormValues` |
| `apps/web/src/routes.tsx` | Modificar | Substituir import `LoginPageStub` por `LoginPage` real |

> 3 criados + 1 modificado = **4 arquivos-alvo**. Dentro do teto.

### Detalhamento Técnico

**1. `src/lib/schemas/login.ts`**:

```typescript
import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().min(1, "Informe seu e-mail").email("E-mail inválido"),
  senha: z.string().min(8, "Senha deve ter ao menos 8 caracteres"),
});

export type LoginFormValues = z.infer<typeof loginSchema>;
```

**2. `src/pages/Login/LoginPage.tsx`**:

```typescript
import { useEffect, useRef, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  Container, Paper, Typography, TextField, Button, Alert, Link, Tooltip, Box,
} from "@mui/material";
import { useAuth } from "@/auth/AuthContext";
import { saudacaoAgora } from "@/lib/saudacao";
import { parseApiError } from "@/lib/errors";
import { loginSchema, type LoginFormValues } from "@/lib/schemas/login";

interface ErrorState { code: string; message: string; }

const MENSAGENS: Record<string, string> = {
  UNAUTHORIZED: "E-mail ou senha inválidos. Verifique e tente novamente.",
  RATE_LIMITED: "Muitas tentativas. Aguarde alguns instantes e tente novamente.",
  NETWORK_ERROR: "Falha de conexão. Verifique o serviço local.",
};

export function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [serverError, setServerError] = useState<ErrorState | null>(null);
  const senhaRef = useRef<HTMLInputElement | null>(null);

  const {
    register, handleSubmit, formState: { errors, isValid, isSubmitting }, resetField, setFocus,
  } = useForm<LoginFormValues>({
    mode: "onBlur",
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", senha: "" },
  });

  // Já autenticado → redirecionar
  useEffect(() => {
    if (isAuthenticated) {
      const from = (location.state as { from?: string } | null)?.from ?? "/jornadas";
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, location.state, navigate]);

  async function onSubmit(values: LoginFormValues): Promise<void> {
    setServerError(null);
    try {
      await login(values.email, values.senha);
      navigate("/jornadas", { replace: true });
    } catch (err) {
      const parsed = parseApiError(err);
      setServerError({
        code: parsed.code,
        message: MENSAGENS[parsed.code] ?? parsed.message,
      });
      // Limpa senha e foca
      resetField("senha");
      setTimeout(() => setFocus("senha"), 0);
    }
  }

  const saud = saudacaoAgora();

  return (
    <Container maxWidth="xs" sx={{ mt: 8 }}>
      <Paper elevation={2} sx={{ p: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Login
        </Typography>
        <Typography variant="h5" component="p" color="text.secondary" mb={3}>
          {saud}.
        </Typography>
        <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate>
          <TextField
            label="E-mail"
            type="email"
            fullWidth
            margin="normal"
            error={Boolean(errors.email)}
            helperText={errors.email?.message ?? " "}
            inputProps={{ "aria-invalid": Boolean(errors.email) }}
            {...register("email")}
            autoFocus
          />
          <TextField
            label="Senha"
            type="password"
            fullWidth
            margin="normal"
            error={Boolean(errors.senha)}
            helperText={errors.senha?.message ?? " "}
            inputProps={{ "aria-invalid": Boolean(errors.senha) }}
            {...register("senha")}
            inputRef={senhaRef}
          />
          {serverError && (
            <Alert severity="error" role="alert" sx={{ mt: 2 }}>
              {serverError.message}
            </Alert>
          )}
          <Button
            type="submit"
            variant="contained"
            fullWidth
            size="large"
            sx={{ mt: 3, mb: 2 }}
            disabled={!isValid || isSubmitting}
            aria-busy={isSubmitting}
          >
            {isSubmitting ? "Entrando..." : "Entrar"}
          </Button>
          <Tooltip title="Recuperação de senha disponível em breve">
            <Link
              component="span"
              aria-disabled="true"
              sx={{ display: "block", textAlign: "center", color: "text.disabled", cursor: "not-allowed" }}
            >
              Esqueci minha senha
            </Link>
          </Tooltip>
        </Box>
      </Paper>
    </Container>
  );
}
```

**3. `src/routes.tsx` — diff (substituir o stub):**

```typescript
// Remover:
// import { LoginPageStub, ... } from "@/routes/PageStubs";

// Adicionar:
import { LoginPage } from "@/pages/Login/LoginPage";
// (Manter import dos OUTROS stubs no PageStubs até suas próprias tasks substituírem.)

// E na lista de rotas, substituir:
// { path: "/login", element: <LoginPageStub /> },
// Por:
// { path: "/login", element: <LoginPage /> },
```

> **Regra de toque em `routes.tsx`**: substituir SOMENTE a linha de `/login`; não tocar outras rotas (suas tasks fazem o mesmo). Conflitos de merge improváveis (cada task edita linhas distintas e import distinto).

## Contratos com camadas adjacentes

```
Produz para:
  Phase 6 (E2E): página de Login estável; fluxo "Onboarding completo" parte daqui.

Consome de:
  TASK-020: useAuth().login, parseApiError, saudacaoAgora, renderWithProviders (testes).
  Backend Phase 3 (TASK-013): POST /api/v1/auth/login.

Erros:
  - 401 UNAUTHORIZED → alert "E-mail ou senha inválidos. Verifique e tente novamente." + limpa senha + foco
  - 429 RATE_LIMITED → alert "Muitas tentativas. Aguarde alguns instantes e tente novamente."
  - NETWORK_ERROR → alert "Falha de conexão. Verifique o serviço local."
  - Outros: usar parsed.message (passthrough do backend)
```

## Contrato HTTP

```
POST /api/v1/auth/login
Content-Type: application/json

Request body:
{
  "email": "maria@acme.com",        // EmailStr; client valida com Zod email()
  "senha": "MinhaSenha123"          // min 8 max 128
}

Response 200:
{
  "access_token": "<jwt>",
  "refresh_token": "<token>",
  "terceiro_id": "<uuid>",
  "expires_in": 900               // segundos (15 min)
}

Response 401: {"code":"UNAUTHORIZED","message":"E-mail ou senha inválidos","details":[]}
Response 429: {"code":"RATE_LIMITED","message":"...","details":[]}
Response 422: {"code":"VALIDATION_ERROR","message":"...","details":[{"field":"body.email","issue":"..."}]}
```

**Validação obrigatória pelo executor antes de marcar done:**

1. `cd apps/web && npm test -- --run src/pages/Login/LoginPage.test.tsx` — 8 testes passam.
2. `cd apps/web && npm test -- --run` — toda a suite continua verde; coverage >= 80.
3. `cd apps/web && npm run typecheck` — 0 erros.
4. `cd apps/web && npm run lint` — 0 warnings.
5. `cd apps/web && npm run build` — `dist/` gerado sem erros.
6. `make smoke` (raiz) — Phase 1 smoke continua passando.

> Executor DEVE rodar 1–6 e garantir saída 0 antes de retornar. Falha = task não concluída.

**Refatoração:** após green, extrair `<SaudacaoHeader />` para `src/components/SaudacaoHeader.tsx` somente se TASK-022 (Privacidade) também usar saudação acima do form — caso contrário, manter inline.
