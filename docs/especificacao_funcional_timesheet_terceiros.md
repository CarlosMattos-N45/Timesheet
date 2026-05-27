# ESPECIFICAÇÃO FUNCIONAL — APLICATIVO DE MARCAÇÃO DE HORÁRIOS DE TERCEIROS

| Campo | Valor |
|---|---|
| **Nome do Projeto** | TimeSheet Terceiros |
| **Versão do Documento** | 1.0 |
| **Tipo** | Especificação Funcional (Functional Requirements Specification) |
| **Audiência** | Plataforma de IA para geração de especificação técnica e código |
| **Idioma do Sistema** | Português (pt-BR) |
| **Fuso Horário** | America/Sao_Paulo (UTC-3) |

---

## 1. OBJETIVO E ESCOPO

### 1.1. Objetivo
Especificar de forma inequívoca o comportamento de um sistema híbrido (agente desktop + aplicação web + backend) destinado ao registro automatizado e manual de jornadas de trabalho de profissionais terceirizados, incluindo controle de início de jornada, intervalo de almoço, fim de jornada, registro de atividades, ajustes manuais e geração de relatórios mensais em PDF com envio por e-mail.

### 1.2. Escopo
- **Em escopo**: agente desktop com inicialização automática junto ao sistema operacional; detecção de eventos de atividade/inatividade do usuário; cadastro inicial do terceiro; persistência local e sincronização remota das marcações; portal web para consulta e ajuste; geração de relatório PDF mensal; envio de relatório por e-mail.
- **Fora de escopo**: integração com sistemas de RH ou ERP externos; folha de pagamento; controle biométrico; geolocalização; integração com ponto eletrônico físico; aplicativo mobile.

### 1.3. Plataformas-Alvo
- **Agente Desktop**: Windows 10/11 (prioritário). Recomenda-se arquitetura desacoplada para permitir futura portabilidade a macOS e Linux.
- **Aplicação Web**: navegadores modernos (Chromium, Firefox, Edge) em versões com suporte ativo.
- **Backend**: API REST/HTTPS hospedável em ambiente cloud.

---

## 2. GLOSSÁRIO

| Termo | Definição |
|---|---|
| **Terceiro** | Profissional autônomo ou colaborador de empresa prestadora de serviços cuja jornada é controlada pelo sistema. |
| **Empresa Contratante** | Pessoa jurídica destinatária do relatório mensal de horas. |
| **Empresa do Terceiro** | Pessoa jurídica à qual o Terceiro está vinculado contratualmente. |
| **Agente Desktop** | Serviço de software que executa em background na máquina do Terceiro. |
| **Jornada** | Conjunto de marcações pertencentes a um único dia de trabalho. |
| **Marcação** | Evento timestamped de um dos tipos: `INICIO_JORNADA`, `SAIDA_ALMOCO`, `RETORNO_ALMOCO`, `FIM_JORNADA`. |
| **Janela de Tolerância** | Intervalo simétrico de ±30 minutos em torno de um horário cadastrado. |
| **Inatividade** | Ausência de eventos de input (teclado/mouse) detectados pelo sistema operacional. |
| **Dia Fechado** | Dia cuja jornada já possui evento `FIM_JORNADA` registrado. |

---

## 3. ATORES DO SISTEMA

| Ator | Descrição |
|---|---|
| **Terceiro** | Usuário primário; interage com o Agente Desktop e com a Aplicação Web. |
| **Agente Desktop** | Ator não-humano; emite eventos automatizados de marcação. |
| **Scheduler do Backend** | Ator não-humano; dispara a geração mensal do relatório. |
| **Sistema Operacional** | Provedor de eventos de boot, atividade do usuário e gerenciamento de serviços. |

---

## 4. ARQUITETURA LÓGICA (Visão de Componentes)

O sistema é composto por **quatro módulos** desacoplados que se comunicam por API REST sobre HTTPS:

1. **Módulo Agente Desktop (`agent`)**
   - Serviço em background com inicialização automática (autostart) junto ao SO.
   - Responsável por: exibir saudação; capturar eventos de boot, atividade e inatividade; aplicar regras de tolerância; emitir notificações ao Terceiro; persistir marcações localmente em armazenamento offline-first; sincronizar com o backend.
2. **Módulo Backend / API (`api`)**
   - Expõe endpoints REST autenticados (JWT ou equivalente).
   - Gerencia entidades, regras de negócio servidoras, persistência relacional e agendamento de relatórios.
