// apps/web/e2e/seed.mjs — seed idempotente do Terceiro E2E
// Estratégia: POST /api/v1/terceiros; 201 = criado; 403 SETUP_ALREADY_DONE = já existe (ok)
// O Makefile apaga e2e.sqlite ANTES de iniciar, garantindo banco limpo a cada rodada completa.
import { TERCEIRO_E2E } from "./terceiro.fixture.mjs";

const BASE = process.env.E2E_API_BASE ?? "http://127.0.0.1:8765";

async function main() {
  const res = await fetch(`${BASE}/api/v1/terceiros`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(TERCEIRO_E2E),
  });

  if (res.status === 201) {
    console.log("[seed] Terceiro criado com sucesso.");
    return;
  }

  const body = await res.json().catch(() => ({}));

  if (res.status === 403 && body.code === "SETUP_ALREADY_DONE") {
    console.log("[seed] Terceiro já existe — ok (idempotente).");
    return;
  }

  console.error(`[seed] falha inesperada: ${res.status}`, body);
  process.exit(1);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
