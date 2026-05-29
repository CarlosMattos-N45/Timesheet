using Microsoft.EntityFrameworkCore;
using Timesheet.Agent.Domain;

namespace Timesheet.Agent.Infra.Db;

public sealed class EstadoJornadaRepository(AgentDbContext ctx)
{
    public Task<EstadoJornadaAtual?> GetAsync() =>
        ctx.EstadoJornadaAtual.FirstOrDefaultAsync();

    public async Task UpsertAsync(EstadoJornadaAtual estado)
    {
        var existing = await ctx.EstadoJornadaAtual.FindAsync(1);
        if (existing is null)
        {
            estado = new EstadoJornadaAtual
            {
                DataJornada = estado.DataJornada,
                Status = estado.Status,
                UltimoInput = estado.UltimoInput,
                AtualizadoEm = estado.AtualizadoEm,
            };
            ctx.EstadoJornadaAtual.Add(estado);
        }
        else
        {
            existing.DataJornada = estado.DataJornada;
            existing.Status = estado.Status;
            existing.UltimoInput = estado.UltimoInput;
            existing.AtualizadoEm = estado.AtualizadoEm;
        }
        await ctx.SaveChangesAsync();
    }
}
