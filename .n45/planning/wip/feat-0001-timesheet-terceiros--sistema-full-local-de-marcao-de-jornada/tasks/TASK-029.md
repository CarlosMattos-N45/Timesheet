---
checkpoint: null
complexity: M
created_at: "2026-05-29 10:30:54"
criteria:
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~LoginAsync
      text: LoginAsync parseia tokens em 200 e lanca AuthException(code=UNAUTHORIZED) em 401
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~RefreshAsync_parses_rotated_tokens_on_200
      text: RefreshAsync parseia tokens rotacionados em 200
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~CreateTerceiroAsync_throws_SetupAlreadyDone_on_403
      text: CreateTerceiroAsync lanca AuthException(code=SETUP_ALREADY_DONE) em 403
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~PostMarcacao_returns
      text: PostMarcacaoAsync mapeia 409 AJUSTE_WEB_WINS->DiscardLocal, 409 CONFLICT->AlreadyExists, 422->Rejected
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~PostMarcacao_body_includes_idempotency_key_and_origem
      text: PostMarcacaoAsync envia body com idempotency_key e origem
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~PostMarcacao_retries_on_503_then_succeeds
      text: Polly reabsorve 503 transientes (retorna Created apos 3x503+201) e retorna TransientFailure quando retry esgota
    - done: true
      test: cd apps/agent && dotnet test --filter FullyQualifiedName~IsReadyAsync_false_on_503
      text: IsHealthyAsync/IsReadyAsync retornam bool sem lancar (false em 503)
    - done: true
      text: Testes passando com cobertura Infra.Http >= 70%
deps:
    - TASK-028
id: TASK-029
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
tests: cd apps/agent && dotnet test Timesheet.Agent.sln -c Debug --filter FullyQualifiedName~BackendClientTests
title: 'Infra HTTP: BackendClient (login/refresh/terceiros/marcacoes/health/ready) + Polly (circuit breaker + retry)'
updated_at: "2026-05-29 10:50:36"
---
## Contexto

O Agente registra marcações localmente (SQLite, offline-first) e precisa sincronizá-las com o Backend FastAPI local (`http://127.0.0.1:8765`). Esta task implementa a **camada HTTP resiliente** do Agente (`Timesheet.Agent.Infra.Http`): o cliente HTTP tipado (`BackendClient`) com Polly (circuit breaker + retry exponencial), os DTOs de request/response, o mapeamento de status HTTP → resultado de negócio, e o registro DI do `HttpClient` com as políticas Polly.

Esta é a **primeira de duas tasks** que substituem a antiga TASK-029 (dividida por exceder o orçamento de arquivos). A **persistência/refresh de token** (`DpapiTokenStore` + `TokenManager`) fica na task seguinte (TASK-035), que depende desta. Aqui NÃO se implementa DPAPI nem refresh automático de token — o `BackendClient.PostMarcacaoAsync` recebe o access token já válido por parâmetro; quem gere a validade é o `TokenManager` da TASK-035.

A Fundação (TASK-028) já forneceu: `IClock`, constantes `MarcacaoTipo`/`OrigemMarcacao`, os repositórios (`MarcacaoLocalRepository`, `ConfiguracaoLocalRepository`), e o método `AddAgentInfra`. Esta task consome esses elementos — nunca recria relógio nem repositório.

O Backend (Phase 3, done) expõe os endpoints reais que esta task consome (contratos exatos extraídos do código em `apps/api`):

- `POST /api/v1/auth/login` → `{access_token, refresh_token, terceiro_id, expires_in}` (200)
- `POST /api/v1/auth/refresh` → `{access_token, refresh_token, expires_in}` (200) — rotation: cada uso invalida o refresh anterior
- `POST /api/v1/terceiros` → 201 `{terceiro_id, criado_em}`; 403 `code="SETUP_ALREADY_DONE"` após o primeiro
- `POST /api/v1/marcacoes` (Bearer) → 201 `MarcacaoResponse`; 409 `code="CONFLICT"` ou `code="AJUSTE_WEB_WINS"`; 422 `code="FIM_DE_SEMANA_NAO_PERMITIDO"`
- `GET /api/v1/health` → 200 `{status, version}` (sem auth)
- `GET /api/v1/ready` → 200 `{status:"ready"}` / 503 (sem auth)

