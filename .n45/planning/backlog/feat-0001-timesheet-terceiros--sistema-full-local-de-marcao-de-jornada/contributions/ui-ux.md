---
created_at: "2026-05-27 12:03:28"
from: ui-ux
n45_version: 0.2.0
spec_id: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
---
### Telas

#### `/login` — Login

**Conteúdo:** Logo centralizado, saudação contextual (Bom dia/Boa tarde/Boa noite) acima do form, campos e-mail + senha, botão "Entrar", link "Esqueci minha senha" (desabilitado/cinza com tooltip "Disponível em breve").
**Ações disponíveis:** Entrar; nenhuma outra ação (sem cadastro — o Terceiro é criado via Agente Desktop no onboarding).
**Navegação:** Sucesso → `/privacidade` (one-time) ou `/jornadas` (demais acessos).
**Estados:**

- Loading: spinner no botão "Entrar", campos desabilitados.
- Vazio: form em branco, botão "Entrar" desabilitado até ambos os campos preenchidos.
- Erro: alert MUI inline abaixo do form — "E-mail ou senha inválidos. Verifique e tente novamente." Campos de senha limpo; foco retorna ao campo senha.

**Fricção identificada:** Link "Esqueci minha senha" desabilitado sem explicação pode confundir; adicionar tooltip "Recuperação de senha disponível em breve" resolve com um atributo.

---

#### `/privacidade` — Aviso de Privacidade (one-time)

**Conteúdo:** Cabeçalho "Aviso de Privacidade", bloco de texto scrollável (dados coletados, finalidade, retenção, base legal, contato DPO), checkbox "Li e aceito os termos de privacidade", botão "Continuar" (desabilitado até check).
**Ações disponíveis:** Aceitar e continuar. Sem opção de recusar — usuário precisa aceitar para usar o sistema (LGPD art. 7, VI — execução de contrato).
**Navegação:** Aceite → `/jornadas`.
**Estados:**

- Loading (pós-clique): botão "Continuar" com spinner, checkbox desabilitado.
- Erro: toast MUI snackbar vermelho — "Não foi possível registrar o aceite. Tente novamente."

**Observação UX:** Rota deve ser inacessível após primeiro aceite — react-router guard redireciona `/privacidade` → `/jornadas` se `privacy_acceptance` existir. Sem isso, o usuário que digitar a URL diretamente veria a tela novamente.

---

#### `/jornadas` — Lista Mensal

**Conteúdo:** Seletor de mês (MUI DatePicker, default = mês atual, máximo = mês atual), tabela MUI DataGrid com colunas: Data | Dia da Semana | Início | Saída Almoço | Retorno Almoço | Fim | Total | Status (badge colorido). Rodapé com total mensal em horas. Barra de ações: botão "Nova jornada manual", botão "Baixar PDF", botão "Enviar por e-mail".
**Ações disponíveis:** Trocar mês; clicar linha → detalhe; criar jornada manual; baixar PDF; enviar PDF por e-mail.
**Navegação:** Clique em linha → `/jornadas/:id`; "Nova jornada manual" → `/jornadas/manual`; "Baixar PDF" → download direto (FileResponse); "Enviar por e-mail" → modal de confirmação com campo e-mail preenchido com `email_destinatario_relatorio` (editável).
**Estados:**

- Loading: skeleton MUI (5 linhas) na tabela, total exibindo "—".
- Vazio: ilustração neutra + "Nenhuma jornada registrada para este mês." + botão CTA "Criar jornada manual".
- Erro: alert MUI inline "Não foi possível carregar as jornadas." + botão "Tentar novamente".
- Badge de status: `EM_ANDAMENTO` = chip cinza, `FECHADA` = chip verde, `AJUSTADA_MANUALMENTE` = chip âmbar, `PENDENTE` = chip vermelho com ícone de alerta.

**Fricção identificada:** Botões "Baixar PDF" e "Enviar por e-mail" devem ser desabilitados com tooltip "Nenhuma jornada registrada neste mês" quando o estado for vazio, evitando requisição desnecessária e confusão.

---

#### `/jornadas/:id` — Detalhe da Jornada

