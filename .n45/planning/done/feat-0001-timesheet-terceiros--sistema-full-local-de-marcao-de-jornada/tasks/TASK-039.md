---
checkpoint: null
complexity: G
created_at: "2026-05-29 12:34:28"
criteria:
    - done: true
      test: cd apps/web && npx playwright test --list
      text: npx playwright test --list sai 0 e reconhece playwright.config.ts
    - done: true
      text: webServer da config sobe backend (uvicorn 8765, TIMESHEET_DEV=true, TIMESHEET_DB_URL e2e) e frontend (vite 5173); baseURL = http://127.0.0.1:5173
    - done: true
      text: 'Seed e idempotente: 2a execucao com Terceiro existente trata 403 SETUP_ALREADY_DONE e sai 0 sem erro, mantendo 1 Terceiro'
    - done: true
      text: seed.mjs cria Terceiro com email_contato terceiro.e2e@example.com e CNPJ valido 11222333000181 retornando 201 na 1a execucao
    - done: true
      test: cd apps/web && npx playwright test infra
      text: infra.spec.ts asserta GET /api/v1/health = 200 com body status=ok e version string via webServer
    - done: true
      text: Makefile expoe web-e2e (zera apps/api/data/e2e.sqlite, sobe mailhog, roda playwright) e web-e2e-install (playwright install chromium)
    - done: true
      text: Suite passando (infra.spec verde com webServer real)
deps: []
id: TASK-039
linter: cd apps/web && npm run lint
n45_version: 0.2.0
persona: qa
phase: Phase 7 — E2E
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: done
tests: cd apps/web && npx playwright test --list
title: 'Setup E2E: Playwright install + config (webServer backend+web), seed idempotente do Terceiro, fixtures/global-setup, Makefile web-e2e'
updated_at: "2026-05-29 12:52:43"
---
## Contexto

Esta é a primeira de 3 tasks da Phase 7 — E2E. Ela monta toda a infraestrutura de teste end-to-end com Playwright para a Web SPA do Timesheet Terceiros, sem escrever ainda nenhum spec de fluxo (isso fica nas tasks 2 e 3). O objetivo é deixar `npx playwright test` capaz de subir backend + frontend reais e ter dados semeados, de forma idempotente e repetível.

Estado atual relevante (fatos extraídos do código já entregue nas fases anteriores):

- **Backend** (`apps/api`): FastAPI em `app.main:app`. Sobe em dev com `uvicorn app.main:app --host 127.0.0.1 --port 8765`. Flag `TIMESHEET_DEV=true` habilita OpenAPI e os endpoints dev. O banco é SQLite em `./data/timesheet.sqlite` por padrão, configurável via env var `TIMESHEET_DB_URL` (ex.: `sqlite+aiosqlite:///./data/e2e.sqlite`). A KEK fica em `./data/key.kek` (gerada automaticamente na 1ª execução se ausente). O scheduler APScheduler sobe no lifespan e é exigido por `GET /api/v1/ready` (que retorna 503 se o scheduler não estiver `STATE_RUNNING`). As migrations Alembic precisam ter sido aplicadas ao banco-alvo antes do backend servir requests de domínio.
- **Frontend** (`apps/web`): Vite + React. `npm run dev` sobe o dev server em `http://127.0.0.1:5173` e faz proxy de `/api` → `http://127.0.0.1:8765` (configurado em `vite.config.ts`, `server.proxy`). Logo, no E2E o Playwright navega para `http://127.0.0.1:5173` e as chamadas `/api/...` chegam ao backend transparentemente.
- **Sistema é single-tenant**: `POST /api/v1/terceiros` cria o único Terceiro e retorna `201`; após o primeiro, retorna `403 FORBIDDEN` com `code="SETUP_ALREADY_DONE"`. Não há tela web de cadastro do Terceiro (isso é feito pelo Agente Desktop .NET, fora do alcance do Playwright). Portanto o seed do E2E cria o Terceiro **via API**.
- **Mailhog** (SMTP fake) sobe via `make smtp-up` (docker-compose `docker-compose.dev.yml`): SMTP em `localhost:1025`, UI/API HTTP em `http://localhost:8025`. A task 3 (Jornadas Completas) usa Mailhog para validar o envio de relatório; este setup garante que o seed/infra documenta como subi-lo, mas o teardown de Mailhog é responsabilidade do `make`/CI, não do Playwright.

