---
checkpoint: null
complexity: G
created_at: "2026-05-28 12:37:21"
criteria:
    - done: false
      test: cd apps/web && npm test -- --run src/auth/AuthContext.test.tsx -t "login persiste tokens"
      text: POST /auth/login persiste tokens no sessionStorage e atualiza isAuthenticated
    - done: false
      test: cd apps/web && npm test -- --run src/api/client.test.ts -t "injeta Authorization Bearer"
      text: 'Request interceptor injeta Authorization: Bearer com access_token do sessionStorage'
    - done: false
      test: cd apps/web && npm test -- --run src/api/client.test.ts -t "em 401 chama /auth/refresh"
      text: Response 401 dispara POST /auth/refresh, atualiza tokens e refaz o request original
    - done: false
      test: cd apps/web && npm test -- --run src/api/client.test.ts -t "em refresh falhando"
      text: Refresh falhando limpa sessionStorage e propaga 401
    - done: false
      test: cd apps/web && npm test -- --run src/routes/ProtectedRoute.test.tsx -t "redireciona para /login"
      text: ProtectedRoute redireciona para /login quando isAuthenticated=false
    - done: false
      test: cd apps/web && npm test -- --run src/lib/saudacao.test.ts
      text: saudacaoPorHora retorna Bom dia para 0..11, Boa tarde 12..17, Boa noite 18..23 (valores exatos)
    - done: false
      test: cd apps/web && npm test -- --run src/lib/errors.test.ts
      text: parseApiError extrai code message e fields com strip do prefixo body.
    - done: false
      test: 'grep -E "path: \"/(login|privacidade|jornadas|cadastro|relatorios|configuracoes/smtp)" apps/web/src/routes.tsx'
      text: Routes registra TODAS as 9 rotas /login /privacidade /jornadas /jornadas/:id /jornadas/manual /cadastro /cadastro/senha /relatorios /configuracoes/smtp
    - done: false
      text: ESLint passa sem warnings e tsc strict 0 erros
    - done: false
      test: cd apps/web && npm run build
      text: vite build gera dist sem erros
    - done: false
      text: Testes passando com cobertura >= 80%
    - done: false
      text: make smoke continua passando
deps: []
id: TASK-020
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
tests: cd apps/web && npm test -- --run
title: 'Fundação Frontend: Axios + JWT interceptor, AuthContext, QueryClient, Router central com guards, AppLayout, types do contrato, helpers'
updated_at: "2026-05-28 12:37:21"
---
## Contexto

Fundação transversal do Frontend (React 18 + Vite + MUI + TanStack Query + React Hook Form + Zod + Axios) — todas as features de Phase 4 (Login, Privacidade, Jornadas listar/detalhe/manual, Cadastro, Senha, Relatórios, SMTP Config) consomem esta task. A fundação **decide e cria** o transversal arquitetural do `apps/web` que se torna **regra dura** para as 7 tasks subsequentes:

- **HTTP client único** (`axios`) com `baseURL=""` (aproveita proxy `/api` do Vite dev e mesmo origin em prod) + interceptor de Authorization Bearer + interceptor de refresh 401→`/auth/refresh`→retry.
- **AuthContext** com persistência em `sessionStorage` (não localStorage — fecha aba = logout, alinhado a "1 Terceiro single-tenant") dos campos `{accessToken, refreshToken, terceiroId, expiresIn, expiresAt}`. Expõe `login(email, senha)`, `logout()`, `isAuthenticated`, `terceiroId`. Refresh é orquestrado pelo interceptor, **não** pelo contexto.
- **Padrão de query/mutation**: TanStack Query v5; **um arquivo `api/<dominio>.ts` por domínio** exporta `<dominio>Keys` (query keys factory) + funções HTTP puras (sem `useQuery`); **um arquivo `hooks/use<Dominio>.ts` por domínio** exporta os hooks (`useLogin`, `useJornadasMes`, etc). Padrão **fechado** — task subsequente nunca cria axios próprio, AuthContext próprio ou QueryClient próprio.
- **Roteamento**: `react-router-dom` v6, todas as rotas registradas em `src/routes.tsx` (não em `App.tsx`) com `createBrowserRouter` + `RouterProvider`. Guards: `<ProtectedRoute>` (exige `isAuthenticated`), `<PrivacyGuard>` (exige aceite atual, redireciona para `/privacidade` se faltar). Cada página tem um **stub** (componente placeholder com 1 `<Typography>` "Em construção") substituído pela task da feature.
- **AppLayout**: AppBar superior MUI com saudação contextual (Bom dia/Boa tarde/Boa noite, RF-001) + nome do Terceiro + Drawer lateral com links (Jornadas, Cadastro, Relatórios) + botão de logout. Páginas autenticadas (todas exceto `/login` e `/privacidade`) renderizam dentro de `<AppLayout><Outlet/></AppLayout>`.
- **Tipos do contrato** em `src/types/contracts.ts` (espelham exatamente os schemas Pydantic do Backend Phase 3 — não inferir, copiar).
- **Helpers de erro**: função `parseApiError(err)` retorna `{code, message, fields: Record<string,string>}` a partir do formato padronizado `{code, message, details:[{field, issue}]}` do Backend.
- **Test infra**: `MockAdapter` do `axios-mock-adapter` para mockar HTTP nos testes; **fixture `renderWithProviders(ui, {route, authState})`** que monta `QueryClientProvider` + `MemoryRouter` + `AuthContext.Provider` + `ThemeProvider` MUI.

**State atual** (Phase 1 entregou via TASK-003): `apps/web` com `package.json` + `vite.config.ts` + `tsconfig.json` strict + `src/App.tsx` (apenas Typography "TimeSheet Terceiros") + `src/main.tsx` (ThemeProvider) + `src/App.test.tsx` + `src/test/setup.ts`. Esta task **substitui** `App.tsx` (passa a só conter `<RouterProvider router={router}/>`) e **substitui** `App.test.tsx` (passa a testar que rota `/login` renderiza heading da página) — o atual teste de "TimeSheet Terceiros" será movido para teste do `AppLayout` (a saudação inclui o nome do produto).

**Phase 3 backend já entregue** com os endpoints `/api/v1/{auth, terceiros, privacidade, smtp, marcacoes, jornadas, atividades, auditoria, relatorios, health, ready, config}` — contratos de request/response copiados nas seções "Contrato HTTP" desta task; as tasks de feature recebem o subset que consomem.

