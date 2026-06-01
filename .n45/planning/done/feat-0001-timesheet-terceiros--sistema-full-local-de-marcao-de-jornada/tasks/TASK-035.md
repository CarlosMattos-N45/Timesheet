---
checkpoint: null
complexity: M
created_at: "2026-05-29 10:33:38"
criteria:
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~Protect_then_Unprotect_roundtrips
      text: DpapiTokenStore.Protect produz blob cifrado != texto puro e Unprotect faz round-trip (Windows-only)
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~SalvarTokens_persists_encrypted_and_sets_expiry
      text: SalvarTokensAsync persiste tokens cifrados (!= texto puro) e ExpiraEm=now+ExpiresIn
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~GetValidAccessToken_returns_cached_when_not_expired
      text: GetValidAccessTokenAsync retorna access cacheado sem chamar RefreshAsync quando nao expirado
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~GetValidAccessToken_refreshes_when_expired
      text: GetValidAccessTokenAsync chama RefreshAsync 1x quando expirado e persiste tokens rotacionados + novo ExpiraEm
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~GetValidAccessToken_propagates_AuthException_when_refresh_revoked
      text: GetValidAccessTokenAsync propaga AuthException(code=UNAUTHORIZED) quando refresh revogado e quando nao ha config persistida; nao persiste tokens
    - done: true
      text: Testes passando com cobertura Infra.Http (TokenManager) >= 70%
deps:
    - TASK-029
id: TASK-035
linter: cd apps/agent && dotnet format Timesheet.Agent.sln --verify-no-changes
n45_version: 0.2.0
persona: backend
phase: Phase 5 — Agente Desktop
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: done
tdd:
    green: true
    red: true
    refactor: true
tests: cd apps/agent && dotnet test Timesheet.Agent.sln -c Debug --filter "FullyQualifiedName~DpapiTokenStoreTests|FullyQualifiedName~TokenManagerTests"
title: 'Token persistence: DpapiTokenStore (ProtectedData CurrentUser) + TokenManager (refresh automatico via IBackendClient)'
updated_at: "2026-05-29 11:07:02"
---
## Contexto

Esta task é a **segunda metade** da antiga TASK-029 (dividida por exceder o orçamento de arquivos). Implementa a **persistência e o refresh automático de token JWT** do Agente, sobre a camada HTTP já entregue pela TASK-029.

A TASK-029 (dependência desta) entregou: `IBackendClient` (com `RefreshAsync(string refreshToken) → AuthResult` e `AuthException` com `Code`), os DTOs (`AuthResult`), e o `AddAgentHttp` que registra o `HttpClient` tipado + Polly. Esta task NÃO recria o cliente HTTP nem faz parsing de rede — apenas guarda os tokens cifrados e decide quando refrescar.

Os tokens não podem ficar em texto puro no disco. No Windows, a proteção padrão por usuário é o **DPAPI** (`System.Security.Cryptography.ProtectedData`, escopo `CurrentUser`). O `DpapiTokenStore` cifra/decifra os tokens; o `TokenManager` os persiste em `ConfiguracaoLocal` (singleton Id=1, repositório entregue pela TASK-028) e decide, a cada uso, se o access token ainda é válido ou se precisa chamar `IBackendClient.RefreshAsync`.

A Fundação (TASK-028) já forneceu: `IClock` (`NowUtc`), `ConfiguracaoLocalRepository` (`GetAsync`/`UpsertAsync`, singleton Id=1). O `ConfiguracaoLocal` guarda os campos de token cifrado e o instante de expiração — esta task usa/estende esse repositório (campos `JwtAccessCifrado`, `JwtRefreshCifrado`, `ExpiraEm`; se ausentes no modelo da TASK-028, adicioná-los à entidade `ConfiguracaoLocal` e ao mapeamento do repositório).

O Service host (TASK-033) chama `TokenManager.GetValidAccessTokenAsync()` antes de cada `PostMarcacaoAsync`; a UI de onboarding (TASK-034) persiste os tokens iniciais após o login via `TokenManager.SalvarTokensAsync(AuthResult)`.

