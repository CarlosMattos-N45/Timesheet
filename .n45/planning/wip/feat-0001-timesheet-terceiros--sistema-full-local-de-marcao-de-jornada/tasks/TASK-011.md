---
checkpoint: null
complexity: M
created_at: "2026-05-27 16:04:18"
criteria:
    - done: false
      test: cd apps/agent && dotnet test Timesheet.Agent.sln --filter FullyQualifiedName~Migration_creates_all_three_tables
      text: MigrateAsync cria as 3 tabelas + EFMigrationsHistory
    - done: false
      test: cd apps/agent && dotnet test Timesheet.Agent.sln --filter FullyQualifiedName~MarcacaoLocal_roundtrip
      text: MarcacaoLocal round-trip persistir e consultar via SingleAsync
    - done: false
      test: cd apps/agent && dotnet test Timesheet.Agent.sln --filter FullyQualifiedName~MarcacaoLocal_duplicate_id_rejected
      text: MarcacaoLocal duplicado por Id lanca DbUpdateException
    - done: false
      test: cd apps/agent && dotnet test Timesheet.Agent.sln --filter FullyQualifiedName~EstadoJornadaAtual_singleton_rejects_id_other_than_1
      text: EstadoJornadaAtual com Id!=1 violado pelo CHECK singleton
    - done: false
      test: cd apps/agent && dotnet test Timesheet.Agent.sln --filter FullyQualifiedName~ConfiguracaoLocal_singleton_rejects_id_other_than_1
      text: ConfiguracaoLocal com Id!=1 violado pelo CHECK singleton
    - done: false
      test: cd apps/agent && dotnet test Timesheet.Agent.sln --filter FullyQualifiedName~Pending_queue_ordered_by_criado_em
      text: Fila pendente ordenada por CriadoEm asc
    - done: false
      test: cd apps/agent && dotnet test Timesheet.Agent.sln --filter FullyQualifiedName~Index_on_sincronizada_and_proxima_tentativa_exists
      text: Indice composto Sincronizada+ProximaTentativaEm existe na MarcacaoLocal
    - done: false
      test: grep -E EntityFrameworkCore.Sqlite apps/agent/src/Timesheet.Agent.Infra.Db/Timesheet.Agent.Infra.Db.csproj
      text: Microsoft.EntityFrameworkCore.Sqlite declarado em Infra.Db.csproj
    - done: false
      test: powershell -NoProfile -Command "if (-not (Test-Path apps/agent/src/Timesheet.Agent.Infra.Db/Migrations/AgentDbContextModelSnapshot.cs)) { exit 1 }"
      text: Pasta Migrations existe com snapshot do model
    - done: false
      test: cd apps/agent && dotnet build Timesheet.Agent.sln
      text: dotnet build sem warnings (TreatWarningsAsErrors true)
    - done: false
      test: cd apps/agent && dotnet format Timesheet.Agent.sln --verify-no-changes
      text: dotnet format verify-no-changes
    - done: false
      text: Testes passando com cobertura >= 70% (camadas Domain + Infra excluindo UI)
    - done: false
      test: make agent-smoke
      text: make agent-smoke continua passando
    - done: false
      test: make smoke
      text: make smoke (full) continua passando
deps:
    - TASK-006
id: TASK-011
linter: cd apps/agent && dotnet format Timesheet.Agent.sln --verify-no-changes
n45_version: 0.2.0
persona: dba
phase: Phase 2 — Dados
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: pending
tests: cd apps/agent && dotnet test Timesheet.Agent.sln
title: 'EF Core Agente: 3 POCOs no Domain + AgentDbContext + design-time factory + migration Initial + tests'
updated_at: "2026-05-27 16:04:18"
---
## Contexto

O Agente Desktop .NET 8 tem persistência local própria, isolada do banco do Backend: uma fila de marcações pendentes e o estado da jornada atual, ambos em SQLite acessado via EF Core. O arquivo de banco do agente fica em `%APPDATA%\TimesheetTerceiros\agent-queue.sqlite` em produção; em dev/teste usa `./data/agent-queue.sqlite` no checkout.