**Dependência sequencial**: nenhuma — primeira task da fase. Todas as outras (TASK-021..027) dependem desta. Cabe a esta task decidir todos os padrões arquiteturais; tasks de feature que precisem algo fora deste contrato devem bloquear e escalar, nunca improvisar.

## Comportamento Esperado

| Entrada / Ação | Saída / Efeito esperado |
| -------------- | ----------------------- |
| `import api from "@/api/client"; await api.get("/api/v1/health")` em qualquer módulo | Retorna `{data: {status: "ok", version: "0.1.0"}}`; baseURL vazia ⇒ proxy Vite encaminha para `127.0.0.1:8765` |
| Request a endpoint autenticado com `accessToken` no `sessionStorage` | Header `Authorization: Bearer <token>` injetado pelo request interceptor |
| Resposta `401` durante request autenticado | Response interceptor chama `POST /api/v1/auth/refresh` com `refresh_token`; sucesso → atualiza tokens, refaz request original; falha → `logout()` + redireciona `/login` |
| `useAuth().login("maria@acme.com", "MinhaSenha123!")` com credenciais válidas | Chama `POST /api/v1/auth/login`; persiste `{accessToken, refreshToken, terceiroId, expiresAt}` em `sessionStorage`; estado React atualiza `isAuthenticated=true` |
| Navegar para `/jornadas` sem `isAuthenticated` | `<ProtectedRoute>` redireciona via `<Navigate to="/login" replace state={{from: "/jornadas"}}/>` |
| Navegar para `/jornadas` com aceite de privacidade pendente | `<PrivacyGuard>` consulta `GET /api/v1/privacidade`; `accepted=false` → redirect `/privacidade` |
| Navegar para `/privacidade` com aceite já registrado | `<PrivacyGuard>` redirect `/jornadas` |
| Hora local 10:30 ao montar `<AppLayout>` | AppBar exibe "Bom dia, <nome>" (faixa 0–12 = "Bom dia") |
| Hora local 14:00 | "Boa tarde, <nome>" (faixa 12–18) |
| Hora local 20:00 | "Boa noite, <nome>" (faixa 18–24) |
| Backend retorna `{code:"VALIDATION_ERROR", message:"...", details:[{field:"body.empresa_cnpj", issue:"CNPJ inválido"}]}` | `parseApiError(err)` retorna `{code:"VALIDATION_ERROR", message:"...", fields:{empresa_cnpj:"CNPJ inválido"}}` (strip do prefixo `body.`) |
| Clicar "Sair" no AppBar | `logout()` limpa `sessionStorage`, invalida queries, redireciona `/login` |

## TDD

**Testes a escrever antes da implementação:**

