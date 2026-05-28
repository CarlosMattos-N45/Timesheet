---
checkpoint: null
complexity: M
created_at: "2026-05-28 12:53:29"
criteria:
    - done: false
      test: cd apps/web && npm test -- --run src/lib/cnpj.test.ts -t "isValidCnpj"
      text: isValidCnpj retorna true para 00000000000191 e 11444777000161, false para 00000000000000, 11111111111111 e 00000000000200
    - done: false
      test: cd apps/web && npm test -- --run src/lib/cnpj.test.ts -t "formatCnpj"
      text: formatCnpj 00000000000191 -> 00.000.000/0001-91
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Cadastro/CadastroPage.test.tsx -t "preenche"
      text: Mount /cadastro carrega GET /api/v1/terceiros/me e preenche os campos com nome, empresa_nome, CNPJ formatado e horarios HH:MM
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Cadastro/CadastroPage.test.tsx -t "CNPJ invalido"
      text: 'CNPJ invalido client-side (ex: 00.000.000/0000-99) exibe helper text exato CNPJ invalido (digito verificador incorreto). e desabilita Salvar'
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Cadastro/CadastroPage.test.tsx -t "PUT /terceiros/me sucesso"
      text: PUT /api/v1/terceiros/me 200 invalida terceirosKeys.me e exibe toast Cadastro atualizado com sucesso.
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Cadastro/CadastroPage.test.tsx -t "Alterar senha navega"
      text: Botao Alterar senha em /cadastro navega para /cadastro/senha
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Cadastro/SenhaPage.test.tsx -t "heading h1 Alterar Senha"
      text: Mount /cadastro/senha renderiza heading h1 Alterar Senha com Salvar desabilitado por padrao
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Cadastro/SenhaPage.test.tsx -t "nao coincidem"
      text: nova_senha diferente de confirmar_senha exibe helper text As senhas nao coincidem e desabilita Salvar
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Cadastro/SenhaPage.test.tsx -t "navega para /login"
      text: Sucesso 204 do PUT /me/senha emite toast Senha alterada com sucesso., chama logout (sessionStorage limpo) e navega para /login
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Cadastro/SenhaPage.test.tsx -t "Senha atual incorreta"
      text: 401 do PUT /me/senha exibe alert texto exato Senha atual incorreta. + limpa campo senha_atual + foco em senha_atual
    - done: false
      test: cd apps/web && npm test -- --run src/pages/Cadastro/SenhaPage.test.tsx -t "Cancelar navega para /cadastro"
      text: Cancelar em /cadastro/senha navega para /cadastro
    - done: false
      test: grep -E "<CadastroPage ?/>|<SenhaPage ?/>" apps/web/src/routes.tsx
      text: routes.tsx substitui CadastroPageStub por CadastroPage e SenhaPageStub por SenhaPage
    - done: false
      test: grep -E "from \"@/api/terceiros\"" apps/web/src/components/AppLayout.tsx
      text: AppLayout.tsx importa terceirosKeys de @/api/terceiros (consolidacao da key)
    - done: false
      text: ESLint passa sem warnings e tsc strict 0 erros
    - done: false
      text: Testes passando com cobertura >= 80%
    - done: false
      text: make smoke continua passando
deps:
    - TASK-020
id: TASK-026
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
tests: cd apps/web && npm test -- --run src/lib/cnpj.test.ts src/pages/Cadastro/CadastroPage.test.tsx src/pages/Cadastro/SenhaPage.test.tsx
title: 'Cadastro + Senha (RF-007.5): /cadastro com PUT /terceiros/me + validacao CNPJ modulo 11 client-side; /cadastro/senha com PUT /senha 204 e logout forcado (revogacao de refresh tokens server-side)'
updated_at: "2026-05-28 12:53:29"
---
## Contexto

Implementar `/cadastro` (RF-007.5 — edição do cadastro do Terceiro) e `/cadastro/senha` (alteração de senha com revogação de refresh tokens). Slice: 2 páginas + zod schemas + integração com `GET/PUT /api/v1/terceiros/me` e `PUT /api/v1/terceiros/me/senha` + substituição dos 2 stubs em `routes.tsx`.

**State atual:**
- TASK-020 entregou `api/client`, `useAuth`, `AppLayout`, `parseApiError`, `renderWithProviders`, `CadastroPageStub` e `SenhaPageStub` em `routes.tsx`. Também já existe `terceiroKeys.me = ["terceiros", "me"]` (em `src/components/AppLayout.tsx`) — esta task **importa e reutiliza**.
- Backend Phase 3 TASK-013:
  - `GET /api/v1/terceiros/me` → `TerceiroResponse`.
  - `PUT /api/v1/terceiros/me` (auth) → `TerceiroResponse` atualizada; valida CNPJ módulo 11 e horários cronológicos; gera `LogAuditoria(Terceiro)`.
  - `PUT /api/v1/terceiros/me/senha` (auth) → 204; valida `senha_atual`, troca, **revoga todos refresh tokens ativos**. `KEK` é imutável.
- TASK-024 entregou `auditoriaKeys` + `getAuditoria` (não consumido nesta task; apenas para referência futura).

**Decisão de UX (Spec §5 — `/cadastro` e `/cadastro/senha`):**

`/cadastro` (Editar Cadastro):
- `<h1>` "Meu Cadastro".
- Loading: skeleton dos campos enquanto `useQuery(terceiroKeys.me)` carrega.
- Form com todos os campos do `terceiro`:
  - `nome` (1..120), `empresa_nome` (1..150), `empresa_cnpj` (14 dígitos, máscara `00.000.000/0000-00`, validação cliente módulo 11).
  - 4 `TextField` type=time (ou TimePicker MUI): início, saída almoço, retorno almoço, fim — cronológicos.
  - Switch `trabalha_fim_de_semana`.
  - `email_contato` (EmailStr).
  - `email_destinatario_relatorio` (EmailStr opcional, vazio → `null` no PUT).