Esta task instala o Playwright como devDependency em `apps/web`, cria `playwright.config.ts` com `webServer` que sobe backend + frontend, cria um script de seed idempotente e os fixtures/helpers reutilizáveis pelas tasks 2 e 3. Não escreve nenhum spec de jornada.

## Comportamento Esperado

O comando de listagem do Playwright funciona após a instalação, e o seed é idempotente (rodar 2× deixa exatamente 1 Terceiro, sem erro de duplicidade).

**Exemplos (entrada → saída esperada)** — valores reais:

| Entrada / Ação | Saída / Efeito esperado |
| -------------- | ----------------------- |
| `cd apps/web && npx playwright test --list` | Sai com código `0` e imprime a árvore de specs (vazia ou só com o arquivo de exemplo removido); o comando reconhece `playwright.config.ts` |
| `node e2e/seed.mjs` rodado com backend up e banco e2e zerado | `POST /api/v1/terceiros` retorna `201`; processo sai `0`; existe 1 Terceiro com `email_contato="terceiro.e2e@example.com"` |
| `node e2e/seed.mjs` rodado 2ª vez (Terceiro já existe) | Script apaga o arquivo SQLite e2e antes de semear (ou trata `403 SETUP_ALREADY_DONE` como já-semeado) → sai `0`, **sem** lançar erro, mantendo exatamente 1 Terceiro |
| `playwright.config.ts` → `use.baseURL` | `"http://127.0.0.1:5173"` |
| `playwright.config.ts` → `webServer` | Lista com 2 entradas: backend (uvicorn em 8765 com `TIMESHEET_DEV=true` e `TIMESHEET_DB_URL` apontando para o banco e2e) e frontend (vite em 5173); `reuseExistingServer: !process.env.CI` |
| Login programático via `request.post('/api/v1/auth/login', {email, senha})` no fixture `apiContext` | Retorna `200` com `access_token` no corpo |

## Estratégia de Teste

> Persona devops/QA de infra: esta task **não** escreve asserts de jornada. O "teste" desta task é a própria infra funcionar — verificada pelos critérios mecânicos (`--list` sai 0, seed idempotente). Não há controle negativo brownfield aqui porque não há spec de comportamento ainda; as tasks 2 e 3 trazem os asserts reais.

O único arquivo de spec criado aqui é um **smoke de infra mínimo** opcional que apenas valida que `webServer` sobe e o backend responde — mas para evitar duplicar a task 2 (Smoke Test), **não** crie spec de fluxo de UI. Em vez disso, valide a infra com:

1. `npx playwright test --list` (config válida).
2. Um spec único `e2e/specs/infra.spec.ts` com 1 teste que faz `request.get('/api/v1/health')` e asserta status `200` e corpo `{ status: "ok", version: <string> }` — isto exercita o `webServer` (sobe backend) e o `request` fixture do Playwright. Sem UI, sem navegação. Este é o controle de que a infra está de pé.

```ts
// e2e/specs/infra.spec.ts — controle de infra, NÃO é o smoke de UI (esse é a task 2)
import { test, expect } from "@playwright/test";

test("backend health responde 200 via webServer", async ({ request }) => {
  const res = await request.get("/api/v1/health");
  expect(res.status()).toBe(200);
  const body = await res.json();
  expect(body.status).toBe("ok");
  expect(typeof body.version).toBe("string");
});
```

## O que Implementar

