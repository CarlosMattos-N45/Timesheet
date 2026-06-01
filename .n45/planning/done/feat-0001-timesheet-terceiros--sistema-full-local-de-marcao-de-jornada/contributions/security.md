---
created_at: "2026-05-27 12:02:37"
from: security
n45_version: 0.2.0
spec_id: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
---
### Requisitos de Implementação — Crítico / Alto

- **[Crítico]** A chave SQLCipher derivada da senha do Terceiro via Argon2id deve usar um salt armazenado separado do banco cifrado (`%APPDATA%\TimesheetTerceiros\key.salt`). Se salt e banco estiverem no mesmo local sem proteção adicional, um invasor com acesso ao sistema de arquivos pode reutilizar o salt para derivar a chave por força bruta. O salt deve ser gerado na instalação (32 bytes, CSPRNG) e, se possível, protegido com DPAPI antes de persistir.
- **[Crítico]** A senha no `smtp_config.password_enc` é cifrada com AES-GCM usando chave derivada da senha do Terceiro. A Spec não define onde o IV/nonce fica armazenado nem a âncora de derivação. Requisito: nonce de 12 bytes único por cifração, armazenado concatenado ao ciphertext (`nonce || ciphertext || tag`). A derivação para AES-GCM deve usar chave separada da chave SQLCipher (dois contextos distintos via `HKDF-Expand` com `info="smtp"` e `info="db"` respectivamente).
- **[Crítico]** `PUT /api/v1/terceiros/me/senha` deve revogar **todos** os refresh tokens ativos do Terceiro imediatamente após a troca de senha bem-sucedida. A troca de senha invalida a derivação da chave SQLCipher (se usada para derivar a chave do banco) — documentar esse impacto e planejar re-derivação/re-cifragem ou uso de chave mestra independente.
- **[Alto]** Os tokens JWT (`jwt_access_token`, `jwt_refresh_token`) no `configuracao_local` do Agente devem ser protegidos via DPAPI (`ProtectedData.Protect`) antes de persistir no SQLite local. A Spec menciona "DPAPI protected" apenas para o refresh token — estender para access token ou garantir que o access token em memória não seja persistido em texto claro.
- **[Alto]** Refresh token rotation: ao detectar reuso de token revogado, o sistema deve revogar **toda a cadeia** de refresh tokens do Terceiro (proteção contra token theft). A Spec menciona isso na seção RF-009, mas deve ser implementado explicitamente no serviço de auth.
- **[Alto]** O Backend expõe `/docs` (Swagger UI) em `http://127.0.0.1:8765/docs` por padrão via FastAPI. Em produção (binário PyInstaller), desabilitar completamente o OpenAPI UI (`docs_url=None, redoc_url=None, openapi_url=None`) — a documentação deve ser gerada apenas em ambiente de desenvolvimento via flag de ambiente.
- **[Alto]** Rate limiting obrigatório nos endpoints: `POST /auth/login` (≤5 tentativas/min por IP/email) e `POST /auth/refresh` (≤10/min). Sem rate limiting, a binding em `127.0.0.1` não é proteção suficiente — processo local malicioso pode fazer brute force. Usar middleware de rate limit (ex: `slowapi` + `limits`).
- **[Alto]** Validação CNPJ com algoritmo módulo 11 deve estar implementada server-side no Backend (não apenas no Frontend/Agente). Qualquer entrada de `empresa_cnpj` deve ser revalidada no Backend antes de persistir.
- **[Alto]** O endpoint `POST /api/v1/terceiros` cria o primeiro (e único) Terceiro. Após o cadastro inicial, este endpoint deve ser desativado ou protegido com flag de configuração para impedir criação de múltiplos Terceiros (o sistema é single-tenant).

### Requisitos de Implementação — Médio / Baixo

- **[Médio]** O PDF gerado pelo WeasyPrint contém PII (nome, empresa, CNPJ, jornada). O arquivo em disco deve ter permissões restritas ao usuário do serviço (`TimesheetBackend`). Usar ACLs no MSI para definir permissões na pasta de PDFs durante a instalação.
- **[Médio]** Logs rotativos do Backend (structlog) e do Agente (Serilog) não devem incluir senhas, tokens JWT, conteúdo de `before_json`/`after_json` completo ou PII desnecessário. Implementar `redact` de campos sensíveis no pipeline de logging antes de qualquer sink.
- **[Médio]** `GET /api/v1/auditoria` deve exigir autenticação JWT (está listado com `auth_dep` implícito nos outros endpoints, mas não explicitado no contrato do endpoint de auditoria). Confirmar que `Depends(auth_dep)` está presente.
- **[Médio]** O timeout de inatividade de sessão Web (client-side) deve ser implementado: após X min sem interação no browser, redirecionar para `/login` e limpar tokens em memória. Access token de 15 min + refresh automático é insuficiente como controle de sessão visual.
- **[Médio]** Headers de segurança HTTP devem ser adicionados via middleware FastAPI: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Content-Security-Policy` adequado para SPA local. Mesmo em `127.0.0.1`, ataques DNS rebinding são possíveis — adicionar validação do header `Host` para aceitar apenas `127.0.0.1` e `localhost`.
- **[Médio]** O named pipe `\\.\pipe\TimesheetAgent` deve verificar a identidade do processo conectado via `GetNamedPipeClientProcessId` + comparação de hash do executável ou ACL do pipe restrita ao SID do serviço, para impedir que processos locais maliciosos injetem mensagens `DIALOG_RESPONSE`.
- **[Baixo]** O aviso de privacidade (`privacy_acceptance`) armazenado no banco SQLCipher cobre a rastreabilidade de aceite. Garantir que `versao_aviso` seja um identificador versionado (ex: `"1.0"`) e atualizado a cada revisão do texto, permitindo re-exibição em futuras versões.
- **[Baixo]** A purga de PDFs com mais de 24 meses deve também apagar o arquivo físico em disco, não apenas o registro em `relatorio_gerado`. Registrar a operação de purga em log de auditoria.

### Para tasks

- `50a8844c7d`: validação CNPJ server-side, rate limiting em `/auth/login` e `/auth/refresh`, revogar todos refresh tokens na troca de senha, desabilitar `/docs` em produção, `Depends(auth_dep)` em `/auditoria`, revogação de cadeia em reuso de token revogado, validação header `Host` middleware.
- `844dd534f4`: headers de segurança HTTP (`X-Content-Type-Options`, `X-Frame-Options`, `CSP`), timeout de sessão client-side, `redact` de campos sensíveis nos logs do Frontend.
- `82654b3833`: proteção DPAPI para access token e refresh token no Agente, verificação de identidade de processo no named pipe, salt separado + DPAPI para chave SQLCipher, nonce/IV AES-GCM correto para `smtp_config.password_enc`, dois contextos HKDF separados para chave DB e chave SMTP, ACLs na pasta de PDFs via MSI, `redact` de campos sensíveis nos logs do Backend/Agente, purga física de arquivos PDF + log de auditoria.

### Conflitos com outras áreas

- ⚠ Conflito com arquitetura: a derivação da chave SQLCipher a partir da senha do Terceiro cria dependência entre autenticação e criptografia em repouso. Se a senha for trocada, a chave do banco muda — requer re-cifragem do banco ou uso de chave mestra (KEK) protegida por DPAPI que independe da senha. Recomendo: usar KEK gerada na instalação, protegida por DPAPI, sem derivação da senha. Isso elimina o problema de re-cifragem e é mais seguro.