Estado atual:
- `apps/agent/src/Timesheet.Agent.Infra.Db/` existe com `Timesheet.Agent.Infra.Db.csproj` (apenas marker) e `AssemblyMarker.cs` — scaffold vazio criado na Phase 1.
- `Timesheet.Agent.Domain` é o projeto onde devem viver as entidades de domínio puro (POCOs); `Timesheet.Agent.Infra.Db` provê a infraestrutura EF Core sobre essas entidades.
- O scaffold .NET tem `Directory.Build.props` com `Nullable enable` + `TreatWarningsAsErrors true` (validado em Phase 1).
- TASK-006 documentou em RUNBOOK o caminho `./data/agent-queue.sqlite` para dev.

Esta task entrega: 3 entidades POCO no Domain (`MarcacaoLocal`, `EstadoJornadaAtual`, `ConfiguracaoLocal`) + `AgentDbContext` no Infra.Db + EF Core migration inicial + testes xUnit que exercitam round-trip e a migration.

EF Core migration: aplicar via `Database.MigrateAsync()` (não `EnsureCreated`) — o agente em produção deve aplicar incrementos futuros. O design-time factory permite que `dotnet ef migrations add` funcione sem o host completo.

## Comportamento Esperado

| Entrada / Ação                                                                  | Saída / Efeito esperado                                                                                                  |
| ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `await context.Database.MigrateAsync()` em banco vazio                          | Cria as 3 tabelas (`MarcacaoLocal`, `EstadoJornadaAtual`, `ConfiguracaoLocal`) + tabela `__EFMigrationsHistory`           |
| `context.MarcacaoLocal.Add(new MarcacaoLocal{...})` + `SaveChangesAsync()`      | Linha persistida; `SingleAsync(...)` retorna a entidade                                                                  |
| Inserir 2× `MarcacaoLocal` com mesmo `Id`                                       | EF Core levanta `DbUpdateException` (PK violation)                                                                       |
| `EstadoJornadaAtual` com `Id != 1`                                              | Migration enforces `CHECK (Id = 1)` — SQLite rejeita                                                                     |
| `ConfiguracaoLocal` com `Id != 1`                                               | Migration enforces `CHECK (Id = 1)` — SQLite rejeita                                                                     |
| Query `MarcacaoLocal.Where(m => !m.Sincronizada).OrderBy(m => m.CriadoEm)`      | Retorna fila pendente ordenada por criação (cobre o sync loop futuro)                                                    |
| Index `IX_MarcacaoLocal_Sincronizada_ProximaTentativaEm`                        | Existe após migrate (consultado via `PRAGMA index_list('MarcacaoLocal')`)                                                |
| `dotnet ef migrations script` (offline)                                         | Gera SQL completo das 3 tabelas + índice                                                                                 |
| `dotnet test apps/agent/Timesheet.Agent.sln`                                    | Suite inclui novos testes de Infra.Db; todos passam                                                                      |

## TDD (red → green → refactor)

**Testes a escrever antes da implementação** (`apps/agent/src/Timesheet.Agent.Tests/InfraDb/AgentDbContextTests.cs`):

