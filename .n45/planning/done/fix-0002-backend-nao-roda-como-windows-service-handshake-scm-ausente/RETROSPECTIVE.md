---
created_at: "2026-06-02 18:33:08"
id: fix-0002-backend-nao-roda-como-windows-service-handshake-scm-ausente
metrics:
    added_tasks: 0
    blocks: 0
    planned_tasks: 3
    re_reviews: 0
    scope_changes: 0
    validation_changes: 0
    validation_fixes: 2
n45_version: 0.2.0
recommendations:
    - 'Incluir testes de integração com o instalador MSI para custom actions JavaScript (ações diferidas): cobrir cenários onde session.Log() não está disponível antes de promover para produção'
    - Validar custom actions WiX em ambiente de execução diferida durante o ciclo de review do task, não apenas na validação final de MSI — erros de contexto de execução não aparecem em make installer-validate
---
## Fricções

Nenhuma task problemática: todas as 3 tasks foram aprovadas na primeira review, sem bloqueios, sem re-reviews e sem escalations.

## Ajustes pós-conclusão

- `[hot-fix]` fix(installer): corrigir custom action WaitForServiceReady — erro 1720 — a custom action JavaScript `WaitForServiceReady.js` usava a propriedade `Session.Log()` que não está disponível no contexto de execução diferida (deferred), causando erro MSI 1720; a solução foi remover a chamada de log e ajustar o polling de `sc query`
- `[hot-fix]` fix(installer): remover session.Log() de WaitForServiceReady.js — refinamento do fix anterior; a raiz era o uso de `session.Log()` em ação diferida, que o WiX/MSI não suporta; remoção completa da chamada resolveu o problema sem quebrar a lógica de aguardo do serviço