Toda a estrutura de E2E vive em `apps/web/e2e/`. Playwright é devDependency de `apps/web`.

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| ------- | ---- | --------- |
| `apps/web/package.json` | Modificar | Adicionar devDep `@playwright/test` (`^1.48.0`) e scripts `"e2e": "playwright test"`, `"e2e:ui": "playwright test --ui"`, `"e2e:install": "playwright install --with-deps chromium"` |
| `apps/web/playwright.config.ts` | Criar | Config com `testDir: "./e2e/specs"`, `baseURL`, `webServer` (backend + frontend), projeto chromium, `reporter`, timeouts |
| `apps/web/e2e/seed.mjs` | Criar | Script Node idempotente: zera o banco e2e e cria o Terceiro via `POST /api/v1/terceiros` |
| `apps/web/e2e/fixtures.ts` | Criar | Fixtures Playwright reutilizáveis: `seededPage` (página já logada + privacidade aceita), helpers `loginViaApi`, `aceitarPrivacidadeViaApi`, constantes do Terceiro semeado |
| `apps/web/e2e/specs/infra.spec.ts` | Criar | 1 spec de controle de infra (health 200) — descrito em "Estratégia de Teste" |
| `apps/web/.gitignore` | Modificar (ou criar se ausente) | Ignorar `test-results/`, `playwright-report/`, `e2e/.auth/`, `blob-report/`, `playwright/.cache/` |
| `Makefile` | Modificar | Adicionar targets `web-e2e` (sobe Mailhog, instala browsers, roda playwright) e `web-e2e-install` |

### Detalhamento Técnico

1. **Constantes do Terceiro semeado** (em `e2e/fixtures.ts`, exportadas e reusadas pelo seed e pelos specs). Use um CNPJ com dígitos verificadores **válidos** (módulo 11) — o backend valida server-side e rejeita CNPJ inválido. CNPJ válido conhecido: `11222333000181`. Horários cronológicos (`HH:MM:SS`):

   ```ts
   export const TERCEIRO_E2E = {
     nome: "Maria E2E",
     empresa_nome: "Contratante E2E LTDA",
     empresa_cnpj: "11222333000181", // dígitos verificadores válidos (módulo 11)
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
   ```

2. **`playwright.config.ts`** — `webServer` aceita um array de servidores. O banco e2e e a KEK ficam em `apps/api/data/` (caminhos relativos ao `cwd` do uvicorn). Use env vars para isolar do banco de dev. O backend precisa das migrations Alembic aplicadas: o comando do backend deve rodar `alembic upgrade head` antes de subir o uvicorn (encadeie com `&&`). Garanta `TIMESHEET_SCHEDULER_ENABLED=true` para `/ready` passar.

   ```ts
   import { defineConfig, devices } from "@playwright/test";

   const API_DIR = "../api"; // relativo a apps/web
   const E2E_DB = "sqlite+aiosqlite:///./data/e2e.sqlite";

   export default defineConfig({
     testDir: "./e2e/specs",
     timeout: 60_000,
     expect: { timeout: 10_000 },
     fullyParallel: false, // banco compartilhado single-tenant → serial
     workers: 1,
     forbidOnly: !!process.env.CI,
     retries: process.env.CI ? 1 : 0,
     reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
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
         command: "npm run dev",
         url: "http://127.0.0.1:5173",
         reuseExistingServer: !process.env.CI,
         timeout: 60_000,
       },
     ],
   });
   ```

   > A migration roda contra o banco e2e a cada start. Como o seed (passo 3) zera o arquivo antes de semear, a sequência operacional é: zerar banco → `alembic upgrade head` (via webServer) → seed → specs. Documente no README/Makefile que `node e2e/seed.mjs` deve rodar **depois** que o backend estiver up (a global setup do Playwright pode chamá-lo; ver passo 4).

