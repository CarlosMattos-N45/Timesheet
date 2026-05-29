using System.Runtime.Versioning;
using System.Security.Cryptography;
using System.Text;

namespace Timesheet.Agent.Infra.Http;

/// <summary>
/// Abstração de proteção de token — permite fake em testes cross-platform.
/// </summary>
public interface ITokenStore
{
    string Protect(string plaintext);
    string Unprotect(string blobBase64);
}

/// <summary>
/// Implementação de ITokenStore usando DPAPI (ProtectedData.CurrentUser).
/// Só funciona em Windows.
/// </summary>
[SupportedOSPlatform("windows")]
public sealed class DpapiTokenStore : ITokenStore
{
    public string Protect(string plaintext)
    {
        var bytes = Encoding.UTF8.GetBytes(plaintext);
        var encrypted = ProtectedData.Protect(bytes, null, DataProtectionScope.CurrentUser);
        return Convert.ToBase64String(encrypted);
    }

    public string Unprotect(string blobBase64)
    {
        var encrypted = Convert.FromBase64String(blobBase64);
        var bytes = ProtectedData.Unprotect(encrypted, null, DataProtectionScope.CurrentUser);
        return Encoding.UTF8.GetString(bytes);
    }
}
