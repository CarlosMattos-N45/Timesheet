---
checkpoint: null
complexity: M
created_at: "2026-05-27 14:11:00"
criteria:
    - done: false
      test: cd apps/web && npm test -- --run src/App.test.tsx
      text: App.tsx renderiza heading h1 com texto TimeSheet Terceiros via MUI Typography
    - done: false
      text: Heading usa MUI Typography component=h1 com classe MuiTypography
    - done: false
      test: cd apps/web && npm run build
      text: Build de producao gera dist sem erros
    - done: false
      test: cd apps/web && npm run lint
      text: ESLint passa sem warnings
    - done: false
      test: cd apps/web && npm run typecheck
      text: TypeScript strict passa sem erros
    - done: false
      test: grep -E '127.0.0.1:8765' apps/web/vite.config.ts
      text: Vite dev server escuta em 127.0.0.1:5173 com proxy /api para 127.0.0.1:8765 configurado em vite.config.ts
    - done: false
      text: Testes passando com cobertura >= 80%
deps:
    - TASK-001
id: TASK-003
linter: cd apps/web && npm run lint && npm run typecheck
n45_version: 0.2.0
persona: frontend
phase: Phase 1 — Scaffold Mínimo
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: done
tdd:
    green: false
    red: false
    refactor: false
tests: cd apps/web && npm test -- --run
title: Frontend React+Vite+TS+MUI scaffold em /apps/web com pagina inicial
updated_at: "2026-05-27 15:06:52"
---

## Contexto

Frontend Web SPA do TimeSheet Terceiros: React 18 + TypeScript + Vite + Material UI v5, servido localmente pelo Backend Python a partir de `/apps/api/app/static/` em produção (Phase 6 — empacotamento copia o build para lá). Em desenvolvimento, roda via `vite dev` em porta separada (default `5173`).

Phase 1 entrega o scaffold mínimo: `package.json` com toolchain (Vite, ESLint, Prettier, MUI, React Router, TanStack Query, React Hook Form, Zod, Axios), `tsconfig.json` em strict mode, `vite.config.ts` com proxy para `/api` apontando para `127.0.0.1:8765`, e uma página inicial mínima que renderiza "TimeSheet Terceiros" usando MUI Typography. Sem rotas, sem auth, sem chamadas de API — Phase 4 cria as features (Login, Privacidade, Jornadas, etc).

A decisão arquitetural firmada aqui é consumida por todas as tasks de Phase 4: layout em `src/pages/` (slices verticais por página/feature), `src/components/` (componentes MUI compostos reutilizáveis), `src/hooks/`, `src/api/` (axios client + queries TanStack), `src/lib/` (zod schemas + formatters), `src/types/`. Esta task **não** cria essas pastas vazias — cada uma nasce com a task que a usa.

Depende de TASK-001.

## Comportamento Esperado

Após `npm install` e `npm run dev`, Vite serve em `http://127.0.0.1:5173/` e exibe uma página com o título "TimeSheet Terceiros" via componente MUI Typography (variante `h4`). Sem erros no console. `npm run build` produz `dist/` válido. `npm run lint` passa. `npm run typecheck` (alias para `tsc --noEmit`) passa. `npm test` roda Vitest (zero testes de produção; placeholder smoke test).

**Exemplos (entrada / ação → saída / efeito esperado)** — valores reais:

| Entrada / Ação                                                     | Saída / Efeito esperado                                                                          |
| ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| `npm run dev` em `apps/web/` → abrir `http://127.0.0.1:5173/`      | Página renderiza heading "TimeSheet Terceiros" via MUI Typography (variante h4); console limpo  |
| Componente `<App />` montado em teste Vitest                       | `screen.getByRole("heading", { level: 1, name: /TimeSheet Terceiros/i })` resolve (1 elemento)   |
| `npm run build`                                                    | Gera `dist/index.html` e `dist/assets/`; exit code 0                                             |
| `npm run lint`                                                     | Exit code 0; sem warnings                                                                        |
| `npm run typecheck`                                                | Exit code 0; sem erros do `tsc --noEmit`                                                         |
| `npm test -- --run`                                                | Vitest reporta `1 passed`; exit code 0                                                           |
| Em dev, requisição do client para `/api/v1/health` (proxy Vite)    | Vite encaminha para `http://127.0.0.1:8765/api/v1/health` (resposta depende do backend rodando)  |
| `npm run format -- --check`                                        | Exit code 0; Prettier não detecta arquivos fora do padrão                                        |

