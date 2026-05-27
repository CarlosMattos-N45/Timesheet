---
created_at: "2026-05-27 12:02:48"
from: sre
n45_version: 0.2.0
spec_id: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
---
### Resiliência

**Agente → Backend (HTTP local, Polly):**
- Circuit breaker: `HttpClient` + Polly — fail_max: 5 tentativas em 30s, reset_timeout: 60s, fallback: enfileira localmente (comportamento já previsto no RF-011)
- Retry: exponencial — 1s → 2s → 4s → 8s → 16s (max 5 tentativas); condições: `HttpRequestException`, `TaskCanceledException`, status 5xx; NÃO aplicar retry em 4xx (exceto 429 se surgir)
- Timeout por requisição HTTP do Agente: 10s (local loopback; valor alto apenas para proteger contra Backend travado)
- `proxima_tentativa_em` em `marcacao_local` deve refletir o backoff calculado para evitar polling desnecessário quando o circuit está aberto

**Backend → SMTP (smtplib):**
- Retry: 3 tentativas com backoff linear 5s (SMTP não é idempotente por padrão, mas o job é mensal e o registro `HistoricoEnvioRelatorio` evita duplicação); condições: `SMTPConnectError`, `SMTPHeloError`, `socket.timeout`
- Timeout: `smtplib.SMTP(timeout=30)` — evita que job de geração de relatório trave indefinidamente aguardando resposta do SMTP
- Fallback: registra `FALHA` com mensagem de erro; não lança exceção que derrube o processo; exibe alerta na Web no próximo acesso
- Circuit breaker: não aplicável (operação única por mês, não há loop de chamadas)

**WeasyPrint (geração PDF):**
- Timeout: envolver chamada em `asyncio.wait_for` com timeout de 120s (PDF pode ser lento por libpango/libcairo Windows-native)
- Fallback: registra erro estruturado em log; mantém `relatorio_gerado.invalidado_em` setado para retentativa via on-demand

**APScheduler (job dia 1, 00:00 BRT):**
- Misfire grace time: 3600s — se o serviço estiver offline no momento exato, executa assim que voltar dentro de 1h
- coalesce: true — se o serviço ficou offline vários dias, não acumula execuções atrasadas; executa apenas 1 vez

**Graceful Shutdown — Backend (Uvicorn single-worker Windows Service):**
- Timeout de shutdown: 30s para drenar requests em andamento
- APScheduler: `scheduler.shutdown(wait=True)` antes de encerrar Uvicorn — aguarda job em execução terminar ou 60s (evita PDF truncado)
- Fechar pool `aiosqlite` após drenar requests; liberar SQLCipher cleanly

**Graceful Shutdown — Agente (.NET Windows Service):**
- `IHostedService.StopAsync` com `CancellationToken` timeout de 10s
- Flush do Serilog antes de encerrar (`Log.CloseAndFlush()`)
- Fechar named pipe graciosamente; se WPF processo filho ativo, enviar `TOAST` de encerramento antes de matar

---

### Health Checks

| Endpoint        | Tipo      | Verifica                                                                        |
| --------------- | --------- | ------------------------------------------------------------------------------- |
| /api/v1/health  | liveness  | Processo FastAPI respondendo (retorna `{"status":"ok","version":"<ver>"}`)      |
| /api/v1/ready   | readiness | Conexão SQLite/SQLCipher abrível + SELECT 1 executável + APScheduler rodando    |

Observações:
- O Agente já usa `GET /api/v1/health` para o sync loop (RF-011) — este endpoint deve permanecer sem autenticação e com latência < 50ms (sem acesso ao banco)
- `/api/v1/ready` é novo: usado pelo instalador MSI para aguardar o Backend ficar pronto após start do Service, e pelo tray icon para exibir estado de conectividade
- Separar os dois endpoints evita falso "down" quando o banco está momentaneamente bloqueado por migration ou geração de PDF

---

### Log Estruturado

**Campos obrigatórios por request (structlog — Backend):**
```
timestamp, level, event, request_id (UUID gerado por middleware), method, path, status_code, duration_ms, terceiro_id (se autenticado)
```