```typescript
// src/auth/AuthContext.test.tsx
import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import MockAdapter from "axios-mock-adapter";
import api from "@/api/client";
import { AuthProvider, useAuth } from "@/auth/AuthContext";

const mock = new MockAdapter(api);

describe("AuthContext", () => {
  beforeEach(() => {
    sessionStorage.clear();
    mock.reset();
  });

  it("login persiste tokens no sessionStorage e marca autenticado", async () => {
    mock.onPost("/api/v1/auth/login").reply(200, {
      access_token: "atok",
      refresh_token: "rtok",
      terceiro_id: "uuid-1",
      expires_in: 900,
    });
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <AuthProvider>{children}</AuthProvider>
    );
    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.isAuthenticated).toBe(false);
    await act(async () => {
      await result.current.login("maria@acme.com", "MinhaSenha123!");
    });
    await waitFor(() => expect(result.current.isAuthenticated).toBe(true));
    expect(result.current.terceiroId).toBe("uuid-1");
    expect(sessionStorage.getItem("ts:access_token")).toBe("atok");
    expect(sessionStorage.getItem("ts:refresh_token")).toBe("rtok");
  });

  it("logout limpa sessionStorage e marca desautenticado", async () => {
    sessionStorage.setItem("ts:access_token", "atok");
    sessionStorage.setItem("ts:refresh_token", "rtok");
    sessionStorage.setItem("ts:terceiro_id", "uuid-1");
    sessionStorage.setItem("ts:expires_at", String(Date.now() + 60_000));
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <AuthProvider>{children}</AuthProvider>
    );
    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.isAuthenticated).toBe(true);
    act(() => result.current.logout());
    expect(result.current.isAuthenticated).toBe(false);
    expect(sessionStorage.getItem("ts:access_token")).toBeNull();
  });
});

// src/api/client.test.ts
import { describe, it, expect, beforeEach } from "vitest";
import MockAdapter from "axios-mock-adapter";
import api from "@/api/client";

const mock = new MockAdapter(api);

describe("api client interceptors", () => {
  beforeEach(() => {
    sessionStorage.clear();
    mock.reset();
  });

  it("injeta Authorization Bearer quando access_token presente", async () => {
    sessionStorage.setItem("ts:access_token", "atok-123");
    mock.onGet("/api/v1/jornadas").reply((config) => {
      expect(config.headers?.Authorization).toBe("Bearer atok-123");
      return [200, { mes_referencia: "2026-05", total_horas_mes_s: 0, jornadas: [] }];
    });
    await api.get("/api/v1/jornadas", { params: { mes: "2026-05" } });
  });

  it("em 401 chama /auth/refresh, persiste novos tokens e refaz request", async () => {
    sessionStorage.setItem("ts:access_token", "atok-velho");
    sessionStorage.setItem("ts:refresh_token", "rtok-velho");
    let primeiraChamada = true;
    mock.onGet("/api/v1/jornadas").reply(() => {
      if (primeiraChamada) {
        primeiraChamada = false;
        return [401, { code: "UNAUTHORIZED", message: "expirado", details: [] }];
      }
      return [200, { mes_referencia: "2026-05", total_horas_mes_s: 0, jornadas: [] }];
    });
    mock.onPost("/api/v1/auth/refresh").reply(200, {
      access_token: "atok-novo",
      refresh_token: "rtok-novo",
      expires_in: 900,
    });
    const r = await api.get("/api/v1/jornadas", { params: { mes: "2026-05" } });
    expect(r.status).toBe(200);
    expect(sessionStorage.getItem("ts:access_token")).toBe("atok-novo");
    expect(sessionStorage.getItem("ts:refresh_token")).toBe("rtok-novo");
  });

  it("em refresh falhando, limpa sessão e propaga 401", async () => {
    sessionStorage.setItem("ts:access_token", "atok");
    sessionStorage.setItem("ts:refresh_token", "rtok-revogado");
    mock.onGet("/api/v1/jornadas").reply(401, { code: "UNAUTHORIZED", message: "expirado", details: [] });
    mock.onPost("/api/v1/auth/refresh").reply(401, { code: "UNAUTHORIZED", message: "revogado", details: [] });
    await expect(api.get("/api/v1/jornadas", { params: { mes: "2026-05" } })).rejects.toThrow();
    expect(sessionStorage.getItem("ts:access_token")).toBeNull();
  });
});

// src/lib/saudacao.test.ts
import { describe, it, expect } from "vitest";
import { saudacaoPorHora } from "@/lib/saudacao";

describe("saudacaoPorHora", () => {
  it("0 a 11 → Bom dia", () => {
    expect(saudacaoPorHora(0)).toBe("Bom dia");
    expect(saudacaoPorHora(11)).toBe("Bom dia");
  });
  it("12 a 17 → Boa tarde", () => {
    expect(saudacaoPorHora(12)).toBe("Boa tarde");
    expect(saudacaoPorHora(17)).toBe("Boa tarde");
  });
  it("18 a 23 → Boa noite", () => {
    expect(saudacaoPorHora(18)).toBe("Boa noite");
    expect(saudacaoPorHora(23)).toBe("Boa noite");
  });
});

// src/lib/errors.test.ts
import { describe, it, expect } from "vitest";
import { parseApiError } from "@/lib/errors";
import { AxiosError } from "axios";

describe("parseApiError", () => {
  it("extrai code, message e fields (strip body. prefix)", () => {
    const err = new AxiosError("Request failed");
    (err as any).response = {
      data: {
        code: "VALIDATION_ERROR",
        message: "Erro de validação",
        details: [
          { field: "body.empresa_cnpj", issue: "CNPJ inválido" },
          { field: "body.senha", issue: "muito curta" },
        ],
      },
    };
    expect(parseApiError(err)).toEqual({
      code: "VALIDATION_ERROR",
      message: "Erro de validação",
      fields: { empresa_cnpj: "CNPJ inválido", senha: "muito curta" },
    });
  });
  it("erro de rede sem response retorna code=NETWORK_ERROR", () => {
    const err = new AxiosError("Network Error");
    expect(parseApiError(err)).toEqual({
      code: "NETWORK_ERROR",
      message: "Falha de conexão. Verifique o serviço local.",
      fields: {},
    });
  });
});

// src/routes/ProtectedRoute.test.tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/auth/AuthContext";
import { ProtectedRoute } from "@/routes/ProtectedRoute";

describe("ProtectedRoute", () => {
  beforeEach(() => sessionStorage.clear());
  it("redireciona para /login quando não autenticado", () => {
    render(
      <MemoryRouter initialEntries={["/jornadas"]}>
        <AuthProvider>
          <Routes>
            <Route element={<ProtectedRoute />}>
              <Route path="/jornadas" element={<div>JornadasOK</div>} />
            </Route>
            <Route path="/login" element={<div>LoginPage</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );
    expect(screen.getByText("LoginPage")).toBeInTheDocument();
  });
  it("renderiza Outlet quando autenticado", () => {
    sessionStorage.setItem("ts:access_token", "atok");
    sessionStorage.setItem("ts:refresh_token", "rtok");
    sessionStorage.setItem("ts:terceiro_id", "uuid");
    sessionStorage.setItem("ts:expires_at", String(Date.now() + 60_000));
    render(
      <MemoryRouter initialEntries={["/jornadas"]}>
        <AuthProvider>
          <Routes>
            <Route element={<ProtectedRoute />}>
              <Route path="/jornadas" element={<div>JornadasOK</div>} />
            </Route>
            <Route path="/login" element={<div>LoginPage</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    );
    expect(screen.getByText("JornadasOK")).toBeInTheDocument();
  });
});

// src/components/AppLayout.test.tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { renderWithProviders } from "@/test/render";
import { AppLayout } from "@/components/AppLayout";

describe("AppLayout", () => {
  it("renderiza saudação 'Bom dia' quando hora=09", () => {
    vi.setSystemTime(new Date("2026-05-27T09:00:00-03:00"));
    renderWithProviders(<AppLayout><div>conteudo</div></AppLayout>, {
      authState: { terceiroId: "uuid", terceiroNome: "Maria" },
    });
    expect(screen.getByRole("banner")).toHaveTextContent(/Bom dia, Maria/i);
  });
  it("link 'Sair' chama logout", async () => {
    sessionStorage.setItem("ts:access_token", "a");
    sessionStorage.setItem("ts:refresh_token", "r");
    sessionStorage.setItem("ts:terceiro_id", "u");
    sessionStorage.setItem("ts:expires_at", String(Date.now() + 60_000));
    renderWithProviders(<AppLayout><div>x</div></AppLayout>, {
      authState: { terceiroId: "u", terceiroNome: "Maria" },
    });
    await userEvent.click(screen.getByRole("button", { name: /sair/i }));
    expect(sessionStorage.getItem("ts:access_token")).toBeNull();
  });
});
```

> **Vitest fake timers**: usar `vi.useFakeTimers()` + `vi.setSystemTime(...)` no início de cada teste de saudação; chamar `vi.useRealTimers()` no `afterEach` global. Sem isso, os testes falham 2× ao dia quando o relógio real cruzar a borda da faixa.