3. **`e2e/seed.mjs`** — idempotente. Estratégia: o seed apaga o arquivo SQLite e2e antes de semear **não é viável em runtime** porque o backend já tem o arquivo aberto. Em vez disso, torne o seed tolerante: tentar `POST /api/v1/terceiros`; se vier `201`, ok; se vier `403` com `code="SETUP_ALREADY_DONE"`, considere já-semeado e saia `0`. Para garantir banco limpo entre execuções completas, o **Makefile/CI** apaga `apps/api/data/e2e.sqlite` antes de iniciar (passo 6). Use `fetch` nativo do Node 18+.

   ```js
   // apps/web/e2e/seed.mjs
   import { TERCEIRO_E2E } from "./fixtures.ts"; // se .ts não importável em .mjs, duplicar a constante aqui
   const BASE = process.env.E2E_API_BASE ?? "http://127.0.0.1:8765";

   async function main() {
     const res = await fetch(`${BASE}/api/v1/terceiros`, {
       method: "POST",
       headers: { "Content-Type": "application/json" },
       body: JSON.stringify(TERCEIRO_E2E),
     });
     if (res.status === 201) {
       console.log("[seed] Terceiro criado");
       return;
     }
     const body = await res.json().catch(() => ({}));
     if (res.status === 403 && body.code === "SETUP_ALREADY_DONE") {
       console.log("[seed] Terceiro já existe — ok (idempotente)");
       return;
     }
     console.error(`[seed] falha inesperada: ${res.status}`, body);
     process.exit(1);
   }
   main().catch((e) => { console.error(e); process.exit(1); });
   ```

   > **Nota sobre import .ts em .mjs:** Node não importa `.ts` diretamente. Defina `TERCEIRO_E2E` como JSON/objeto em `e2e/seed.mjs` e re-exporte de `fixtures.ts` importando o `.mjs`, OU duplique a constante (preferir uma única fonte: crie `e2e/terceiro.fixture.mjs` exportando o objeto e importe nos dois). Decida por uma fonte única e documente — não deixe duas cópias divergentes.

4. **Global setup do seed:** registre `globalSetup` no `playwright.config.ts` apontando para `e2e/global-setup.ts`, que (a) espera o backend responder `/api/v1/ready` 200 (o `webServer.url` já garante isso) e (b) executa o seed chamando a mesma lógica do `seed.mjs`. Alternativa aceitável: chamar o seed dentro de uma fixture `worker`-scoped com `automatic` que roda uma vez. Escolha `globalSetup` por ser explícito.

5. **`e2e/fixtures.ts`** — estende `test` do Playwright com:
   - `loginViaApi(request, email, senha)`: `POST /api/v1/auth/login` → retorna tokens.
   - Fixture `seededPage`: injeta o `access_token` no `sessionStorage` (o `AuthContext` lê tokens de `sessionStorage` — confirmado no código do frontend), navega para `/jornadas`, e garante privacidade aceita (chama `POST /api/v1/privacidade/aceitar` via `request` com Bearer). Isso evita repetir login+privacidade em cada spec.
   - Helper `aceitarPrivacidadeViaApi(request, accessToken)`.

   > **Chave do sessionStorage:** confirme o nome exato lendo `apps/web/src/auth/AuthContext.tsx` (a fase 4 persistiu tokens em `sessionStorage`). Use exatamente as chaves que o `AuthContext` lê — não invente nomes. Se o login programático por sessionStorage for frágil, faça o login pela UI no fixture (preencher e-mail/senha e clicar "Entrar") — é mais robusto e ainda reutilizável.

6. **`Makefile`** — alvos:

   ```makefile
   web-e2e-install:
   	cd $(WEB_DIR) && npm ci && npx playwright install --with-deps chromium

   web-e2e:
   	@powershell -NoProfile -Command "if (Test-Path apps/api/data/e2e.sqlite) { Remove-Item apps/api/data/e2e.sqlite -Force }"
   	docker compose -f docker-compose.dev.yml up -d mailhog
   	cd $(WEB_DIR) && npm run e2e
   ```

   > Adicione `web-e2e web-e2e-install` à linha `.PHONY`.

7. **`apps/web/.gitignore`** — adicionar (criar o arquivo se não existir):

   ```
   test-results/
   playwright-report/
   blob-report/
   playwright/.cache/
   e2e/.auth/
   ```

**Refatoração:** Nenhuma — código novo, isolado em `apps/web/e2e/`.