3. **Módulo Web (`web`)**
   - SPA (Single Page Application) para consulta, edição e justificativa de marcações; download e envio do relatório.
4. **Módulo Relatório (`report-service`)**
   - Gera PDF a partir dos dados consolidados; envia por SMTP configurável.

### 4.1. Modo de Sincronização
- O Agente Desktop deve operar **offline-first**: persistir todos os eventos localmente (SQLite ou equivalente) e enfileirar sincronizações ao backend.
- Em caso de falha de rede, o Agente continua funcional; sincroniza quando a conectividade for restabelecida.
- Estratégia de resolução de conflito: **last-write-wins** baseado em timestamp do evento, com prioridade para eventos originados no Agente sobre ajustes web não confirmados.

---

## 5. MODELO DE DADOS

### 5.1. Entidade `Terceiro`
| Campo | Tipo | Restrição |
|---|---|---|
| `id` | UUID | PK, gerado pelo sistema |
| `nome` | string(120) | obrigatório, não vazio |
| `empresa_nome` | string(150) | obrigatório |
| `empresa_cnpj` | string(14) | obrigatório, validar dígitos verificadores |
| `horario_inicio_jornada` | time | obrigatório, formato HH:MM |
| `horario_saida_almoco` | time | obrigatório |
| `horario_retorno_almoco` | time | obrigatório, > `horario_saida_almoco` |
| `horario_fim_jornada` | time | obrigatório, > `horario_retorno_almoco` |
| `trabalha_fim_de_semana` | boolean | obrigatório, default `false` |
| `email_contato` | string(150) | opcional, validação RFC 5322 |
| `criado_em` | timestamp | gerado |
| `atualizado_em` | timestamp | gerado |

### 5.2. Entidade `Jornada`
| Campo | Tipo | Restrição |
|---|---|---|
| `id` | UUID | PK |
| `terceiro_id` | UUID | FK → Terceiro |
| `data` | date | obrigatório, unique (`terceiro_id`, `data`) |
| `status` | enum | `EM_ANDAMENTO`, `FECHADA`, `AJUSTADA_MANUALMENTE` |
| `total_horas_apuradas` | duration | calculado |
| `criada_em` | timestamp | |
| `fechada_em` | timestamp | nullable |

### 5.3. Entidade `Marcacao`
| Campo | Tipo | Restrição |
|---|---|---|
| `id` | UUID | PK |
| `jornada_id` | UUID | FK → Jornada |
| `tipo` | enum | `INICIO_JORNADA`, `SAIDA_ALMOCO`, `RETORNO_ALMOCO`, `FIM_JORNADA` |
| `horario_registrado` | timestamp | obrigatório |
| `horario_efetivo` | timestamp | aplicado após regras de tolerância e confirmação |
| `origem` | enum | `AGENTE_AUTOMATICO`, `AGENTE_CONFIRMADO`, `AJUSTE_WEB` |
| `confirmado_pelo_usuario` | boolean | default `false` |

### 5.4. Entidade `Atividade`
| Campo | Tipo | Restrição |
|---|---|---|
| `id` | UUID | PK |
| `jornada_id` | UUID | FK → Jornada |
| `descricao` | text | obrigatório, mínimo 10 caracteres |
| `registrada_em` | timestamp | |

### 5.5. Entidade `Justificativa`
| Campo | Tipo | Restrição |
|---|---|---|
| `id` | UUID | PK |
| `jornada_id` | UUID | FK → Jornada |
| `motivo` | text | obrigatório quando há ajuste em dia fechado ou dia sem eventos |
| `usuario_responsavel` | string(120) | identificação do autor do ajuste |
| `criada_em` | timestamp | |

### 5.6. Entidade `ConfiguracaoEmail`
| Campo | Tipo | Restrição |
|---|---|---|
| `email_destinatario` | string(150) | validação RFC 5322 |
| `ultimo_envio` | timestamp | nullable |

---

## 6. REQUISITOS FUNCIONAIS

### RF-001 — Inicialização Automática do Agente Desktop
- **Descrição**: O Agente Desktop deve registrar-se como serviço/processo de inicialização automática do SO (Windows Service ou entrada de Startup).
- **Critério**: ao ligar o computador, o agente é executado sem intervenção do usuário.
- **Exibição**: imediatamente após inicialização bem-sucedida, exibir notificação visual de saudação contendo o texto exato: **"Bom dia! Tenha um ótimo dia de trabalho"**.
- **Modo de exibição**: notificação nativa do SO (toast) e/ou janela modal não-bloqueante, com fechamento automático após 10 segundos ou por ação do usuário.

