---
checkpoint: null
complexity: P
created_at: "2026-06-02 16:45:41"
criteria:
    - done: true
      test: grep -E "Arguments=\" service\"" apps/installer/Components.wxs
      text: O ServiceInstall Id=TimesheetBackendService inclui Arguments com valor espaco+service
    - done: true
      text: O ServiceInstall do TimesheetAgent permanece sem atributo Arguments (inalterado)
    - done: true
      test: python -c "import xml.dom.minidom as m; m.parse(open(apps/installer/Components.wxs))"
      text: Components.wxs permanece XML bem-formado
    - done: true
      text: Demais atributos e filhos (ServiceConfig, ServiceControl, RegistryValue) do TimesheetBackendService inalterados
deps: []
id: TASK-003
n45_version: 0.2.0
persona: devops
phase: Phase 1 — Handshake SCM do Backend
roadmap: fix-0002-backend-nao-roda-como-windows-service-handshake-scm-ausente
status: done
tests: make installer-validate
title: Argumento service no binPath do ServiceInstall do TimesheetBackend (Components.wxs)
updated_at: "2026-06-02 17:12:18"
---
## Contexto

O MSI (WiX) registra o `timesheet-backend.exe` como Windows Service nativo via `<ServiceInstall Id="TimesheetBackendService" ...>` em `apps/installer/Components.wxs`. A correção do handshake do SCM (feita em outra task no `launcher.py`) ativa o modo serviço **por argumento explícito**: o binário só entra no fluxo do dispatcher SCM quando invocado como `timesheet-backend.exe service`. Sem o argumento, o exe roda em modo console (comportamento atual) e o SCM nunca recebe o handshake → o passo `StartServices` do MSI falha por timeout → instalação aborta.

Esta task garante que o serviço seja registrado com o argumento `service` no binPath. No WiX, o `ServiceInstall` aceita o atributo `Arguments`, que é concatenado ao caminho do exe no binPath do SCM. **Espaço inicial obrigatório** (`Arguments=" service"`): o WiX junta os argumentos diretamente após o caminho do executável, então sem o espaço o binPath ficaria `...timesheet-backend.exeservice`. O resultado esperado do binPath registrado é `"C:\Program Files\TimesheetTerceiros\timesheet-backend.exe" service`.

Estado atual do `<ServiceInstall Id="TimesheetBackendService">` (linhas ~44-62): possui `Name`, `DisplayName`, `Description`, `Type="ownProcess"`, `Start="auto"`, `ErrorControl="normal"`, `Account="LocalSystem"`, `Interactive="no"` e um filho `<util:ServiceConfig>` — **não possui** `Arguments`. O `<ServiceInstall Id="TimesheetAgentService">` (serviço .NET, linhas ~132-149) **não deve ser alterado** por este fix.

## Comportamento Esperado

O `ServiceInstall` do `TimesheetBackend` passa a ter `Arguments=" service"`; o `ServiceInstall` do `TimesheetAgent` permanece exatamente como está.

**Exemplos (verificação → resultado esperado):**

| Verificação | Resultado esperado |
| ----------- | ------------------ |
| Atributo `Arguments` no `<ServiceInstall Id="TimesheetBackendService">` | presente, valor `" service"` (com espaço inicial) |
| binPath efetivo registrado no SCM | `"...\timesheet-backend.exe" service` |
| `<ServiceInstall Id="TimesheetAgentService">` tem atributo `Arguments` | ausente (inalterado) |
| Demais atributos do `TimesheetBackendService` (`Type`, `Start`, `Account`, etc.) | inalterados |
| `<util:ServiceConfig>` filho do `TimesheetBackendService` | inalterado |

## O que Implementar

Persona `devops` (WiX/MSI). Adicionar o atributo `Arguments=" service"` ao elemento `<ServiceInstall Id="TimesheetBackendService">` em `apps/installer/Components.wxs`. Mudança localizada de um único atributo.

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| ------- | ---- | --------- |
| `apps/installer/Components.wxs` | Modificar | Adicionar `Arguments=" service"` ao `<ServiceInstall Id="TimesheetBackendService">` |

### Detalhamento Técnico

1. Localizar o elemento `<ServiceInstall Id="TimesheetBackendService" Name="TimesheetBackend" ...>`.
2. Adicionar o atributo `Arguments=" service"` (espaço inicial dentro das aspas — obrigatório). Posicionar junto aos demais atributos, por exemplo logo após `Interactive="no"`.
3. **Não** tocar o `<ServiceInstall Id="TimesheetAgentService">`, nem o `<util:ServiceConfig>`, nem `<ServiceControl>`, nem os `<RegistryValue>` de env vars.

**Exemplo de implementação (atributo adicionado ao elemento existente):**

```xml
        <ServiceInstall
          Id="TimesheetBackendService"
          Name="TimesheetBackend"
          DisplayName="Timesheet Backend"
          Description="Servidor HTTP local do Timesheet Terceiros (porta [TIMESHEET_PORT])"
          Type="ownProcess"
          Start="auto"
          ErrorControl="normal"
          Account="LocalSystem"
          Interactive="no"
          Arguments=" service">
          <!-- espaço inicial obrigatório: WiX concatena Arguments ao caminho do exe no binPath -->
          <util:ServiceConfig
            ServiceName="TimesheetBackend"
            FirstFailureActionType="restart"
            SecondFailureActionType="restart"
            ThirdFailureActionType="none"
            ResetPeriodInDays="1"
            RestartServiceDelayInSeconds="5" />
        </ServiceInstall>
```

**Refatoração:** Nenhuma.

> **Validação (devops):** o `Components.wxs` é XML — deve permanecer bem-formado. Onde disponível, validar via `make installer-validate` (valida o MSI sem buildar os executáveis, conforme runbook). Em CI Linux/sem WiX, o critério mecânico é a presença textual do atributo `Arguments=" service"` no `TimesheetBackendService` e a ausência de `Arguments` no `TimesheetAgentService`. O build/instalação real do MSI roda no CI Windows.