- Botão "Salvar" — desabilitado até `isDirty && isValid`.
- Botão "Alterar senha" → `navigate("/cadastro/senha")`.
- Sucesso 200 → invalida `terceiroKeys.me` (re-busca atualiza AppLayout) + toast "Cadastro atualizado com sucesso."
- 422 `VALIDATION_ERROR` com campo `body.empresa_cnpj` → helper text inline "CNPJ inválido (dígito verificador incorreto)." + alerta superior com mensagem.

`/cadastro/senha` (Alterar Senha):
- `<h1>` "Alterar Senha".
- Form com 3 campos:
  - `senha_atual` (type=password, mínimo 1 char — backend valida).
  - `nova_senha` (type=password, mínimo 8 chars, indicador de força visual simples: barra/cor — fraca <10, média 10-13, forte >=14).
  - `confirmar_senha` (type=password) — Zod refine `nova_senha === confirmar_senha`.
- Botão "Salvar" — desabilitado até válido.
- Link "Cancelar" → `navigate("/cadastro")`.
- Sucesso 204 → toast "Senha alterada com sucesso." + `useAuth().logout()` (porque o backend revoga refresh tokens; access atual fica órfão; melhor forçar relogin) → redirect `/login` com state informativo.
- 401 (senha atual incorreta) → alert "Senha atual incorreta." + limpa campo `senha_atual` + foco.
- 422 → alert com `parsed.message`.

> **Decisão alternativa rejeitada**: deixar o usuário logado após troca de senha. **Rejeitada porque** o backend revoga *todos* os refresh tokens na mesma transação (RF-007.5); o próximo refresh automático falhará e o usuário cairá no fluxo de logout via `ts:auth-logout`. Forçar logout aqui dá UX previsível.

**Validação de CNPJ módulo 11 client-side:** copiar algoritmo padrão (digit check) em `src/lib/cnpj.ts`. Backend re-valida via `stdnum.br.cnpj.is_valid` (não-trivial, mas exato — algoritmo módulo 11 com pesos `[5,4,3,2,9,8,7,6,5,4,3,2]` para DV1 e `[6,5,4,3,2,9,8,7,6,5,4,3,2]` para DV2).

**Dependência:** TASK-020. **Compartilha helpers** com TASK-023/024/025: `formatHoraBR` (não usado aqui — cadastro usa `HH:MM` puro, sem TZ), mas `horarioParaIsoUtc` não é necessário porque o contrato do Terceiro usa `time` (`"HH:MM:SS"`) sem data.

## Comportamento Esperado

### `/cadastro` (Editar)

| Entrada / Ação | Saída / Efeito esperado |
| -------------- | ----------------------- |
| Mount `/cadastro` autenticado | Skeleton enquanto `GET /api/v1/terceiros/me` carrega; após 200, form preenchido com `nome`, `empresa_nome`, `empresa_cnpj` formatado (`00.000.000/0000-00`), 4 horários (HH:MM), switch fim de semana, e-mails |
| Trocar `nome` para "Maria S." | Botão "Salvar" passa de desabilitado para habilitado (`isDirty=true`) |
| Trocar CNPJ para `00000000000200` (dígito errado) + blur | Helper text "CNPJ inválido (dígito verificador incorreto)." + `aria-invalid="true"`; botão "Salvar" desabilitado |
| Trocar horário fim para 11:00 (< início) + blur | Helper text inline no campo fim ou saída_almoco "Os horários devem ser em ordem cronológica."; "Salvar" desabilitado |
| "Salvar" com payload válido | Chama `PUT /api/v1/terceiros/me` com body **sem** `senha`; sucesso 200 → invalida `terceiroKeys.me` + toast "Cadastro atualizado com sucesso." + form preserva valores |
| 422 do PUT (CNPJ inválido server-side) | Alert vermelho + helper text inline no `empresa_cnpj` |
| Clicar "Alterar senha" | `navigate("/cadastro/senha")` |

### `/cadastro/senha` (Alterar Senha)

| Entrada / Ação | Saída / Efeito esperado |
| -------------- | ----------------------- |
| Mount `/cadastro/senha` | Form com 3 campos; botão "Salvar" desabilitado |
| Digitar `nova_senha` = "abc" (3 chars) | Indicador "Fraca" (vermelho); helper "Mínimo 8 caracteres"; Salvar desabilitado |
| Digitar `nova_senha` = "SenhaMedia123" + `confirmar_senha` = "Outra123!" | Helper "As senhas não coincidem"; Salvar desabilitado |
| `senha_atual` "VelhaSenha123" + `nova_senha` "NovaSenha123!" + `confirmar_senha` "NovaSenha123!" + Salvar | Chama `PUT /api/v1/terceiros/me/senha`; sucesso 204 → toast "Senha alterada com sucesso." + `logout()` + `navigate("/login")` com state `{passwordChanged: true}` |
| 401 (senha atual incorreta) | Alert "Senha atual incorreta." + limpa `senha_atual` + foco em `senha_atual` |
| Clicar "Cancelar" | `navigate("/cadastro")` |

## TDD

**Testes a escrever antes da implementação:**

`apps/web/src/pages/Cadastro/CadastroPage.test.tsx`:

```typescript
import { describe, it, expect, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MockAdapter from "axios-mock-adapter";
import api from "@/api/client";
import { renderWithProviders } from "@/test/render";
import { CadastroPage } from "@/pages/Cadastro/CadastroPage";

const mock = new MockAdapter(api);

const T_BASE = {
  id: "u1", nome: "Maria", empresa_nome: "ACME LTDA",
  empresa_cnpj: "00000000000191",
  horario_inicio_jornada: "09:00:00", horario_saida_almoco: "12:00:00",
  horario_retorno_almoco: "13:00:00", horario_fim_jornada: "18:00:00",
  trabalha_fim_de_semana: false,
  email_contato: "maria@acme.com",
  email_destinatario_relatorio: "rh@acme.com",
  criado_em: "2026-01-01T00:00:00Z", atualizado_em: "2026-05-27T00:00:00Z",
};

beforeEach(() => {
  mock.reset();
  sessionStorage.setItem("ts:access_token", "tok");
  sessionStorage.setItem("ts:refresh_token", "r");
  sessionStorage.setItem("ts:terceiro_id", "u1");
  sessionStorage.setItem("ts:expires_at", String(Date.now() + 60_000));
});

describe("CadastroPage", () => {
  it("carrega GET /terceiros/me e preenche o form", async () => {
    mock.onGet("/api/v1/terceiros/me").reply(200, T_BASE);
    renderWithProviders(<CadastroPage />, { route: "/cadastro" });
    const nome = await screen.findByLabelText(/Nome/i) as HTMLInputElement;
    expect(nome.value).toBe("Maria");
    expect((screen.getByLabelText(/CNPJ/i) as HTMLInputElement).value).toMatch(/00\.000\.000\/0001-91/);
  });

  it("Salvar fica desabilitado por padrão e habilita ao tornar o form dirty + valid", async () => {
    mock.onGet("/api/v1/terceiros/me").reply(200, T_BASE);
    renderWithProviders(<CadastroPage />, { route: "/cadastro" });
    const btn = await screen.findByRole("button", { name: /^Salvar$/ });
    expect(btn).toBeDisabled();
    const nome = screen.getByLabelText(/Nome/i) as HTMLInputElement;
    await userEvent.clear(nome);
    await userEvent.type(nome, "Maria Silva");
    await waitFor(() => expect(btn).toBeEnabled());
  });

  it("CNPJ inválido client-side exibe helper text e bloqueia Salvar", async () => {
    mock.onGet("/api/v1/terceiros/me").reply(200, T_BASE);
    renderWithProviders(<CadastroPage />, { route: "/cadastro" });
    const cnpj = await screen.findByLabelText(/CNPJ/i) as HTMLInputElement;
    await userEvent.clear(cnpj);
    await userEvent.type(cnpj, "00.000.000/0000-99"); // DV errado
    await userEvent.tab();
    expect(await screen.findByText(/CNPJ inválido \(dígito verificador incorreto\)\./i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Salvar$/ })).toBeDisabled();
  });

  it("PUT /terceiros/me sucesso invalida cache e mostra toast", async () => {
    mock.onGet("/api/v1/terceiros/me").reply(200, T_BASE);
    mock.onPut("/api/v1/terceiros/me").reply(200, { ...T_BASE, nome: "Maria Silva" });
    renderWithProviders(<CadastroPage />, { route: "/cadastro" });
    const nome = await screen.findByLabelText(/Nome/i) as HTMLInputElement;
    await userEvent.clear(nome);
    await userEvent.type(nome, "Maria Silva");
    await userEvent.click(screen.getByRole("button", { name: /^Salvar$/ }));
    expect(await screen.findByText(/Cadastro atualizado com sucesso\./i)).toBeInTheDocument();
  });

  it("422 do PUT com field body.empresa_cnpj exibe alert", async () => {
    mock.onGet("/api/v1/terceiros/me").reply(200, T_BASE);
    mock.onPut("/api/v1/terceiros/me").reply(422, {
      code: "VALIDATION_ERROR",
      message: "Erro de validação",
      details: [{ field: "body.empresa_cnpj", issue: "CNPJ inválido (dígito verificador incorreto)" }],
    });
    renderWithProviders(<CadastroPage />, { route: "/cadastro" });
    const nome = await screen.findByLabelText(/Nome/i) as HTMLInputElement;
    await userEvent.clear(nome); await userEvent.type(nome, "X");
    await userEvent.click(screen.getByRole("button", { name: /^Salvar$/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/Erro de validação/i);
  });

  it("Alterar senha navega para /cadastro/senha", async () => {
    mock.onGet("/api/v1/terceiros/me").reply(200, T_BASE);
    renderWithProviders(<CadastroPage />, { route: "/cadastro" });
    await userEvent.click(await screen.findByRole("button", { name: /Alterar senha/i }));
    expect(window.location.pathname).toBe("/cadastro/senha");
  });
});
```

`apps/web/src/pages/Cadastro/SenhaPage.test.tsx`:

```typescript
import { describe, it, expect, beforeEach } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import MockAdapter from "axios-mock-adapter";
import api from "@/api/client";
import { renderWithProviders } from "@/test/render";
import { SenhaPage } from "@/pages/Cadastro/SenhaPage";

const mock = new MockAdapter(api);

beforeEach(() => {
  mock.reset();
  sessionStorage.setItem("ts:access_token", "tok");
  sessionStorage.setItem("ts:refresh_token", "r");
  sessionStorage.setItem("ts:terceiro_id", "u1");
  sessionStorage.setItem("ts:expires_at", String(Date.now() + 60_000));
});

describe("SenhaPage", () => {
  it("renderiza heading h1 Alterar Senha e Salvar desabilitado por padrão", () => {
    renderWithProviders(<SenhaPage />, { route: "/cadastro/senha" });
    expect(screen.getByRole("heading", { level: 1, name: /Alterar Senha/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Salvar$/ })).toBeDisabled();
  });

  it("nova_senha != confirmar_senha exibe 'As senhas não coincidem' e Salvar desabilitado", async () => {
    renderWithProviders(<SenhaPage />, { route: "/cadastro/senha" });
    await userEvent.type(screen.getByLabelText(/Senha atual/i), "OldPass1");
    await userEvent.type(screen.getByLabelText(/Nova senha/i), "NovaSenha123");
    await userEvent.type(screen.getByLabelText(/Confirmar nova senha/i), "DifSenha123");
    await userEvent.tab();
    expect(await screen.findByText(/As senhas não coincidem/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Salvar$/ })).toBeDisabled();
  });

  it("sucesso 204 emite toast, chama logout e navega para /login", async () => {
    mock.onPut("/api/v1/terceiros/me/senha").reply(204, "");
    renderWithProviders(<SenhaPage />, { route: "/cadastro/senha" });
    await userEvent.type(screen.getByLabelText(/Senha atual/i), "OldPass1");
    await userEvent.type(screen.getByLabelText(/Nova senha/i), "NovaSenha123");
    await userEvent.type(screen.getByLabelText(/Confirmar nova senha/i), "NovaSenha123");
    await userEvent.click(screen.getByRole("button", { name: /^Salvar$/ }));
    expect(await screen.findByText(/Senha alterada com sucesso\./i)).toBeInTheDocument();
    await waitFor(() => expect(sessionStorage.getItem("ts:access_token")).toBeNull());
    await waitFor(() => expect(window.location.pathname).toBe("/login"));
  });

  it("401 'Senha atual incorreta' exibe alert + limpa senha_atual + foco em senha_atual", async () => {
    mock.onPut("/api/v1/terceiros/me/senha").reply(401, {
      code: "UNAUTHORIZED", message: "Senha atual incorreta", details: [],
    });
    renderWithProviders(<SenhaPage />, { route: "/cadastro/senha" });
    const atual = screen.getByLabelText(/Senha atual/i) as HTMLInputElement;
    await userEvent.type(atual, "ErradaPass1");
    await userEvent.type(screen.getByLabelText(/Nova senha/i), "NovaSenha123");
    await userEvent.type(screen.getByLabelText(/Confirmar nova senha/i), "NovaSenha123");
    await userEvent.click(screen.getByRole("button", { name: /^Salvar$/ }));
    expect(await screen.findByText(/Senha atual incorreta\./i)).toBeInTheDocument();
    expect(atual.value).toBe("");
    expect(document.activeElement).toBe(atual);
  });

  it("Cancelar navega para /cadastro", async () => {
    renderWithProviders(<SenhaPage />, { route: "/cadastro/senha" });
    await userEvent.click(screen.getByRole("button", { name: /Cancelar/i }));
    expect(window.location.pathname).toBe("/cadastro");
  });
});
```

> **Quirk axios-mock-adapter + 401 + interceptor de TASK-020**: o endpoint `/auth/login`, `/auth/refresh`, `/auth/logout` é tratado como `isAuthEndpoint` e o interceptor NÃO faz refresh em 401. **Mas `/terceiros/me/senha` NÃO é endpoint de auth** — então em 401 o interceptor TENTARÁ `/auth/refresh`. Para o teste de 401 funcionar, mockar também `mock.onPost("/api/v1/auth/refresh").reply(401, {...})` para que o refresh falhe e o erro propague.

> **Atualização do teste de 401:** acrescentar `mock.onPost("/api/v1/auth/refresh").reply(401, { code: "UNAUTHORIZED", message: "refresh inválido", details: [] });` antes do clique em Salvar.

**Refatoração:** após green, extrair `<PasswordStrengthMeter>` para `src/components/PasswordStrengthMeter.tsx` se reusar em outro lugar (improvável v1.0 — manter inline).

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| ------- | ---- | --------- |
| `apps/web/src/pages/Cadastro/CadastroPage.tsx` | Criar | Componente `/cadastro` |
| `apps/web/src/pages/Cadastro/CadastroPage.test.tsx` | Criar | TDD acima |
| `apps/web/src/pages/Cadastro/SenhaPage.tsx` | Criar | Componente `/cadastro/senha` |
| `apps/web/src/pages/Cadastro/SenhaPage.test.tsx` | Criar | TDD acima |
| `apps/web/src/api/terceiros.ts` | Criar | `getTerceiroMe`, `putTerceiroMe`, `putSenha` (funções HTTP) |
| `apps/web/src/lib/cnpj.ts` | Criar | `isValidCnpj(value: string): boolean` (módulo 11) + `formatCnpj(value: string): string` (máscara) |
| `apps/web/src/lib/cnpj.test.ts` | Criar | Testes do validador/formatador |
| `apps/web/src/lib/schemas/cadastro.ts` | Criar | Zod schemas `cadastroSchema` e `senhaSchema` |
| `apps/web/src/routes.tsx` | Modificar | Substituir `CadastroPageStub` e `SenhaPageStub` |

> 8 criados + 1 modificado = **9 arquivos-alvo**. **Excede o teto por 1** — justificativa: duas rotas estreitamente acopladas (mesmo domínio "cadastro", a senha é um sub-fluxo do cadastro com CTA explícita "Alterar senha" em `/cadastro`); separar em 2 tasks aumentaria o cap da fase de 8 para 9 (estouro pior). `cnpj.ts` + teste + zod compartilhados entre os 2 arquivos justifica coesão.

### Detalhamento Técnico

**1. `src/lib/cnpj.ts`:**

