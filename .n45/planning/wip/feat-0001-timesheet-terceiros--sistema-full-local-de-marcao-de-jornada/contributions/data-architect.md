---
created_at: "2026-05-27 12:03:07"
from: data-architect
n45_version: 0.2.0
spec_id: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
---
### Correções de Schema

```sql
-- 1. Índice composto em jornada para queries por terceiro+período (único Terceiro na v1.0,
--    mas o campo terceiro_id está no WHERE de toda query de listagem)
CREATE INDEX idx_jornada_terceiro_data ON jornada(terceiro_id, data);
-- idx_jornada_data pode ser removido — o composto o substitui com vantagem.

-- 2. Índice em marcacao por jornada_id (necessário para JOIN e CASCADE verify)
CREATE INDEX idx_marcacao_jornada ON marcacao(jornada_id);

-- 3. Índice em justificativa por jornada_id (sem esse índice, busca de justificativas
--    por jornada é full scan)
CREATE INDEX idx_justificativa_jornada ON justificativa(jornada_id);

-- 4. CHECK de formato em relatorio_gerado.mes_referencia (consistência com
--    historico_envio_relatorio que já tem o CHECK)
ALTER TABLE relatorio_gerado ADD CHECK (length(mes_referencia) = 7);
-- Em SQLite, CHECK deve ir na criação; ajuste a migration 0001:
-- mes_referencia TEXT NOT NULL UNIQUE CHECK (length(mes_referencia) = 7),

-- 5. Coluna atualizado_em em atividade (necessária para log de auditoria de edição inline
--    — RF-007.4 gera LogAuditoria com antes_json/depois_json; sem timestamp de atualização
--    o snapshot "antes" fica sem âncora temporal)
ALTER TABLE atividade ADD COLUMN atualizado_em TEXT NULL;
-- Na criação (migration 0001), incluir:
-- atualizado_em TEXT NULL  -- ISO 8601 UTC; NULL = nunca editado após criação

-- 6. Retenção explícita em log_auditoria: adicionar coluna para TTL/purge futuro
--    (não obriga purge na v1.0, mas sem ela não há como implementar retenção depois
--    sem migration destrutiva)
ALTER TABLE log_auditoria ADD COLUMN expira_em TEXT NULL;
-- Na criação (migration 0001):
-- expira_em TEXT NULL  -- ISO 8601 UTC; NULL = retenção indefinida (v1.0); job futuro purga
```

**Problema crítico — re-criptografia de smtp_config.password_enc na troca de senha:**
A senha do Terceiro deriva a chave AES-GCM que protege `smtp_config.password_enc`. `PUT /api/v1/terceiros/me/senha` não descreve re-encriptação do campo. Sem isso, após a troca de senha o envio SMTP falha silenciosamente na próxima tentativa automática (dia 1 do mês).

Correção necessária na lógica de `PUT /api/v1/terceiros/me/senha`:
1. Descriptografar `password_enc` com a chave derivada da `senha_atual` (antes do hash).
2. Re-criptografar com chave derivada da `nova_senha`.
3. Persistir `smtp_config.password_enc` atualizado na mesma transação.
4. Se `smtp_config` não existir, ignorar (nenhuma ação).

Sem essa lógica, `smtp_config.password_enc` ficará corrompido/indecifrável após a primeira troca de senha.

### Índices

| Tabela | Colunas | Tipo | Query que atende |
| --- | --- | --- | --- |
| `jornada` | `(terceiro_id, data)` | composto | `GET /jornadas?mes=YYYY-MM` — filtro por terceiro e range de datas |
| `marcacao` | `jornada_id` | simples | JOIN implícito em todo carregamento de detalhe de jornada; ON DELETE CASCADE verify |
| `justificativa` | `jornada_id` | simples | Busca de justificativas ao carregar detalhe da jornada |

O índice `idx_jornada_data` existente pode ser substituído pelo composto `idx_jornada_terceiro_data` — cobre o mesmo caso e elimina o simples.

### Estratégia de Exclusão

| Entidade | Estratégia | Critério |
| --- | --- | --- |
| `terceiro` | Soft delete (v1.0 sem endpoint de deleção; out of scope) | Quando implementado (fase 2), soft delete necessário para LGPD: `excluido_em TEXT NULL`. Hard delete imediato exigiria cascade auditado para garantir remoção de PII em log_auditoria |
| `jornada` | Soft delete recomendado | Valor auditável; usuário pode querer recuperar jornada deletada acidentalmente |
| `marcacao` | Hard delete via CASCADE de jornada | Sem valor independente da jornada |
| `atividade` | Hard delete via CASCADE de jornada | Idem |
| `justificativa` | Hard delete via CASCADE de jornada | Idem; justificativa sem jornada não tem sentido |
| `log_auditoria` | Hard delete por TTL (job futuro) | Coluna `expira_em` prepara a infra; v1.0 sem purge |
| `refresh_token` | Hard delete via CASCADE de terceiro + revogação por uso | Já implementado via `revogado_em` |
| `relatorio_gerado` | Hard delete por job semanal após 24 meses | Conforme RF-008 |
| `historico_envio_relatorio` | Retenção indefinida na v1.0 | Baixo volume; sem PII direto |
| `smtp_config` | Hard delete junto com terceiro (manual/cascade) | Contém credencial; deve ser removido em eventual deleção do Terceiro |
| `privacy_acceptance` | Hard delete junto com terceiro | Consentimento vinculado ao titular |

