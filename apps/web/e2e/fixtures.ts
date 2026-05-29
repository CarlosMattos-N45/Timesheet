// apps/web/e2e/fixtures.ts — fixtures e helpers reutilizáveis pelas tasks 2 e 3
import { test as base, type APIRequestContext } from "@playwright/test";

// Constantes do Terceiro semeado — espelho de terceiro.fixture.mjs (fonte canônica: .mjs)
// Mantido aqui para uso TypeScript nos specs sem exigir import dinâmico de .mjs
export const TERCEIRO_E2E = {
  nome: "Maria E2E",
  empresa_nome: "Contratante E2E LTDA",
  empresa_cnpj: "11222333000181",
  horario_inicio_jornada: "09:00:00",
  horario_saida_almoco: "12:00:00",
  horario_retorno_almoco: "13:00:00",
  horario_fim_jornada: "18:00:00",
  trabalha_fim_de_semana: false,
  email_contato: "terceiro.e2e@example.com",
  email_destinatario_relatorio: "destinatario.e2e@example.com",
  senha: "SenhaE2E!2026",
  senha_confirmacao: "SenhaE2E!2026",
} as const;

// Chaves de sessionStorage — devem coincidir exatamente com STORAGE em src/api/client.ts
export const STORAGE_KEYS = {
  accessToken: "ts:access_token",
  refreshToken: "ts:refresh_token",
  terceiroId: "ts:terceiro_id",
  expiresAt: "ts:expires_at",
} as const;

interface LoginResult {
  access_token: string;
  refresh_token: string;
  terceiro_id: string;
  expires_in: number;
}

/**
 * Login programático via API — retorna tokens sem passar pela UI.
 */
export async function loginViaApi(
  request: APIRequestContext,
  email: string,
  senha: string
): Promise<LoginResult> {
  const res = await request.post("/api/v1/auth/login", {
    data: { email, senha },
  });
  if (res.status() !== 200) {
    throw new Error(`loginViaApi falhou: ${res.status()} ${await res.text()}`);
  }
  return res.json() as Promise<LoginResult>;
}

/**
 * Aceita a política de privacidade via API usando o Bearer token fornecido.
 */
export async function aceitarPrivacidadeViaApi(
  request: APIRequestContext,
  accessToken: string
): Promise<void> {
  const res = await request.post("/api/v1/privacidade/aceitar", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  // 200 = aceite registrado; 409 ou similar pode significar já aceito — tratar ambos como ok
  if (res.status() !== 200 && res.status() !== 201 && res.status() !== 204) {
    const body = await res.text();
    throw new Error(`aceitarPrivacidade falhou: ${res.status()} ${body}`);
  }
}

// Tipos de fixtures customizadas
interface E2EFixtures {
  seededPage: import("@playwright/test").Page;
}

/**
 * test estendido com fixture `seededPage`:
 * - faz login via API com o Terceiro E2E
 * - injeta access_token no sessionStorage
 * - aceita privacidade via API
 * - navega para /jornadas
 *
 * Reutilizável nos specs das tasks 2 e 3.
 */
export const test = base.extend<E2EFixtures>({
  seededPage: async ({ page, request }, use) => {
    // Login programático
    const tokens = await loginViaApi(
      request,
      TERCEIRO_E2E.email_contato,
      TERCEIRO_E2E.senha
    );

    // Aceitar privacidade via API antes de navegar
    await aceitarPrivacidadeViaApi(request, tokens.access_token);

    // Injetar tokens no sessionStorage para que AuthContext reconheça o usuário
    // Navegar para a app primeiro (sessionStorage exige contexto de origem)
    await page.goto("/");
    await page.evaluate(
      ({ keys, tok }) => {
        const expAt = Date.now() + tok.expires_in * 1000;
        sessionStorage.setItem(keys.accessToken, tok.access_token);
        sessionStorage.setItem(keys.refreshToken, tok.refresh_token);
        sessionStorage.setItem(keys.terceiroId, tok.terceiro_id);
        sessionStorage.setItem(keys.expiresAt, String(expAt));
      },
      { keys: STORAGE_KEYS, tok: tokens }
    );

    // Navegar para a rota protegida após injetar tokens
    await page.goto("/jornadas");

    await use(page);
  },
});

export { expect } from "@playwright/test";
