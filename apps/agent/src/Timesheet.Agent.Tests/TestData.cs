using Timesheet.Agent.Domain;

namespace Timesheet.Agent.Tests;

internal static class TestData
{
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