**Refatoração:** após green, considerar extrair `STORAGE_KEYS = {accessToken: "ts:access_token", ...}` para `src/auth/storage.ts` se ≥2 lugares lerem direto (duplicação real). Por ora, manter inline em `AuthContext.tsx`.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| ------- | ---- | --------- |
| `apps/web/package.json` | Modificar | Adicionar `react-router-dom` já está; **adicionar** `axios-mock-adapter` em devDependencies (`^1.22.0`) |
| `apps/web/src/api/client.ts` | Criar | Instância Axios + request interceptor (Authorization) + response interceptor (refresh 401) |
| `apps/web/src/api/auth.ts` | Criar | `postLogin`, `postRefresh`, `postLogout` (funções puras retornando `Promise<LoginResponse|...>`) |
| `apps/web/src/auth/AuthContext.tsx` | Criar | `AuthProvider`, `useAuth()`, persistência em sessionStorage |
| `apps/web/src/auth/AuthContext.test.tsx` | Criar | Testes do hook |
| `apps/web/src/api/client.test.ts` | Criar | Testes dos interceptors |
| `apps/web/src/lib/saudacao.ts` | Criar | `saudacaoPorHora(h: number): "Bom dia"\|"Boa tarde"\|"Boa noite"` |
| `apps/web/src/lib/saudacao.test.ts` | Criar | Testes do helper |
| `apps/web/src/lib/errors.ts` | Criar | `parseApiError(err): {code, message, fields}` |
| `apps/web/src/lib/errors.test.ts` | Criar | Testes do parser |
| `apps/web/src/types/contracts.ts` | Criar | Tipos TS espelhando schemas Pydantic (copiados — não inferir) |
| `apps/web/src/components/AppLayout.tsx` | Criar | AppBar + Drawer + Outlet |
| `apps/web/src/components/AppLayout.test.tsx` | Criar | Testes do layout |
| `apps/web/src/routes/ProtectedRoute.tsx` | Criar | Outlet protegido por `useAuth` |
| `apps/web/src/routes/ProtectedRoute.test.tsx` | Criar | Testes do guard de auth |
| `apps/web/src/routes/PrivacyGuard.tsx` | Criar | Outlet protegido por `useQuery(/privacidade)` |
| `apps/web/src/routes/PageStubs.tsx` | Criar | Componentes-stub para cada rota (Login, Privacidade, Jornadas, JornadaDetalhe, JornadaManual, Cadastro, Senha, Relatorios, SmtpConfig). Cada stub: `<Typography>Em construção — TASK-NNN</Typography>` |
| `apps/web/src/routes.tsx` | Criar | `createBrowserRouter` exportando `router`; declara TODAS as rotas com componentes-stub; substituições virão das tasks 021..027 |
| `apps/web/src/test/render.tsx` | Criar | `renderWithProviders(ui, opts)`: monta QueryClient + MemoryRouter + AuthContext + Theme |
| `apps/web/src/App.tsx` | Modificar | Substituir conteúdo por `<QueryClientProvider><AuthProvider><RouterProvider router={router}/></AuthProvider></QueryClientProvider>` |
| `apps/web/src/App.test.tsx` | Modificar | Substituir: testar que `App` renderiza `LoginPage` (stub "Em construção") na rota inicial `/login` |
| `apps/web/src/main.tsx` | Modificar | Mantém ThemeProvider; remove import de `App` antigo, importa `App` novo |

> Total: 18 criados + 3 modificados = **21 alvos**. **Excede** o teto de 8 — Fundação Frontend é exceção análoga à Fundação Backend (TASK-012). Justificativa documentada: coesão arquitetural (cliente HTTP, interceptor, auth context, router central, guards, layout, helpers, infra de teste) — dividir gera dependências em árvore (Router precisa de Guards que precisam de AuthContext que precisa de api/client que precisa de types) com risco alto de drift entre subtasks. **Tipos pesados** = 0 (sem mount E2E aqui); arquivos médios; cabe em uma sessão.

### Detalhamento Técnico

**1. `src/api/client.ts`** — Axios + interceptors:

```typescript
import axios, { AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from "axios";

const STORAGE = {
  accessToken: "ts:access_token",
  refreshToken: "ts:refresh_token",
  terceiroId: "ts:terceiro_id",
  expiresAt: "ts:expires_at",
} as const;

const api = axios.create({
  baseURL: "",
  timeout: 15_000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const tok = sessionStorage.getItem(STORAGE.accessToken);
  if (tok && config.headers) {
    config.headers.Authorization = `Bearer ${tok}`;
  }
  return config;
});

type RetriableConfig = InternalAxiosRequestConfig & { _retry?: boolean };

let refreshPromise: Promise<string> | null = null;

async function doRefresh(): Promise<string> {
  const rtok = sessionStorage.getItem(STORAGE.refreshToken);
  if (!rtok) throw new Error("no refresh token");
  // Usar instância nova para evitar loop infinito de interceptors
  const fresh = axios.create({ baseURL: "" });
  const r = await fresh.post<{ access_token: string; refresh_token: string; expires_in: number }>(
    "/api/v1/auth/refresh",
    { refresh_token: rtok }
  );
  sessionStorage.setItem(STORAGE.accessToken, r.data.access_token);
  sessionStorage.setItem(STORAGE.refreshToken, r.data.refresh_token);
  sessionStorage.setItem(STORAGE.expiresAt, String(Date.now() + r.data.expires_in * 1000));
  return r.data.access_token;
}

function clearSession() {
  sessionStorage.removeItem(STORAGE.accessToken);
  sessionStorage.removeItem(STORAGE.refreshToken);
  sessionStorage.removeItem(STORAGE.terceiroId);
  sessionStorage.removeItem(STORAGE.expiresAt);
}

api.interceptors.response.use(
  (r: AxiosResponse) => r,
  async (error: AxiosError) => {
    const status = error.response?.status;
    const cfg = error.config as RetriableConfig | undefined;
    const url = cfg?.url ?? "";

    // Sem retry para os próprios endpoints de auth ou se já tentou
    const isAuthEndpoint =
      url.includes("/api/v1/auth/login") ||
      url.includes("/api/v1/auth/refresh") ||
      url.includes("/api/v1/auth/logout");

    if (status === 401 && cfg && !cfg._retry && !isAuthEndpoint) {
      cfg._retry = true;
      try {
        const novoToken = await (refreshPromise ?? (refreshPromise = doRefresh()));
        cfg.headers = cfg.headers ?? {};
        cfg.headers.Authorization = `Bearer ${novoToken}`;
        return api(cfg);
      } catch {
        clearSession();
        // Disparar evento custom para AuthProvider sincronizar e router redirecionar
        window.dispatchEvent(new CustomEvent("ts:auth-logout"));
        throw error;
      } finally {
        refreshPromise = null;
      }
    }
    return Promise.reject(error);
  }
);

export { STORAGE };
export default api;
```

> **Por que `let refreshPromise`**: dedupe — se 5 requests paralelas tomarem 401 ao mesmo tempo, só 1 `POST /auth/refresh` dispara; as outras 4 aguardam o mesmo Promise.

> **Evento `ts:auth-logout`**: AuthProvider escuta e chama seu `logout()` interno + router navega; alternativa (acoplar Axios ao Router) seria pior.

**2. `src/api/auth.ts`** — funções puras de auth:

