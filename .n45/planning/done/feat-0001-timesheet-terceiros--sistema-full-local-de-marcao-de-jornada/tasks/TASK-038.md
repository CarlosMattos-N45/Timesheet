---
checkpoint: null
complexity: G
created_at: "2026-05-29 11:47:00"
criteria:
    - done: true
      test: wix build apps/installer/Product.wxs apps/installer/Components.wxs -ext WixToolset.Util.wixext -ext WixToolset.UI.wixext -o dist/TimesheetTerceiros.msi
      text: wix build de Product.wxs + Components.wxs gera dist/TimesheetTerceiros.msi sem erro de validacao
    - done: true
      test: grep -E 'TimesheetBackend' apps/installer/Components.wxs
      text: Components.wxs registra os 2 Windows Services TimesheetBackend (porta configuravel via TIMESHEET_PORT default 8765) e TimesheetAgent via ServiceInstall/ServiceControl com Start=auto
    - done: true
      text: MSI provisiona dados em ProgramData/TimesheetTerceiros (key.kek, timesheet.sqlite, pdfs/, scheduler.sqlite) com ACL restrita na pasta pdfs via util:PermissionEx e define as env vars TIMESHEET_* do Service backend
    - done: true
      text: CustomAction WaitForServiceReady faz polling em /api/v1/ready com contador/timeout limitado e falha a instalacao se nao ficar ready
    - done: true
      text: make build encadeia build-backend + publish-agent + wix build; make setup prepara dev sem subir/parar app; make release assina com signtool quando SIGN_CERT presente
    - done: true
      text: RUNBOOK estendido preserva a secao Infraestrutura na integra e adiciona a secao Aplicacao (msiexec, 2 services, sc start/stop, ProgramData, healthchecks /health e /ready); verificacao pos-escrita re-le e confirma as duas secoes
deps:
    - TASK-036
    - TASK-037
id: TASK-038
linter: wix build apps/installer/Product.wxs apps/installer/Components.wxs -ext WixToolset.Util.wixext -ext WixToolset.UI.wixext -o dist/TimesheetTerceiros.msi
n45_version: 0.2.0
persona: devops
phase: Phase 6 — Empacotamento Windows (PyInstaller + WiX MSI)
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: done
tests: wix build apps/installer/Product.wxs apps/installer/Components.wxs -ext WixToolset.Util.wixext -ext WixToolset.UI.wixext -o dist/TimesheetTerceiros.msi
title: Instalador WiX MSI (2 Windows Services + dados ProgramData + ACLs + porta/JWT) + Makefile build/release + RUNBOOK Aplicacao
updated_at: "2026-05-29 12:18:10"
---
## Contexto

Task final da Phase 6 (Empacotamento Windows) e a que **amarra tudo**: o instalador MSI WiX que distribui o produto full-local. Depende de TASK-036 (`apps/api/dist/timesheet-backend.exe`, que já embute a SPA do Web + migrations) e TASK-037 (`apps/agent/dist/service/TimesheetAgent.exe` + `apps/agent/dist/ui/TimesheetAgentUi.exe`, self-contained). Hoje `apps/installer/` só tem `.gitkeep` — nada de WiX. O Makefile raiz só tem targets de dev/smoke (`api-dev`, `web-build`, `agent-build`, `smtp-*`); não há `build`/`release`/`setup` de produção. O RUNBOOK tem apenas a seção "Infraestrutura" (Mailhog dev) e termina com `> Secao "Aplicacao" sera adicionada pela Phase 5 (Containerizacao / Empacotamento).` — esta task adiciona a seção "Aplicação".