**Conteúdo:** Breadcrumb "Jornadas > DD/MM/YYYY", badge de status no cabeçalho, 4 campos de horário (MUI TimePicker, editáveis somente para jornadas `FECHADA` e `AJUSTADA_MANUALMENTE` — `PENDENTE` e `EM_ANDAMENTO` bloqueados), total diário recalculado em tempo real, textarea "Atividade do dia" (editável em qualquer status exceto `EM_ANDAMENTO`), seção colapsada "Histórico de auditoria" (accordion MUI), seção "Justificativas anteriores". Botão "Salvar alterações" (visível somente se algo foi editado).
**Ações disponíveis:** Editar horários; editar atividade; salvar (abre modal de justificativa); voltar via breadcrumb.
**Navegação:** Salvar com sucesso → permanece na tela (dados atualizados via TanStack Query invalidation); breadcrumb → `/jornadas`.
**Estados:**

- Loading: skeleton nos campos de horário e textarea.
- Erro ao carregar: alert + botão "Tentar novamente".
- Modal de justificativa: input obrigatório ≥ 5 chars com contador de caracteres, botões "Cancelar" / "Confirmar alterações". Confirm desabilitado até mínimo atingido.
- Sucesso ao salvar: toast "Jornada atualizada com sucesso." Badge atualiza.
- Erro ao salvar: toast vermelho com mensagem do campo `message` do erro.

**Fricção identificada:** Jornada `PENDENTE` exige que o usuário entenda por que não pode editar os horários normalmente. Adicionar banner informativo no topo — "Esta jornada possui marcações pendentes. Ajuste os horários sinalizados." — com os campos PENDENTE destacados em âmbar.

**Acessibilidade:** TimePickers devem ter `aria-label` descritivo ("Horário de início da jornada"); accordion de auditoria com `aria-expanded`; badge de status com `role="status"`.

---

#### `/jornadas/manual` — Criar Jornada Manual

**Conteúdo:** Cabeçalho "Nova Jornada Manual", MUI DatePicker para data (sem jornada existente — validação client-side consultando cache local), 4 TimePickes de horário com validação cronológica em tempo real, textarea "Atividade" (≥10 chars, contador), textarea "Justificativa" (≥5 chars, contador), botões "Cancelar" / "Salvar".
**Ações disponíveis:** Selecionar data, preencher horários, preencher atividade e justificativa, salvar, cancelar.
**Navegação:** Sucesso → `/jornadas/:id` da jornada criada (via `Location` do `201`); Cancelar → `/jornadas`.
**Estados:**

- Loading: botão "Salvar" com spinner.
- Vazio: form inicial. Botão "Salvar" desabilitado até todos os campos válidos.
- Erro de validação: campos inválidos com helper text inline (ex: "Os horários devem ser em ordem cronológica.").
- Erro 409: alert "Já existe uma jornada para este dia. Abra-a para editar." + link para `/jornadas/:id_existente`.

**Fricção identificada:** O campo de data deve desabilitar dias futuros e indicar visualmente dias que já têm jornada (dot no calendar picker do MUI), evitando que o usuário só descubra o 409 no submit.

---

#### `/cadastro` — Editar Cadastro

**Conteúdo:** Form com todos os campos do `terceiro` (nome, empresa, CNPJ, 4 horários, flag fim de semana, e-mail contato, e-mail destinatário relatório). Seção separada com botão "Alterar senha" → redireciona para `/cadastro/senha`. Botão "Salvar".
**Ações disponíveis:** Editar campos, salvar, alterar senha.
**Navegação:** Salvar → permanece com toast de sucesso; "Alterar senha" → `/cadastro/senha`.
**Estados:**

- Loading: skeleton nos campos.
- Erro de validação: CNPJ inválido com helper text "CNPJ inválido (dígito verificador incorreto)."
- Erro 4xx: alert com mensagem.
- Sucesso: toast "Cadastro atualizado com sucesso."

---

#### `/cadastro/senha` — Alterar Senha

**Conteúdo:** Campo "Senha atual", campo "Nova senha" (com indicador de força), campo "Confirmar nova senha", botão "Salvar", link "Cancelar".
**Ações disponíveis:** Salvar, cancelar.
**Navegação:** Sucesso → `/cadastro`; Cancelar → `/cadastro`.
**Estados:**

- Erro 401: alert "Senha atual incorreta." Campo "Senha atual" limpo, foco retorna a ele.
- Erro validação: senhas não coincidem — helper text inline antes do submit.
- Sucesso: toast "Senha alterada com sucesso." + redirect para `/cadastro`.

---

#### `/relatorios` — Relatórios

**Conteúdo:** Seletor de mês (máximo = mês anterior — relatório do mês corrente só ao final), iframe com prévia do PDF (ou placeholder "PDF indisponível"), histórico de envios em tabela (data, destinatário, status, erro), botão "Baixar PDF", botão "Enviar agora", botão "Configurar SMTP".
**Ações disponíveis:** Selecionar mês, baixar PDF, enviar, configurar SMTP.
**Navegação:** "Configurar SMTP" → `/configuracoes/smtp`.
**Estados:**