## TDD

**Testes a escrever antes da implementação:**

`apps/web/src/App.test.tsx`:

```typescript
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "./App";

describe("App", () => {
  it("renderiza o título do produto como heading h1", () => {
    render(<App />);
    const heading = screen.getByRole("heading", {
      level: 1,
      name: /TimeSheet Terceiros/i,
    });
    expect(heading).toBeInTheDocument();
  });

  it("usa Typography do MUI no heading", () => {
    render(<App />);
    const heading = screen.getByRole("heading", {
      level: 1,
      name: /TimeSheet Terceiros/i,
    });
    // MUI Typography variant=h4 aplica classe que começa com "MuiTypography"
    expect(heading.className).toMatch(/MuiTypography/);
  });
});
```

**Refatoração:** após green, nenhuma — código mínimo sem duplicação.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo                                | Ação      | Descrição                                                                                                                                                                                                                                            |
| -------------------------------------- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `apps/web/package.json`                | Criar     | Conforme bloco "package.json" abaixo                                                                                                                                                                                                                 |
| `apps/web/tsconfig.json`               | Criar     | TS strict mode; `target: "ES2022"`, `module: "ESNext"`, `moduleResolution: "Bundler"`, `jsx: "react-jsx"`, `strict: true`, `noUncheckedIndexedAccess: true`, `noImplicitOverride: true`, paths `@/*` → `src/*`                                        |
| `apps/web/tsconfig.node.json`          | Criar     | Config para `vite.config.ts` (Node side)                                                                                                                                                                                                             |
| `apps/web/vite.config.ts`              | Criar     | Plugins: `@vitejs/plugin-react`. Server `port: 5173`, `host: "127.0.0.1"`. Proxy `/api` → `http://127.0.0.1:8765`. Resolve `@` → `src`. Test config Vitest (`environment: "jsdom"`, `setupFiles: ["./src/test/setup.ts"]`)                            |
| `apps/web/index.html`                  | Criar     | Boilerplate Vite com `<div id="root"></div>` e `<script type="module" src="/src/main.tsx">`. `<title>TimeSheet Terceiros</title>`, `lang="pt-BR"`                                                                                                     |
| `apps/web/src/main.tsx`                | Criar     | Monta `<App />` em `#root`. Envolve em `<React.StrictMode>` e em `ThemeProvider` MUI com tema default + `CssBaseline`                                                                                                                                  |
| `apps/web/src/App.tsx`                 | Criar     | Componente `App` que retorna `<Typography variant="h4" component="h1">TimeSheet Terceiros</Typography>` envolto em `<Container>` MUI. **`component="h1"`** explícito para que `getByRole("heading", { level: 1 })` resolva (variant=h4 dá só o estilo)|
| `apps/web/src/test/setup.ts`           | Criar     | `import "@testing-library/jest-dom/vitest"`                                                                                                                                                                                                          |
| `apps/web/src/App.test.tsx`            | Criar     | Conforme TDD acima                                                                                                                                                                                                                                   |
| `apps/web/.eslintrc.cjs`               | Criar     | Extends `eslint:recommended`, `plugin:@typescript-eslint/recommended`, `plugin:react-hooks/recommended`, `plugin:react/jsx-runtime`. Parser `@typescript-eslint/parser`. Rule `react/prop-types: off`                                                  |
| `apps/web/.prettierrc.json`            | Criar     | `{"semi": true, "singleQuote": false, "trailingComma": "all", "printWidth": 100, "arrowParens": "always"}`                                                                                                                                            |
| `apps/web/.eslintignore`               | Criar     | `dist/`, `node_modules/`, `coverage/`                                                                                                                                                                                                                |
| `apps/web/.prettierignore`             | Criar     | `dist/`, `node_modules/`, `coverage/`, `*.md`                                                                                                                                                                                                        |
| `apps/web/README.md`                   | Criar     | Como instalar (`npm install`), rodar (`npm run dev`), testar (`npm test`), build (`npm run build`)                                                                                                                                                   |
| `Makefile` (raiz)                      | Modificar | Adicionar targets `web-dev` (npm run dev em `apps/web`), `web-build`, `web-test`, `web-lint`. Atualizar `help`                                                                                                                                       |

### Detalhamento Técnico