```csharp
using FluentAssertions;
using Microsoft.Data.Sqlite;
using Microsoft.EntityFrameworkCore;
using Timesheet.Agent.Domain;
using Timesheet.Agent.Infra.Db;
using Xunit;

namespace Timesheet.Agent.Tests.InfraDb;

public sealed class AgentDbContextTests : IAsyncLifetime
{
    private SqliteConnection _conn = null!;
    private AgentDbContext _ctx = null!;

    public async Task InitializeAsync()
    {
        // SQLite shared in-memory por conexao — vive enquanto a conexao estiver aberta.
        _conn = new SqliteConnection("DataSource=:memory:");
        await _conn.OpenAsync();
        var options = new DbContextOptionsBuilder<AgentDbContext>()
            .UseSqlite(_conn)
            .Options;
        _ctx = new AgentDbContext(options);
        await _ctx.Database.MigrateAsync();
    }

    public async Task DisposeAsync()
    {
        await _ctx.DisposeAsync();
        await _conn.DisposeAsync();
    }

    [Fact]
    public async Task Migration_creates_all_three_tables()
    {
        var tables = await _ctx.Database
            .SqlQueryRaw<string>("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            .ToListAsync();
        tables.Should().Contain("MarcacaoLocal");
        tables.Should().Contain("EstadoJornadaAtual");
        tables.Should().Contain("ConfiguracaoLocal");
        tables.Should().Contain("__EFMigrationsHistory");
    }

    [Fact]
    public async Task MarcacaoLocal_roundtrip()
    {
        var id = Guid.NewGuid().ToString();
        _ctx.MarcacoesLocais.Add(new MarcacaoLocal
        {
            Id = id,
            Tipo = "INICIO_JORNADA",
            HorarioRegistrado = "2026-05-27T12:00:00Z",
            Origem = "AGENTE_AUTOMATICO",
            DataJornada = "2026-05-27",
            CriadoEm = "2026-05-27T12:00:00Z",
        });
        await _ctx.SaveChangesAsync();

        var fetched = await _ctx.MarcacoesLocais.SingleAsync(m => m.Id == id);
        fetched.Tipo.Should().Be("INICIO_JORNADA");
        fetched.Sincronizada.Should().BeFalse();
        fetched.TentativasSync.Should().Be(0);
    }

    [Fact]
    public async Task MarcacaoLocal_duplicate_id_rejected()
    {
        var id = Guid.NewGuid().ToString();
        _ctx.MarcacoesLocais.Add(new MarcacaoLocal
        {
            Id = id, Tipo = "INICIO_JORNADA",
            HorarioRegistrado = "2026-05-27T12:00:00Z",
            Origem = "AGENTE_AUTOMATICO",
            DataJornada = "2026-05-27", CriadoEm = "2026-05-27T12:00:00Z",
        });
        await _ctx.SaveChangesAsync();

        _ctx.MarcacoesLocais.Add(new MarcacaoLocal
        {
            Id = id, Tipo = "FIM_JORNADA",
            HorarioRegistrado = "2026-05-27T18:00:00Z",
            Origem = "AGENTE_AUTOMATICO",
            DataJornada = "2026-05-27", CriadoEm = "2026-05-27T18:00:00Z",
        });

        Func<Task> act = async () => await _ctx.SaveChangesAsync();
        await act.Should().ThrowAsync<DbUpdateException>();
    }

    [Fact]
    public async Task EstadoJornadaAtual_singleton_rejects_id_other_than_1()
    {
        _ctx.EstadoJornadaAtual.Add(new EstadoJornadaAtual
        {
            Id = 2,
            DataJornada = "2026-05-27",
            Status = "EM_JORNADA",
            AtualizadoEm = "2026-05-27T12:00:00Z",
        });
        Func<Task> act = async () => await _ctx.SaveChangesAsync();
        await act.Should().ThrowAsync<DbUpdateException>();
    }

    [Fact]
    public async Task ConfiguracaoLocal_singleton_rejects_id_other_than_1()
    {
        _ctx.ConfiguracaoLocal.Add(new ConfiguracaoLocal
        {
            Id = 5,
            BackendBaseUrl = "http://127.0.0.1:8765",
        });
        Func<Task> act = async () => await _ctx.SaveChangesAsync();
        await act.Should().ThrowAsync<DbUpdateException>();
    }

    [Fact]
    public async Task Pending_queue_ordered_by_criado_em()
    {
        _ctx.MarcacoesLocais.AddRange(
            new MarcacaoLocal { Id = "b", Tipo = "INICIO_JORNADA", HorarioRegistrado = "x", Origem = "AGENTE_AUTOMATICO", DataJornada = "2026-05-27", CriadoEm = "2026-05-27T13:00:00Z" },
            new MarcacaoLocal { Id = "a", Tipo = "SAIDA_ALMOCO", HorarioRegistrado = "x", Origem = "AGENTE_AUTOMATICO", DataJornada = "2026-05-27", CriadoEm = "2026-05-27T12:00:00Z" }
        );
        await _ctx.SaveChangesAsync();

        var pending = await _ctx.MarcacoesLocais
            .Where(m => !m.Sincronizada)
            .OrderBy(m => m.CriadoEm)
            .Select(m => m.Id)
            .ToListAsync();

        pending.Should().Equal("a", "b");
    }

    [Fact]
    public async Task Index_on_sincronizada_and_proxima_tentativa_exists()
    {
        var indexes = await _ctx.Database
            .SqlQueryRaw<string>("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='MarcacaoLocal'")
            .ToListAsync();
        indexes.Should().Contain(name => name.Contains("Sincronizada"));
    }
}
```