### RF-002 — Cadastro Inicial do Terceiro (Onboarding)
- **Gatilho**: primeira execução do Agente Desktop em uma máquina sem cadastro persistido.
- **Bloqueio**: o serviço de marcação não opera enquanto o cadastro não estiver completo.
- **Campos obrigatórios** (vide Seção 5.1):
  1. Nome do Terceiro
  2. Nome da Empresa do Terceiro
  3. CNPJ da Empresa do Terceiro (validar formato e dígitos verificadores)
  4. Horário de início de jornada (HH:MM)
  5. Horário de saída para almoço (HH:MM)
  6. Horário de retorno do almoço (HH:MM)
  7. Horário de fim de jornada (HH:MM)
  8. Flag booleana: "Trabalha aos finais de semana?"
- **Validações**:
  - Os quatro horários devem respeitar ordem cronológica: `inicio < saida_almoco < retorno_almoco < fim_jornada`.
  - CNPJ deve passar pelo algoritmo de validação de dígitos.
- **Persistência**: armazenar local e remotamente; após cadastro o Agente entra em modo operacional.

### RF-003 — Registro de Início de Jornada
- **Gatilho**: detecção do evento de boot/login do SO.
- **Captura**: timestamp do momento em que o computador foi ligado e/ou usuário logou-se.
- **Regra de tolerância** (vide RN-001):
  - Seja `T` o timestamp capturado e `H` o horário cadastrado de início.
  - Se `|T - H| ≤ 30 minutos`: registrar `T` como `horario_efetivo` sem interação.
  - Se `T - H > 30 minutos` (atraso): emitir **alerta informativo** indicando a diferença em minutos; registrar `T` como `horario_efetivo`.
  - Se `H - T > 30 minutos` (antecipação): emitir **diálogo de confirmação** com texto que informe a diferença e pergunte se o Terceiro deseja iniciar a jornada antecipadamente.
    - **Resposta SIM**: registrar `T` como `horario_efetivo`.
    - **Resposta NÃO**: registrar `H` (horário cadastrado) como `horario_efetivo`.
- **Considerações sobre finais de semana**: se o dia atual for sábado/domingo e `trabalha_fim_de_semana = false`, o Agente não deve registrar jornada automática; pode apenas exibir a saudação.

### RF-004 — Registro de Saída para Almoço
- **Detecção**: o Agente monitora eventos de input do SO (teclado e mouse). Ao detectar **inatividade contínua ≥ 10 minutos**, avalia se o instante de **início da inatividade** está dentro da janela `[horario_saida_almoco - 30min, horario_saida_almoco + 30min]`.
- **Se dentro da janela**: registrar evento `SAIDA_ALMOCO` com `horario_efetivo` = instante de início da inatividade. Não solicitar confirmação ao Terceiro neste momento.
- **Se fora da janela**: a inatividade não é interpretada como almoço; o sistema mantém o estado anterior.
- **Idempotência**: somente uma `SAIDA_ALMOCO` por jornada.

### RF-005 — Registro de Retorno do Almoço
- **Gatilho**: detecção de retorno à atividade (primeiro input de teclado/mouse) após uma `SAIDA_ALMOCO` registrada na mesma jornada.
- **Captura**: timestamp `R` do primeiro input pós-almoço.
- **Regra de tolerância**:
  - Se `R` está dentro de `[horario_retorno_almoco - 30min, horario_retorno_almoco + 30min]`: registrar `R` como `horario_efetivo`.
  - Se `R` está fora desta janela: exibir **mensagem informativa** + **diálogo de confirmação** apresentando o horário detectado e a divergência.
    - **Resposta SIM**: confirma e registra `R`.
    - **Resposta NÃO**: o registro deve ser tratado como pendente de ajuste manual via portal web (não registrar até que haja ajuste); o sistema pode solicitar uma nova entrada de horário pelo Terceiro ou deixar a marcação em estado `PENDENTE`.

