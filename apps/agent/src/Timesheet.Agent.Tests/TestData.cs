using Timesheet.Agent.Domain;

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
}