O MSI deve (Spec §2 "Distribuição", §6 "in scope", §7 "Constraints", §8 RF-013, §9 "Smoke test do MSI"):
- Instalar `timesheet-backend.exe` e registrá-lo como Windows Service **`TimesheetBackend`** (bind `127.0.0.1:<porta>`).
- Instalar `TimesheetAgent.exe` e registrá-lo como Windows Service **`TimesheetAgent`**.
- Instalar `TimesheetAgentUi.exe` e configurar autostart na sessão do usuário (logon).
- Provisionar `%APPDATA%\TimesheetTerceiros\` (banco SQLite+SQLCipher, `key.kek`, `pdfs/`, `scheduler.sqlite`) com **ACLs restritas** à conta do Service `TimesheetBackend` na pasta de PDFs (Spec §7 "ACLs de arquivo").
- Permitir configurar a **porta** na instalação (property `TIMESHEET_PORT`, default 8765) e gerar um `TIMESHEET_JWT_SECRET` aleatório (≥32 chars) na instalação.
- Definir as env vars de produção para o Service backend apontarem para `%APPDATA%\TimesheetTerceiros\`.
- Aguardar o backend ficar `ready` (`GET /api/v1/ready` → 200) após start do Service (Spec RF-013).
- Desinstalar de forma limpa (remove serviços, EXEs e atalhos; preserva ou remove dados conforme convenção — ver Detalhamento).

Estado atual relevante (fatos):
- Backend exe lê env vars `TIMESHEET_*` (ver TASK-036). Em produção espera: `TIMESHEET_KEK_PATH`, `TIMESHEET_DB_URL`, `TIMESHEET_PDF_DIR`, `TIMESHEET_SCHEDULER_JOBSTORE`, `TIMESHEET_PORT`, `TIMESHEET_JWT_SECRET`; `TIMESHEET_DEV` **ausente** (OpenAPI off). KEK gerada na 1ª execução do backend via `ensure_kek` (DPAPI).
- Service backend não tem `--service` flag; roda como processo HTTP comum. Windows Service via WiX `ServiceInstall` + `ServiceControl` (o exe deve sobreviver como serviço; uvicorn rodando em foreground sob o SCM funciona se o exe trata o sinal de stop — ver Detalhamento, nota sobre wrapper de serviço).
- Agente Service `TimesheetAgent` já usa `AddWindowsService(ServiceName="TimesheetAgent")` no `Program.cs` — integra direto com o SCM.
- RUNBOOK atual (preservar na íntegra a seção Infraestrutura; frontmatter atual: `start: docker compose -f docker-compose.dev.yml up -d`, `stop: docker compose -f docker-compose.dev.yml down`, `services: [postgres? não — mailhog]`, healthcheck mailhog). **Conferir o conteúdo atual via binário antes de reescrever** (passo no Detalhamento).

## Comportamento Esperado

Persona devops — verificação por validação do WiX (`wix build`/`candle`+`light` ou `dotnet build` do projeto `.wixproj`), `docker compose config`-equivalente para WiX é o **build do MSI**, e o smoke de install/uninstall. Não há lógica de negócio testável.

**Exemplos (entrada / ação → saída esperada)** — valores reais:

| Entrada / Ação | Saída / Efeito esperado |
| -------------- | ----------------------- |
| `wix build apps/installer/Product.wxs apps/installer/Components.wxs -o dist/TimesheetTerceiros.msi` | MSI gerado sem erro de validação |
| `msiexec /i TimesheetTerceiros.msi /qn TIMESHEET_PORT=8765` (instalação silenciosa) | 2 serviços criados (`sc query TimesheetBackend` e `sc query TimesheetAgent` → `RUNNING`) |
| Após install, aguardar ready | `curl http://127.0.0.1:8765/api/v1/health` → 200 e `.../api/v1/ready` → 200 |
| `%APPDATA%\TimesheetTerceiros\` após primeiro start do backend | contém `timesheet.sqlite`, `key.kek`, `pdfs/`, `scheduler.sqlite`; `pdfs/` com ACL restrita à conta do Service |
| `msiexec /x TimesheetTerceiros.msi /qn` (uninstall) | `sc query TimesheetBackend` e `TimesheetAgent` → não existe; EXEs e atalho de autostart removidos |
| `make build` | roda build-backend (TASK-036) + publish-agent (TASK-037) + `wix build` → MSI em `dist/` |
| `make setup` | (com infra/app já instaláveis) prepara o ambiente local de dev: `make data-dir` + deriva caminhos — não sobe nem para a aplicação |

## O que Implementar

> Persona devops — sem TDD. Critérios verificados por `wix build` (validação do MSI) e pelo smoke de install/uninstall silencioso.

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| ------- | ---- | --------- |
| `apps/installer/Product.wxs` | Criar | Pacote MSI: Product/Package, propriedades (`TIMESHEET_PORT` default 8765, geração de JWT secret), diretórios (`ProgramFiles64Folder\TimesheetTerceiros`, `AppDataFolder\TimesheetTerceiros`), Features, UI mínima (ou silent), `CustomAction`/`WaitForServiceReady` chamando `/api/v1/ready` |
| `apps/installer/Components.wxs` | Criar | Componentes: backend exe + `ServiceInstall`/`ServiceControl` (`TimesheetBackend`), agent service exe + service (`TimesheetAgent`), agent UI exe + autostart (Run key `HKCU` ou atalho Startup), env vars do Service backend, criação de `%APPDATA%\TimesheetTerceiros\pdfs` com `util:PermissionEx` (ACL) |
| `apps/installer/Timesheet.Installer.wixproj` | Criar | Projeto WiX 4+ (`dotnet build` / `wix`), referencia `WixToolset.Util.wixext` (PermissionEx, ServiceConfig) e `WixToolset.UI.wixext` |
| `Makefile` | Modificar | Adicionar `build` (build-backend + publish-agent + wix build → MSI), `release` (build + assinatura via `signtool` — flag/var de cert opcional), `setup` (prep ambiente dev, sem subir app), `installer-validate` (`wix build` apenas, para CI) |
| `.env.example` (raiz ou `apps/api/.env.example`) | Modificar | Documentar as env vars de **produção** que o MSI define no Service backend (`TIMESHEET_KEK_PATH`, `TIMESHEET_DB_URL`, `TIMESHEET_PDF_DIR`, `TIMESHEET_SCHEDULER_JOBSTORE`, `TIMESHEET_PORT`, `TIMESHEET_JWT_SECRET`) com os valores `%APPDATA%\TimesheetTerceiros\...` |
| `.n45/docs/RUNBOOK.md` | Modificar (via binário) | Estender com seção "Aplicação" — **read→merge→create** via `n45.exe` (ver Detalhamento passo 7). NÃO editar com Write/Edit |

### Detalhamento Técnico

1. **`Product.wxs`** — WiX 4 schema. `Package` com `Name="Timesheet Terceiros"`, `Manufacturer`, `Version="1.0.0"`, `UpgradeCode` fixo (GUID), `InstallerVersion="500"`, `Scope="perMachine"`. `MajorUpgrade` para upgrade limpo. Property `TIMESHEET_PORT` com `Value="8765"` (sobrescrevível na linha de comando). Gerar JWT secret: `CustomAction` que executa um pequeno gerador (ou usar `<util:GenerateGuid>`-style — preferir um `CustomAction` que escreve um secret aleatório de ≥32 chars; alternativa simples e aceitável na v1.0: concatenar 2 GUIDs sem hífens = 64 chars hex). Persistir o secret e a porta nas env vars do Service (passo 2).

2. **`Components.wxs`** — três blocos:
   - **Backend Service**: `Component` com o `File` `timesheet-backend.exe` (de `apps/api/dist/`); `ServiceInstall` `Name="TimesheetBackend"`, `DisplayName="Timesheet Backend"`, `Start="auto"`, `Type="ownProcess"`, `ErrorControl="normal"`, conta `LocalSystem` (precisa de DPAPI máquina/usuário — usar conta de serviço dedicada ou `LocalSystem`; documentar trade-off: DPAPI da KEK fica vinculada à conta do Service — manter conta estável). `ServiceControl` `Start="install"` `Stop="both"` `Remove="uninstall"`. Env vars via `<ServiceInstall>` + registry ou `Environment` element apontando para `%APPDATA%\TimesheetTerceiros\` (ver nota sobre %APPDATA% de serviço abaixo).
   - **Agent Service**: `File` `TimesheetAgent.exe`; `ServiceInstall` `Name="TimesheetAgent"` `Start="auto"` `Type="ownProcess"`; `ServiceControl` start/stop/remove. (O exe já chama `AddWindowsService` — integra com SCM.)
   - **Agent UI autostart**: `File` `TimesheetAgentUi.exe` em `ProgramFiles64Folder\TimesheetTerceiros`; autostart na sessão do usuário via `RegistryValue` em `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` **ou** atalho em `StartupFolder`. (HKCU Run com per-machine install exige `MSIINSTALLPERUSER`/component por-usuário — preferir atalho em `StartupFolder` com `Shortcut`, mais robusto para perMachine.)
   - **Pasta de dados + ACL**: `CreateFolder` para `%APPDATA%\TimesheetTerceiros\pdfs` com `<util:PermissionEx>` concedendo acesso só à conta do Service backend (Spec §7). 

   > **Nota %APPDATA% para Windows Service:** `LocalSystem`/conta de serviço tem um `%APPDATA%` próprio (perfil do serviço), **não** o do usuário interativo. Para o backend (Service) e o agente (Service) escreverem no mesmo `%APPDATA%\TimesheetTerceiros\` previsível, definir as env vars `TIMESHEET_*` com um caminho **absoluto e fixo** resolvido na instalação (ex.: `[CommonAppDataFolder]TimesheetTerceiros\...` = `C:\ProgramData\TimesheetTerceiros`), e não `%APPDATA%` literal. **Decisão:** usar `CommonAppDataFolder` (`C:\ProgramData\TimesheetTerceiros`) para os dados de produção — acessível por ambos os serviços e estável entre contas; ACL restrita a SYSTEM + conta do Service. Documentar no RUNBOOK que produção usa `ProgramData`, não `%APPDATA%` (o RUNBOOK atual menciona `%APPDATA%` — corrigir na seção Aplicação para refletir a decisão). Alternativa rejeitada: `%APPDATA%` literal — não compartilhável entre conta de serviço e usuário.

3. **Env vars do Service backend** — definir (via `ServiceInstall` child `Environment` ou registry de serviço): `TIMESHEET_KEK_PATH=[CommonAppDataFolder]TimesheetTerceiros\key.kek`, `TIMESHEET_DB_URL=sqlite+aiosqlite:///[CommonAppDataFolder]TimesheetTerceiros\timesheet.sqlite`, `TIMESHEET_PDF_DIR=[CommonAppDataFolder]TimesheetTerceiros\pdfs`, `TIMESHEET_SCHEDULER_JOBSTORE=[CommonAppDataFolder]TimesheetTerceiros\scheduler.sqlite`, `TIMESHEET_PORT=[TIMESHEET_PORT]`, `TIMESHEET_JWT_SECRET=[GENERATED_SECRET]`. (Backslash/forward-slash no DB_URL: usar barras compatíveis com SQLAlchemy — `sqlite+aiosqlite:///C:/ProgramData/...`.)

