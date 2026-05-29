using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Timesheet.Agent.Domain;

namespace Timesheet.Agent.Infra.Db;

public static class ServiceCollectionExtensions
{
    public static IServiceCollection AddAgentInfra(this IServiceCollection services, string dbPath)
    {
        services.AddDbContext<AgentDbContext>(o => o.UseSqlite($"Data Source={dbPath}"));
        services.AddScoped<MarcacaoLocalRepository>();
        services.AddScoped<ConfiguracaoLocalRepository>();
        services.AddScoped<EstadoJornadaRepository>();
        services.AddSingleton<IClock, SystemClock>();
        return services;
    }
}