- Loading: skeleton no iframe.
- Vazio (mês sem dados): "Nenhuma jornada registrada para este mês. Não é possível gerar o relatório."
- PDF invalidado (jornada editada depois da geração): badge âmbar "PDF desatualizado — clique em 'Atualizar relatório' para regenerar." Botão extra "Atualizar relatório" chama `GET /relatorios/{mes}` que aciona regeneração.
- Erro envio SMTP: alerta vermelho no topo — "Último envio falhou: [erro_mensagem]. Verifique as configurações SMTP." + link para `/configuracoes/smtp`.
- Sucesso envio: toast "Relatório enviado para [email]."

**Fricção identificada:** Usuário que nunca configurou SMTP e clica "Enviar agora" deve ver modal de alerta com CTA "Configurar SMTP agora" em vez de mensagem de erro crua.

---

#### `/configuracoes/smtp` — Configuração SMTP

**Conteúdo:** Campos host, porta (default 587), usuário, senha (masked), toggle STARTTLS, from_address, botão "Testar conexão", botão "Salvar".
**Ações disponíveis:** Preencher/editar configuração, testar conexão, salvar.
**Navegação:** Salvar → permanece com toast; Cancelar → `/relatorios`.
**Estados:**

- Loading (teste/salvar): botão com spinner.
- Sucesso teste: toast "Conexão SMTP testada com sucesso."
- Erro teste: alert inline com mensagem do servidor ("Conexão recusada", "Autenticação falhou").
- Sucesso salvar: toast "Configuração SMTP salva."

---

#### Agente Desktop — Cadastro Inicial (WPF Wizard)

**Conteúdo:** Wizard 3 passos com barra de progresso visual:
- Passo 1: Nome completo, nome da empresa, CNPJ (com máscara e validação de dígitos em tempo real).
- Passo 2: 4 TimePickes de horários (validação cronológica em tempo real), toggle "Trabalha nos fins de semana".
- Passo 3: E-mail de contato, senha (≥8 chars, força visual), confirmar senha, e-mail destinatário do relatório (opcional).

**Ações disponíveis:** Avançar (desabilitado até passo válido), Voltar, Finalizar (passo 3, desabilitado até válido).
**Navegação:** Finalizar → fecha modal wizard → tray ativo → abre browser em `http://127.0.0.1:8765`.
**Estados:**

- Validação inline por campo (não apenas no submit).
- "Avançar" desabilitado até todos os campos do passo atual passarem na validação.
- Passo 3: erro 409 (e-mail já cadastrado) → alert no passo 3 "Este e-mail já está em uso."

---

#### Agente Desktop — Diálogos Modais (WPF)

**Diálogo antecipação:** Título "Início fora do horário previsto", corpo "Você iniciou às [T]. Seu horário cadastrado é [H_INI]. Deseja registrar [T]?", botões "Sim, registrar [T]" / "Não, usar [H_INI]". Timeout visual (progress bar) em 60s → comportamento padrão = NÃO.

**Diálogo retorno fora de janela:** Título "Retorno detectado fora da janela", corpo "Detectamos atividade às [T]. Deseja confirmar este horário como retorno do almoço?", botões "Confirmar [T]" / "Marcar como pendente". Timeout = 60s → PENDENTE.

**Diálogo fim de jornada:** Título "Encerrar jornada", corpo "São [H_FIM]. Deseja encerrar sua jornada agora?", botões "Sim, encerrar" / "Lembrar em 30 min". Ao clicar "Sim" → form de atividade como passo 2 do mesmo diálogo.

**Form de atividade:** Título "O que você fez hoje?", textarea com contador (mínimo 10 chars), botões "Salvar e encerrar" (desabilitado < 10 chars) / "Cancelar" (volta ao diálogo de fim).

**Toast saudação:** Notificação nativa do Windows (balloon tip ou toast moderno se Win 10 1903+), auto-fechamento 10s, sem interação necessária.

---

### Fluxos de Usuário

**Onboarding completo:** Instalar MSI → login Windows → Wizard Cadastro (3 passos com validação inline) → Finalizar → tray ativo → browser abre em `/login` → login com e-mail/senha cadastrados → `/privacidade` (aceitar) → `/jornadas` (vazio com CTA "Criar jornada manual").

Desvio: CNPJ inválido no passo 1 → campo sinalizado em vermelho, botão "Avançar" bloqueado → usuário corrige.