```typescript
const PESOS_DV1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
const PESOS_DV2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];

function calcDV(digits: number[], pesos: number[]): number {
  const soma = digits.reduce((acc, d, i) => acc + d * pesos[i]!, 0);
  const resto = soma % 11;
  return resto < 2 ? 0 : 11 - resto;
}

export function isValidCnpj(value: string): boolean {
  const digits = value.replace(/\D/g, "");
  if (digits.length !== 14) return false;
  if (/^(\d)\1{13}$/.test(digits)) return false; // todos iguais (00000000000000)
  const arr = digits.split("").map(Number);
  const dv1 = calcDV(arr.slice(0, 12), PESOS_DV1);
  if (dv1 !== arr[12]) return false;
  const dv2 = calcDV(arr.slice(0, 13), PESOS_DV2);
  return dv2 === arr[13];
}

export function formatCnpj(value: string): string {
  const d = value.replace(/\D/g, "").slice(0, 14);
  if (d.length <= 2) return d;
  if (d.length <= 5) return `${d.slice(0, 2)}.${d.slice(2)}`;
  if (d.length <= 8) return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5)}`;
  if (d.length <= 12) return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8)}`;
  return `${d.slice(0, 2)}.${d.slice(2, 5)}.${d.slice(5, 8)}/${d.slice(8, 12)}-${d.slice(12)}`;
}

export function unmaskCnpj(value: string): string {
  return value.replace(/\D/g, "");
}
```

**2. `src/lib/cnpj.test.ts`:**

```typescript
import { describe, it, expect } from "vitest";
import { isValidCnpj, formatCnpj, unmaskCnpj } from "@/lib/cnpj";

describe("cnpj", () => {
  describe("isValidCnpj", () => {
    it("'00000000000191' (CNPJ válido público — Banco do Brasil) → true", () => {
      expect(isValidCnpj("00000000000191")).toBe(true);
    });
    it("'11444777000161' (Petrobras) → true", () => {
      expect(isValidCnpj("11444777000161")).toBe(true);
    });
    it("'00000000000000' (todos zero) → false", () => {
      expect(isValidCnpj("00000000000000")).toBe(false);
    });
    it("'11111111111111' (todos iguais) → false", () => {
      expect(isValidCnpj("11111111111111")).toBe(false);
    });
    it("'00000000000200' (DV incorreto) → false", () => {
      expect(isValidCnpj("00000000000200")).toBe(false);
    });
    it("'00.000.000/0001-91' (com máscara) → true (strip)", () => {
      expect(isValidCnpj("00.000.000/0001-91")).toBe(true);
    });
    it("string vazia → false", () => {
      expect(isValidCnpj("")).toBe(false);
    });
  });
  describe("formatCnpj", () => {
    it("'00000000000191' → '00.000.000/0001-91'", () => {
      expect(formatCnpj("00000000000191")).toBe("00.000.000/0001-91");
    });
    it("'123' → '123'", () => expect(formatCnpj("123")).toBe("123"));
    it("'0000000000019100' (>14 dígitos) → trunca para 14 e formata", () => {
      expect(formatCnpj("0000000000019100")).toBe("00.000.000/0001-91");
    });
  });
  describe("unmaskCnpj", () => {
    it("'00.000.000/0001-91' → '00000000000191'", () => {
      expect(unmaskCnpj("00.000.000/0001-91")).toBe("00000000000191");
    });
  });
});
```

**3. `src/lib/schemas/cadastro.ts`:**

```typescript
import { z } from "zod";
import { isValidCnpj, unmaskCnpj } from "@/lib/cnpj";

const horarioRegex = /^([01]\d|2[0-3]):[0-5]\d$/;
const horarioField = z.string().regex(horarioRegex, "Horário inválido (use HH:MM)");

export const cadastroSchema = z
  .object({
    nome: z.string().min(1, "Nome obrigatório").max(120, "Máximo 120 caracteres"),
    empresa_nome: z.string().min(1, "Empresa obrigatória").max(150, "Máximo 150 caracteres"),
    empresa_cnpj: z.string().transform(unmaskCnpj).refine(isValidCnpj, "CNPJ inválido (dígito verificador incorreto)."),
    inicio: horarioField,
    saidaAlmoco: horarioField,
    retornoAlmoco: horarioField,
    fim: horarioField,
    trabalha_fim_de_semana: z.boolean(),
    email_contato: z.string().email("E-mail inválido").max(254),
    email_destinatario_relatorio: z.union([z.literal(""), z.string().email("E-mail inválido")]).optional(),
  })
  .refine(
    (v) => v.inicio < v.saidaAlmoco && v.saidaAlmoco < v.retornoAlmoco && v.retornoAlmoco < v.fim,
    { message: "Os horários devem ser em ordem cronológica.", path: ["saidaAlmoco"] }
  );

export type CadastroFormValues = z.infer<typeof cadastroSchema>;

export const senhaSchema = z
  .object({
    senha_atual: z.string().min(1, "Senha atual obrigatória"),
    nova_senha: z.string().min(8, "Mínimo 8 caracteres").max(128, "Máximo 128 caracteres"),
    confirmar_senha: z.string().min(1, "Confirmação obrigatória"),
  })
  .refine((v) => v.nova_senha === v.confirmar_senha, {
    message: "As senhas não coincidem",
    path: ["confirmar_senha"],
  });

export type SenhaFormValues = z.infer<typeof senhaSchema>;
```

**4. `src/api/terceiros.ts`:**

```typescript
import api from "./client";
import type { TerceiroResponse, UpdateTerceiroRequest, ChangePasswordRequest } from "@/types/contracts";

export const terceirosKeys = {
  me: ["terceiros", "me"] as const,
};

export async function getTerceiroMe(): Promise<TerceiroResponse> {
  const r = await api.get<TerceiroResponse>("/api/v1/terceiros/me");
  return r.data;
}

export async function putTerceiroMe(body: UpdateTerceiroRequest): Promise<TerceiroResponse> {
  const r = await api.put<TerceiroResponse>("/api/v1/terceiros/me", body);
  return r.data;
}

export async function putSenha(body: ChangePasswordRequest): Promise<void> {
  await api.put("/api/v1/terceiros/me/senha", body);
}
```

