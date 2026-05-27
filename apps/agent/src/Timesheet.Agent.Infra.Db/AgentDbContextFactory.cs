using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;

namespace Timesheet.Agent.Infra.Db;

public sealed class AgentDbContextFactory : IDesignTimeDbContextFactory<AgentDbContext>
{
    public AgentDbContext CreateDbContext(string[] args)
    {
        var optionsBuilder = new DbContextOptionsBuilder<AgentDbContext>();
        // Caminho relativo a partir do diretorio onde 'dotnet ef' e chamado.
        var path = Environment.GetEnvironmentVariable("AGENT_DB_PATH")
                   ?? "../../../data/agent-queue.sqlite";
        optionsBuilder.UseSqlite($"Data Source={path}");
        return new AgentDbContext(optionsBuilder.Options);
    }
}
