using System.Net;
using Timesheet.Agent.Domain;
using Timesheet.Agent.Infra.Http;

namespace Timesheet.Agent.Tests;

internal static class TestData
{
    public static DateTimeOffset At(int h, int m, int s) =>
        new(2026, 5, 27, h, m, s, TimeSpan.FromHours(-3));

    public static MarcacaoLocal Marcacao(string id, string criadoEm, string tipo = "INICIO_JORNADA") =>
        new MarcacaoLocal
        {
            Id = id,
            Tipo = tipo,
            HorarioRegistrado = criadoEm,
            Origem = "AGENTE_AUTOMATICO",
            DataJornada = "2026-05-27",
            CriadoEm = criadoEm,
        };

    public static MarcacaoLocal SampleMarcacao(
        string idem = "11111111-1111-4111-8111-111111111111",
        string origem = "AGENTE_AUTOMATICO") =>
        new()
        {
            Id = idem,
            Tipo = MarcacaoTipo.InicioJornada,
            HorarioRegistrado = "2026-05-27T12:02:00Z",
            HorarioEfetivo = "2026-05-27T12:00:00Z",
            Origem = origem,
            DataJornada = "2026-05-27",
            CriadoEm = "2026-05-27T12:02:00Z",
        };

    public static CreateTerceiroDto SampleTerceiro() =>
        new(
            Nome: "Maria Silva",
            EmpresaNome: "ACME LTDA",
            EmpresaCnpj: "11222333000181",
            HorarioInicioJornada: "09:00:00",
            HorarioSaidaAlmoco: "12:00:00",
            HorarioRetornoAlmoco: "13:00:00",
            HorarioFimJornada: "18:00:00",
            TrabalhaFimDeSemana: false,
            EmailContato: "maria@x.com",
            EmailDestinatarioRelatorio: null,
            Senha: "Senha123",
            SenhaConfirmacao: "Senha123");

    public const string MarcacaoRespJson =
        """{"id":"aaa","jornada_id":"bbb","tipo":"INICIO_JORNADA","horario_registrado":"2026-05-27T12:02:00Z","horario_efetivo":"2026-05-27T12:00:00Z","origem":"AGENTE_AUTOMATICO","status":"PENDENTE","confirmado_pelo_usuario":false,"idempotency_key":"11111111-1111-4111-8111-111111111111","criada_em":"2026-05-27T12:02:00Z"}""";

    public static HttpResponseMessage JsonResponse(int status, string body) =>
        new((HttpStatusCode)status)
        {
            Content = new StringContent(body, System.Text.Encoding.UTF8, "application/json")
        };
}