**Campos obrigatórios por evento de domínio (Backend):**
- Marcação recebida: `event=marcacao_received, tipo, origem, idempotency_key, jornada_id, resultado` (CRIADA | JA_EXISTENTE | CONFLITO)
- Sync conflict resolution: `event=sync_conflict_resolved, marcacao_id, regra_aplicada` (AJUSTE_WEB_VENCE | LAST_WRITE_WINS | AGENTE_EMPATE)
- Job PDF: `event=relatorio_job_started/completed/failed, mes_referencia, duracao_ms, erro`
- SMTP: `event=smtp_send_started/succeeded/failed, mes_referencia, email_destinatario, tentativa, erro`
- Auth: `event=login_success/login_failure/token_refreshed/logout, terceiro_id, ip=127.0.0.1` (ip fixo, apenas para auditoria local)
- Graceful shutdown: `event=shutdown_started/shutdown_completed, duracao_ms`

**Campos obrigatórios por evento (Agente — Serilog JSON):**
```
Timestamp, Level, EventId, MachineState, JornadaData, MarcacaoId, Tipo, Sincronizada, TentativasSync, Erro
```
Eventos críticos: `SessionLogon`, `InactivityDetected`, `DialogShown/Dismissed`, `SyncAttempt/SyncSuccess/SyncFailed`, `CircuitBreakerOpened/Closed`, `ServiceStarted/Stopped`

**Nunca logar:**
- `senha`, `senha_hash`, `password_enc` (SMTP config), `jwt_access_token`, `jwt_refresh_token`, `token_hash`
- Corpo completo de requests de autenticação
- Chave de derivação SQLCipher

**Retenção de logs:**
- Backend: rotativo por tamanho (10 MB/arquivo, max 30 arquivos) = ~300 MB max
- Agente: rotativo por tamanho (5 MB/arquivo, max 20 arquivos) = ~100 MB max

---

### Para tasks

- `50a8844c7d` (executor principal Backend):
  - Implementar middleware structlog com `request_id` obrigatório em cada request
  - Implementar `GET /api/v1/ready` que verifica SQLite + APScheduler
  - Aplicar `asyncio.wait_for(timeout=120)` na chamada WeasyPrint
  - Configurar `smtplib.SMTP(timeout=30)` + retry 3x com backoff 5s
  - Configurar APScheduler: `misfire_grace_time=3600, coalesce=True`
  - Implementar graceful shutdown: `scheduler.shutdown(wait=True)` + fechar pool aiosqlite antes do Uvicorn encerrar
  - Logar nunca: `senha`, `senha_hash`, `password_enc`, tokens JWT
  - Log de eventos de domínio: marcação recebida, conflito resolvido, job PDF, SMTP

- `d92c04968c` / executor Agente (.NET):
  - Configurar Polly: circuit breaker (fail_max=5/30s, reset=60s) + retry exponencial (1→2→4→8→16s, max 5 tentativas), timeout por request de 10s
  - Implementar `GET /api/v1/ready` como healthcheck de pré-sync (não usar apenas `/health` que não verifica banco)
  - Implementar `IHostedService.StopAsync` com `CancellationToken(timeout=10s)` + `Log.CloseAndFlush()`
  - Logar: `SessionLogon`, `InactivityDetected`, `DialogShown/Dismissed`, `SyncAttempt/SyncSuccess/SyncFailed`, `CircuitBreakerOpened/Closed`
  - Logar nunca: `jwt_access_token`, `jwt_refresh_token`

- `82654b3833` (SRE/infra — se ativado em fase futura):
  - Configurar health check probes no instalador WiX/Service Manager para `/api/v1/health` e `/api/v1/ready`

---

### Conflitos com outras áreas

- ⚠ Conflito potencial com Security: o endpoint `/api/v1/ready` não deve exigir autenticação (usado pelo instalador antes de qualquer login), mas expõe indiretamente que o banco está operacional. Mitigação: retornar apenas `{"status":"ready"}` sem detalhes do banco, mantendo bind em `127.0.0.1` (já constraint da Spec).
- ⚠ Conflito com APScheduler + SQLite: o jobstore do APScheduler não pode usar o mesmo arquivo SQLite do domínio (constraint já na Spec — "APScheduler em jobstore separado para evitar lock com migrations"). Confirmar que o graceful shutdown drena o job antes de fechar o pool do SQLite de domínio — não fechar na ordem inversa.
