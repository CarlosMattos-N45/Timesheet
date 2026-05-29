using Microsoft.EntityFrameworkCore;
using Timesheet.Agent.Domain;

namespace Timesheet.Agent.Infra.Db;

public sealed class MarcacaoLocalRepository(AgentDbContext ctx)
{
    public async Task EnqueueAsync(MarcacaoLocal m)
    {
        ctx.MarcacoesLocais.Add(m);
        await ctx.SaveChangesAsync();
    }

    public Task<List<MarcacaoLocal>> GetPendentesOrdenadasAsync() =>
        ctx.MarcacoesLocais.Where(m => !m.Sincronizada).OrderBy(m => m.CriadoEm).ToListAsync();

    public async Task MarcarSincronizadaAsync(string id)
    {
        var m = await ctx.MarcacoesLocais.SingleAsync(x => x.Id == id);
        m.Sincronizada = true;
        await ctx.SaveChangesAsync();
    }

    public async Task RegistrarFalhaSyncAsync(string id, string erro, string proximaTentativaEm)
    {
        var m = await ctx.MarcacoesLocais.SingleAsync(x => x.Id == id);
        m.TentativasSync += 1;
        m.UltimoErroSync = erro;
        m.ProximaTentativaEm = proximaTentativaEm;
        await ctx.SaveChangesAsync();
    }

    public Task<MarcacaoLocal?> GetByIdAsync(string id) =>
        ctx.MarcacoesLocais.SingleOrDefaultAsync(m => m.Id == id);
}
