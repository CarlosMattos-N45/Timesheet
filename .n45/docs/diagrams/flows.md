## Fluxos de Usuário

Sequência de interações para os principais fluxos da aplicação.

---

### Onboarding

```mermaid
%%{init: {'theme': 'neutral'} }%%
sequenceDiagram
  actor U as Terceiro
  participant A as Agente WPF
  participant B as Backend API
  participant W as Web SPA

  U->>A: Instala MSI + faz login Windows
  A->>A: Detecta cadastro pendente
  A->>U: Abre wizard Cadastro Inicial (3 passos)
  U->>A: Preenche dados (nome, empresa, CNPJ, horários, email, senha)
  A->>B: POST /api/v1/terceiros
  B-->>A: 201 Created
  A->>U: Abre browser em http://127.0.0.1:8765/login
  U->>W: Login com credenciais cadastradas
  W->>B: POST /api/v1/auth/login
  B-->>W: 200 access_token + refresh_token
  W->>U: Redireciona para /privacidade
  U->>W: Aceita aviso de privacidade
  W->>B: POST /api/v1/privacidade/aceite
  B-->>W: 200 ok
  W->>U: Redireciona para /jornadas (vazio)
```

### Dia Normal (marcações automáticas)

```mermaid
%%{init: {'theme': 'neutral'} }%%
sequenceDiagram
  actor U as Terceiro
  participant OS as Windows OS
  participant A as Agente WPF
  participant B as Backend API

  OS->>A: Evento login Windows
  A->>A: Calcula horario_efetivo (tolerância ±30 min)
  A->>B: POST /api/v1/marcacoes (INICIO_JORNADA)
  B-->>A: 201 Created
  A->>U: Toast "Bom dia, [nome]. Início registrado às [H]."

  Note over A: Polling inatividade (30s) detecta saída almoço
  A->>A: Inatividade ≥10 min dentro da janela almoço
  A->>B: POST /api/v1/marcacoes (SAIDA_ALMOCO)
  B-->>A: 201 Created

  Note over A: Input detectado = retorno almoço
  A->>B: POST /api/v1/marcacoes (RETORNO_ALMOCO)
  B-->>A: 201 Created

  Note over A: Horário fim jornada atingido
  A->>U: Diálogo "Encerrar jornada agora?"
  U->>A: Confirma + preenche atividade
  A->>B: POST /api/v1/marcacoes (FIM_JORNADA)
  B-->>A: 201 Created
  A->>B: POST /api/v1/atividades (descricao)
  B-->>A: 201 Created
```

### Ajuste Manual de Jornada (Web)

```mermaid
%%{init: {'theme': 'neutral'} }%%
sequenceDiagram
  actor U as Terceiro
  participant W as Web SPA
  participant B as Backend API

  U->>W: Acessa /jornadas
  W->>B: GET /api/v1/jornadas?mes=YYYY-MM
  B-->>W: 200 lista de jornadas
  W->>U: Exibe tabela mensal
  U->>W: Clica em jornada com status FECHADA
  W->>B: GET /api/v1/jornadas/:id
  B-->>W: 200 detalhe com marcações
  W->>U: Exibe 4 horários editáveis
  U->>W: Edita horário + clica Salvar
  W->>U: Modal de justificativa (mínimo 5 chars)
  U->>W: Preenche justificativa + Confirma
  W->>B: PUT /api/v1/marcacoes/:id (horario_efetivo + motivo)
  B-->>W: 200 marcação atualizada
  B->>B: Grava log_auditoria
  W->>U: Toast "Jornada atualizada com sucesso." Badge AJUSTADA_MANUALMENTE
```

### Envio de Relatório Mensal

```mermaid
%%{init: {'theme': 'neutral'} }%%
sequenceDiagram
  actor U as Terceiro
  participant W as Web SPA
  participant B as Backend API
  participant SMTP as Servidor SMTP

  U->>W: Acessa /relatorios, seleciona mês
  W->>B: GET /api/v1/relatorios/:mes
  B-->>W: 200 PDF (ou gera sob demanda)
  W->>U: Exibe prévia iframe + histórico de envios
  U->>W: Clica "Enviar por e-mail"
  W->>U: Modal de confirmação com e-mail preenchido
  U->>W: Confirma envio
  W->>B: POST /api/v1/relatorios/:mes/enviar
  B->>SMTP: SMTP send PDF attachment
  alt Envio OK
    SMTP-->>B: 250 OK
    B->>B: Grava historico_envio_relatorio (SUCESSO)
    B-->>W: 200 ok
    W->>U: Toast "Relatório enviado para [email]."
  else Falha SMTP
    SMTP-->>B: Erro conexão/autenticação
    B->>B: Grava historico_envio_relatorio (FALHA)
    B-->>W: 500 erro_mensagem
    W->>U: Alert vermelho com mensagem de erro
  end
```

---

_Criado em: 2026-06-02 18:40:00_
