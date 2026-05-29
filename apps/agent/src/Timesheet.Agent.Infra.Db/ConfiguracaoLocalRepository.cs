using Microsoft.EntityFrameworkCore;
using Timesheet.Agent.Domain;

namespace Timesheet.Agent.Infra.Db;

public sealed class ConfiguracaoLocalRepository(AgentDbContext ctx)
{
    public Task<ConfiguracaoLocal?> GetAsync() =>
        ctx.ConfiguracaoLocal.FirstOrDefaultAsync();

    public async Task UpsertAsync(ConfiguracaoLocal cfg)
    {
        var existing = await ctx.ConfiguracaoLocal.FindAsync(1);
        if (existing is null)
        {
            cfg = new ConfiguracaoLocal
            {
                BackendBaseUrl = cfg.BackendBaseUrl,
                UltimaSincronizacaoEm = cfg.UltimaSincronizacaoEm,
                JwtAccessToken = cfg.JwtAccessToken,
                JwtRefreshToken = cfg.JwtRefreshToken,
                ExpiraEm = cfg.ExpiraEm,
            };
            ctx.ConfiguracaoLocal.Add(cfg);
        }
        else
        {
            existing.BackendBaseUrl = cfg.BackendBaseUrl;
            existing.UltimaSincronizacaoEm = cfg.UltimaSincronizacaoEm;
            existing.JwtAccessToken = cfg.JwtAccessToken;
            existing.JwtRefreshToken = cfg.JwtRefreshToken;
            existing.ExpiraEm = cfg.ExpiraEm;
        }
        await ctx.SaveChangesAsync();
    }
}