### RF-006 — Registro de Fim de Jornada
- **Gatilho temporal**: o Agente avalia continuamente o relógio do sistema; quando o horário atual atingir o `horario_fim_jornada` cadastrado, dispara o fluxo.
- **Fluxo**:
  1. Exibir **diálogo modal de confirmação** com texto solicitando que o Terceiro confirme o encerramento da jornada.
  2. Se **CONFIRMADO**: prosseguir ao passo 3.
  3. Se **NEGADO**: reagendar nova exibição do diálogo **a cada 30 minutos** até obter confirmação positiva, persistindo indefinidamente (limite máximo recomendado: 23:59 do dia corrente; após esse limite, encerrar automaticamente registrando o último timestamp conhecido de atividade).
  4. Após confirmação, exibir formulário de **registro de atividades do dia** (campo texto multi-linha, obrigatório, mínimo 10 caracteres) — este é **pré-requisito bloqueante** para o registro do `FIM_JORNADA`.
  5. Persistir a `Atividade` vinculada à jornada e registrar o evento `FIM_JORNADA` com `horario_efetivo` = timestamp do momento da confirmação positiva.
  6. Marcar `Jornada.status = FECHADA`.

### RF-007 — Aplicação Web de Acompanhamento e Ajustes
A aplicação web deve oferecer as seguintes capacidades:

- **RF-007.1 — Listagem de Jornadas**: visualização tabular por mês, com colunas: data, dia da semana, início, saída almoço, retorno almoço, fim, total de horas, status.
- **RF-007.2 — Edição de Jornada Fechada**: permitir ajustar individualmente cada um dos quatro horários de uma jornada com status `FECHADA`. A edição requer salvar uma `Justificativa` (campo texto obrigatório). Após salvar, `Jornada.status` passa a `AJUSTADA_MANUALMENTE`.
- **RF-007.3 — Inserção de Jornada para Dia Sem Eventos**: para datas em que não existe `Jornada` registrada (computador não ligado ou agente inoperante), permitir criar manualmente uma jornada completa. Campos obrigatórios:
  - Os quatro horários da jornada.
  - `Justificativa` (texto, obrigatório).
  - `Atividade` do dia (texto, obrigatório, mínimo 10 caracteres).
- **RF-007.4 — Visualização de Atividades**: exibir, por dia, as atividades registradas.
- **RF-007.5 — Tela de Cadastro do Terceiro**: permitir edição dos dados cadastrais (Seção 5.1), com propagação de alterações ao Agente Desktop na próxima sincronização.
- **RF-007.6 — Tela de Relatório Mensal**: ver RF-008.

### RF-008 — Geração e Envio de Relatório Mensal em PDF
- **Geração automática**: agendamento no backend para gerar o PDF no último dia de cada mês, à meia-noite (00:00 do primeiro dia do mês seguinte, no fuso `America/Sao_Paulo`).
- **Geração sob demanda**: a aplicação web deve oferecer botão "Gerar Relatório" disponível a qualquer momento, gerando o PDF do mês selecionado.
- **Conteúdo obrigatório do PDF**:
  1. **Cabeçalho com dados cadastrais**: Nome do Terceiro, Nome da Empresa do Terceiro, CNPJ, mês/ano de referência.
  2. **Tabela diária** contendo, para cada dia do mês:
     - Data
     - Dia da semana
     - Horário de início de jornada
     - Horário de saída para almoço
     - Horário de retorno do almoço
     - Horário de fim de jornada
     - Total de horas trabalhadas no dia (calculado conforme RN-005)
     - Indicador visual ou textual quando a jornada foi ajustada manualmente
  3. **Total de horas apuradas no mês** (somatório de todos os totais diários).
  4. **Listagem das atividades** registradas por dia (pode ser anexo do PDF ou seção complementar).
- **Envio por e-mail**:
  - A interface web deve possuir botão **"Enviar por E-mail"**.
  - Ao acionar: solicitar (ou exibir para confirmação) o e-mail de destino.
  - Validar o e-mail conforme RFC 5322 antes do envio.
  - O backend executa o envio via SMTP autenticado, com o PDF como anexo.
  - Registrar histórico de envios (data, e-mail, status).

---

## 7. REGRAS DE NEGÓCIO

