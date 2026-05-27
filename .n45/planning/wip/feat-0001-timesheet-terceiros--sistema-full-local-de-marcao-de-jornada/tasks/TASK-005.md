---
checkpoint: null
complexity: M
created_at: "2026-05-27 14:13:34"
criteria:
    - done: false
      test: make api-smoke
      text: App sobe e healthcheck responde 200
    - done: false
      test: make web-smoke
      text: Web build de producao passa sem erros
    - done: false
      test: make agent-smoke
      text: Agent build e dotnet test passam
    - done: false
      test: make smoke
      text: make smoke executa os 3 verifiers em sequencia e imprime [SMOKE OK]
    - done: false
      test: grep -E 'status.*ok' scripts/api_smoke.ps1
      text: Script api_smoke.ps1 valida body JSON com status=ok e version=0.1.0
    - done: false
      test: grep -E 'maxAttempts' scripts/api_smoke.ps1
      text: Loop de espera no api_smoke.ps1 tem contador maximo (sem while true)
    - done: false
      test: make help
      text: make help lista smoke api-smoke web-smoke agent-smoke
deps:
    - TASK-002
    - TASK-003
    - TASK-004
id: TASK-005
n45_version: 0.2.0
persona: backend
phase: Phase 1 — Scaffold Mínimo
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: pending
tdd:
    green: false
    red: false
    refactor: false
tests: make smoke
title: 'Smoke verifier: Makefile com make smoke validando api/health + web build + agent build'
updated_at: "2026-05-27 14:13:34"
---
## Contexto

Última task da Phase 1 — Scaffold Mínimo. Garante que as 3 aplicações scaffoldadas pelas tasks anteriores (Backend Python, Web React, Agente .NET) se levantam e operam em harmonia: o Backend serve `/api/v1/health` retornando 200; o Web dev server inicia sem erros; a solução .NET do Agente compila e o smoke test xUnit passa.

Esta é a **task de wiring** da Phase 1: ela toca o `Makefile` da raiz (arquivo central — ver "Arquivos sempre sequenciais" no Standards), adicionando um único target `make smoke` que orquestra a validação ponta-a-ponta dos 3 stacks em ambiente local. Não toca código de aplicação; apenas amarra o que as outras tasks entregaram.

O critério de saída é o **smoke composto** da Spec §9 Quality Gates: ao rodar `make smoke`, todos os 3 ambientes operam. Esta é a entrega verificável do Scaffold conforme a regra dura do Standards: "App sobe e verificação de smoke passa".

Depende de TASK-002, TASK-003 e TASK-004.

## Comportamento Esperado

`make smoke` executa, em sequência, os 3 verifiers:

1. **API smoke** — sobe `uvicorn app.main:app` em background, espera até 10s pelo `/api/v1/health` retornar 200, valida que o body é `{"status":"ok","version":"0.1.0"}`, mata o processo.
2. **Web smoke** — roda `npm run build` em `apps/web` (já valida tipos via `tsc --noEmit` no script `build`).
3. **Agent smoke** — roda `dotnet build` e `dotnet test` em `apps/agent/Timesheet.Agent.sln`.

Qualquer um dos 3 falhando interrompe `make smoke` com exit ≠ 0. Sucesso dos 3 → exit 0 + mensagem `[SMOKE OK]`.

**Exemplos (entrada / ação → saída / efeito esperado)** — valores reais:

| Entrada / Ação                                              | Saída / Efeito esperado                                                                                                                                  |
| ----------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `make smoke` (todos os stacks íntegros)                     | Exit code 0; última linha contém `[SMOKE OK]`                                                                                                            |
| `make smoke` com `apps/web/package.json` corrompido         | Exit code ≠ 0; mensagem indica falha em `web-build`                                                                                                      |
| `make smoke` com bug no `Service/Program.cs` (não compila)  | Exit code ≠ 0; mensagem indica falha em `agent-build`                                                                                                    |
| `make smoke` com `/health` ausente                          | Exit code ≠ 0; mensagem indica timeout ou status ≠ 200                                                                                                   |
| `make help` (atualizado)                                    | Lista inclui `smoke`, `api-smoke`, `web-smoke`, `agent-smoke`, `api-dev`, `web-dev`, `agent-build`, etc.                                                  |
| `make api-smoke` isolado                                    | Exit code 0; valida apenas backend                                                                                                                       |
| `make agent-smoke` isolado                                  | Exit code 0; valida apenas agente                                                                                                                        |
| `make web-smoke` isolado                                    | Exit code 0; valida apenas web (build)                                                                                                                   |
| Verificar que `scripts/api_smoke.ps1` existe e tem `Invoke-RestMethod` para `/api/v1/health` | `Get-Content` mostra a linha `Invoke-RestMethod` apontando para `http://127.0.0.1:8765/api/v1/health`                                  |

## TDD

A task entrega **infraestrutura de validação** (Makefile + script PowerShell), não código aplicacional com TDD red-green. O critério verificável é `make smoke` retornar exit 0 quando os scaffolds de TASK-002/003/004 estão íntegros.

