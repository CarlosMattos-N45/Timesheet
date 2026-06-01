---
checkpoint: null
complexity: M
created_at: "2026-06-01 09:08:00"
criteria:
    - done: false
      test: actionlint .github/workflows/release.yml
      text: actionlint valida release.yml sem erros de schema
    - done: false
      test: grep -F windows-latest .github/workflows/release.yml
      text: Workflow dispara em tag v*.*.* e roda em windows-latest
    - done: false
      test: grep -F make build .github/workflows/release.yml
      text: Workflow builda backend agente e MSI via make build
    - done: false
      test: grep -F api/v1/ready .github/workflows/release.yml
      text: Smoke do MSI faz install silencioso checa health e ready e uninstall
    - done: false
      test: grep -F SIGN_CERT_PFX_BASE64 .github/workflows/release.yml
      text: Assinatura via signtool so ocorre quando o secret existe nunca com cert placeholder
    - done: false
      test: grep -F TimesheetTerceiros.msi .github/workflows/release.yml
      text: Publica o MSI como asset do GitHub Release
deps:
    - TASK-036
    - TASK-037
    - TASK-038
id: TASK-044
linter: actionlint .github/workflows/release.yml
n45_version: 0.2.0
persona: devops
phase: Phase 8 — CI/CD
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: pending
tests: actionlint .github/workflows/release.yml
title: 'Release no CI: workflow GitHub Actions em tag vX.Y.Z (windows-latest) com build do MSI, smoke install/health/ready/uninstall, assinatura condicional e publish do Release'
updated_at: "2026-06-01 09:08:00"
---
## Contexto

Terceira e última task da Phase 8 — CI/CD e do roadmap inteiro. A Spec define no Quadro de Stack: **"CI/CD · GitHub Actions · ... build do MSI assinado em tag `vX.Y.Z`"** (§1), e em §2 "Distribuição": **"MSI assinado por certificado de code signing válido. Sem auto-update na v1.0"** (§7 Constraints). O §9 Quality Gate exige **"Smoke test do MSI no CI: instalação silenciosa, sobe os 2 services, `GET /api/v1/health` retorna 200, `GET /api/v1/ready` retorna 200, desinstalação limpa"**.

O pipeline de build já existe e foi validado na Phase 6 (TASK-036/037/038), exposto via `Makefile` da raiz:
- `make build-backend` → `apps/api/scripts/build-backend.ps1`: `npm run build` (SPA) → copia `apps/web/dist` para `apps/api/app/static` → PyInstaller `timesheet-backend.spec` → `apps/api/dist/timesheet-backend.exe`.
- `make publish-agent` → `apps/agent/scripts/publish-agent.ps1`: `dotnet publish` self-contained single-file de `Timesheet.Agent.Service` e `Timesheet.Agent.Ui` (win-x64) → `apps/agent/dist/service/TimesheetAgent.exe` e `.../ui/TimesheetAgentUi.exe`.
- `make installer-validate` → `wix build apps/installer/Product.wxs apps/installer/Components.wxs -ext WixToolset.Util.wixext -ext WixToolset.UI.wixext -o dist/TimesheetTerceiros.msi`.
- `make build` = `build-backend` + `publish-agent` + `installer-validate`.
- `make release` = `make build` + assinatura via `signtool` quando `$env:SIGN_CERT` está presente (senão MSI não assinado, modo dev).

O MSI (TASK-038): instalação silenciosa `msiexec /i TimesheetTerceiros.msi /qn TIMESHEET_PORT=8765` cria 2 Windows Services (`TimesheetBackend`, `TimesheetAgent`); um `CustomAction WaitForServiceReady` faz polling em `/api/v1/ready` (RF-013). Uninstall: `msiexec /x TimesheetTerceiros.msi /qn` remove services e EXEs.

Esta task cria **somente** o workflow de release (`.github/workflows/release.yml`) — arquivo separado do `ci.yml` (TASK-042) e `e2e.yml` (TASK-043). Roda em `windows-latest` (WiX, PyInstaller, dotnet publish win-x64, signtool são todos Windows-only).

## Comportamento Esperado

