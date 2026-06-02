---
created_at: "2026-06-02 12:41:58"
from: security
n45_version: 0.2.0
spec_id: fix-0002-backend-nao-roda-como-windows-service-handshake-scm-ausente
---
### Requisitos de Implementação — Crítico / Alto

Nenhum requisito crítico ou alto identificado para esta fix. A superfície de ataque é restrita ao ciclo de vida do serviço Windows gerenciado pelo SCM; não há novas rotas HTTP, autenticação, PII ou upload de arquivos envolvidos.

### Requisitos de Implementação — Médio / Baixo

- **[Médio] Nenhum pré-processamento sensível antes do dispatcher:** No path `argv[1] == "service"` de `main()`, nenhum código privilegiado (DPAPI, migrations, uvicorn, leitura de secrets) pode ser executado antes da chamada a `servicemanager.StartServiceCtrlDispatcher()`. O bootstrap completo deve ocorrer somente dentro de `SvcDoRun`, após o dispatcher validar que o processo foi invocado pelo SCM (`ERROR_FAILED_SERVICE_CONTROLLER_CONNECT` interrompe antes disso). RF-03 já prevê isso — adicionar nota explícita no código/comentário.

- **[Médio] Sanitização do log de exceção no bootstrap:** Quando `SvcDoRun` captura exceção no bootstrap (`prepare_runtime`, `run_migrations`), a mensagem passada a `servicemanager.LogErrorMsg` e ao `logger.exception` não deve incluir valores de configuração sensíveis (PRAGMA key, connection string com credenciais, DPAPI blob). Usar apenas o tipo da exceção e a camada onde ocorreu — nunca `str(exc)` direto quando o contexto pode conter segredos.

- **[Baixo] Timeout de join obrigatório no SvcStop:** O join da thread do uvicorn no `SvcStop` deve ter timeout máximo definido em código (sugestão: 10 s). Após o timeout, logar aviso e retornar — o SCM escalará para `TerminateProcess` se necessário. Sem timeout fixo o serviço pode ficar travado em `STOP_PENDING` indefinidamente, o que impede reinicializações de segurança emergenciais.

- **[Baixo] `win32api` em `hiddenimports` — escopo mínimo:** Confirmar que apenas os módulos estritamente necessários para o `ServiceFramework` são adicionados ao bundle (`win32serviceutil`, `win32service`, `win32event`, `servicemanager`, `win32api`). Não adicionar outros módulos pywin32 de propósito geral que ampliariam a superfície sem necessidade.

### Para tasks

- `50a8844c7d`: sanitizar log de exceção no bootstrap (não expor PRAGMA key, connection strings, DPAPI blobs em `logger.exception` / `LogErrorMsg`); garantir ausência de pré-processamento sensível antes do dispatcher no path `service`.
- `82654b3833`: definir timeout de join obrigatório (10 s) no `SvcStop`; validar que hidden imports do pywin32 no spec ficam restritos aos módulos listados na Spec.

### Conflitos com outras áreas

Nenhum conflito identificado. Esta fix não altera endpoints HTTP, schema de banco, auth/authz, CORS, upload nem fluxo de tokens — as superfícies cobertas por outras áreas permanecem inalteradas.
