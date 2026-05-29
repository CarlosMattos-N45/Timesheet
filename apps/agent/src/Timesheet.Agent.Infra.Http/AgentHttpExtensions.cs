using Microsoft.Extensions.DependencyInjection;
using Polly;
using Polly.Extensions.Http;

namespace Timesheet.Agent.Infra.Http;

public static class AgentHttpExtensions
{
    public static IServiceCollection AddAgentHttp(this IServiceCollection services, string baseUrl)
    {
        var retryPolicy = HttpPolicyExtensions
            .HandleTransientHttpError()
            .WaitAndRetryAsync(5, attempt => TimeSpan.FromSeconds(Math.Pow(2, attempt - 1)));

        var circuitBreakerPolicy = HttpPolicyExtensions
            .HandleTransientHttpError()
            .CircuitBreakerAsync(5, TimeSpan.FromSeconds(60));

        services
            .AddHttpClient<IBackendClient, BackendClient>(client =>
            {
                client.BaseAddress = new Uri(baseUrl);
                client.Timeout = TimeSpan.FromSeconds(10);
            })
            .AddPolicyHandler(retryPolicy)
            .AddPolicyHandler(circuitBreakerPolicy);

#pragma warning disable CA1416 // DpapiTokenStore é Windows-only; o agente só é implantado em Windows
        services.AddSingleton<ITokenStore, DpapiTokenStore>();
#pragma warning restore CA1416
        services.AddScoped<ITokenManager, TokenManager>();
        services.AddScoped<TokenManager>(sp => (TokenManager)sp.GetRequiredService<ITokenManager>());

        return services;
    }
}