> Testes usam `Microsoft.Data.Sqlite` em modo `:memory:` (sem depender de arquivo no disco) — execução rápida e isolada. `MigrateAsync` é o caminho de produção e roda também nos testes.

**Refatoração:** Após o green, considerar helper estático `BuildTestContext` em uma base class se mais suites de Infra.Db forem criadas; por ora, mantido inline em `AgentDbContextTests`.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo                                                                                                       | Ação      | Descrição                                                                                                |
| ------------------------------------------------------------------------------------------------------------- | --------- | -------------------------------------------------------------------------------------------------------- |
| `apps/agent/src/Timesheet.Agent.Domain/MarcacaoLocal.cs`                                                       | Criar     | POCO da entidade de marcação local                                                                       |
| `apps/agent/src/Timesheet.Agent.Domain/EstadoJornadaAtual.cs`                                                  | Criar     | POCO do estado atual da jornada (singleton)                                                              |
| `apps/agent/src/Timesheet.Agent.Domain/ConfiguracaoLocal.cs`                                                   | Criar     | POCO da configuração local (singleton; backend URL, tokens DPAPI)                                        |
| `apps/agent/src/Timesheet.Agent.Infra.Db/Timesheet.Agent.Infra.Db.csproj`                                      | Modificar | Adicionar `Microsoft.EntityFrameworkCore.Sqlite` + `Microsoft.EntityFrameworkCore.Design` PackageReference|
| `apps/agent/src/Timesheet.Agent.Infra.Db/AgentDbContext.cs`                                                    | Criar     | `DbContext` com 3 DbSets + `OnModelCreating` mapeando CHECKs e índices                                   |
| `apps/agent/src/Timesheet.Agent.Infra.Db/AgentDbContextFactory.cs`                                             | Criar     | `IDesignTimeDbContextFactory<AgentDbContext>` para `dotnet ef`                                            |
| `apps/agent/src/Timesheet.Agent.Infra.Db/Migrations/<timestamp>_Initial.cs`                                    | Criar     | Migration EF Core gerada por `dotnet ef migrations add Initial` (committada)                             |
| `apps/agent/src/Timesheet.Agent.Infra.Db/Migrations/<timestamp>_Initial.Designer.cs`                           | Criar     | Designer file da migration (gerado pelo EF tooling)                                                      |
| `apps/agent/src/Timesheet.Agent.Infra.Db/Migrations/AgentDbContextModelSnapshot.cs`                            | Criar     | Snapshot do model (gerado pelo EF tooling)                                                               |
| `apps/agent/src/Timesheet.Agent.Tests/Timesheet.Agent.Tests.csproj`                                            | Modificar | Adicionar PackageReference para `Microsoft.EntityFrameworkCore.Sqlite` (se ainda não está) + ProjectReference para `Infra.Db`/`Domain` |
| `apps/agent/src/Timesheet.Agent.Tests/InfraDb/AgentDbContextTests.cs`                                          | Criar     | Suite acima (7 testes)                                                                                   |