```typescript
import api from "./client";
import type { LoginResponse, RefreshResponse } from "@/types/contracts";

export async function postLogin(email: string, senha: string): Promise<LoginResponse> {
  const r = await api.post<LoginResponse>("/api/v1/auth/login", { email, senha });
  return r.data;
}

export async function postRefresh(refresh_token: string): Promise<RefreshResponse> {
  const r = await api.post<RefreshResponse>("/api/v1/auth/refresh", { refresh_token });
  return r.data;
}

export async function postLogout(refresh_token: string): Promise<void> {
  await api.post("/api/v1/auth/logout", { refresh_token });
}
```

**3. `src/auth/AuthContext.tsx`** — contexto + provider + hook:

```typescript
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { STORAGE } from "@/api/client";
import { postLogin, postLogout } from "@/api/auth";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  terceiroId: string | null;
  expiresAt: number | null;
}

interface AuthContextValue extends AuthState {
  isAuthenticated: boolean;
  login: (email: string, senha: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function readState(): AuthState {
  return {
    accessToken: sessionStorage.getItem(STORAGE.accessToken),
    refreshToken: sessionStorage.getItem(STORAGE.refreshToken),
    terceiroId: sessionStorage.getItem(STORAGE.terceiroId),
    expiresAt: Number(sessionStorage.getItem(STORAGE.expiresAt)) || null,
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(readState);

  useEffect(() => {
    const onLogout = () => setState({ accessToken: null, refreshToken: null, terceiroId: null, expiresAt: null });
    window.addEventListener("ts:auth-logout", onLogout);
    return () => window.removeEventListener("ts:auth-logout", onLogout);
  }, []);

  const login = useCallback(async (email: string, senha: string) => {
    const r = await postLogin(email, senha);
    const expAt = Date.now() + r.expires_in * 1000;
    sessionStorage.setItem(STORAGE.accessToken, r.access_token);
    sessionStorage.setItem(STORAGE.refreshToken, r.refresh_token);
    sessionStorage.setItem(STORAGE.terceiroId, r.terceiro_id);
    sessionStorage.setItem(STORAGE.expiresAt, String(expAt));
    setState({
      accessToken: r.access_token,
      refreshToken: r.refresh_token,
      terceiroId: r.terceiro_id,
      expiresAt: expAt,
    });
  }, []);

  const logout = useCallback(() => {
    const rtok = sessionStorage.getItem(STORAGE.refreshToken);
    if (rtok) {
      // best-effort; ignora falha
      postLogout(rtok).catch(() => {});
    }
    sessionStorage.removeItem(STORAGE.accessToken);
    sessionStorage.removeItem(STORAGE.refreshToken);
    sessionStorage.removeItem(STORAGE.terceiroId);
    sessionStorage.removeItem(STORAGE.expiresAt);
    setState({ accessToken: null, refreshToken: null, terceiroId: null, expiresAt: null });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ ...state, isAuthenticated: Boolean(state.accessToken), login, logout }),
    [state, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const v = useContext(AuthContext);
  if (!v) throw new Error("useAuth deve ser usado dentro de <AuthProvider>");
  return v;
}
```

**4. `src/types/contracts.ts`** — espelha schemas Pydantic do Backend (copiados literalmente):

```typescript
// Auth
export interface LoginRequest { email: string; senha: string; }
export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  terceiro_id: string;
  expires_in: number;
}
export interface RefreshRequest { refresh_token: string; }
export interface RefreshResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

// Terceiro
export interface CreateTerceiroRequest {
  nome: string;
  empresa_nome: string;
  empresa_cnpj: string;
  horario_inicio_jornada: string; // "HH:MM:SS"
  horario_saida_almoco: string;
  horario_retorno_almoco: string;
  horario_fim_jornada: string;
  trabalha_fim_de_semana: boolean;
  email_contato: string;
  email_destinatario_relatorio?: string | null;
  senha: string;
  senha_confirmacao: string;
}
export interface CreateTerceiroResponse { terceiro_id: string; criado_em: string; }
export interface TerceiroResponse {
  id: string;
  nome: string;
  empresa_nome: string;
  empresa_cnpj: string;
  horario_inicio_jornada: string;
  horario_saida_almoco: string;
  horario_retorno_almoco: string;
  horario_fim_jornada: string;
  trabalha_fim_de_semana: boolean;
  email_contato: string;
  email_destinatario_relatorio: string | null;
  criado_em: string;
  atualizado_em: string;
}
export interface UpdateTerceiroRequest {
  nome: string; empresa_nome: string; empresa_cnpj: string;
  horario_inicio_jornada: string; horario_saida_almoco: string;
  horario_retorno_almoco: string; horario_fim_jornada: string;
  trabalha_fim_de_semana: boolean;
  email_contato: string;
  email_destinatario_relatorio?: string | null;
}
export interface ChangePasswordRequest { senha_atual: string; nova_senha: string; }

// Privacidade
export interface PrivacyStatus {
  accepted: boolean;
  versao_aviso: string | null;
  aceito_em: string | null;
}

// Jornadas
export type StatusJornada = "EM_ANDAMENTO" | "FECHADA" | "AJUSTADA_MANUALMENTE" | "PENDENTE";
export type TipoMarcacao = "INICIO_JORNADA" | "SAIDA_ALMOCO" | "RETORNO_ALMOCO" | "FIM_JORNADA";
export type OrigemMarcacao = "AGENTE_AUTOMATICO" | "AGENTE_CONFIRMADO" | "AJUSTE_WEB";
export type StatusMarcacao = "CONFIRMADA" | "PENDENTE" | "AJUSTADA";

export interface JornadaResumo {
  id: string;
  data: string; // "YYYY-MM-DD"
  status: StatusJornada;
  total_horas_apuradas_s: number | null;
  tem_marcacao_pendente: boolean;
  horario_inicio: string | null; // ISO UTC ou null
  horario_saida_almoco: string | null;
  horario_retorno_almoco: string | null;
  horario_fim: string | null;
}
export interface JornadasMesResponse {
  mes_referencia: string; // "YYYY-MM"
  total_horas_mes_s: number;
  jornadas: JornadaResumo[];
}
export interface MarcacaoDetalhe {
  id: string;
  tipo: TipoMarcacao;
  horario_registrado: string; // ISO UTC
  horario_efetivo: string | null;
  origem: OrigemMarcacao;
  status: StatusMarcacao;
}
export interface AtividadeDetalhe {
  id: string;
  jornada_id: string;
  descricao: string;
  registrada_em: string;
  atualizado_em: string | null;
}
export interface JustificativaDetalhe {
  id: string;
  motivo: string;
  usuario_responsavel: string;
  criada_em: string;
}
export interface JornadaDetalheResponse {
  id: string;
  data: string;
  status: StatusJornada;
  total_horas_apuradas_s: number | null;
  marcacoes: MarcacaoDetalhe[];
  atividade: AtividadeDetalhe | null;
  justificativas: JustificativaDetalhe[];
}
export interface AjusteMarcacaoItem { tipo: TipoMarcacao; horario_efetivo: string; }
export interface AjusteJornadaRequest { marcacoes: AjusteMarcacaoItem[]; motivo: string; }
export interface JornadaManualRequest {
  data: string;
  marcacoes: AjusteMarcacaoItem[];
  atividade: string;
  motivo: string;
}
export interface AtividadeRequest { descricao: string; }

// Marcacoes
export interface PostMarcacaoRequest {
  tipo: TipoMarcacao;
  horario_registrado: string;
  horario_efetivo?: string | null;
  origem: "AGENTE_AUTOMATICO" | "AGENTE_CONFIRMADO";
  idempotency_key: string;
}
export interface AjusteMarcacaoRequest { horario_efetivo: string; motivo: string; }
export interface MarcacaoResponse {
  id: string;
  jornada_id: string;
  tipo: string;
  horario_registrado: string;
  horario_efetivo: string | null;
  origem: string;
  status: string;
  confirmado_pelo_usuario: boolean;
  idempotency_key: string;
  criada_em: string;
}

// Auditoria
export interface AuditoriaItem {
  id: string;
  entidade: "Jornada" | "Marcacao" | "Terceiro" | "Atividade";
  entidade_id: string;
  autor: string;
  antes_json: string | null;
  depois_json: string;
  motivo: string | null;
  criado_em: string;
}

// SMTP
export interface SmtpConfigRequest {
  host: string;
  port: number;
  username: string;
  password: string;
  use_starttls: boolean;
  from_address: string;
}
export interface SmtpConfigResponse {
  host: string;
  port: number;
  username: string;
  use_starttls: boolean;
  from_address: string;
  atualizado_em: string;
}

// Relatórios
export interface RelatorioMesResponse {
  mes_referencia: string;
  caminho_arquivo: string;
  gerado_em: string;
  invalidado_em: string | null;
}
export interface HistoricoEnvioItem {
  id: string;
  mes_referencia: string;
  email_destinatario: string;
  status: "SUCESSO" | "FALHA";
  erro_mensagem: string | null;
  enviado_em: string;
}
export interface EnviarRelatorioRequest { email?: string | null; }
export interface EnviarResponse { status: string; historico_id: string; }

// Formato de erro padronizado
export interface ApiErrorBody {
  code: string;
  message: string;
  details: Array<{ field?: string; issue?: string }>;
}
```