## Comportamento Esperado

Casos de sucesso e erro. Os testes verificam exatamente isto. `DpapiTokenStore` só roda em Windows (CI do Agente é Windows) — o teste de DPAPI é marcado para rodar só nessa plataforma. O `TokenManager` é testado com `IBackendClient` mock (Moq), `IClock` = `FakeClock`, e `ConfiguracaoLocalRepository` sobre SQLite `:memory:`.

**Exemplos (entrada → saída esperada)** — valores reais, base direta das assertions:

| Entrada / Ação | Saída / Efeito esperado |
| -------------- | ----------------------- |
| `DpapiTokenStore.Protect("RT")` | retorna base64 ≠ `"RT"` (cifrado, não texto puro) |
| `DpapiTokenStore.Unprotect(Protect("RT"))` | retorna `"RT"` (round-trip via ProtectedData.CurrentUser) |
| `TokenManager.SalvarTokensAsync(AuthResult(AccessToken="AT",RefreshToken="RT",ExpiresIn=900))` com `clock.NowUtc=2026-05-27T12:00:00Z` | `ConfiguracaoLocal` persiste `JwtAccessCifrado`/`JwtRefreshCifrado` (≠ texto puro) e `ExpiraEm=2026-05-27T12:15:00Z` (now + 900s) |
| `GetValidAccessTokenAsync()` com access válido (`ExpiraEm` > now + 30s margem) | retorna o access desprotegido SEM chamar `IBackendClient.RefreshAsync` |
| `GetValidAccessTokenAsync()` com access expirado (`ExpiraEm` < now) e refresh válido; client devolve novos tokens | chama `RefreshAsync(refreshArmazenado)` 1×, persiste novos tokens cifrados + novo `ExpiraEm`, retorna o novo access |
| `GetValidAccessTokenAsync()` com `RefreshAsync` lançando `AuthException(code="UNAUTHORIZED")` | propaga `AuthException` (cadeia revogada → host pausa sync até novo login); NÃO persiste tokens |
| `GetValidAccessTokenAsync()` sem config persistida (nunca logou) | lança `AuthException(code="UNAUTHORIZED")` (sem token → exige login) |

## TDD (red → green → refactor)

**Testes a escrever antes da implementação:**