4. **Wrapper de serviço do backend (decisão):** uvicorn não responde ao SCM por padrão. **Decisão:** confiar em `ServiceControl Stop` enviando o sinal de parada do SCM e o exe tratando shutdown gracioso (uvicorn já faz graceful shutdown em SIGTERM/CTRL). Se o exe single-file não responder ao SCM como `ownProcess`, fallback documentado: instalar via `sc.exe` com `srvany`-style ou usar `Microsoft.Extensions.Hosting.WindowsServices` no launcher Python — **fora do escopo Python**; portanto a abordagem v1.0 é `ServiceInstall ownProcess` + `WaitForServiceReady` por `/ready`. Documentar como risco conhecido caso o SCM mate o processo por timeout de start (mitigar com `/ready` rápido — health não toca banco, latência <50ms).

5. **`WaitForServiceReady`** — `CustomAction` (deferred ou pós-`InstallServices`) que faz polling em `http://127.0.0.1:[TIMESHEET_PORT]/api/v1/ready` com contador/timeout (ex.: 60 tentativas × 1s) — falha a instalação se não ficar ready (Spec RF-013: "Instalador MSI usa /ready para aguardar Backend pronto"). Loop com limite (Spec "Loop de espera com limite").

6. **Makefile** — novos targets (sintaxe compatível com o Makefile atual, que usa `powershell` em Windows):
   ```makefile
   build:
   	powershell -ExecutionPolicy Bypass -File apps/api/scripts/build-backend.ps1
   	powershell -ExecutionPolicy Bypass -File apps/agent/scripts/publish-agent.ps1
   	wix build apps/installer/Product.wxs apps/installer/Components.wxs -ext WixToolset.Util.wixext -ext WixToolset.UI.wixext -o dist/TimesheetTerceiros.msi

   installer-validate:
   	wix build apps/installer/Product.wxs apps/installer/Components.wxs -ext WixToolset.Util.wixext -ext WixToolset.UI.wixext -o dist/TimesheetTerceiros.msi

   release: build
   	powershell -NoProfile -Command "if ($$env:SIGN_CERT) { signtool sign /f $$env:SIGN_CERT /fd SHA256 /t http://timestamp.digicert.com dist/TimesheetTerceiros.msi } else { Write-Host '[release] SIGN_CERT ausente — MSI nao assinado (dev)' }"

   setup: data-dir
   	@echo "[setup] ambiente dev preparado (data/). Producao via MSI."
   ```
   `start`/`stop` programáticos do RUNBOOK: produção = `sc start TimesheetBackend` / `sc stop TimesheetBackend` (e o mesmo para `TimesheetAgent`) — nunca interativo.

