import { defineConfig, devices } from "@playwright/test";

const API_DIR = "../api"; // relativo a apps/web
const E2E_DB = "sqlite+aiosqlite:///./data/e2e.sqlite";

export default defineConfig({
  testDir: "./e2e/specs",
  globalSetup: "./e2e/global-setup.ts",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false, // banco compartilhado single-tenant → serial
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI
    ? [["github"], ["html", { open: "never" }]]
    : "list",
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      // backend: aplica migrations e sobe uvicorn no banco e2e isolado
      command:
        `cd ${API_DIR} && alembic upgrade head && ` +
        `uvicorn app.main:app --host 127.0.0.1 --port 8765`,
      env: {
        TIMESHEET_DEV: "true",
        TIMESHEET_DB_URL: E2E_DB,
        TIMESHEET_SCHEDULER_ENABLED: "true",
      },
      url: "http://127.0.0.1:8765/api/v1/ready",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      stdout: "pipe",
      stderr: "pipe",
    },
    {
      // Usa node diretamente para evitar problema de resolução de binário
      // shell com '&' no caminho do diretório (Windows)
      command: "node node_modules/vite/bin/vite.js",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
});
