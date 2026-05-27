using Microsoft.EntityFrameworkCore;
using Timesheet.Agent.Domain;

namespace Timesheet.Agent.Infra.Db;

public sealed class AgentDbContext : DbContext
{
    public AgentDbContext(DbContextOptions<AgentDbContext> options) : base(options) { }

    public DbSet<MarcacaoLocal> MarcacoesLocais => Set<MarcacaoLocal>();
    public DbSet<EstadoJornadaAtual> EstadoJornadaAtual => Set<EstadoJornadaAtual>();
    public DbSet<ConfiguracaoLocal> ConfiguracaoLocal => Set<ConfiguracaoLocal>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<MarcacaoLocal>(e =>
        {
            e.ToTable("MarcacaoLocal", t =>
            {
                t.HasCheckConstraint("CK_MarcacaoLocal_Tipo",
                    "Tipo IN ('INICIO_JORNADA','SAIDA_ALMOCO','RETORNO_ALMOCO','FIM_JORNADA')");
                t.HasCheckConstraint("CK_MarcacaoLocal_Origem",
                    "Origem IN ('AGENTE_AUTOMATICO','AGENTE_CONFIRMADO')");
            });
            e.HasKey(m => m.Id);
            e.Property(m => m.Id).IsRequired();
            e.Property(m => m.Tipo).IsRequired();
            e.Property(m => m.HorarioRegistrado).IsRequired();
            e.Property(m => m.Origem).IsRequired();
            e.Property(m => m.DataJornada).IsRequired();
            e.Property(m => m.CriadoEm).IsRequired();
            e.Property(m => m.Sincronizada).HasDefaultValue(false);
            e.Property(m => m.TentativasSync).HasDefaultValue(0);
            e.HasIndex(m => new { m.Sincronizada, m.ProximaTentativaEm })
                .HasDatabaseName("IX_MarcacaoLocal_Sincronizada_ProximaTentativaEm");
        });

        modelBuilder.Entity<EstadoJornadaAtual>(e =>
        {
            e.ToTable("EstadoJornadaAtual", t =>
                t.HasCheckConstraint("CK_EstadoJornadaAtual_Singleton", "Id = 1"));
            e.HasKey(s => s.Id);
            e.Property(s => s.Id).ValueGeneratedNever();
            e.Property(s => s.DataJornada).IsRequired();
            e.Property(s => s.Status).IsRequired();
            e.Property(s => s.AtualizadoEm).IsRequired();
        });

        modelBuilder.Entity<ConfiguracaoLocal>(e =>
        {
            e.ToTable("ConfiguracaoLocal", t =>
                t.HasCheckConstraint("CK_ConfiguracaoLocal_Singleton", "Id = 1"));
            e.HasKey(c => c.Id);
            e.Property(c => c.Id).ValueGeneratedNever();
            e.Property(c => c.BackendBaseUrl).IsRequired();
        });
    }
}
