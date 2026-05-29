// apps/web/e2e/global-setup.ts — executa seed antes dos specs
// O webServer do playwright.config.ts já garante backend up antes deste módulo rodar.
import { chromium } from "@playwright/test";
import { TERCEIRO_E2E } from "./fixtures";

const BASE = process.env.E2E_API_BASE ?? "http://127.0.0.1:8765";

async function seedTerceiro(): Promise<void> {
  const res = await fetch(`${BASE}/api/v1/terceiros`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(TERCEIRO_E2E),
  });

  if (res.status === 201) {
    console.log("[global-setup] Terceiro criado.");
    return;
  }

  const body = await res.json().catch(() => ({})) as { code?: string };

  if (res.status === 403 && body.code === "SETUP_ALREADY_DONE") {
    console.log("[global-setup] Terceiro já existe — ok (idempotente).");
    return;
  }

  throw new Error(`[global-setup] seed falhou: ${res.status} ${JSON.stringify(body)}`);
}

async function globalSetup(): Promise<void> {
  // Verificar que o backend está respondendo (webServer já o garantiu, mas double-check)
  const healthRes = await fetch(`${BASE}/api/v1/health`);
  if (!healthRes.ok) {
    throw new Error(`[global-setup] backend não saudável: ${healthRes.status}`);
  }

  await seedTerceiro();

  // Fechar contexto de chromium caso tenha sido aberto — neste setup não abrimos browser
  // mas importar chromium garante que playwright está disponível
  void chromium;
}

export default globalSetup;