1. **`package.json`** (chave):

   ```json
   {
     "name": "timesheet-web",
     "private": true,
     "version": "0.1.0",
     "type": "module",
     "scripts": {
       "dev": "vite",
       "build": "tsc --noEmit && vite build",
       "preview": "vite preview",
       "test": "vitest",
       "lint": "eslint . --ext .ts,.tsx",
       "typecheck": "tsc --noEmit",
       "format": "prettier --write .",
       "format:check": "prettier --check ."
     },
     "dependencies": {
       "react": "^18.3.1",
       "react-dom": "^18.3.1",
       "react-router-dom": "^6.27.0",
       "@mui/material": "^5.16.7",
       "@mui/icons-material": "^5.16.7",
       "@emotion/react": "^11.13.3",
       "@emotion/styled": "^11.13.0",
       "@tanstack/react-query": "^5.59.0",
       "react-hook-form": "^7.53.0",
       "zod": "^3.23.8",
       "@hookform/resolvers": "^3.9.0",
       "axios": "^1.7.7"
     },
     "devDependencies": {
       "@types/react": "^18.3.11",
       "@types/react-dom": "^18.3.0",
       "@vitejs/plugin-react": "^4.3.2",
       "typescript": "^5.6.2",
       "vite": "^5.4.8",
       "vitest": "^2.1.2",
       "jsdom": "^25.0.1",
       "@testing-library/react": "^16.0.1",
       "@testing-library/jest-dom": "^6.5.0",
       "@testing-library/user-event": "^14.5.2",
       "eslint": "^8.57.1",
       "@typescript-eslint/eslint-plugin": "^8.8.0",
       "@typescript-eslint/parser": "^8.8.0",
       "eslint-plugin-react": "^7.37.1",
       "eslint-plugin-react-hooks": "^4.6.2",
       "prettier": "^3.3.3"
     }
   }
   ```

2. **`vite.config.ts`** (chave):

   ```typescript
   import { defineConfig } from "vite";
   import react from "@vitejs/plugin-react";
   import path from "node:path";

   export default defineConfig({
     plugins: [react()],
     resolve: {
       alias: { "@": path.resolve(__dirname, "./src") },
     },
     server: {
       host: "127.0.0.1",
       port: 5173,
       proxy: {
         "/api": {
           target: "http://127.0.0.1:8765",
           changeOrigin: false,
         },
       },
     },
     test: {
       globals: true,
       environment: "jsdom",
       setupFiles: ["./src/test/setup.ts"],
       css: false,
     },
   });
   ```

3. **`src/main.tsx`** (chave):

   ```tsx
   import React from "react";
   import ReactDOM from "react-dom/client";
   import { ThemeProvider, createTheme, CssBaseline } from "@mui/material";
   import App from "./App";

   const theme = createTheme({
     palette: { mode: "light" },
     typography: { fontFamily: "Roboto, system-ui, sans-serif" },
   });

   ReactDOM.createRoot(document.getElementById("root")!).render(
     <React.StrictMode>
       <ThemeProvider theme={theme}>
         <CssBaseline />
         <App />
       </ThemeProvider>
     </React.StrictMode>,
   );
   ```

4. **`src/App.tsx`** (chave) — **NOTA importante:** `Typography variant="h4"` dá o **estilo** visual, mas usar `component="h1"` faz o elemento real ser `<h1>`. Isto importa para acessibilidade (uma página = um `<h1>`) e para o teste passar com `getByRole("heading", { level: 1 })`.

   ```tsx
   import { Container, Typography } from "@mui/material";

   export default function App() {
     return (
       <Container maxWidth="md" sx={{ mt: 4 }}>
         <Typography variant="h4" component="h1">
           TimeSheet Terceiros
         </Typography>
       </Container>
     );
   }
   ```

5. **Estrutura de pastas** estabelecida (mas não criada ainda nesta task — só `src/`, `src/test/`):
   - `src/pages/` — uma pasta por rota (criadas em Phase 4)
   - `src/components/` — composições MUI reutilizáveis
   - `src/hooks/` — hooks customizados
   - `src/api/` — axios client + queries
   - `src/lib/` — zod schemas, formatters
   - `src/types/` — types compartilhados

6. **Makefile (adições):**

   ```makefile
   .PHONY: web-dev web-build web-test web-lint

   WEB_DIR := apps/web

   web-dev:
   	cd $(WEB_DIR) && npm run dev

   web-build:
   	cd $(WEB_DIR) && npm run build

   web-test:
   	cd $(WEB_DIR) && npm test -- --run

   web-lint:
   	cd $(WEB_DIR) && npm run lint && npm run typecheck
   ```

**Refatoração:** Nenhuma — task de scaffold sem duplicação.
