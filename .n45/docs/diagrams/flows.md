## Fluxos de Usuário

Sequência de interações para os principais fluxos da aplicação.

---

### Registro Automático de Marcação (Agente)

```mermaid
%%{init: {'theme': 'neutral'} }%%
sequenceDiagram
  actor W as Windows
  participant A as Agente Service
  participant D as Domain\nState Machine
  participant UI as WPF UI\nTray
  participant B as Backend API

  W->>A: SessionLogon event
  A->>D: ProcessLoginEvent()
  D->>UI: TOAST saudação contextual
  D->>D: Cria MarcacaoLocal(INICIO_JORNADA)
  D->>B: POST /api/v1/marcacoes (idempotency_key)
  B-->>D: 201 Created
  D->>D: sincronizada = true

  Note over D: Polling 30s GetLastInputInfo
  D->>D: Detecta inatividade >= 10min\n(janela saida_almoco +/- 30min)
  D->>D: Cria MarcacaoLocal(SAIDA_ALMOCO)
  D->>B: POST /api/v1/marcacoes
  B-->>D: 201 Created

  D->>D: Detecta primeiro input pós-almoço
  alt dentro da janela
    D->>D: Cria MarcacaoLocal(RETORNO_ALMOCO)
  else fora da janela
    D->>UI: DIALOG_REQUEST CONFIRM_RETORNO_FORA_JANELA
    UI-->>D: SIM / NAO / TIMEOUT
    D->>D: Cria MarcacaoLocal(status conforme resposta)
  end
  D->>B: POST /api/v1/marcacoes
  B-->>D: 201 Created

  D->>UI: DIALOG_REQUEST PROMPT_FIM_JORNADA (timeout 60s)
  UI-->>D: SIM + atividade
  D->>D: Cria MarcacaoLocal(FIM_JORNADA)
  D->>B: POST /api/v1/marcacoes
  B-->>D: 201 Created
```

### Login Web e Acesso ao Dashboard

```mermaid
%%{init: {'theme': 'neutral'} }%%
sequenceDiagram
  actor U as Terceiro
  participant F as Frontend SPA
  participant B as Backend API

  U->>F: Acessa /login
  F->>F: Exibe saudação contextual\n(Bom dia/tarde/noite)
  U->>F: Preenche e-mail + senha
  F->>B: POST /api/v1/auth/login
  alt credenciais válidas
    B-->>F: 200 access_token + refresh_token
    F->>B: GET /api/v1/privacidade
    alt aceite pendente
      B-->>F: aceito_em null
      F->>U: Redireciona /privacidade
      U->>F: Aceita termos
      F->>B: POST /api/v1/privacidade/aceitar
      B-->>F: 204
    end
    F->>U: Redireciona /jornadas
    F->>B: GET /api/v1/jornadas?mes=YYYY-MM
    B-->>F: 200 lista jornadas
    F->>U: Exibe tabela mensal
  else credenciais inválidas
    B-->>F: 401
    F->>U: Alert "E-mail ou senha inválidos"
  end
```

### Ajuste Manual de Jornada (Web)

```mermaid
%%{init: {'theme': 'neutral'} }%%
sequenceDiagram
  actor U as Terceiro
  participant F as Frontend SPA
  participant B as Backend API

  U->>F: Clica linha na tabela /jornadas
  F->>B: GET /api/v1/jornadas/{id}
  B-->>F: 200 detalhe + marcacoes + auditoria
  F->>U: Exibe detalhe com horários editáveis
  U->>F: Edita horários
  F->>F: Recalcula total diário em tempo real
  U->>F: Clica "Salvar alterações"
  F->>U: Modal de justificativa (>= 5 chars)
  U->>F: Preenche motivo e confirma
  F->>B: PUT /api/v1/jornadas/{id}
  B->>B: Atualiza marcacoes (origem=AJUSTE_WEB)\nCria LogAuditoria + Justificativa\nInvalida relatorio_gerado do mês
  B-->>F: 200 jornada atualizada
  F->>U: Toast "Jornada atualizada com sucesso"\nBadge atualiza para AJUSTADA_MANUALMENTE
```

### Geração e Envio de Relatório Mensal

```mermaid
%%{init: {'theme': 'neutral'} }%%
sequenceDiagram
  participant S as APScheduler\n(dia 1 00:00 BRT)
  participant B as Backend Service
  participant DB as SQLite
  participant PDF as WeasyPrint
  participant SMTP as Servidor SMTP

  S->>B: trigger job relatorio_mensal
  B->>DB: SELECT jornadas mês anterior
  DB-->>B: dados consolidados
  B->>PDF: Renderiza HTML -> PDF (timeout 120s)
  PDF-->>B: bytes PDF
  B->>DB: INSERT relatorio_gerado
  B->>SMTP: Envia e-mail (3x retry backoff 5s, timeout 30s)
  alt envio bem-sucedido
    SMTP-->>B: OK
    B->>DB: INSERT historico_envio(SUCESSO)
  else falha após 3 tentativas
    B->>DB: INSERT historico_envio(FALHA, erro_mensagem)
  end
```

---

_Criado em: 2026-06-01 00:00_
