using FluentAssertions;
using Microsoft.Extensions.Http;
using Polly;
using Polly.Extensions.Http;
using Timesheet.Agent.Infra.Http;
using Xunit;

namespace Timesheet.Agent.Tests.InfraHttp;

public class BackendClientTests
{
    // ── fake handler ──────────────────────────────────────────────────────────

    private sealed class FakeHandler(Queue<HttpResponseMessage> responses) : HttpMessageHandler
    {
        public List<string> SentBodies { get; } = new();

        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage req, CancellationToken ct)
        {
            if (req.Content is not null)
                SentBodies.Add(await req.Content.ReadAsStringAsync(ct));
            return responses.Dequeue();
        }
    }

    private static BackendClient MakeClient(FakeHandler handler, bool fastRetry = false)
    {
        HttpMessageHandler innerHandler = handler;

        if (fastRetry)
        {
            var retryPolicy = HttpPolicyExtensions
                .HandleTransientHttpError()
                .WaitAndRetryAsync(5, attempt => TimeSpan.FromMilliseconds(attempt * 10));

            innerHandler = new PolicyHttpMessageHandler(retryPolicy)
            {
                InnerHandler = handler
            };
        }

        var httpClient = new HttpClient(innerHandler)
        {
            BaseAddress = new Uri("http://127.0.0.1:8765")
        };

        return new BackendClient(httpClient);
    }

    // ── login ─────────────────────────────────────────────────────────────────

    [Fact]
    public async Task LoginAsync_parses_tokens_on_200()
    {
        var h = new FakeHandler(new(new[] { TestData.JsonResponse(200, """{"access_token":"AT","refresh_token":"RT","terceiro_id":"u1","expires_in":900}""") }));
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
        var h = new FakeHandler(new(new[] { TestData.JsonResponse(401, """{"code":"UNAUTHORIZED","message":"E-mail ou senha invalidos"}""") }));
        var sut = MakeClient(h);
        var act = async () => await sut.LoginAsync("x@x.com", "bad");
        (await act.Should().ThrowAsync<AuthException>()).Which.Code.Should().Be("UNAUTHORIZED");
    }

    // ── refresh ───────────────────────────────────────────────────────────────

    [Fact]
    public async Task RefreshAsync_parses_rotated_tokens_on_200()
    {
        var h = new FakeHandler(new(new[] { TestData.JsonResponse(200, """{"access_token":"AT2","refresh_token":"RT2","expires_in":900}""") }));
        var sut = MakeClient(h);
        var r = await sut.RefreshAsync("RT");
        r.AccessToken.Should().Be("AT2");
        r.RefreshToken.Should().Be("RT2");
        r.ExpiresIn.Should().Be(900);
    }

    // ── terceiros ─────────────────────────────────────────────────────────────

    [Fact]
    public async Task CreateTerceiroAsync_throws_SetupAlreadyDone_on_403()
    {
        var h = new FakeHandler(new(new[] { TestData.JsonResponse(403, """{"code":"SETUP_ALREADY_DONE"}""") }));
        var sut = MakeClient(h);
        var act = async () => await sut.CreateTerceiroAsync(TestData.SampleTerceiro());
        (await act.Should().ThrowAsync<AuthException>()).Which.Code.Should().Be("SETUP_ALREADY_DONE");
    }

    // ── marcacoes ─────────────────────────────────────────────────────────────

    [Fact]
    public async Task PostMarcacao_returns_DiscardLocal_on_409_AjusteWebWins()
    {
        var h = new FakeHandler(new(new[] { TestData.JsonResponse(409, """{"code":"AJUSTE_WEB_WINS"}""") }));
        var sut = MakeClient(h);
        var outcome = await sut.PostMarcacaoAsync(TestData.SampleMarcacao(), "AT");
        outcome.Should().Be(SyncOutcome.DiscardLocal);
    }

    [Fact]
    public async Task PostMarcacao_returns_AlreadyExists_on_409_Conflict()
    {
        var h = new FakeHandler(new(new[] { TestData.JsonResponse(409, """{"code":"CONFLICT"}""") }));
        var sut = MakeClient(h);
        (await sut.PostMarcacaoAsync(TestData.SampleMarcacao(), "AT")).Should().Be(SyncOutcome.AlreadyExists);
    }

    [Fact]
    public async Task PostMarcacao_returns_Rejected_on_422()
    {
        var h = new FakeHandler(new(new[] { TestData.JsonResponse(422, """{"code":"FIM_DE_SEMANA_NAO_PERMITIDO"}""") }));
        var sut = MakeClient(h);
        (await sut.PostMarcacaoAsync(TestData.SampleMarcacao(), "AT")).Should().Be(SyncOutcome.Rejected);
    }

    [Fact]
    public async Task PostMarcacao_body_includes_idempotency_key_and_origem()
    {
        var h = new FakeHandler(new(new[] { TestData.JsonResponse(201, TestData.MarcacaoRespJson) }));
        var sut = MakeClient(h);
        await sut.PostMarcacaoAsync(TestData.SampleMarcacao(idem: "11111111-1111-4111-8111-111111111111", origem: "AGENTE_AUTOMATICO"), "AT");
        h.SentBodies[0].Should().Contain("11111111-1111-4111-8111-111111111111");
        h.SentBodies[0].Should().Contain("AGENTE_AUTOMATICO");
    }

    [Fact]
    public async Task PostMarcacao_retries_on_503_then_succeeds()
    {
        var h = new FakeHandler(new(new[] { TestData.JsonResponse(503, ""), TestData.JsonResponse(503, ""), TestData.JsonResponse(503, ""), TestData.JsonResponse(201, TestData.MarcacaoRespJson) }));
        var sut = MakeClient(h, fastRetry: true);
        (await sut.PostMarcacaoAsync(TestData.SampleMarcacao(), "AT")).Should().Be(SyncOutcome.Created);
    }

    [Fact]
    public async Task PostMarcacao_returns_TransientFailure_when_retries_exhausted()
    {
        var h = new FakeHandler(new(new[] { TestData.JsonResponse(503, ""), TestData.JsonResponse(503, ""), TestData.JsonResponse(503, ""), TestData.JsonResponse(503, ""), TestData.JsonResponse(503, ""), TestData.JsonResponse(503, "") }));
        var sut = MakeClient(h, fastRetry: true);
        (await sut.PostMarcacaoAsync(TestData.SampleMarcacao(), "AT")).Should().Be(SyncOutcome.TransientFailure);
    }

    // ── health / ready ────────────────────────────────────────────────────────

    [Fact]
    public async Task IsReadyAsync_false_on_503()
    {
        var h = new FakeHandler(new(new[] { TestData.JsonResponse(503, "") }));
        (await MakeClient(h).IsReadyAsync()).Should().BeFalse();
    }
}
