using System.Text.Json.Serialization;

namespace Timesheet.Agent.Infra.Http;

// ── Auth ─────────────────────────────────────────────────────────────────────

public sealed record AuthResult(
    string AccessToken,
    string RefreshToken,
    string? TerceiroId,
    int ExpiresIn);

internal sealed record LoginRequestDto(
    [property: JsonPropertyName("email")] string Email,
    [property: JsonPropertyName("senha")] string Senha);

internal sealed record RefreshRequestDto(
    [property: JsonPropertyName("refresh_token")] string RefreshToken);

// ── Terceiros ─────────────────────────────────────────────────────────────────

public sealed record CreateTerceiroDto(
    [property: JsonPropertyName("nome")] string Nome,
    [property: JsonPropertyName("empresa_nome")] string EmpresaNome,
    [property: JsonPropertyName("empresa_cnpj")] string EmpresaCnpj,
    [property: JsonPropertyName("horario_inicio_jornada")] string HorarioInicioJornada,
    [property: JsonPropertyName("horario_saida_almoco")] string HorarioSaidaAlmoco,
    [property: JsonPropertyName("horario_retorno_almoco")] string HorarioRetornoAlmoco,
    [property: JsonPropertyName("horario_fim_jornada")] string HorarioFimJornada,
    [property: JsonPropertyName("trabalha_fim_de_semana")] bool TrabalhaFimDeSemana,
    [property: JsonPropertyName("email_contato")] string EmailContato,
    [property: JsonPropertyName("email_destinatario_relatorio")] string? EmailDestinatarioRelatorio,
    [property: JsonPropertyName("senha")] string Senha,
    [property: JsonPropertyName("senha_confirmacao")] string SenhaConfirmacao);

public sealed record CreateTerceiroResult(
    [property: JsonPropertyName("terceiro_id")] string TerceiroId,
    [property: JsonPropertyName("criado_em")] string CriadoEm);

// ── Marcacoes ─────────────────────────────────────────────────────────────────

internal sealed record PostMarcacaoDto(
    [property: JsonPropertyName("tipo")] string Tipo,
    [property: JsonPropertyName("horario_registrado")] string HorarioRegistrado,
    [property: JsonPropertyName("horario_efetivo")] string? HorarioEfetivo,
    [property: JsonPropertyName("origem")] string Origem,
    [property: JsonPropertyName("idempotency_key")] string IdempotencyKey);