**Dia normal:** Login Windows → toast "Bom dia, [Nome]" 10s → trabalho → almoço silencioso (SAIDA_ALMOCO + RETORNO_ALMOCO automáticos, sem interrupção) → 18:00 diálogo "Encerrar?" → SIM → textarea atividade → "Salvar e encerrar" → tray mostra status ativo.

**Ajuste manual via Web:** `/jornadas` → linha 25/05 com badge PENDENTE → clique → detalhe com banner âmbar → edita campo FIM de 18:02 para 18:00 → botão "Salvar alterações" aparece → clique → modal justificativa → digita ≥5 chars → "Confirmar alterações" → toast sucesso → badge vira AJUSTADA_MANUALMENTE → accordion auditoria mostra 1 entrada.

Desvio: justificativa < 5 chars → botão "Confirmar alterações" permanece desabilitado.

**Geração e envio de relatório:** Usuário acessa `/relatorios` → seleciona mês anterior → iframe carrega PDF → clica "Enviar agora" → modal confirma e-mail (preenchido com `email_destinatario_relatorio`) → "Enviar" → toast "Relatório enviado para [email]." → tabela histórico ganha nova linha verde SUCESSO.

Desvio SMTP não configurado: clica "Enviar agora" → modal de alerta "Servidor SMTP não configurado." com CTA "Configurar agora" → `/configuracoes/smtp`.

**Offline e re-sync:** Backend crashou → tray mostra badge vermelho com contador → marcações continuam sendo registradas localmente → backend sobe → próxima passada 30s → badge zera → toast discreta "X marcações sincronizadas."

---

### Para tasks

- `844dd534f4` (Frontend executor):
  - Implementar guard de rota `/privacidade` que redireciona para `/jornadas` se `privacy_acceptance` existir; e guarda oposta para rotas autenticadas redireciona para `/privacidade` se aceite pendente.
  - Na tela `/jornadas`, desabilitar botões "Baixar PDF" e "Enviar por e-mail" com tooltip quando estado for vazio.
  - Na tela `/jornadas/manual`, usar DatePicker com `shouldDisableDate` para destacar/desabilitar dias futuros e dias com jornada existente.
  - Na tela `/jornadas/:id`, exibir banner âmbar explicativo para jornadas `PENDENTE` com campos sinalizados individualmente.
  - Na tela `/relatorios`, exibir badge "PDF desatualizado" quando `relatorio_gerado.invalidado_em` estiver preenchido, com botão "Atualizar relatório".
  - Na tela `/relatorios`, ao clicar "Enviar agora" sem SMTP configurado, exibir modal com CTA para `/configuracoes/smtp` em vez de erro crú.
  - Todos os TimePickers com `aria-label` descritivo; badges de status com `role="status"`; accordion de auditoria com `aria-expanded`.
  - Timeout visual (progress bar) nos diálogos WPF de confirmação (60s → ação padrão).

- `50a8844c7d` (Backend executor):
  - `GET /api/v1/relatorios/{mes}` deve indicar no response se o PDF está invalidado (`invalidado_em` não nulo) para o frontend exibir o badge.
  - `POST /api/v1/relatorios/{mes}/enviar` deve retornar `422` com `code="SMTP_NOT_CONFIGURED"` quando `smtp_config` ausente, permitindo distinção no frontend.
  - `GET /api/v1/jornadas` deve incluir flag por linha se alguma marcação do dia tem `status=PENDENTE`, para badge na lista sem necessidade de carregar detalhe.

---

### Conflitos com outras áreas

⚠ Conflito de contrato com backend: `GET /api/v1/jornadas` não inclui flag de marcações PENDENTE por linha na Spec atual. Sem isso o frontend precisa carregar o detalhe de cada jornada para saber se deve exibir badge vermelho, o que inviabiliza a lista mensal com boa UX. Recomendo adicionar campo `tem_marcacao_pendente: bool` no `JornadaResumo`.

⚠ Conflito de contrato com backend: endpoint `POST /api/v1/relatorios/{mes}/enviar` retorna `202` mas não especifica código de erro para SMTP ausente. Sem código distinto (`SMTP_NOT_CONFIGURED`), o frontend não pode diferenciar falha de config de falha de envio para exibir o modal correto.

⚠ Conflito de fluxo no Agente: diálogos modais WPF não especificam timeout nem ação padrão ao expirar. Em RF-006, re-prompt a cada 30 min mas sem timeout no diálogo em si. Recomendo timeout de 60s com ação padrão "NÃO / Lembrar em 30 min" para não bloquear o workflow do usuário indefinidamente.