O workflow dispara em `push` de tags que casam `v*.*.*` (ex.: `v1.0.0`). Job único `release` em `windows-latest` que: instala os 3 toolchains + WiX CLI, builda backend (PyInstaller) + agente (dotnet publish) + MSI (wix build), roda o **smoke do MSI** (install silencioso → 2 services RUNNING → `/health` 200 → `/ready` 200 → uninstall limpo), assina o MSI com `signtool` quando o secret de certificado existe, e publica o MSI como GitHub Release asset.

**Exemplos (entrada → efeito esperado):**

| Entrada / Ação | Saída / Efeito esperado |
| -------------- | ----------------------- |
| `git push` da tag `v1.0.0` | Workflow dispara; gera `dist/TimesheetTerceiros.msi`; smoke do MSI passa; MSI anexado ao GitHub Release `v1.0.0` |
| Build do MSI falha (ex.: `wix build` erro de schema) | Passo de build falha → job falha antes do smoke; nenhum release publicado |
| Smoke do MSI: `/api/v1/ready` não responde 200 em 60s após install | Step de smoke retorna exit ≠ 0 → job falha; release não publicado |
| Secret `SIGN_CERT_PFX_BASE64` ausente | `signtool` é pulado com aviso (MSI não assinado, modo dev/fork); build e smoke continuam — assinatura nunca usa cert placeholder |
| `actionlint .github/workflows/release.yml` | exit 0 — YAML válido |

## O que Implementar

Criar `.github/workflows/release.yml`. Persona devops — sem TDD. Verificação: `actionlint` valida o YAML; o smoke do MSI (instalação/desinstalação silenciosa + health/ready) é o gate de §9 já provado na Phase 6 via `make build` + smoke manual. O executor **deve** rodar `actionlint` antes de retornar.

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| ------- | ---- | --------- |
| `.github/workflows/release.yml` | Criar | Workflow disparado em tag `v*.*.*` em `windows-latest`: setup toolchains + WiX, `make build` (backend+agent+MSI), smoke do MSI (install/health/ready/uninstall), assinatura condicional via signtool, publish do MSI como Release asset |

### Detalhamento Técnico

1. **Triggers:** `on: { push: { tags: ["v*.*.*"] } }`. `permissions: { contents: write }` (necessário para criar o GitHub Release e anexar o asset). `concurrency: { group: "release-${{ github.ref }}", cancel-in-progress: false }` (releases não devem ser cancelados no meio).

2. **Job `release`** (`runs-on: windows-latest`):
   - `actions/checkout@v4`
   - `actions/setup-python@v5` (`python-version: "3.12"`) + `pip install -e ".[dev,build]"` em `apps/api` (grupo `build` traz PyInstaller `6.*`).
   - `actions/setup-node@v4` (`node-version: "20"`) + `npm ci` em `apps/web` (a SPA é buildada pelo `build-backend.ps1`).
   - `actions/setup-dotnet@v4` (`dotnet-version: "8.0.x"`).
   - **Instala WiX CLI:** `dotnet tool install --global wix` e instala as extensões usadas pelo `installer-validate`: `wix extension add -g WixToolset.Util.wixext` e `wix extension add -g WixToolset.UI.wixext`. (O `make installer-validate` chama `wix build ... -ext WixToolset.Util.wixext -ext WixToolset.UI.wixext`.)
   - **Build:** `make build` (= build-backend + publish-agent + installer-validate). Alternativa se `make` der problema com `&` no path: chamar os 3 scripts diretos (`powershell -ExecutionPolicy Bypass -File apps/api/scripts/build-backend.ps1`, `... apps/agent/scripts/publish-agent.ps1`, `wix build ...`). Preferir `make build` (já validado).
   - **Smoke do MSI (Spec §9)** — step `shell: pwsh`:
     1. `Start-Process msiexec -ArgumentList '/i','dist/TimesheetTerceiros.msi','/qn','TIMESHEET_PORT=8765','/l*v','dist/install.log' -Wait` (install silencioso; capturar log).
     2. Verificar 2 services: `sc.exe query TimesheetBackend` e `sc.exe query TimesheetAgent` → estado `RUNNING` (falhar se não). O `CustomAction WaitForServiceReady` do MSI já aguarda `/ready`; ainda assim revalidar no smoke.
     3. `curl.exe -fsS http://127.0.0.1:8765/api/v1/health` → 200 e `.../api/v1/ready` → 200, com loop contador/timeout (ex.: 60× 1s) caso o service demore.
     4. Uninstall: `Start-Process msiexec -ArgumentList '/x','dist/TimesheetTerceiros.msi','/qn' -Wait`; confirmar `sc.exe query TimesheetBackend` retorna "service does not exist" (exit code 1060).
     5. Qualquer etapa que falhe → `exit 1` no step (anexar `dist/install.log` como artefato em `if: failure()`).
   - **Assinatura condicional** — step `shell: pwsh` que só assina se o secret existir:
     - Secret `SIGN_CERT_PFX_BASE64` (PFX em base64) + `SIGN_CERT_PASSWORD`. Se `$env:SIGN_CERT_PFX_BASE64` presente: decodificar para `cert.pfx`, `signtool sign /f cert.pfx /p $env:SIGN_CERT_PASSWORD /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 dist/TimesheetTerceiros.msi`. Senão: `Write-Host '[release] SIGN_CERT ausente -- MSI nao assinado (dev).'` (mesma semântica do `make release`). **Nunca** usar cert placeholder.
     - Passar os secrets via `env:` no step: `SIGN_CERT_PFX_BASE64: ${{ secrets.SIGN_CERT_PFX_BASE64 }}`, `SIGN_CERT_PASSWORD: ${{ secrets.SIGN_CERT_PASSWORD }}`.
   - **Publish do Release:** `softprops/action-gh-release@v2` com `files: dist/TimesheetTerceiros.msi` (usa o `GITHUB_TOKEN` automático; o `name`/`tag_name` derivam de `github.ref`). Roda só em sucesso (default).