**5. `src/lib/saudacao.ts`**:

```typescript
export type Saudacao = "Bom dia" | "Boa tarde" | "Boa noite";

export function saudacaoPorHora(h: number): Saudacao {
  if (h < 12) return "Bom dia";
  if (h < 18) return "Boa tarde";
  return "Boa noite";
}

export function saudacaoAgora(now: Date = new Date()): Saudacao {
  return saudacaoPorHora(now.getHours());
}
```

**6. `src/lib/errors.ts`**:

```typescript
import { AxiosError } from "axios";
import type { ApiErrorBody } from "@/types/contracts";

export interface ParsedApiError {
  code: string;
  message: string;
  fields: Record<string, string>;
}

const FIELD_PREFIX = /^body\./;

export function parseApiError(err: unknown): ParsedApiError {
  if (err instanceof AxiosError) {
    const body = err.response?.data as ApiErrorBody | undefined;
    if (body && typeof body === "object" && "code" in body) {
      const fields: Record<string, string> = {};
      for (const d of body.details ?? []) {
        if (d.field) {
          const name = d.field.replace(FIELD_PREFIX, "");
          fields[name] = d.issue ?? "";
        }
      }
      return { code: body.code, message: body.message, fields };
    }
    if (!err.response) {
      return {
        code: "NETWORK_ERROR",
        message: "Falha de conexão. Verifique o serviço local.",
        fields: {},
      };
    }
  }
  return { code: "UNKNOWN_ERROR", message: "Ocorreu um erro inesperado.", fields: {} };
}
```

**7. `src/routes/ProtectedRoute.tsx`** + `src/routes/PrivacyGuard.tsx`:

```typescript
// ProtectedRoute.tsx
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/auth/AuthContext";

export function ProtectedRoute() {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}
```

```typescript
// PrivacyGuard.tsx
import { useQuery } from "@tanstack/react-query";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import api from "@/api/client";
import type { PrivacyStatus } from "@/types/contracts";
import { CircularProgress, Box } from "@mui/material";

export const privacyKeys = {
  status: ["privacidade", "status"] as const,
};

export function PrivacyGuard() {
  const location = useLocation();
  const { data, isLoading } = useQuery({
    queryKey: privacyKeys.status,
    queryFn: async (): Promise<PrivacyStatus> => {
      const r = await api.get<PrivacyStatus>("/api/v1/privacidade");
      return r.data;
    },
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    );
  }

  const isPrivacyRoute = location.pathname === "/privacidade";
  if (data?.accepted && isPrivacyRoute) {
    return <Navigate to="/jornadas" replace />;
  }
  if (!data?.accepted && !isPrivacyRoute) {
    return <Navigate to="/privacidade" replace />;
  }
  return <Outlet />;
}
```

**8. `src/routes/PageStubs.tsx`** — placeholder único para todas as 9 páginas:

```typescript
import { Typography, Box } from "@mui/material";

function makeStub(label: string, taskId: string) {
  return function Stub() {
    return (
      <Box p={4}>
        <Typography variant="h5" component="h1">{label}</Typography>
        <Typography color="text.secondary">Em construção — {taskId}</Typography>
      </Box>
    );
  };
}

export const LoginPageStub = makeStub("Login", "TASK-021");
export const PrivacidadePageStub = makeStub("Privacidade", "TASK-022");
export const JornadasPageStub = makeStub("Jornadas", "TASK-023");
export const JornadaDetalhePageStub = makeStub("Detalhe da Jornada", "TASK-024");
export const JornadaManualPageStub = makeStub("Nova Jornada Manual", "TASK-025");
export const CadastroPageStub = makeStub("Cadastro", "TASK-026");
export const SenhaPageStub = makeStub("Alterar Senha", "TASK-026");
export const RelatoriosPageStub = makeStub("Relatórios", "TASK-027");
export const SmtpConfigPageStub = makeStub("Configuração SMTP", "TASK-027");
```