`HttpClient` + Polly conforme Spec §2: circuit breaker `fail_max=5` em 30s, `reset_timeout=60s`; retry exponencial 1→2→4→8→16s (max 5); timeout 10s por request.

## Comportamento Esperado

Casos de sucesso e erro. Os testes verificam exatamente isto. Para isolar de rede real, o `HttpClient` recebe um `HttpMessageHandler` mockável (handler fake retornando respostas pré-programadas); Polly é configurado no `HttpClient`.

**Exemplos (entrada → saída esperada)** — valores reais, base direta das assertions:

| Entrada / Ação | Saída / Efeito esperado |
| -------------- | ----------------------- |
| `LoginAsync("maria@x.com","Senha123")` com handler devolvendo 200 `{access_token:"AT",refresh_token:"RT",terceiro_id:"u1",expires_in:900}` | retorna `AuthResult(AccessToken="AT", RefreshToken="RT", TerceiroId="u1", ExpiresIn=900)` |
| `LoginAsync(...)` com handler 401 `{code:"UNAUTHORIZED"}` | lança `AuthException` com `Code=="UNAUTHORIZED"` |
| `RefreshAsync("RT")` com handler 200 `{access_token:"AT2",refresh_token:"RT2",expires_in:900}` | retorna `AuthResult(AccessToken="AT2", RefreshToken="RT2", TerceiroId=null, ExpiresIn=900)` |
| `CreateTerceiroAsync(dto)` com handler 403 `{code:"SETUP_ALREADY_DONE"}` | lança `AuthException` com `Code=="SETUP_ALREADY_DONE"` |
| `PostMarcacaoAsync(m,"AT")` handler 201 `MarcacaoResponse` | retorna `SyncOutcome.Created` |
| `PostMarcacaoAsync(m,"AT")` handler 409 `{code:"AJUSTE_WEB_WINS"}` | retorna `SyncOutcome.DiscardLocal` (Agente descarta — RN-012 #1) |
| `PostMarcacaoAsync(m,"AT")` handler 409 `{code:"CONFLICT"}` | retorna `SyncOutcome.AlreadyExists` (idempotência: já existe, tratado como sucesso) |
| `PostMarcacaoAsync(m,"AT")` handler 422 `{code:"FIM_DE_SEMANA_NAO_PERMITIDO"}` | retorna `SyncOutcome.Rejected` (não reenfileira) |
| `PostMarcacaoAsync(m,"AT")` body enviado | contém `idempotency_key` (= id local) e `origem` ("AGENTE_AUTOMATICO") |
| `PostMarcacaoAsync(m,"AT")` handler 503 3× depois 201 | retorna `SyncOutcome.Created` (retry Polly reabsorveu falhas transientes) |
| `PostMarcacaoAsync(m,"AT")` handler 503 5× (esgota retry) | retorna `SyncOutcome.TransientFailure` (host reenfileira) |
| `IsHealthyAsync()` handler 200 `{status:"ok"}` | `true` |
| `IsReadyAsync()` handler 503 | `false` |

## TDD (red → green → refactor)

**Testes a escrever antes da implementação** (`Timesheet.Agent.Tests/InfraHttp/BackendClientTests.cs`):

```csharp
// FakeHttpMessageHandler: enfileira HttpResponseMessage; conta chamadas; permite assertar request body.
private sealed class FakeHandler(Queue<HttpResponseMessage> responses) : HttpMessageHandler
{
    public List<string> SentBodies { get; } = new();
    protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage req, CancellationToken ct)
    {
        if (req.Content is not null) SentBodies.Add(await req.Content.ReadAsStringAsync(ct));
        return responses.Dequeue();
    }
}

[Fact]
public async Task LoginAsync_parses_tokens_on_200()
{
    var h = new FakeHandler(new(new[] { Json(200, "{\"access_token\":\"AT\",\"refresh_token\":\"RT\",\"terceiro_id\":\"u1\",\"expires_in\":900}") }));
    var sut = MakeClient(h);
    var r = await sut.LoginAsync("maria@x.com", "Senha123");
    r.AccessToken.Should().Be("AT");
    r.RefreshToken.Should().Be("RT");
    r.TerceiroId.Should().Be("u1");
    r.ExpiresIn.Should().Be(900);
}

[Fact]
public async Task LoginAsync_throws_AuthException_on_401()
{
    var h = new FakeHandler(new(new[] { Json(401, "{\"code\":\"UNAUTHORIZED\",\"message\":\"E-mail ou senha invalidos\"}") }));
    var sut = MakeClient(h);
    var act = async () => await sut.LoginAsync("x@x.com", "bad");
    (await act.Should().ThrowAsync<AuthException>()).Which.Code.Should().Be("UNAUTHORIZED");
}

[Fact]
public async Task RefreshAsync_parses_rotated_tokens_on_200()
{
    var h = new FakeHandler(new(new[] { Json(200, "{\"access_token\":\"AT2\",\"refresh_token\":\"RT2\",\"expires_in\":900}") }));
    var sut = MakeClient(h);
    var r = await sut.RefreshAsync("RT");
    r.AccessToken.Should().Be("AT2");
    r.RefreshToken.Should().Be("RT2");
    r.ExpiresIn.Should().Be(900);
}

[Fact]
public async Task CreateTerceiroAsync_throws_SetupAlreadyDone_on_403()
{
    var h = new FakeHandler(new(new[] { Json(403, "{\"code\":\"SETUP_ALREADY_DONE\"}") }));
    var sut = MakeClient(h);
    var act = async () => await sut.CreateTerceiroAsync(SampleTerceiro());
    (await act.Should().ThrowAsync<AuthException>()).Which.Code.Should().Be("SETUP_ALREADY_DONE");
}

[Fact]
public async Task PostMarcacao_returns_DiscardLocal_on_409_AjusteWebWins()
{
    var h = new FakeHandler(new(new[] { Json(409, "{\"code\":\"AJUSTE_WEB_WINS\"}") }));
    var sut = MakeClient(h);
    var outcome = await sut.PostMarcacaoAsync(SampleMarcacao(), "AT");
    outcome.Should().Be(SyncOutcome.DiscardLocal);
}

[Fact]
public async Task PostMarcacao_returns_AlreadyExists_on_409_Conflict()
{
    var h = new FakeHandler(new(new[] { Json(409, "{\"code\":\"CONFLICT\"}") }));
    var sut = MakeClient(h);
    (await sut.PostMarcacaoAsync(SampleMarcacao(), "AT")).Should().Be(SyncOutcome.AlreadyExists);
}

[Fact]
public async Task PostMarcacao_returns_Rejected_on_422()
{
    var h = new FakeHandler(new(new[] { Json(422, "{\"code\":\"FIM_DE_SEMANA_NAO_PERMITIDO\"}") }));
    var sut = MakeClient(h);
    (await sut.PostMarcacaoAsync(SampleMarcacao(), "AT")).Should().Be(SyncOutcome.Rejected);
}

[Fact]
public async Task PostMarcacao_body_includes_idempotency_key_and_origem()
{
    var h = new FakeHandler(new(new[] { Json(201, MarcacaoRespJson) }));
    var sut = MakeClient(h);
    await sut.PostMarcacaoAsync(SampleMarcacao(idem: "11111111-1111-4111-8111-111111111111", origem: "AGENTE_AUTOMATICO"), "AT");
    h.SentBodies[0].Should().Contain("11111111-1111-4111-8111-111111111111");
    h.SentBodies[0].Should().Contain("AGENTE_AUTOMATICO");
}

[Fact]
public async Task PostMarcacao_retries_on_503_then_succeeds()
{
    var h = new FakeHandler(new(new[] { Json(503,""), Json(503,""), Json(503,""), Json(201, MarcacaoRespJson) }));
    var sut = MakeClient(h, fastRetry: true); // delays curtos no teste
    (await sut.PostMarcacaoAsync(SampleMarcacao(), "AT")).Should().Be(SyncOutcome.Created);
}

[Fact]
public async Task PostMarcacao_returns_TransientFailure_when_retries_exhausted()
{
    var h = new FakeHandler(new(new[] { Json(503,""), Json(503,""), Json(503,""), Json(503,""), Json(503,""), Json(503,"") }));
    var sut = MakeClient(h, fastRetry: true);
    (await sut.PostMarcacaoAsync(SampleMarcacao(), "AT")).Should().Be(SyncOutcome.TransientFailure);
}

[Fact]
public async Task IsReadyAsync_false_on_503()
{
    var h = new FakeHandler(new(new[] { Json(503, "") }));
    (await MakeClient(h).IsReadyAsync()).Should().BeFalse();
}
```

> Retry com delays reais (1→2→4…s) tornaria os testes lentos: o construtor do client (ou o helper `MakeClient`) aceita uma policy de delays injetável; em teste passar delays de milissegundos (`fastRetry: true`). Em produção usar `AddAgentHttp` com os delays da Spec.

**Refatoração:** após green, extrair `Json(status, body)`, `SampleMarcacao(...)`, `SampleTerceiro()` e `MarcacaoRespJson` para `Timesheet.Agent.Tests/TestData.cs` (compartilhado com TASK-028 se já existir). Consolidar parsing de erro `{code,message}` num único `ApiError` record reutilizado por login, terceiro e marcação.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo | Ação | Descrição |
| ------- | ---- | --------- |
| `apps/agent/src/Timesheet.Agent.Infra.Http/ApiError.cs` | Criar | Record `{Code, Message}` do formato de erro padronizado do Backend |
| `apps/agent/src/Timesheet.Agent.Infra.Http/AuthException.cs` | Criar | Exceção com `Code` (do `ApiError`) — usada por login/refresh/terceiro |
| `apps/agent/src/Timesheet.Agent.Infra.Http/SyncOutcome.cs` | Criar | Enum: `Created, AlreadyExists, DiscardLocal, Rejected, TransientFailure` |
| `apps/agent/src/Timesheet.Agent.Infra.Http/Dtos.cs` | Criar | `AuthResult`, `LoginRequestDto`, `RefreshRequestDto`, `PostMarcacaoDto`, `CreateTerceiroDto` (request body real) |
| `apps/agent/src/Timesheet.Agent.Infra.Http/BackendClient.cs` | Criar | `IBackendClient` + impl: `LoginAsync`, `RefreshAsync`, `CreateTerceiroAsync`, `PostMarcacaoAsync`, `IsHealthyAsync`, `IsReadyAsync` |
| `apps/agent/src/Timesheet.Agent.Infra.Http/AgentHttpExtensions.cs` | Criar | `AddAgentHttp(IServiceCollection, string baseUrl)` — registra o `HttpClient` tipado de `IBackendClient` com Polly (circuit breaker + retry). NÃO registra TokenManager/DpapiTokenStore (TASK-035 estende este arquivo) |
| `apps/agent/src/Timesheet.Agent.Infra.Http/Timesheet.Agent.Infra.Http.csproj` | Modificar | Add `Microsoft.Extensions.Http.Polly` 8.0.*, `Microsoft.Extensions.DependencyInjection.Abstractions` 8.0.*; ProjectReference para `Infra.Db` |
| `apps/agent/src/Timesheet.Agent.Tests/InfraHttp/BackendClientTests.cs` | Criar | Testes acima (FakeHandler, login/refresh/terceiro/marcação/health/ready/retry) + helpers `Json`/`SampleMarcacao`/`SampleTerceiro` |

> **Fronteira de arquivos:** esta task NÃO cria `DpapiTokenStore.cs` nem `TokenManager.cs` — eles são da TASK-035. O `AgentHttpExtensions.AddAgentHttp` registra apenas o `IBackendClient` + Polly; a TASK-035 (sequencial, depende desta) estende este mesmo arquivo para registrar `DpapiTokenStore` e `TokenManager`. Como a dependência é sequencial, não há conflito de merge.

### Detalhamento Técnico

1. **Contrato HTTP — `POST /api/v1/marcacoes`** (consumido):

```
POST /api/v1/marcacoes
Content-Type: application/json
Authorization: Bearer <access_token>

Request body (valores reais):
{
  "tipo": "INICIO_JORNADA",              // enum: INICIO_JORNADA|SAIDA_ALMOCO|RETORNO_ALMOCO|FIM_JORNADA
  "horario_registrado": "2026-05-27T12:02:00Z",  // ISO 8601 UTC, obrigatório
  "horario_efetivo": "2026-05-27T12:00:00Z",      // ISO 8601 UTC, opcional (null se ausente)
  "origem": "AGENTE_AUTOMATICO",         // enum: AGENTE_AUTOMATICO|AGENTE_CONFIRMADO (AJUSTE_WEB nunca do Agente)
  "idempotency_key": "11111111-1111-4111-8111-111111111111"  // UUID v4, = id local
}

Response 201: { "id","jornada_id","tipo","horario_registrado","horario_efetivo","origem","status","confirmado_pelo_usuario","idempotency_key","criada_em" }
Response 409: { "code": "AJUSTE_WEB_WINS" }  → SyncOutcome.DiscardLocal
Response 409: { "code": "CONFLICT" }         → SyncOutcome.AlreadyExists (sucesso idempotente)
Response 422: { "code": "FIM_DE_SEMANA_NAO_PERMITIDO" } → SyncOutcome.Rejected
Response 401: token inválido/expirado → propagar AuthException(code="UNAUTHORIZED") (o TokenManager da TASK-035 trata refresh; aqui só propaga)
```

Mapeamento de status → `SyncOutcome` no `PostMarcacaoAsync`:
- 201 → `Created`; 409 `AJUSTE_WEB_WINS` → `DiscardLocal`; 409 `CONFLICT` → `AlreadyExists`; 422 → `Rejected`; 5xx/timeout após retries esgotados → `TransientFailure` (reenfileira).

`PostMarcacaoAsync(MarcacaoLocal m, string accessToken, CancellationToken ct = default)` — esta é a assinatura consumida pelo Service host (TASK-033). Monta `PostMarcacaoDto` a partir do `MarcacaoLocal` (campos `Tipo`, `HorarioRegistrado`, `HorarioEfetivo`, `Origem`, `idempotency_key = m.Id`), adiciona header `Authorization: Bearer {accessToken}` ao request.

2. **Contrato HTTP — `POST /api/v1/auth/login`** (consumido):

```
POST /api/v1/auth/login
Content-Type: application/json
{ "email": "maria@x.com", "senha": "Senha123" }
Response 200: { "access_token","refresh_token","terceiro_id","expires_in": 900 }
Response 401: { "code":"UNAUTHORIZED" } ; Response 429: rate limit (5/min)
```

3. **Contrato HTTP — `POST /api/v1/auth/refresh`** (consumido):

```
POST /api/v1/auth/refresh
{ "refresh_token": "RT" }
Response 200: { "access_token","refresh_token","expires_in": 900 }   // rotation: RT antigo é invalidado
Response 401: cadeia revogada → forçar novo login (propaga AuthException code="UNAUTHORIZED")
```

`RefreshAsync(string refreshToken)` retorna `AuthResult` (com `TerceiroId=null`, pois o refresh não devolve esse campo).

4. **Contrato HTTP — `POST /api/v1/terceiros`** (consumido no onboarding — TASK-034):

```
POST /api/v1/terceiros
Content-Type: application/json
{
  "nome": "Maria Silva",
  "empresa_nome": "ACME LTDA",
  "empresa_cnpj": "11222333000181",      // 14 dígitos, sem máscara
  "horario_inicio_jornada": "09:00:00",  // HH:MM:SS (time)
  "horario_saida_almoco": "12:00:00",
  "horario_retorno_almoco": "13:00:00",
  "horario_fim_jornada": "18:00:00",
  "trabalha_fim_de_semana": false,
  "email_contato": "maria@x.com",
  "email_destinatario_relatorio": "rh@empresa.com",  // opcional, pode ser null
  "senha": "Senha123",
  "senha_confirmacao": "Senha123"
}
Response 201: { "terceiro_id", "criado_em" }
Response 403: { "code":"SETUP_ALREADY_DONE" }  → lança AuthException(code="SETUP_ALREADY_DONE"); onboarding já feito, abrir browser direto
Response 422: { "code":"VALIDATION_ERROR", "details":[{"field":"empresa_cnpj","issue":"CNPJ inválido"}] }
```

`CreateTerceiroAsync(CreateTerceiroDto dto)` retorna `{terceiro_id, criado_em}` (record simples) no 201; lança `AuthException` com o `code` em 403/422.

5. **Polly** — em `AddAgentHttp`: `AddPolicyHandler` com `WaitAndRetryAsync(5, attempt => TimeSpan.FromSeconds(Math.Pow(2, attempt-1)))` (1,2,4,8,16s) e `CircuitBreakerAsync(5, TimeSpan.FromSeconds(60))`; `HttpClient.Timeout = TimeSpan.FromSeconds(10)`. Retry só em `HttpRequestException`, `TimeoutRejectedException` e status 5xx/`TransientHttpError` — nunca em 4xx (4xx é resposta de negócio, não falha transiente). Para testes, expor os delays como parâmetro injetável (ex.: `MakeClient(handler, fastRetry: true)` usa delays de milissegundos).

6. **`BackendClient`** — recebe `HttpClient` (configurado por DI com base address `http://127.0.0.1:8765` e Polly). Usa `System.Text.Json` para serializar/desserializar. Parsing de erro `{code, message}` num único `ApiError` reutilizado. `IsHealthyAsync`/`IsReadyAsync` fazem GET sem auth e retornam bool (200 → true; qualquer outro/exceção → false), sem lançar.

**Contrato com camadas adjacentes:**

```
Produz para: Service host (TASK-033) — loop de sync
  - IBackendClient.PostMarcacaoAsync(MarcacaoLocal m, string accessToken, CancellationToken ct) → SyncOutcome
    host decide: Created/AlreadyExists/DiscardLocal/Rejected ⇒ MarcarSincronizadaAsync; TransientFailure ⇒ RegistrarFalhaSyncAsync + backoff
  - IBackendClient.IsHealthyAsync(CancellationToken ct) / IsReadyAsync(CancellationToken ct) → gate do loop (só drena fila se up)
Produz para: WPF onboarding (TASK-034)
  - IBackendClient.CreateTerceiroAsync (201 / 403 SETUP_ALREADY_DONE / 422) e LoginAsync
Produz para: TokenManager (TASK-035)
  - IBackendClient.RefreshAsync(string refreshToken) → AuthResult (rotation) ; lança AuthException code="UNAUTHORIZED" se cadeia revogada
Consome de: Backend FastAPI (Phase 3, done) — contratos HTTP literais acima
Consome de: Fundação (TASK-028) — MarcacaoLocal (entidade), constantes MarcacaoTipo/OrigemMarcacao
```
