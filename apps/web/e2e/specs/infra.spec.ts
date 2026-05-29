// e2e/specs/infra.spec.ts — controle de infra, NÃO é o smoke de UI (esse é a task 2)
// Valida que o webServer sobe o backend e o health endpoint responde corretamente.
import { test, expect } from "@playwright/test";

test("backend health responde 200 via webServer", async ({ request }) => {
  const res = await request.get("/api/v1/health");
  expect(res.status()).toBe(200);
  const body = await res.json() as { status: string; version: string };
  expect(body.status).toBe("ok");
  expect(typeof body.version).toBe("string");
});