```csharp
// Timesheet.Agent.Tests/InfraHttp/DpapiTokenStoreTests.cs  — só roda em Windows
public class DpapiTokenStoreTests
{
    [SkippableFact] // ou [Fact] com Skip se !OperatingSystem.IsWindows()
    public void Protect_then_Unprotect_roundtrips()
    {
        Skip.IfNot(OperatingSystem.IsWindows());
        var store = new DpapiTokenStore();
        var blob = store.Protect("RT");
        blob.Should().NotBe("RT");          // está cifrado
        store.Unprotect(blob).Should().Be("RT");
    }
}

// Timesheet.Agent.Tests/InfraHttp/TokenManagerTests.cs
public class TokenManagerTests
{
    [Fact]
    public async Task SalvarTokens_persists_encrypted_and_sets_expiry()
    {
        // clock fixo 12:00:00Z; repo :memory:; store fake (ou DPAPI no-op em teste)
        await _sut.SalvarTokensAsync(new AuthResult("AT", "RT", "u1", 900));
        var cfg = await _repo.GetAsync();
        cfg!.JwtAccessCifrado.Should().NotBe("AT");                       // cifrado
        cfg.ExpiraEm.Should().Be("2026-05-27T12:15:00Z");                // now + 900s, ISO "o"
    }

    [Fact]
    public async Task GetValidAccessToken_returns_cached_when_not_expired()
    {
        await SeedConfig(access: "AT", refresh: "RT", expiraEm: "2026-05-27T12:15:00Z"); // now=12:00
        var token = await _sut.GetValidAccessTokenAsync();
        token.Should().Be("AT");
        _client.Verify(c => c.RefreshAsync(It.IsAny<string>(), It.IsAny<CancellationToken>()), Times.Never);
    }

    [Fact]
    public async Task GetValidAccessToken_refreshes_when_expired()
    {
        await SeedConfig(access: "ATold", refresh: "RT", expiraEm: "2026-05-27T11:00:00Z"); // expirado (now=12:00)
        _client.Setup(c => c.RefreshAsync("RT", It.IsAny<CancellationToken>()))
               .ReturnsAsync(new AuthResult("ATnew", "RTnew", null, 900));
        var token = await _sut.GetValidAccessTokenAsync();
        token.Should().Be("ATnew");
        var cfg = await _repo.GetAsync();
        _store.Unprotect(cfg!.JwtRefreshCifrado).Should().Be("RTnew");   // novo refresh persistido (rotation)
        cfg.ExpiraEm.Should().Be("2026-05-27T12:15:00Z");
    }

    [Fact]
    public async Task GetValidAccessToken_propagates_AuthException_when_refresh_revoked()
    {
        await SeedConfig(access: "ATold", refresh: "RT", expiraEm: "2026-05-27T11:00:00Z");
        _client.Setup(c => c.RefreshAsync("RT", It.IsAny<CancellationToken>()))
               .ThrowsAsync(new AuthException("UNAUTHORIZED"));
        var act = async () => await _sut.GetValidAccessTokenAsync();
        (await act.Should().ThrowAsync<AuthException>()).Which.Code.Should().Be("UNAUTHORIZED");
    }

    [Fact]
    public async Task GetValidAccessToken_throws_when_no_config()
    {
        // repo vazio (nunca logou)
        var act = async () => await _sut.GetValidAccessTokenAsync();
        (await act.Should().ThrowAsync<AuthException>()).Which.Code.Should().Be("UNAUTHORIZED");
    }
}
```

> **Controle de teste do DPAPI:** o `DpapiTokenStore` real depende do Windows. Nos testes do `TokenManager`, injetar uma abstração de proteção (interface `ITokenStore { string Protect(string); string Unprotect(string); }` implementada por `DpapiTokenStore`) com um fake que faz prefixo reversível (`"enc:" + s`), de modo que `JwtAccessCifrado.Should().NotBe("AT")` continua válido e os testes rodam cross-platform. O teste do DPAPI real fica isolado em `DpapiTokenStoreTests` com guard de plataforma.

**Refatoração:** após green, extrair a margem de expiração (30s) para constante nomeada; reutilizar o helper `SeedConfig` em todos os testes do `TokenManager`. `"Nenhuma."` adicional no código de produção.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| ------- | ---- | --------- |
| `apps/agent/src/Timesheet.Agent.Infra.Http/DpapiTokenStore.cs` | Criar | `ITokenStore` + impl `DpapiTokenStore`: `Protect(string)→base64 blob`, `Unprotect(base64)→string` via `ProtectedData` (CurrentUser). `[SupportedOSPlatform("windows")]` |
| `apps/agent/src/Timesheet.Agent.Infra.Http/TokenManager.cs` | Criar | `GetValidAccessTokenAsync()` (lê config, refresca se expirado, persiste), `SalvarTokensAsync(AuthResult)` |
| `apps/agent/src/Timesheet.Agent.Infra.Http/AgentHttpExtensions.cs` | Modificar | Adicionar `services.AddSingleton<ITokenStore, DpapiTokenStore>()` e `services.AddScoped<TokenManager>()` ao `AddAgentHttp` (arquivo criado pela TASK-029; dep sequencial garante sem conflito) |
| `apps/agent/src/Timesheet.Agent.Infra.Http/Timesheet.Agent.Infra.Http.csproj` | Modificar | Add `System.Security.Cryptography.ProtectedData` 8.0.* (arquivo já editado pela TASK-029; dep sequencial) |
| `apps/agent/src/Timesheet.Agent.Tests/InfraHttp/DpapiTokenStoreTests.cs` | Criar | Round-trip DPAPI com guard de plataforma Windows |
| `apps/agent/src/Timesheet.Agent.Tests/InfraHttp/TokenManagerTests.cs` | Criar | Testes acima (cached/refresh/revoked/no-config) com `ITokenStore` fake, `IClock`=FakeClock, repo :memory: |