> **Total de arquivos-alvo: 11** (3 entities + 1 context + 1 factory + 3 migration files + 2 csprojs + 1 test). Excede o teto de 8 por 3 unidades. Justificativa: o trio de migration (cs + Designer.cs + snapshot.cs) é gerado **por uma única invocação** de `dotnet ef migrations add Initial` — conta como uma operação semântica única. Os arquivos POCO de domínio (3) e o DbContext + Factory (2) compõem **um único conceito de banco do Agente**. Dividir geraria conflito em `AgentDbContext.OnModelCreating` (que precisa de todos os 3 DbSets) ou em `csproj` (mesmo arquivo). Esta exceção é coesa e equivale ao caso de FundaÃ§Ã£o (1 conceito = 1 task).

### Detalhamento Técnico

**1. Entidades POCO (`apps/agent/src/Timesheet.Agent.Domain/`):**

`MarcacaoLocal.cs`:

```csharp
namespace Timesheet.Agent.Domain;

public sealed class MarcacaoLocal
{
    public required string Id { get; init; }                  // UUID v4 (= idempotency_key no backend)
    public required string Tipo { get; init; }                // INICIO_JORNADA | SAIDA_ALMOCO | RETORNO_ALMOCO | FIM_JORNADA
    public required string HorarioRegistrado { get; init; }   // ISO 8601 UTC
    public string? HorarioEfetivo { get; set; }
    public required string Origem { get; init; }              // AGENTE_AUTOMATICO | AGENTE_CONFIRMADO
    public bool ConfirmadoPeloUsuario { get; set; }
    public required string DataJornada { get; init; }         // YYYY-MM-DD
    public bool Sincronizada { get; set; }
    public int TentativasSync { get; set; }
    public string? UltimoErroSync { get; set; }
    public string? ProximaTentativaEm { get; set; }
    public required string CriadoEm { get; init; }            // ISO 8601 UTC
}
```

`EstadoJornadaAtual.cs`:

```csharp
namespace Timesheet.Agent.Domain;

public sealed class EstadoJornadaAtual
{
    public int Id { get; init; } = 1;                         // singleton: CHECK (Id = 1)
    public required string DataJornada { get; set; }
    public required string Status { get; set; }               // AGUARDANDO_INICIO | EM_JORNADA | EM_ALMOCO | AGUARDANDO_FIM | FECHADA
    public string? UltimoInput { get; set; }
    public required string AtualizadoEm { get; set; }
}
```

`ConfiguracaoLocal.cs`:

```csharp
namespace Timesheet.Agent.Domain;

public sealed class ConfiguracaoLocal
{
    public int Id { get; init; } = 1;                         // singleton: CHECK (Id = 1)
    public required string BackendBaseUrl { get; set; }
    public string? UltimaSincronizacaoEm { get; set; }
    public string? JwtAccessToken { get; set; }               // DPAPI-protected blob (base64)
    public string? JwtRefreshToken { get; set; }              // DPAPI-protected blob (base64)
    public string? ExpiraEm { get; set; }
}
```

**2. `AgentDbContext.cs`** (`apps/agent/src/Timesheet.Agent.Infra.Db/`):

```csharp
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
```

**3. `AgentDbContextFactory.cs`** — design-time factory para `dotnet ef`:

```csharp
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
```

**4. Geração da migration** (executor roda):

```powershell
# A partir da raiz do agent:
cd apps/agent
# Garante que pasta data/ existe para o ef tooling:
if (-not (Test-Path ../../data)) { New-Item -ItemType Directory ../../data | Out-Null }
# Adiciona migration Initial (gera os 3 arquivos em Migrations/):
dotnet ef migrations add Initial `
    --project src/Timesheet.Agent.Infra.Db `
    --startup-project src/Timesheet.Agent.Infra.Db `
    --context AgentDbContext