> **Refactor sutil em `src/components/AppLayout.tsx`**: a chave `terceiroKeys.me` foi definida em `AppLayout.tsx` por TASK-020. Esta task move a definição para `src/api/terceiros.ts` (canônico — keys com a API) e atualiza `AppLayout.tsx` para importar `terceirosKeys.me`. **Edição cirúrgica de 1 linha** — mesmo padrão das tasks anteriores.

**5. `src/pages/Cadastro/CadastroPage.tsx`** (resumo):

```typescript
import { useEffect, useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Container, Typography, Box, Button, Stack, TextField, Switch, FormControlLabel,
  Skeleton, Snackbar, Alert,
} from "@mui/material";
import { getTerceiroMe, putTerceiroMe, terceirosKeys } from "@/api/terceiros";
import { formatCnpj, unmaskCnpj } from "@/lib/cnpj";
import { parseApiError } from "@/lib/errors";
import { cadastroSchema, type CadastroFormValues } from "@/lib/schemas/cadastro";

function timeToHHmm(t: string): string {
  return t.slice(0, 5);
}

export function CadastroPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [snackbar, setSnackbar] = useState<{ msg: string; severity: "success" | "error" } | null>(null);

  const { data: terceiro, isLoading } = useQuery({
    queryKey: terceirosKeys.me, queryFn: getTerceiroMe,
  });

  const {
    control, register, handleSubmit, reset, watch,
    formState: { errors, isDirty, isValid, isSubmitting },
  } = useForm<CadastroFormValues>({
    mode: "onBlur",
    resolver: zodResolver(cadastroSchema),
    defaultValues: {
      nome: "", empresa_nome: "", empresa_cnpj: "",
      inicio: "", saidaAlmoco: "", retornoAlmoco: "", fim: "",
      trabalha_fim_de_semana: false,
      email_contato: "", email_destinatario_relatorio: "",
    },
  });

  useEffect(() => {
    if (terceiro) {
      reset({
        nome: terceiro.nome,
        empresa_nome: terceiro.empresa_nome,
        empresa_cnpj: formatCnpj(terceiro.empresa_cnpj),
        inicio: timeToHHmm(terceiro.horario_inicio_jornada),
        saidaAlmoco: timeToHHmm(terceiro.horario_saida_almoco),
        retornoAlmoco: timeToHHmm(terceiro.horario_retorno_almoco),
        fim: timeToHHmm(terceiro.horario_fim_jornada),
        trabalha_fim_de_semana: terceiro.trabalha_fim_de_semana,
        email_contato: terceiro.email_contato,
        email_destinatario_relatorio: terceiro.email_destinatario_relatorio ?? "",
      });
    }
  }, [terceiro, reset]);

  const mutation = useMutation({
    mutationFn: async (v: CadastroFormValues) =>
      putTerceiroMe({
        nome: v.nome,
        empresa_nome: v.empresa_nome,
        empresa_cnpj: unmaskCnpj(v.empresa_cnpj),
        horario_inicio_jornada: `${v.inicio}:00`,
        horario_saida_almoco: `${v.saidaAlmoco}:00`,
        horario_retorno_almoco: `${v.retornoAlmoco}:00`,
        horario_fim_jornada: `${v.fim}:00`,
        trabalha_fim_de_semana: v.trabalha_fim_de_semana,
        email_contato: v.email_contato,
        email_destinatario_relatorio: v.email_destinatario_relatorio || null,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: terceirosKeys.me });
      setSnackbar({ msg: "Cadastro atualizado com sucesso.", severity: "success" });
    },
    onError: (e) => {
      setSnackbar({ msg: parseApiError(e).message, severity: "error" });
    },
  });

  if (isLoading) return <Container sx={{ mt: 2 }}><Skeleton variant="rectangular" height={400} /></Container>;

  return (
    <Container maxWidth="md" sx={{ mt: 2 }}>
      <Typography variant="h4" component="h1" gutterBottom>Meu Cadastro</Typography>
      <Box component="form" onSubmit={handleSubmit((v) => mutation.mutate(v))}>
        <TextField label="Nome" fullWidth margin="normal"
          {...register("nome")} error={Boolean(errors.nome)} helperText={errors.nome?.message ?? " "} />
        <TextField label="Empresa" fullWidth margin="normal"
          {...register("empresa_nome")} error={Boolean(errors.empresa_nome)} helperText={errors.empresa_nome?.message ?? " "} />
        <Controller
          control={control}
          name="empresa_cnpj"
          render={({ field }) => (
            <TextField
              label="CNPJ"
              fullWidth margin="normal"
              value={field.value}
              onChange={(e) => field.onChange(formatCnpj(e.target.value))}
              onBlur={field.onBlur}
              inputProps={{ maxLength: 18, "aria-invalid": Boolean(errors.empresa_cnpj) }}
              error={Boolean(errors.empresa_cnpj)}
              helperText={errors.empresa_cnpj?.message ?? " "}
            />
          )}
        />
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
          {([
            ["inicio", "Início"],
            ["saidaAlmoco", "Saída Almoço"],
            ["retornoAlmoco", "Retorno Almoço"],
            ["fim", "Fim"],
          ] as const).map(([n, label]) => (
            <TextField
              key={n}
              label={label}
              type="time"
              {...register(n)}
              error={Boolean(errors[n])}
              helperText={errors[n]?.message ?? " "}
              InputLabelProps={{ shrink: true }}
              sx={{ flex: 1 }}
            />
          ))}
        </Stack>
        <Controller
          control={control}
          name="trabalha_fim_de_semana"
          render={({ field }) => (
            <FormControlLabel
              control={<Switch checked={field.value} onChange={(_e, c) => field.onChange(c)} />}
              label="Trabalha nos fins de semana"
              sx={{ mt: 1 }}
            />
          )}
        />
        <TextField label="E-mail de contato" type="email" fullWidth margin="normal"
          {...register("email_contato")} error={Boolean(errors.email_contato)} helperText={errors.email_contato?.message ?? " "} />
        <TextField label="E-mail destinatário do relatório" type="email" fullWidth margin="normal"
          {...register("email_destinatario_relatorio")} error={Boolean(errors.email_destinatario_relatorio)}
          helperText={errors.email_destinatario_relatorio?.message ?? "Opcional"} />

        <Stack direction="row" spacing={2} mt={3}>
          <Button onClick={() => navigate("/cadastro/senha")}>Alterar senha</Button>
          <Button
            type="submit" variant="contained"
            disabled={!isDirty || !isValid || isSubmitting || mutation.isPending}
          >
            {mutation.isPending ? "Salvando..." : "Salvar"}
          </Button>
        </Stack>
      </Box>
      <Snackbar open={Boolean(snackbar)} autoHideDuration={5000} onClose={() => setSnackbar(null)}>
        <Alert
          severity={snackbar?.severity ?? "info"}
          onClose={() => setSnackbar(null)}
          role={snackbar?.severity === "error" ? "alert" : "status"}
        >{snackbar?.msg}</Alert>
      </Snackbar>
    </Container>
  );
}
```