7. **RUNBOOK — estender (read→merge→create via binário):**
   1. Ler o conteúdo atual: `"C:\Users\cemat\OneDrive\Documents\N45\Projetos\C&M Tecnologia\Timesheet Terceiros\.n45\bin\n45.exe" 49aefa26 --bee531 --b79b13 --a6a0ee claude`
   2. Redigir o RUNBOOK completo = frontmatter atual (ajustar `start`/`stop` para incluir comandos de produção OU manter dev e documentar produção na seção) + **seção "Infraestrutura" preservada na íntegra** + nova **seção "Aplicação"** com: como o MSI instala (comando `msiexec /i`), os 2 Windows Services (`TimesheetBackend` na porta configurável, `TimesheetAgent`), `TimesheetAgentUi` autostart, caminho de dados de produção (`C:\ProgramData\TimesheetTerceiros\`), healthchecks de produção (`curl http://127.0.0.1:8765/api/v1/health` → 200, `.../ready` → 200), comandos `sc start/stop`, e os targets `make build`/`make release`/`make setup`.
   3. Gravar via `"C:\Users\cemat\OneDrive\Documents\N45\Projetos\C&M Tecnologia\Timesheet Terceiros\.n45\bin\n45.exe" 69443222 --bee531 --a6a0ee claude` com o conteúdo completo (escrever o body em `.n45/tmp/runbook-draft.md` antes e passar via `--1a0cb6`). Pós-escrita: reler o RUNBOOK e confirmar que **as duas seções** (Infraestrutura + Aplicação) estão presentes — perder a Infraestrutura quebra a Phase 7.

8. **`.gitignore`** — garantir `dist/` (raiz) e `apps/installer/obj`/`bin` ignorados. Verificar via `git check-ignore` antes de assumir.

**Contrato com camadas adjacentes:**

```
Consome de: TASK-036 → apps/api/dist/timesheet-backend.exe (SPA embutida + migrations + /health + /ready)
Consome de: TASK-037 → apps/agent/dist/service/TimesheetAgent.exe, apps/agent/dist/ui/TimesheetAgentUi.exe (self-contained)
Produz para: usuário final / Phase 7 (E2E) → MSI instalável que sobe os 2 serviços e responde /health + /ready em 127.0.0.1:<porta>
Smoke gate (Spec §9): instalação silenciosa → 2 services RUNNING → /health 200 → /ready 200 → uninstall limpo
```