**9. `src/routes.tsx`** — Router central:

```typescript
import { createBrowserRouter, Navigate } from "react-router-dom";
import { ProtectedRoute } from "@/routes/ProtectedRoute";
import { PrivacyGuard } from "@/routes/PrivacyGuard";
import { AppLayout } from "@/components/AppLayout";
import {
  LoginPageStub,
  PrivacidadePageStub,
  JornadasPageStub,
  JornadaDetalhePageStub,
  JornadaManualPageStub,
  CadastroPageStub,
  SenhaPageStub,
  RelatoriosPageStub,
  SmtpConfigPageStub,
} from "@/routes/PageStubs";

export const router = createBrowserRouter([
  { path: "/", element: <Navigate to="/jornadas" replace /> },
  { path: "/login", element: <LoginPageStub /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <PrivacyGuard />,
        children: [
          { path: "/privacidade", element: <PrivacidadePageStub /> },
          {
            element: <AppLayout />,
            children: [
              { path: "/jornadas", element: <JornadasPageStub /> },
              { path: "/jornadas/manual", element: <JornadaManualPageStub /> },
              { path: "/jornadas/:id", element: <JornadaDetalhePageStub /> },
              { path: "/cadastro", element: <CadastroPageStub /> },
              { path: "/cadastro/senha", element: <SenhaPageStub /> },
              { path: "/relatorios", element: <RelatoriosPageStub /> },
              { path: "/configuracoes/smtp", element: <SmtpConfigPageStub /> },
            ],
          },
        ],
      },
    ],
  },
  { path: "*", element: <Navigate to="/jornadas" replace /> },
]);
```

> **Substituições nas tasks 021..027**: cada task **importa o componente real** e **substitui no `routes.tsx`** o stub correspondente. `routes.tsx` é o **único arquivo central de roteamento** — toque por todas as features, **dep transitiva via TASK-020**, **sem task de wiring final** (cada feature só edita 1 linha do `routes.tsx`, conflito improvável; merge sequencial resolve sem perda).

> **Decisão**: NÃO criar task final de wiring para o `routes.tsx` porque (a) cada feature edita 1 linha (substitui import do stub pelo real); (b) deps são sequenciais por padrão; (c) o `routes.tsx` é menor e cabe na mesma sessão da feature. Trade-off: cada feature editaria 1 arquivo compartilhado — aceita-se porque cada uma edita linha distinta. Alternativa rejeitada (task final de wiring) duplicaria contexto.

**10. `src/components/AppLayout.tsx`** — layout autenticado:

```typescript
import { useState } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  AppBar, Toolbar, Typography, IconButton, Drawer, List, ListItemButton,
  ListItemText, Box, Button, Divider,
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import { useAuth } from "@/auth/AuthContext";
import { useQuery } from "@tanstack/react-query";
import api from "@/api/client";
import type { TerceiroResponse } from "@/types/contracts";
import { saudacaoAgora } from "@/lib/saudacao";

export const terceiroKeys = { me: ["terceiros", "me"] as const };

export function AppLayout({ children }: { children?: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const { logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const { data: terceiro } = useQuery({
    queryKey: terceiroKeys.me,
    queryFn: async (): Promise<TerceiroResponse> => {
      const r = await api.get<TerceiroResponse>("/api/v1/terceiros/me");
      return r.data;
    },
    enabled: isAuthenticated,
    staleTime: 5 * 60_000,
  });

  const saud = saudacaoAgora();
  const nome = terceiro?.nome ?? "";

  return (
    <Box display="flex" flexDirection="column" minHeight="100vh">
      <AppBar position="static">
        <Toolbar>
          <IconButton edge="start" color="inherit" aria-label="abrir menu" onClick={() => setOpen(true)}>
            <MenuIcon />
          </IconButton>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            TimeSheet Terceiros — {saud}{nome ? `, ${nome}` : ""}
          </Typography>
          <Button color="inherit" onClick={() => { logout(); navigate("/login"); }}>
            Sair
          </Button>
        </Toolbar>
      </AppBar>
      <Drawer open={open} onClose={() => setOpen(false)}>
        <Box sx={{ width: 280 }} role="navigation" aria-label="menu principal">
          <List>
            <ListItemButton selected={location.pathname.startsWith("/jornadas")} onClick={() => { navigate("/jornadas"); setOpen(false); }}>
              <ListItemText primary="Jornadas" />
            </ListItemButton>
            <ListItemButton selected={location.pathname === "/jornadas/manual"} onClick={() => { navigate("/jornadas/manual"); setOpen(false); }}>
              <ListItemText primary="Nova jornada manual" />
            </ListItemButton>
            <Divider />
            <ListItemButton selected={location.pathname.startsWith("/relatorios")} onClick={() => { navigate("/relatorios"); setOpen(false); }}>
              <ListItemText primary="Relatórios" />
            </ListItemButton>
            <ListItemButton selected={location.pathname.startsWith("/configuracoes/smtp")} onClick={() => { navigate("/configuracoes/smtp"); setOpen(false); }}>
              <ListItemText primary="Configurar SMTP" />
            </ListItemButton>
            <Divider />
            <ListItemButton selected={location.pathname.startsWith("/cadastro")} onClick={() => { navigate("/cadastro"); setOpen(false); }}>
              <ListItemText primary="Meu cadastro" />
            </ListItemButton>
          </List>
        </Box>
      </Drawer>
      <Box component="main" flexGrow={1} p={3}>
        {children ?? <Outlet />}
      </Box>
    </Box>
  );
}
```

**11. `src/test/render.tsx`** — fixture comum:

```typescript
import { type ReactElement, type ReactNode } from "react";
import { render, type RenderOptions } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider, createTheme } from "@mui/material";
import { AuthProvider } from "@/auth/AuthContext";

interface ProviderOpts {
  route?: string;
  authState?: { accessToken?: string; refreshToken?: string; terceiroId?: string; terceiroNome?: string };
}

export function renderWithProviders(ui: ReactElement, opts: ProviderOpts = {}, rOpts: Omit<RenderOptions, "wrapper"> = {}) {
  if (opts.authState) {
    if (opts.authState.accessToken) sessionStorage.setItem("ts:access_token", opts.authState.accessToken);
    if (opts.authState.refreshToken) sessionStorage.setItem("ts:refresh_token", opts.authState.refreshToken);
    if (opts.authState.terceiroId) sessionStorage.setItem("ts:terceiro_id", opts.authState.terceiroId);
    sessionStorage.setItem("ts:expires_at", String(Date.now() + 60_000));
  }
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const theme = createTheme({ palette: { mode: "light" } });
  const Wrapper = ({ children }: { children: ReactNode }) => (
    <ThemeProvider theme={theme}>
      <MemoryRouter initialEntries={[opts.route ?? "/"]}>
        <QueryClientProvider client={qc}>
          <AuthProvider>{children}</AuthProvider>
        </QueryClientProvider>
      </MemoryRouter>
    </ThemeProvider>
  );
  return render(ui, { wrapper: Wrapper, ...rOpts });
}
```