**Smoke test interno do PowerShell:** o script `scripts/api_smoke.ps1` deve falhar **com mensagem clara** se o backend não responder em 10s. Não há teste unitário para o script — sua verificação é o próprio `make api-smoke` ser determinístico.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo                            | Ação      | Descrição                                                                                                                                                                                                                                                                |
| ---------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `scripts/api_smoke.ps1`            | Criar     | PowerShell script Windows: sobe `uvicorn` em background, aguarda até 10s por `/api/v1/health` 200, valida JSON `{"status":"ok","version":"0.1.0"}`, mata o processo, exit 0/1. Ver bloco PowerShell abaixo                                                              |
| `Makefile` (raiz)                  | Modificar | Adicionar targets `smoke`, `api-smoke`, `web-smoke`, `agent-smoke`. Atualizar `help` para listar todos os comandos                                                                                                                                                       |
| `README.md` (raiz)                 | Modificar | Adicionar seção "Smoke test" explicando que `make smoke` valida o pipeline completo Phase 1                                                                                                                                                                              |

### Detalhamento Técnico

1. **`scripts/api_smoke.ps1`** — PowerShell 5.1+ (Windows nativo, sem deps adicionais):

   ```powershell
   #Requires -Version 5.1
   $ErrorActionPreference = "Stop"

   $apiDir = Join-Path $PSScriptRoot ".." "apps/api"
   $process = $null

   try {
       # Start uvicorn em background
       Push-Location $apiDir
       $process = Start-Process -FilePath "uvicorn" `
           -ArgumentList "app.main:app", "--host", "127.0.0.1", "--port", "8765" `
           -PassThru -WindowStyle Hidden
       Pop-Location

       # Poll /health até 10s (contador limitado, evitar loop infinito)
       $maxAttempts = 20  # 20 * 500ms = 10s
       $attempt = 0
       $ready = $false
       while ($attempt -lt $maxAttempts -and -not $ready) {
           Start-Sleep -Milliseconds 500
           try {
               $response = Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/v1/health" -TimeoutSec 2
               if ($response.status -eq "ok" -and $response.version -eq "0.1.0") {
                   $ready = $true
               }
           } catch {
               # ignora — backend ainda subindo
           }
           $attempt++
       }

       if (-not $ready) {
           Write-Error "[API SMOKE FAIL] /health nao respondeu 200 em 10s ou body invalido"
           exit 1
       }

       Write-Host "[API SMOKE OK] /health respondeu 200 com status=ok version=0.1.0"
       exit 0
   } finally {
       if ($process -and -not $process.HasExited) {
           Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
       }
   }
   ```

   **Decisões:**
   - **Loop com contador `$maxAttempts`** (não `while ($true)`) — conformidade com "Loop de espera com limite" do Standards.
   - **Try/finally** garante que o processo `uvicorn` é morto mesmo se assertion falhar.
   - **Validação de body** confere `status` E `version` literais; muda → falha.
   - **PowerShell**, não bash, porque o projeto é Windows-only (Spec §7 Constraints).

2. **Makefile (adições/modificações):**

   ```makefile
   .PHONY: smoke api-smoke web-smoke agent-smoke

   smoke: api-smoke web-smoke agent-smoke
   	@echo "[SMOKE OK] api + web + agent ok"

   api-smoke:
   	powershell -ExecutionPolicy Bypass -File scripts/api_smoke.ps1

   web-smoke:
   	cd apps/web && npm run build

   agent-smoke:
   	cd apps/agent && dotnet build Timesheet.Agent.sln -c Debug && dotnet test Timesheet.Agent.sln -c Debug --no-restore
   ```

   **Target `help` atualizado** deve listar todos os comandos da Phase 1: `help`, `smoke`, `api-smoke`, `web-smoke`, `agent-smoke`, `api-dev`, `api-test`, `api-lint`, `web-dev`, `web-build`, `web-test`, `web-lint`, `agent-build`, `agent-test`, `agent-format`.

3. **Verificação manual antes de finalizar:**
   - `make api-smoke` → exit 0
   - `make web-smoke` → exit 0
   - `make agent-smoke` → exit 0
   - `make smoke` → exit 0 + linha `[SMOKE OK]`

4. **Por que `make smoke` não levanta o web dev server?** `npm run build` (que internamente roda `tsc --noEmit && vite build`) já valida que o app compila e tipa. Levantar `vite dev` exigiria health check próprio + outra porta + outro processo background — complexidade desnecessária para Phase 1 quando o build já garante integridade. Phase 4 (frontend por feature) cobre interatividade real.

5. **Por que api-smoke não roda `pytest`?** `pytest` está no critério da TASK-002 e roda em `make api-test`. `make smoke` valida **integração de runtime** (servidor responde HTTP), não unit tests — esses já foram cobertos pela própria TASK-002.

**Refatoração:** Nenhuma — task adiciona verificação, não reorganiza código existente.
