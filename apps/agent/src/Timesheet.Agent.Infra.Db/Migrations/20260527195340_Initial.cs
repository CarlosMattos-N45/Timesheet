using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace Timesheet.Agent.Infra.Db.Migrations
{
    /// <inheritdoc />
    public partial class Initial : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "ConfiguracaoLocal",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false),
                    BackendBaseUrl = table.Column<string>(type: "TEXT", nullable: false),
                    UltimaSincronizacaoEm = table.Column<string>(type: "TEXT", nullable: true),
                    JwtAccessToken = table.Column<string>(type: "TEXT", nullable: true),
                    JwtRefreshToken = table.Column<string>(type: "TEXT", nullable: true),
                    ExpiraEm = table.Column<string>(type: "TEXT", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_ConfiguracaoLocal", x => x.Id);
                    table.CheckConstraint("CK_ConfiguracaoLocal_Singleton", "Id = 1");
                });

            migrationBuilder.CreateTable(
                name: "EstadoJornadaAtual",
                columns: table => new
                {
                    Id = table.Column<int>(type: "INTEGER", nullable: false),
                    DataJornada = table.Column<string>(type: "TEXT", nullable: false),
                    Status = table.Column<string>(type: "TEXT", nullable: false),
                    UltimoInput = table.Column<string>(type: "TEXT", nullable: true),
                    AtualizadoEm = table.Column<string>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_EstadoJornadaAtual", x => x.Id);
                    table.CheckConstraint("CK_EstadoJornadaAtual_Singleton", "Id = 1");
                });

            migrationBuilder.CreateTable(
                name: "MarcacaoLocal",
                columns: table => new
                {
                    Id = table.Column<string>(type: "TEXT", nullable: false),
                    Tipo = table.Column<string>(type: "TEXT", nullable: false),
                    HorarioRegistrado = table.Column<string>(type: "TEXT", nullable: false),
                    HorarioEfetivo = table.Column<string>(type: "TEXT", nullable: true),
                    Origem = table.Column<string>(type: "TEXT", nullable: false),
                    ConfirmadoPeloUsuario = table.Column<bool>(type: "INTEGER", nullable: false),
                    DataJornada = table.Column<string>(type: "TEXT", nullable: false),
                    Sincronizada = table.Column<bool>(type: "INTEGER", nullable: false, defaultValue: false),
                    TentativasSync = table.Column<int>(type: "INTEGER", nullable: false, defaultValue: 0),
                    UltimoErroSync = table.Column<string>(type: "TEXT", nullable: true),
                    ProximaTentativaEm = table.Column<string>(type: "TEXT", nullable: true),
                    CriadoEm = table.Column<string>(type: "TEXT", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_MarcacaoLocal", x => x.Id);
                    table.CheckConstraint("CK_MarcacaoLocal_Origem", "Origem IN ('AGENTE_AUTOMATICO','AGENTE_CONFIRMADO')");
                    table.CheckConstraint("CK_MarcacaoLocal_Tipo", "Tipo IN ('INICIO_JORNADA','SAIDA_ALMOCO','RETORNO_ALMOCO','FIM_JORNADA')");
                });

            migrationBuilder.CreateIndex(
                name: "IX_MarcacaoLocal_Sincronizada_ProximaTentativaEm",
                table: "MarcacaoLocal",
                columns: new[] { "Sincronizada", "ProximaTentativaEm" });
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "ConfiguracaoLocal");

            migrationBuilder.DropTable(
                name: "EstadoJornadaAtual");

            migrationBuilder.DropTable(
                name: "MarcacaoLocal");
        }
    }
}
