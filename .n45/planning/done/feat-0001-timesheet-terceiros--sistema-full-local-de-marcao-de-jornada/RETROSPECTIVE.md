---
created_at: "2026-06-01 10:20:30"
id: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
metrics:
    added_tasks: 4
    blocks: 3
    planned_tasks: 40
    re_reviews: 2
    scope_changes: 0
    validation_changes: 0
    validation_fixes: 0
n45_version: 0.2.0
recommendations:
    - Definir limite de escopo por task (max 8 arquivos) na spec de cada fase, nao apenas como restricao do executor — evita bloqueios recorrentes por escopo excessivo
    - Para tasks de infraestrutura .NET, validar no inicio da fase se o SDK necessario esta instalado — adicionar health-check de prerequisitos ao script de setup do projeto
    - Dividir tasks de infra HTTP/token antecipadamente quando o dominio exige DPAPI + HttpClient — esses dois sub-dominios sao naturalmente separaveis e recorrentemente ultrapassam o orcamento juntos
---
## Friccoes

- TASK-003 — Executor frontend auto-bloqueou por escopo (~15 arquivos > limite de 8); resolvido com re-spawn com override de escopo
- TASK-004 — Duplo blocker: .NET SDK ausente no ambiente + escopo (~22 arquivos > 8); resolvido instalando SDK e re-spawn com override
- TASK-029 — Escopo excedeu orcamento (~9 arquivos > 8) e precisou ser dividida em TASK-029 (BackendClient+Polly) + TASK-035 (DpapiTokenStore+TokenManager)

## Ajustes pos-conclusao

Nenhum commit [hot-fix] ou [quick-feat] registrado na branch.