| ID | Regra |
|---|---|
| **RN-001** | A janela de tolerância para qualquer marcação é simétrica de **±30 minutos** em torno do horário cadastrado correspondente. |
| **RN-002** | O critério de detecção de saída para almoço é **inatividade contínua de no mínimo 10 minutos**, cujo instante de início deve cair na janela de tolerância da `SAIDA_ALMOCO`. |
| **RN-003** | Em caso de início antecipado fora da tolerância, o Terceiro deve confirmar explicitamente o início; se recusar, o `horario_efetivo` é o horário cadastrado de início. |
| **RN-004** | O `FIM_JORNADA` só pode ser registrado após o Terceiro informar as atividades do dia (mínimo 10 caracteres). |
| **RN-005** | O total de horas diárias é calculado como: `(SAIDA_ALMOCO - INICIO_JORNADA) + (FIM_JORNADA - RETORNO_ALMOCO)`. |
| **RN-006** | Ajustes em jornadas fechadas ou criação de jornadas para dias sem eventos exigem `Justificativa` textual obrigatória. |
| **RN-007** | Se `trabalha_fim_de_semana = false`, o Agente não cria automaticamente `Jornada` aos sábados e domingos. |
| **RN-008** | O diálogo de confirmação de fim de jornada repete-se a cada 30 minutos enquanto não houver resposta positiva, até as 23:59 do dia. |
| **RN-009** | CNPJ deve ser validado pelo algoritmo oficial de dígitos verificadores. |
| **RN-010** | E-mails devem ser validados conforme RFC 5322 antes de qualquer operação de envio. |
| **RN-011** | A unicidade de uma `Jornada` é dada pela tupla (`terceiro_id`, `data`). |
| **RN-012** | Conflitos de sincronização são resolvidos pela política **last-write-wins** baseada em `horario_efetivo`, com prioridade ao Agente para marcações originalmente automatizadas. |

---

## 8. REQUISITOS NÃO-FUNCIONAIS

| ID | Categoria | Requisito |
|---|---|---|
| **RNF-001** | Disponibilidade | O Agente Desktop deve operar offline; sincronização é eventual. |
| **RNF-002** | Performance | Detecção de inatividade com latência ≤ 5 segundos após o limite de 10 minutos. |
| **RNF-003** | Segurança | Comunicação Agente ↔ Backend somente sobre TLS 1.2+. Autenticação por token JWT renovável. |
| **RNF-004** | Persistência local | Banco local criptografado (ex.: SQLCipher) para proteger dados sensíveis. |
| **RNF-005** | Usabilidade | Notificações em português; diálogos modais devem ser não-bloqueantes ao SO (não impedir uso normal). |
| **RNF-006** | Acessibilidade | A aplicação web deve atender WCAG 2.1 nível AA. |
| **RNF-007** | Internacionalização | Fuso horário fixado em `America/Sao_Paulo` na versão 1.0; arquitetura deve permitir extensão futura. |
| **RNF-008** | Auditoria | Todo ajuste manual deve gerar registro imutável de auditoria (autor, antes, depois, motivo, timestamp). |
| **RNF-009** | Logging | Agente Desktop deve manter logs locais rotativos para diagnóstico. |
| **RNF-010** | Compatibilidade | Agente compatível com Windows 10 build 1809+ e Windows 11. |

---

## 9. FLUXOS PRINCIPAIS (Diagramas de Estado Textuais)

### 9.1. Máquina de Estados da Jornada
```
[NAO_INICIADA]
     │ (boot do SO detectado / dia útil)
     ▼
[INICIO_PENDENTE]
     │ (regra RF-003 aplicada → confirmação se necessário)
     ▼
[EM_ANDAMENTO_PRE_ALMOCO]
     │ (inatividade ≥ 10min dentro da janela de almoço)
     ▼
[EM_ALMOCO]
     │ (input detectado após SAIDA_ALMOCO)
     ▼
[EM_ANDAMENTO_POS_ALMOCO]
     │ (relógio atinge horario_fim_jornada → diálogo de confirmação)
     ▼
[AGUARDANDO_CONFIRMACAO_FIM]  ←──── (re-prompt a cada 30min se negado)
     │ (confirmação positiva + atividades informadas)
     ▼
[FECHADA]
     │ (ajuste via web)
     ▼
[AJUSTADA_MANUALMENTE]
```

### 9.2. Fluxo de Inicialização do Agente
1. SO inicializa → executa o Agente (autostart).
2. Agente verifica existência de cadastro local.
3. Sem cadastro → exibe formulário de onboarding (RF-002), bloqueia operação até conclusão.
4. Com cadastro → exibe saudação (RF-001) e entra em modo monitoramento.
5. Avalia data atual vs. flag `trabalha_fim_de_semana`.
6. Dispara fluxo RF-003 (registro de início de jornada).

---

## 10. CONTRATO DE API (Sugestão para Especificação Técnica)

A plataforma técnica deverá implementar, no mínimo, os seguintes endpoints:

| Método | Rota | Finalidade |
|---|---|---|
| `POST` | `/api/v1/auth/login` | Autenticação do Agente/Web |
| `POST` | `/api/v1/terceiros` | Cadastro inicial |
| `GET` / `PUT` | `/api/v1/terceiros/{id}` | Consulta / atualização cadastral |
| `POST` | `/api/v1/marcacoes` | Envio de marcação pelo Agente |
| `GET` | `/api/v1/jornadas?mes=YYYY-MM` | Listagem mensal |
| `PUT` | `/api/v1/jornadas/{id}` | Ajuste manual com justificativa |
| `POST` | `/api/v1/jornadas/manual` | Criação manual para dia sem eventos |
| `POST` | `/api/v1/atividades` | Registro de atividades do dia |
| `GET` | `/api/v1/relatorios/{mes}` | Download do PDF |
| `POST` | `/api/v1/relatorios/{mes}/enviar` | Envio do PDF por e-mail (payload: `{ "email": "..." }`) |

---

## 11. CRITÉRIOS DE ACEITAÇÃO

| ID | Critério |
|---|---|
| **CA-001** | Ao primeiro boot pós-instalação, o Agente exibe o formulário de cadastro e não inicia monitoramento até a conclusão. |
| **CA-002** | A saudação "Bom dia! Tenha um ótimo dia de trabalho" aparece em todos os boots subsequentes em dias úteis. |
| **CA-003** | Início antecipado de 45 minutos gera diálogo de confirmação; resposta NÃO grava `horario_efetivo` igual ao cadastrado. |
| **CA-004** | Inatividade de 10 minutos iniciada às 11:55 (cadastro de almoço 12:00) registra `SAIDA_ALMOCO`. |
| **CA-005** | Retorno do almoço 45 minutos atrasado em relação ao cadastro dispara diálogo de confirmação. |
| **CA-006** | No horário cadastrado de fim, diálogo é exibido; resposta NÃO faz com que novo diálogo apareça exatamente 30 min depois. |
| **CA-007** | `FIM_JORNADA` não é gravado sem texto de atividades (≥ 10 caracteres). |
| **CA-008** | Ajuste de jornada fechada sem justificativa é rejeitado pela API com HTTP 400. |
| **CA-009** | PDF mensal contém todos os dias do mês, totais diários, total mensal e atividades. |
| **CA-010** | Envio de e-mail com endereço inválido é bloqueado antes da chamada SMTP. |
| **CA-011** | Em sábado/domingo, se `trabalha_fim_de_semana = false`, nenhuma jornada automática é criada. |
| **CA-012** | Marcações geradas offline são sincronizadas com sucesso após reconexão. |

---

## 12. PREMISSAS E RESTRIÇÕES

### 12.1. Premissas
- O Terceiro permanece logado em uma única sessão do SO durante o dia.
- O relógio do sistema operacional do Terceiro está corretamente sincronizado (NTP).
- O backend está acessível pela internet pública via HTTPS.

### 12.2. Restrições
- O Agente Desktop não deve consumir mais de 100 MB de memória em estado idle.
- O Agente não deve interferir em janelas de outros aplicativos em primeiro plano (notificações não devem ser modais bloqueantes do SO).
- A persistência local deve ser criptografada para conformidade com LGPD.

---

## 13. CONSIDERAÇÕES DE CONFORMIDADE (LGPD)

- Dados pessoais (Nome, CNPJ, e-mail, jornada) são tratados sob a base legal de **execução de contrato** entre Terceiro e Empresa Contratante.
- O Terceiro deve receber, no primeiro acesso, um aviso de privacidade descrevendo o tratamento dos dados.
- O sistema deve oferecer mecanismo de exportação e exclusão de dados mediante solicitação.

---

## 14. ENTREGÁVEIS ESPERADOS DA PLATAFORMA DE IA

A partir desta especificação funcional, espera-se que a plataforma de IA produza:

1. Especificação técnica detalhada (escolha de stack, modelagem física do banco, contratos OpenAPI, arquitetura de deploy).
2. Código-fonte dos quatro módulos descritos na Seção 4.
3. Scripts de instalação do Agente Desktop (instalador MSI/EXE para Windows).
4. Testes automatizados cobrindo, no mínimo, todos os Critérios de Aceitação da Seção 11.
5. Documentação de instalação, configuração e operação.

---

**FIM DA ESPECIFICAÇÃO FUNCIONAL**
