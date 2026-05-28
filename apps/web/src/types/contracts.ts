// Auth
export interface LoginRequest { email: string; senha: string; }
export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  terceiro_id: string;
  expires_in: number;
}
export interface RefreshRequest { refresh_token: string; }
export interface RefreshResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

// Terceiro
export interface CreateTerceiroRequest {
  nome: string;
  empresa_nome: string;
  empresa_cnpj: string;
  horario_inicio_jornada: string; // "HH:MM:SS"
  horario_saida_almoco: string;
  horario_retorno_almoco: string;
  horario_fim_jornada: string;
  trabalha_fim_de_semana: boolean;
  email_contato: string;
  email_destinatario_relatorio?: string | null;
  senha: string;
  senha_confirmacao: string;
}
export interface CreateTerceiroResponse { terceiro_id: string; criado_em: string; }
export interface TerceiroResponse {
  id: string;
  nome: string;
  empresa_nome: string;
  empresa_cnpj: string;
  horario_inicio_jornada: string;
  horario_saida_almoco: string;
  horario_retorno_almoco: string;
  horario_fim_jornada: string;
  trabalha_fim_de_semana: boolean;
  email_contato: string;
  email_destinatario_relatorio: string | null;
  criado_em: string;
  atualizado_em: string;
}
export interface UpdateTerceiroRequest {
  nome: string; empresa_nome: string; empresa_cnpj: string;
  horario_inicio_jornada: string; horario_saida_almoco: string;
  horario_retorno_almoco: string; horario_fim_jornada: string;
  trabalha_fim_de_semana: boolean;
  email_contato: string;
  email_destinatario_relatorio?: string | null;
}
export interface ChangePasswordRequest { senha_atual: string; nova_senha: string; }

// Privacidade
export interface PrivacyStatus {
  accepted: boolean;
  versao_aviso: string | null;
  aceito_em: string | null;
}

// Jornadas
export type StatusJornada = "EM_ANDAMENTO" | "FECHADA" | "AJUSTADA_MANUALMENTE" | "PENDENTE";
export type TipoMarcacao = "INICIO_JORNADA" | "SAIDA_ALMOCO" | "RETORNO_ALMOCO" | "FIM_JORNADA";
export type OrigemMarcacao = "AGENTE_AUTOMATICO" | "AGENTE_CONFIRMADO" | "AJUSTE_WEB";
export type StatusMarcacao = "CONFIRMADA" | "PENDENTE" | "AJUSTADA";

export interface JornadaResumo {
  id: string;
  data: string; // "YYYY-MM-DD"
  status: StatusJornada;
  total_horas_apuradas_s: number | null;
  tem_marcacao_pendente: boolean;
  horario_inicio: string | null; // ISO UTC ou null
  horario_saida_almoco: string | null;
  horario_retorno_almoco: string | null;
  horario_fim: string | null;
}
export interface JornadasMesResponse {
  mes_referencia: string; // "YYYY-MM"
  total_horas_mes_s: number;
  jornadas: JornadaResumo[];
}
export interface MarcacaoDetalhe {
  id: string;
  tipo: TipoMarcacao;
  horario_registrado: string; // ISO UTC
  horario_efetivo: string | null;
  origem: OrigemMarcacao;
  status: StatusMarcacao;
}
export interface AtividadeDetalhe {
  id: string;
  jornada_id: string;
  descricao: string;
  registrada_em: string;
  atualizado_em: string | null;
}
export interface JustificativaDetalhe {
  id: string;
  motivo: string;
  usuario_responsavel: string;
  criada_em: string;
}
export interface JornadaDetalheResponse {
  id: string;
  data: string;
  status: StatusJornada;
  total_horas_apuradas_s: number | null;
  marcacoes: MarcacaoDetalhe[];
  atividade: AtividadeDetalhe | null;
  justificativas: JustificativaDetalhe[];
}
export interface AjusteMarcacaoItem { tipo: TipoMarcacao; horario_efetivo: string; }
export interface AjusteJornadaRequest { marcacoes: AjusteMarcacaoItem[]; motivo: string; }
export interface JornadaManualRequest {
  data: string;
  marcacoes: AjusteMarcacaoItem[];
  atividade: string;
  motivo: string;
}
export interface AtividadeRequest { descricao: string; }

// Marcacoes
export interface PostMarcacaoRequest {
  tipo: TipoMarcacao;
  horario_registrado: string;
  horario_efetivo?: string | null;
  origem: "AGENTE_AUTOMATICO" | "AGENTE_CONFIRMADO";
  idempotency_key: string;
}
export interface AjusteMarcacaoRequest { horario_efetivo: string; motivo: string; }
export interface MarcacaoResponse {
  id: string;
  jornada_id: string;
  tipo: string;
  horario_registrado: string;
  horario_efetivo: string | null;
  origem: string;
  status: string;
  confirmado_pelo_usuario: boolean;
  idempotency_key: string;
  criada_em: string;
}

// Auditoria
export interface AuditoriaItem {
  id: string;
  entidade: "Jornada" | "Marcacao" | "Terceiro" | "Atividade";
  entidade_id: string;
  autor: string;
  antes_json: string | null;
  depois_json: string;
  motivo: string | null;
  criado_em: string;
}

// SMTP
export interface SmtpConfigRequest {
  host: string;
  port: number;
  username: string;
  password: string;
  use_starttls: boolean;
  from_address: string;
}
export interface SmtpConfigResponse {
  host: string;
  port: number;
  username: string;
  use_starttls: boolean;
  from_address: string;
  atualizado_em: string;
}

// Relatórios
export interface RelatorioMesResponse {
  mes_referencia: string;
  caminho_arquivo: string;
  gerado_em: string;
  invalidado_em: string | null;
}
export interface HistoricoEnvioItem {
  id: string;
  mes_referencia: string;
  email_destinatario: string;
  status: "SUCESSO" | "FALHA";
  erro_mensagem: string | null;
  enviado_em: string;
}
export interface EnviarRelatorioRequest { email?: string | null; }
export interface EnviarResponse { status: string; historico_id: string; }

// Formato de erro padronizado
export interface ApiErrorBody {
  code: string;
  message: string;
  details: Array<{ field?: string; issue?: string }>;
}