> **Se a entidade `ConfiguracaoLocal` (TASK-028) ainda não tem os campos** `JwtAccessCifrado`, `JwtRefreshCifrado`, `ExpiraEm`: adicioná-los à entidade e ao mapeamento do `ConfiguracaoLocalRepository` (são parte desta task — token persistence). Verificar o source real da TASK-028 antes; se já existirem, apenas usar.

### Detalhamento Técnico

1. **`ITokenStore` + `DpapiTokenStore`** — interface `{ string Protect(string plaintext); string Unprotect(string blobBase64); }`. Impl:
   - `Protect`: `Convert.ToBase64String(ProtectedData.Protect(Encoding.UTF8.GetBytes(token), null, DataProtectionScope.CurrentUser))`.
   - `Unprotect`: reverte — `Encoding.UTF8.GetString(ProtectedData.Unprotect(Convert.FromBase64String(blob), null, DataProtectionScope.CurrentUser))`.
   - Guard `[SupportedOSPlatform("windows")]`.

2. **`TokenManager`** — construtor `(ConfiguracaoLocalRepository repo, ITokenStore store, IBackendClient client, IClock clock)`. Constante `MargemExpiracao = TimeSpan.FromSeconds(30)`.
   - `SalvarTokensAsync(AuthResult auth)`: lê config atual (ou cria nova singleton Id=1), seta `JwtAccessCifrado = store.Protect(auth.AccessToken)`, `JwtRefreshCifrado = store.Protect(auth.RefreshToken)`, `ExpiraEm = clock.NowUtc.AddSeconds(auth.ExpiresIn).ToString("o")` (formato ISO 8601 com `Z`/offset), `UpsertAsync`.
   - `GetValidAccessTokenAsync(CancellationToken ct = default)`:
     - `var cfg = await repo.GetAsync()`; se `cfg == null` ou `JwtRefreshCifrado` vazio → `throw new AuthException("UNAUTHORIZED")` (nunca logou).
     - Parse `ExpiraEm` (`DateTimeOffset.Parse`, estilos UTC). Se `expira > clock.NowUtc + MargemExpiracao` → retorna `store.Unprotect(cfg.JwtAccessCifrado)`.
     - Senão (expirado/perto): `var refresh = store.Unprotect(cfg.JwtRefreshCifrado)`; `var novo = await client.RefreshAsync(refresh, ct)` — se lançar `AuthException` propaga sem persistir; em sucesso `await SalvarTokensAsync(novo)` e retorna `novo.AccessToken`.

   > A assinatura de `IBackendClient.RefreshAsync` é a real da TASK-029 — alinhar ao contrato produzido lá (este é o consumidor). A tabela de exemplos usa `RefreshAsync(string, CancellationToken)`; se a TASK-029 expôs sem `CancellationToken`, usar a real.

3. **Registro DI** (em `AddAgentHttp`, estendendo o arquivo da TASK-029): `ITokenStore`→`DpapiTokenStore` como singleton; `TokenManager` como scoped (consome `ConfiguracaoLocalRepository` que é scoped).

**Contrato com camadas adjacentes:**

```
Produz para: Service host (TASK-033) — TokenManager.GetValidAccessTokenAsync() → access token válido para o POST de marcações;
             AuthException(code="UNAUTHORIZED") ⇒ host pausa sync até novo login
Produz para: WPF onboarding (TASK-034) — TokenManager.SalvarTokensAsync(AuthResult) após LoginAsync inicial
Consome de: TASK-029 — IBackendClient.RefreshAsync, AuthResult, AuthException, AddAgentHttp (estendido aqui)
Consome de: TASK-028 — ConfiguracaoLocalRepository (GetAsync/UpsertAsync, singleton Id=1), IClock
```