### Requisitos LGPD/Compliance

**Dados classificados por entidade:**

| Entidade / Campo | Classe | Obrigação LGPD |
| --- | --- | --- |
| `terceiro.nome` | PII | Retenção definida; exclusão controlada na deleção do titular |
| `terceiro.email_contato` | PII | Idem; base legal = execução contratual |
| `terceiro.email_destinatario_relatorio` | PII (terceiro) | Idem; titular distinto — informar no aviso de privacidade |
| `terceiro.empresa_cnpj` | Financeiro/Negócio | Não é PII pessoal (pessoa jurídica), mas sensível |
| `terceiro.senha_hash` | Credencial | Argon2id adequado; nunca logar |
| `smtp_config.password_enc` | Credencial | AES-GCM adequado; chave derivada da senha — ver problema de re-encriptação acima |
| `smtp_config.username` | PII (email/usuário SMTP) | Armazenar criptografado também (atualmente texto claro) |
| `log_auditoria.antes_json / depois_json` | PII indireta | Pode conter snapshots com campos PII de `terceiro`. Sem TTL/anonimização definidos — adicionar `expira_em` e job de purge em fase 2 |
| `marcacao_local.jwt_access_token` (agente) | Credencial | Proteger com DPAPI (Windows); o `jwt_refresh_token` já está documentado como DPAPI-protected; estender ao access token |
| `configuracao_local.jwt_access_token` | Credencial | Idem — adicionar DPAPI protection explícita no schema do agente |

**Campos obrigatórios adicionais por compliance:**

1. `smtp_config.username` deve ser criptografado em repouso (atualmente `TEXT NOT NULL` sem criptografia), analogamente ao `password_enc`. Base: o username SMTP revela identidade do serviço de e-mail do Terceiro.

2. `log_auditoria` — adicionar TTL via `expira_em` (já incluído nas Correções de Schema acima). Documentar no aviso de privacidade o período de retenção.

3. Aviso de privacidade (`/privacidade`) deve listar explicitamente: (a) `email_destinatario_relatorio` como dado de terceiro coletado; (b) período de retenção do log de auditoria; (c) que credenciais SMTP são armazenadas criptografadas localmente.

4. Exclusão do Terceiro (fase 2) deve remover: `terceiro`, `jornada` (cascade), `smtp_config`, `privacy_acceptance`, `refresh_token` (cascade), e anonimizar `log_auditoria` (substituir PII por `[removido]`), não apenas deletar (para preservar integridade do histórico sem expor o titular).

### Migração (se schema existente)

Projeto novo — não aplicável.

### Para tasks

- `29a9b94336`: Aplicar correções de schema na migration 0001: (1) `idx_jornada_terceiro_data` substituindo `idx_jornada_data`; (2) `idx_marcacao_jornada`; (3) `idx_justificativa_jornada`; (4) `CHECK (length(mes_referencia) = 7)` em `relatorio_gerado`; (5) coluna `atividade.atualizado_em TEXT NULL`; (6) coluna `log_auditoria.expira_em TEXT NULL`. Adicionar lógica de re-encriptação de `smtp_config.password_enc` no handler de `PUT /api/v1/terceiros/me/senha`.
- `50a8844c7d`: Filtros de jornada devem usar índice composto `(terceiro_id, data)`. Handler de troca de senha deve re-criptografar `password_enc` em transação atômica. Repositório de auditoria deve popular `expira_em` quando configurado. Proteger `configuracao_local.jwt_access_token` no agente com DPAPI.

### Conflitos com outras áreas

⚠ Conflito com segurança/auth: `smtp_config.username` está sem criptografia enquanto `password_enc` está criptografado — inconsistência que expõe parcialmente a identidade do serviço SMTP. Recomendo criptografar ambos com a mesma abordagem AES-GCM, ou documentar explicitamente a decisão de deixar o username em claro.

⚠ Conflito com RF-007.5 / troca de senha: a Spec não descreve re-encriptação de `smtp_config.password_enc` após mudança de senha. Sem essa lógica, o envio automático do relatório no dia 1 falha silenciosamente. É um bloqueador funcional que precisa ser resolvido na task do backend.