3. **Artefato de diagnóstico:** step `if: failure()` com `actions/upload-artifact@v4` anexando `dist/install.log` (e o MSI se gerado) para depurar falhas de smoke.

**Exemplo de implementação (trecho):**

```yaml
name: Release

on:
  push:
    tags: ["v*.*.*"]

permissions:
  contents: write

concurrency:
  group: "release-${{ github.ref }}"
  cancel-in-progress: false

jobs:
  release:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -e ".[dev,build]"
        working-directory: apps/api
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: npm ci
        working-directory: apps/web
      - uses: actions/setup-dotnet@v4
        with: { dotnet-version: "8.0.x" }
      - name: Install WiX
        run: |
          dotnet tool install --global wix
          wix extension add -g WixToolset.Util.wixext
          wix extension add -g WixToolset.UI.wixext
      - name: Build backend + agent + MSI
        run: make build
      - name: MSI smoke (install / health / ready / uninstall)
        shell: pwsh
        run: |
          Start-Process msiexec -ArgumentList '/i','dist/TimesheetTerceiros.msi','/qn','TIMESHEET_PORT=8765','/l*v','dist/install.log' -Wait
          # ... sc.exe query + curl /health + /ready (loop com timeout) + uninstall ...
      - name: Sign MSI (conditional)
        shell: pwsh
        env:
          SIGN_CERT_PFX_BASE64: ${{ secrets.SIGN_CERT_PFX_BASE64 }}
          SIGN_CERT_PASSWORD: ${{ secrets.SIGN_CERT_PASSWORD }}
        run: |
          if ($env:SIGN_CERT_PFX_BASE64) {
            [IO.File]::WriteAllBytes('cert.pfx', [Convert]::FromBase64String($env:SIGN_CERT_PFX_BASE64))
            signtool sign /f cert.pfx /p $env:SIGN_CERT_PASSWORD /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 dist/TimesheetTerceiros.msi
          } else {
            Write-Host '[release] SIGN_CERT ausente -- MSI nao assinado (dev).'
          }
      - name: Publish GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          files: dist/TimesheetTerceiros.msi
      - name: Upload diagnostics on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: msi-diagnostics
          path: dist/install.log
```

## Refatoração

Nenhuma — task cria um arquivo novo de workflow; os scripts de build (`build-backend.ps1`, `publish-agent.ps1`) e o `Makefile` já existem e não são alterados.