**12. `src/App.tsx`** — agora apenas providers globais + Router:

```typescript
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";
import { AuthProvider } from "@/auth/AuthContext";
import { router } from "@/routes";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, refetchOnWindowFocus: false, retry: 1 },
    mutations: { retry: 0 },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>
  );
}
```

**13. `src/App.test.tsx`** — substituir:

```typescript
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "./App";

describe("App", () => {
  it("renderiza a tela de Login (stub) na rota inicial /login", () => {
    window.history.pushState({}, "", "/login");
    render(<App />);
    expect(screen.getByRole("heading", { name: /Login/i })).toBeInTheDocument();
  });
});
```

> **Quirk createBrowserRouter em jsdom**: ok porque jsdom expõe `window.history.pushState`; o roteador lê `window.location` no mount. O teste antigo "TimeSheet Terceiros" sai daqui e migra para `AppLayout.test.tsx` (a barra agora exibe "TimeSheet Terceiros — Bom dia/Boa tarde/Boa noite, <nome>").

## Contratos com camadas adjacentes

```
Produz para (regras fechadas que TASK-021..027 NÃO podem violar):
  - api/client.ts: única instância Axios (importar como `import api from "@/api/client"`)
  - api/<dominio>.ts (auth, terceiros, jornadas, marcacoes, atividades, auditoria, relatorios, smtp, privacidade): funções HTTP puras retornando Promise<Tipo>; SEM hooks
  - hooks/use<Dominio>.ts: hooks TanStack Query/Mutation; cada hook reusa os types de contracts.ts e as funções de api/<dominio>.ts
  - Padrão de query keys: `<dominio>Keys.<operacao>` (factory pattern), ex: `jornadasKeys.lista(mes)`, `jornadasKeys.detalhe(id)`
  - useAuth(): única fonte de tokens; nenhuma página lê sessionStorage direto
  - Rotas: editar SEMPRE em `src/routes.tsx` substituindo o import do stub correspondente
  - Tipos: somente de `@/types/contracts` — NUNCA criar tipos paralelos para os schemas existentes
  - AppLayout: aplicado automaticamente via routes.tsx; páginas dentro dele NÃO renderizam AppBar próprio
  - renderWithProviders: única forma de montar componentes nos testes; NUNCA usar render() direto
  - parseApiError(err): única forma de extrair mensagens; NUNCA acessar err.response.data direto

Consome de:
  - TASK-003 (Phase 1): toolchain Vite + MUI + TanStack + RHF + Zod + Axios já em package.json
  - TASK-012..018 (Backend Phase 3): contratos copiados em types/contracts.ts e endpoints já implementados

Erros:
  - 401: tratado automaticamente (refresh + retry)
  - 401 após refresh falhar: ClearSession + evento ts:auth-logout → AuthProvider zera + navegar para /login
  - Demais erros: bubbled ao código de cada feature; parseApiError padroniza extração
```

## Contrato HTTP

```
POST /api/v1/auth/login   (consumido por AuthContext.login)
Request: {"email": "...", "senha": "..."}
Response 200: {"access_token":"...","refresh_token":"...","terceiro_id":"...","expires_in":900}
Response 401: {"code":"UNAUTHORIZED","message":"E-mail ou senha inválidos","details":[]}
Response 429: {"code":"RATE_LIMITED","message":"...","details":[]}

POST /api/v1/auth/refresh   (consumido pelo interceptor de cliente em 401)
Request: {"refresh_token":"..."}
Response 200: {"access_token":"...","refresh_token":"...","expires_in":900}
Response 401: refresh inválido/revogado → interceptor limpa sessão

POST /api/v1/auth/logout   (consumido por AuthContext.logout best-effort)
Request: {"refresh_token":"..."}
Response 204

GET /api/v1/terceiros/me   (consumido por AppLayout para exibir nome)
Response 200: TerceiroResponse

GET /api/v1/privacidade   (consumido por PrivacyGuard)
Response 200: {"accepted": false|true, "versao_aviso": "1.0"|null, "aceito_em": "<iso>"|null}

Formato de erro padronizado (todos 4xx/5xx):
{
  "code": "VALIDATION_ERROR" | "UNAUTHORIZED" | "FORBIDDEN" | "NOT_FOUND" | "CONFLICT" | "INTERNAL_ERROR" | "SMTP_NOT_CONFIGURED" | "SETUP_ALREADY_DONE" | "RATE_LIMITED" | "AJUSTE_WEB_WINS" | "FIM_DE_SEMANA_NAO_PERMITIDO" | "NO_DATA" | "SMTP_SEND_FAILED" | "SMTP_TEST_FAILED",
  "message": "texto em pt-BR",
  "details": [{"field": "body.<campo>", "issue": "<descrição>"}]
}
```

**Validação obrigatória pelo executor antes de marcar done:**

1. `cd apps/web && npm install` — `axios-mock-adapter` instalado.
2. `cd apps/web && npm test -- --run` — 100% verde; coverage >= 80 (gate Vitest).
3. `cd apps/web && npm run typecheck` — `tsc --noEmit` 0 erros.
4. `cd apps/web && npm run lint` — eslint 0 warnings.
5. `cd apps/web && npm run build` — `vite build` exit 0 (gera `dist/`).
6. `make smoke` (raiz) — Phase 1 smoke continua passando (web-build + api/health + agent-build).

> Executor DEVE rodar 1–6 e garantir saída 0 antes de retornar. Falha = task não concluída.

**Refatoração:** após green, considerar (a) extrair `useTerceiroMe()` para `hooks/useTerceiro.ts` se já houver consumo em TASK-026; (b) extrair `STORAGE_KEYS` para `auth/storage.ts` se 2+ módulos lerem direto. Por ora, manter inline.