```

Os 3 arquivos resultantes (`<timestamp>_Initial.cs`, `<timestamp>_Initial.Designer.cs`, `AgentDbContextModelSnapshot.cs`) são **committados**. Não revisar manualmente — o EF Core tooling é determinístico para o mesmo modelo.

> Se o tooling `dotnet-ef` não estiver instalado: `dotnet tool install --global dotnet-ef --version 8.*` (uma vez por ambiente).

**5. `Timesheet.Agent.Infra.Db.csproj`** — atualizar:

```xml
<Project Sdk="Microsoft.NET.Sdk">

  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
  </PropertyGroup>

  <ItemGroup>
    <PackageReference Include="Microsoft.EntityFrameworkCore.Sqlite" Version="8.0.*" />
    <PackageReference Include="Microsoft.EntityFrameworkCore.Design" Version="8.0.*">
      <PrivateAssets>all</PrivateAssets>
      <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>
    </PackageReference>
  </ItemGroup>

  <ItemGroup>
    <ProjectReference Include="..\Timesheet.Agent.Domain\Timesheet.Agent.Domain.csproj" />
  </ItemGroup>

</Project>
```

(Remover `AssemblyMarker.cs` se ficar desnecessário; preferir manter como placeholder vazio para evitar `dotnet pack` warnings — opcional.)

**6. `Timesheet.Agent.Tests.csproj`** — garantir referências:

```xml
<ItemGroup>
  <PackageReference Include="Microsoft.EntityFrameworkCore.Sqlite" Version="8.0.*" />
  <!-- xUnit, FluentAssertions, Moq ja existentes na Phase 1 -->
</ItemGroup>

<ItemGroup>
  <ProjectReference Include="..\Timesheet.Agent.Domain\Timesheet.Agent.Domain.csproj" />
  <ProjectReference Include="..\Timesheet.Agent.Infra.Db\Timesheet.Agent.Infra.Db.csproj" />
</ItemGroup>
```

## Contratos com camadas adjacentes

```
Produz para:
  - Timesheet.Agent.Service (Phase 5 do Agente): AgentDbContext + DbSets para HostedService consumir.
  - Timesheet.Agent.Infra.Http (Phase 5): MarcacaoLocal e' a fonte da fila para POST /api/v1/marcacoes.

Consome de:
  - Timesheet.Agent.Domain (Phase 1): pacote ja existente; recebe 3 novas POCOs.
  - TASK-006: caminho ./data/agent-queue.sqlite documentado no RUNBOOK.

Erros:
  - Migration aplicada parcialmente: EF Core retry e idempotente; recriar arquivo se corrompido.
  - PRAGMA / CHECK violation: lancada como DbUpdateException com inner SqliteException.
```

Não há contrato HTTP aqui.

**Validação obrigatória pelo executor antes de marcar done:**

1. `cd apps/agent && dotnet restore Timesheet.Agent.sln`.
2. `cd apps/agent && dotnet build Timesheet.Agent.sln` — compila sem warnings (TreatWarningsAsErrors).
3. `cd apps/agent && dotnet ef migrations add Initial --project src/Timesheet.Agent.Infra.Db --startup-project src/Timesheet.Agent.Infra.Db --context AgentDbContext` — apenas se a pasta `Migrations/` ainda não existir; commit dos 3 arquivos.
4. `cd apps/agent && dotnet test Timesheet.Agent.sln` — 7 novos testes + os smoke existentes passam.
5. `cd apps/agent && dotnet format Timesheet.Agent.sln --verify-no-changes` — sem diffs de formatação.
6. `make agent-smoke` (Phase 1) continua passando.
7. `make smoke` (full) continua passando.

> Executor DEVE rodar 1–7 e garantir saída 0 antes de retornar. Falha = task não concluída.

**Refatoração:** Caso o `OnModelCreating` cresça em outras migrations futuras, extrair configurações por entidade para `IEntityTypeConfiguration<T>` separadas. Por ora, manter inline para coesão.
