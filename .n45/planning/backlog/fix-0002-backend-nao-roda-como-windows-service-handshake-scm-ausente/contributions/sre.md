---
created_at: "2026-06-02 12:41:35"
from: sre
n45_version: 0.2.0
spec_id: fix-0002-backend-nao-roda-como-windows-service-handshake-scm-ausente
---
### Resiliência

- Circuit breaker: não aplicável — o bootstrap do serviço é local (SQLite + migrações); sem integrações externas em `SvcDoRun`.
- Retry: não aplicável neste fix — falhas de bootstrap devem falhar imediatamente e reportar ao SCM (retries ocultariam falhas de instalação).
- Timeout: `server.started` aguardar ≤ 30 s antes de reportar falha ao SCM (START_PENDING não pode ficar indefinido); join da thread uvicorn em `SvcStop` ≤ 15 s antes de forçar stop com log de aviso.
- Graceful shutdown: `server.should_exit = True` → join da thread uvicorn com timeout de 15 s → reportar `SERVICE_STOPPED`. Se o join expirar, logar `logger.warning("uvicorn thread did not terminate within 15 s; forcing SERVICE_STOPPED")` e retornar.

### Health Checks

| Endpoint       | Tipo      | Verifica                                          |
| -------------- | --------- | ------------------------------------------------- |
| /health/live   | liveness  | processo uvicorn respondendo (app rodando)        |
| /api/v1/health | liveness  | endpoint existente — continua inalterado          |
| /api/v1/ready  | readiness | migrações aplicadas + DB conectado (já existente) |

Não há novo endpoint a criar neste fix — `/api/v1/ready` já cobre readiness pós-bootstrap.

### Log Estruturado

Campos obrigatórios nos eventos do ciclo de vida do serviço:
- `event`: nome do evento (`service_start_pending`, `service_running`, `service_stop_pending`, `service_stopped`, `service_bootstrap_error`)
- `svc_name`: `"TimesheetBackend"`
- `timestamp`: ISO-8601 (já provido pelo logging configurado em `configure_logging()`)

Eventos críticos a logar:
- `service_start_pending` — ao entrar em `SvcDoRun` antes do bootstrap
- `service_running` — após `server.started` confirmado
- `service_stop_pending` — ao entrar em `SvcStop`
- `service_stopped` — após join da thread uvicorn
- `service_bootstrap_error` — qualquer exceção no bootstrap dentro de `SvcDoRun` (nível `ERROR`, com `exc_info=True`)
- `service_stop_timeout` — join da thread uvicorn expirou (nível `WARNING`)

Nunca logar:
- Credenciais, chaves de criptografia, tokens (`PRAGMA key`, secrets de ambiente)

### Para tasks

- `50a8844c7d` (executor backend): implementar timeouts de `server.started` (≤ 30 s) e join `SvcStop` (≤ 15 s); logar todos os eventos críticos listados acima com campos `event` e `svc_name`; garantir que exceção no bootstrap chama `servicemanager.LogErrorMsg` e reporta stop ao SCM antes de propagar.
- `82654b3833` (SRE/observabilidade): não há novos health check probes a criar; `/api/v1/ready` já cobre readiness pós-bootstrap — validar que ele responde 200 após `server.started` no caminho de serviço.

### Conflitos com outras áreas

- ⚠ Risco de regressão de bootstrap cross-platform: imports `win32serviceutil`/`servicemanager` lazy/guardados por `sys.platform` são necessários para não quebrar coleta de pytest em CI Linux — confirmar com o executor que o guard está presente antes do merge.
- Nenhum conflito com security, data ou UI.