**6. `src/pages/Cadastro/SenhaPage.tsx`:**

```typescript
import { useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import {
  Container, Typography, Box, Stack, TextField, Button, Alert, Snackbar, LinearProgress,
} from "@mui/material";
import { putSenha } from "@/api/terceiros";
import { useAuth } from "@/auth/AuthContext";
import { parseApiError } from "@/lib/errors";
import { senhaSchema, type SenhaFormValues } from "@/lib/schemas/cadastro";

function calcForca(s: string): { label: string; value: number; color: "error" | "warning" | "success" } {
  if (s.length < 8) return { label: "Fraca", value: 25, color: "error" };
  if (s.length < 14) return { label: "Média", value: 60, color: "warning" };
  return { label: "Forte", value: 100, color: "success" };
}

export function SenhaPage() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [serverError, setServerError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const senhaAtualRef = useRef<HTMLInputElement | null>(null);

  const {
    register, handleSubmit, watch, resetField, setFocus,
    formState: { errors, isValid, isSubmitting },
  } = useForm<SenhaFormValues>({
    mode: "onChange",
    resolver: zodResolver(senhaSchema),
    defaultValues: { senha_atual: "", nova_senha: "", confirmar_senha: "" },
  });

  const nova = watch("nova_senha");
  const forca = calcForca(nova);

  const mutation = useMutation({
    mutationFn: async (v: SenhaFormValues) => putSenha({ senha_atual: v.senha_atual, nova_senha: v.nova_senha }),
    onSuccess: () => {
      setSuccess(true);
      setTimeout(() => {
        logout();
        navigate("/login", { replace: true, state: { passwordChanged: true } });
      }, 1500);
    },
    onError: (e) => {
      const p = parseApiError(e);
      if (p.code === "UNAUTHORIZED") {
        setServerError("Senha atual incorreta.");
        resetField("senha_atual");
        setTimeout(() => setFocus("senha_atual"), 0);
      } else {
        setServerError(p.message);
      }
    },
  });

  const { ref: refRegisterAtual, ...restRegisterAtual } = register("senha_atual");

  return (
    <Container maxWidth="sm" sx={{ mt: 2 }}>
      <Typography variant="h4" component="h1" gutterBottom>Alterar Senha</Typography>
      <Box component="form" onSubmit={handleSubmit((v) => { setServerError(null); mutation.mutate(v); })}>
        <TextField
          label="Senha atual" type="password" fullWidth margin="normal"
          {...restRegisterAtual}
          inputRef={(el) => { refRegisterAtual(el); senhaAtualRef.current = el; }}
          error={Boolean(errors.senha_atual)}
          helperText={errors.senha_atual?.message ?? " "}
        />
        <TextField
          label="Nova senha" type="password" fullWidth margin="normal"
          {...register("nova_senha")}
          error={Boolean(errors.nova_senha)}
          helperText={errors.nova_senha?.message ?? " "}
        />
        <Box mt={1} mb={1}>
          <LinearProgress variant="determinate" value={forca.value} color={forca.color} />
          <Typography variant="caption" color={forca.color}>{forca.label}</Typography>
        </Box>
        <TextField
          label="Confirmar nova senha" type="password" fullWidth margin="normal"
          {...register("confirmar_senha")}
          error={Boolean(errors.confirmar_senha)}
          helperText={errors.confirmar_senha?.message ?? " "}
        />
        {serverError && <Alert severity="error" role="alert" sx={{ mt: 2 }}>{serverError}</Alert>}
        <Stack direction="row" spacing={2} mt={3}>
          <Button onClick={() => navigate("/cadastro")}>Cancelar</Button>
          <Button
            type="submit" variant="contained"
            disabled={!isValid || isSubmitting || mutation.isPending || success}
          >
            {mutation.isPending ? "Salvando..." : "Salvar"}
          </Button>
        </Stack>
      </Box>
      <Snackbar open={success} autoHideDuration={3000} onClose={() => setSuccess(false)}>
        <Alert severity="success" role="status">Senha alterada com sucesso.</Alert>
      </Snackbar>
    </Container>
  );
}
```

**7. `src/routes.tsx` — diff:**

```typescript
import { CadastroPage } from "@/pages/Cadastro/CadastroPage";
import { SenhaPage } from "@/pages/Cadastro/SenhaPage";
// Substituir:
// { path: "/cadastro", element: <CadastroPageStub /> },
// { path: "/cadastro/senha", element: <SenhaPageStub /> },
// Por:
// { path: "/cadastro", element: <CadastroPage /> },
// { path: "/cadastro/senha", element: <SenhaPage /> },
```

**8. `src/components/AppLayout.tsx` — edição cirúrgica:**

```typescript
// Trocar:
// export const terceiroKeys = { me: ["terceiros", "me"] as const };
// const { data: terceiro } = useQuery({ queryKey: terceiroKeys.me, queryFn: async () => { ... } });

// Por:
import { terceirosKeys, getTerceiroMe } from "@/api/terceiros";
// (remover o export local de terceiroKeys)
const { data: terceiro } = useQuery({
  queryKey: terceirosKeys.me,
  queryFn: getTerceiroMe,
  enabled: isAuthenticated,
  staleTime: 5 * 60_000,
});
```

> JornadasPage (TASK-023) também importa `terceiroKeys` de `AppLayout`. Após esta consolidação, atualizar o import na JornadasPage para usar `terceirosKeys` de `@/api/terceiros`. **Edição cirúrgica de 1 linha de import** — risco de conflito de merge baixo porque cada task editou linhas distintas; este conflito de import é trivial de resolver.

## Contratos com camadas adjacentes

```
Produz para:
  - terceirosKeys.me (canônica): consumida por AppLayout, JornadasPage, e qualquer outra view que mostre dados do Terceiro.
  - isValidCnpj, formatCnpj, unmaskCnpj: helpers reutilizáveis (Phase 5 Agente Desktop pode portar para C#).
  - senhaSchema (Zod): padrão para futuras telas de senha.

Consome de:
  TASK-020: api/client, useAuth, parseApiError, renderWithProviders.
  Backend Phase 3 TASK-013: GET/PUT /terceiros/me, PUT /terceiros/me/senha.

Erros:
  - 422 VALIDATION_ERROR no PUT /me: passthrough message via snackbar.
  - 401 no PUT /me/senha: alert "Senha atual incorreta." + limpa campo + foco; o interceptor padrão NÃO tenta refresh em 401 desta rota (não é endpoint de auth, mas o teste mocka /auth/refresh também 401 para reproduzir).
  - 401 no PUT /me: tratado pelo interceptor (refresh + retry).
```

## Contrato HTTP

```
GET /api/v1/terceiros/me   (auth Bearer)
Response 200: TerceiroResponse (sem senha_hash)
{
  "id": "<uuid>",
  "nome": "Maria", "empresa_nome": "ACME LTDA", "empresa_cnpj": "00000000000191",
  "horario_inicio_jornada": "09:00:00", "horario_saida_almoco": "12:00:00",
  "horario_retorno_almoco": "13:00:00", "horario_fim_jornada": "18:00:00",
  "trabalha_fim_de_semana": false,
  "email_contato": "maria@acme.com",
  "email_destinatario_relatorio": "rh@acme.com" | null,
  "criado_em": "<ISO>", "atualizado_em": "<ISO>"
}
Response 401: {"code":"UNAUTHORIZED",...}

PUT /api/v1/terceiros/me   (auth Bearer)
Request body: UpdateTerceiroRequest
{
  "nome": "Maria Silva",
  "empresa_nome": "ACME LTDA",
  "empresa_cnpj": "00000000000191",                  // CNPJ módulo 11 server-side
  "horario_inicio_jornada": "09:00:00",              // HH:MM:SS, cronológicos
  "horario_saida_almoco": "12:00:00",
  "horario_retorno_almoco": "13:00:00",
  "horario_fim_jornada": "18:00:00",
  "trabalha_fim_de_semana": false,
  "email_contato": "maria@acme.com",
  "email_destinatario_relatorio": "rh@acme.com"      // string | null
}
Response 200: TerceiroResponse atualizada; +1 LogAuditoria(Terceiro)
Response 422: {"code":"VALIDATION_ERROR","message":"...","details":[{"field":"body.empresa_cnpj","issue":"CNPJ inválido (dígito verificador incorreto)"}]}

PUT /api/v1/terceiros/me/senha   (auth Bearer)
Request body:
{
  "senha_atual": "...",        // backend valida via verify_password
  "nova_senha": "..."          // min 8, max 128
}
Response 204: vazio + revoga TODOS RefreshToken ativos do Terceiro (mesma transação)
Response 401: {"code":"UNAUTHORIZED","message":"Senha atual incorreta","details":[]}
Response 422: VALIDATION_ERROR
```

**Validação obrigatória pelo executor antes de marcar done:**

1. `cd apps/web && npm test -- --run src/lib/cnpj.test.ts src/pages/Cadastro/CadastroPage.test.tsx src/pages/Cadastro/SenhaPage.test.tsx` — 17+ testes passam.
2. `cd apps/web && npm test -- --run` — toda a suite continua verde; coverage >= 80.
3. `cd apps/web && npm run typecheck` — 0 erros.
4. `cd apps/web && npm run lint` — 0 warnings.
5. `cd apps/web && npm run build` — `dist/` gerado sem erros.
6. `make smoke` (raiz) — Phase 1 smoke continua passando.

> Executor DEVE rodar 1–6 e garantir saída 0 antes de retornar.

**Refatoração:** após green, considerar extrair `<PasswordStrengthMeter value={s}/>` para `src/components/PasswordStrengthMeter.tsx` (provavelmente não reusará — manter inline).
