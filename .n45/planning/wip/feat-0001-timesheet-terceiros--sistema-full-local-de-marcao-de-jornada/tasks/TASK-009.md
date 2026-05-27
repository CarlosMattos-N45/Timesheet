---
checkpoint: null
complexity: M
created_at: "2026-05-27 15:58:55"
criteria:
    - done: false
      test: cd apps/api && pytest tests/test_crypto.py -k test_ensure_kek_generates_new_file_when_absent
      text: ensure_kek gera novo arquivo KEK de 32 bytes quando ausente
    - done: false
      test: cd apps/api && pytest tests/test_crypto.py -k test_ensure_kek_idempotent_when_file_exists
      text: ensure_kek e idempotente quando arquivo ja existe
    - done: false
      test: cd apps/api && pytest tests/test_crypto.py -k test_ensure_kek_file_permissions_restricted
      text: Arquivo KEK em POSIX tem permissoes 0o600
    - done: false
      test: cd apps/api && pytest tests/test_crypto.py -k test_ensure_kek_refuses_plain_fallback
      text: ensure_kek recusa fallback em nao-Windows sem TIMESHEET_ALLOW_PLAIN_KEK
    - done: false
      test: cd apps/api && pytest tests/test_crypto.py -k test_derive_subkey_deterministic_per_context
      text: derive_subkey e deterministico para o mesmo contexto
    - done: false
      test: cd apps/api && pytest tests/test_crypto.py -k test_derive_subkey_isolated_between_contexts
      text: derive_subkey produz chaves distintas para contextos diferentes (db vs smtp)
    - done: false
      test: cd apps/api && pytest tests/test_crypto.py -k test_aes_gcm_roundtrip
      text: aes_gcm encrypt+decrypt faz round-trip preservando plaintext
    - done: false
      test: cd apps/api && pytest tests/test_crypto.py -k test_aes_gcm_uses_fresh_nonce_per_call
      text: aes_gcm gera nonce CSPRNG distinto por chamada (resultados diferentes para mesmo plaintext)
    - done: false
      test: cd apps/api && pytest tests/test_crypto.py -k test_aes_gcm_rejects_wrong_key
      text: aes_gcm_decrypt levanta InvalidTag com chave errada
    - done: false
      test: cd apps/api && pytest tests/test_crypto.py -k test_format_db_cipher_key_is_hex64
      text: format_db_cipher_key retorna 64 chars hex
    - done: false
      test: grep -E cryptography apps/api/pyproject.toml
      text: cryptography 43 declarado em pyproject.toml
    - done: false
      test: cd apps/api && ruff check .
      text: ruff check sem warnings
    - done: false
      test: cd apps/api && mypy --strict app
      text: mypy --strict app sem erros
    - done: false
      text: Testes passando com cobertura >= 80%
    - done: false
      test: make smoke
      text: make smoke Phase 1 continua passando
deps:
    - TASK-006
    - TASK-008
id: TASK-009
linter: cd apps/api && ruff check . && mypy --strict app
n45_version: 0.2.0
persona: backend
phase: Phase 2 — Dados
roadmap: feat-0001-timesheet-terceiros--sistema-full-local-de-marcao-de-jornada
status: pending
tdd:
    green: false
    red: false
    refactor: false
tests: cd apps/api && pytest tests/test_crypto.py
title: 'Crypto module: KEK ensure (DPAPI/fallback) + HKDF-Expand subkeys (db, smtp) + AES-GCM helpers'
updated_at: "2026-05-27 15:58:55"
---
## Contexto

Phase 2 — Dados precisa estabelecer a base criptográfica que protege dados sensíveis em repouso. Duas necessidades concretas:

1. **KEK (Key Encryption Key)**: chave-mãe imutável de 32 bytes (256 bits), gerada na instalação por CSPRNG e protegida por DPAPI (Windows). A partir dela, via `HKDF-Expand` com contextos `info="db"` e `info="smtp"`, derivam-se duas subchaves distintas — uma para cifrar o banco via SQLCipher (PRAGMA `key`) e outra para AES-GCM dos campos `smtp_config.username_enc` / `password_enc`. A KEK **não deriva da senha do Terceiro** — trocar senha não re-cifra nada (decisão registrada em §10 da Spec).
2. **AES-GCM helpers**: cifrar/decifrar strings curtas (credenciais SMTP) com nonce de 12 bytes gerado por CSPRNG e formato compacto `nonce || ciphertext || tag` em base64 url-safe.

Estado atual:
- Sem módulo de crypto no backend.
- `apps/api/pyproject.toml` não declara `cryptography` nem `pywin32`.
- `apps/api/app/core/config.py` (após TASK-008) lê `TIMESHEET_KEK_PATH` (introduzido em `.env.example` pela TASK-006).
- DPAPI é **Windows-only**. Em CI/macOS/Linux, esta task fornece um fallback **com aviso explícito** que escreve a KEK em claro no disco (suficiente para dev/teste; produção só roda Windows). O fallback é gateado por env var `TIMESHEET_ALLOW_PLAIN_KEK=1` para evitar uso acidental em prod.

Esta task **não** implementa SQLCipher integration (a chave gerada será efetivamente aplicada na conexão do banco apenas quando `TIMESHEET_DB_CIPHER_KEY` for setada — a TASK-008 já consome essa var; aqui apenas se documenta como derivá-la). Esta task **só** cobre o módulo de crypto (KEK + AES-GCM) e seus testes.

## Comportamento Esperado

| Entrada / Ação                                                                                  | Saída / Efeito esperado                                                                                                              |
| ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `ensure_kek(path)` quando `path` não existe (Windows + DPAPI disponível)                        | Gera 32 bytes via `secrets.token_bytes(32)`, protege via `win32crypt.CryptProtectData`, escreve em `path` com permissões restritas; retorna bytes em claro |
| `ensure_kek(path)` quando `path` não existe (não-Windows, sem `TIMESHEET_ALLOW_PLAIN_KEK`)      | Levanta `RuntimeError("DPAPI ausente: configure TIMESHEET_ALLOW_PLAIN_KEK=1 apenas em dev")`                                         |
| `ensure_kek(path)` quando `path` não existe (não-Windows, `TIMESHEET_ALLOW_PLAIN_KEK=1`)        | Gera 32 bytes via CSPRNG, escreve em claro com permissões 0o600, retorna bytes; loga `WARNING` via stdlib logging                    |
| `ensure_kek(path)` quando `path` já existe                                                      | Lê arquivo, desprotege via DPAPI (ou retorna em claro no fallback), retorna 32 bytes; nunca regenera                                 |
| `derive_subkey(kek, info=b"db")`                                                                | Retorna 32 bytes determinísticos para o contexto `db` (HKDF-Expand sem salt, SHA-256)                                                |
| `derive_subkey(kek, info=b"smtp")`                                                              | Retorna 32 bytes determinísticos diferentes da subkey `db`                                                                           |
| `derive_subkey(kek, info=b"db") == derive_subkey(kek, info=b"db")` (mesmo kek, mesmo info)      | Bytes idênticos (determinístico)                                                                                                     |
| `derive_subkey(kek, info=b"db") != derive_subkey(kek, info=b"smtp")` (contextos distintos)      | Bytes diferentes (HKDF info funciona)                                                                                                |
| `aes_gcm_encrypt(subkey, b"senha-smtp-teste")`                                                  | Retorna string base64 url-safe sem padding contendo `nonce(12) || ciphertext || tag(16)`                                             |
| `aes_gcm_decrypt(subkey, encrypted)`                                                            | Retorna `b"senha-smtp-teste"` exatamente; round-trip perfeito                                                                        |
| `aes_gcm_decrypt(subkey_errada, encrypted)`                                                     | Levanta `InvalidTag` (do `cryptography`)                                                                                             |
| `aes_gcm_encrypt(subkey, b"x")` chamado 2 vezes para mesmo plaintext                            | Resultados **diferentes** (nonce CSPRNG único por cifragem); ambos decifram corretamente                                             |
| `format_db_cipher_key(subkey)`                                                                  | Retorna string hex 64 chars (formato esperado pelo PRAGMA `key = "x'<hex>'"` do SQLCipher e pela var `TIMESHEET_DB_CIPHER_KEY`)      |
| Permissões do arquivo KEK em sistema POSIX                                                      | `0o600` (somente owner read/write); validado por `stat.S_IMODE`                                                                       |
| Permissões do arquivo KEK no Windows                                                            | Aplicação no-op (DPAPI já protege); arquivo existe e é legível pelo processo atual                                                  |

## TDD (red → green → refactor)

**Testes a escrever antes da implementação** (`apps/api/tests/test_crypto.py`):

```python
from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

import pytest

from app.core.crypto import (
    aes_gcm_decrypt,
    aes_gcm_encrypt,
    derive_subkey,
    ensure_kek,
    format_db_cipher_key,
)
from cryptography.exceptions import InvalidTag


def test_ensure_kek_generates_new_file_when_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if sys.platform != "win32":
        monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    path = tmp_path / "key.kek"
    kek = ensure_kek(path)
    assert len(kek) == 32
    assert path.exists()


def test_ensure_kek_idempotent_when_file_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if sys.platform != "win32":
        monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    path = tmp_path / "key.kek"
    kek1 = ensure_kek(path)
    kek2 = ensure_kek(path)
    assert kek1 == kek2, "ensure_kek deve ser idempotente quando o arquivo existe"


def test_ensure_kek_file_permissions_restricted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if sys.platform == "win32":
        pytest.skip("Permissoes POSIX nao aplicaveis no Windows")
    monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    path = tmp_path / "key.kek"
    ensure_kek(path)
    mode = stat.S_IMODE(os.stat(path).st_mode)
    assert mode == 0o600, f"Permissao esperada 0o600, obtida 0o{mode:o}"


def test_ensure_kek_refuses_plain_fallback_in_non_windows_without_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if sys.platform == "win32":
        pytest.skip("Fallback so se aplica fora do Windows")
    monkeypatch.delenv("TIMESHEET_ALLOW_PLAIN_KEK", raising=False)
    with pytest.raises(RuntimeError, match="DPAPI"):
        ensure_kek(tmp_path / "key.kek")


def test_derive_subkey_deterministic_per_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if sys.platform != "win32":
        monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    kek = ensure_kek(tmp_path / "k.kek")
    sub1 = derive_subkey(kek, info=b"db")
    sub2 = derive_subkey(kek, info=b"db")
    assert sub1 == sub2
    assert len(sub1) == 32


def test_derive_subkey_isolated_between_contexts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if sys.platform != "win32":
        monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    kek = ensure_kek(tmp_path / "k.kek")
    sub_db = derive_subkey(kek, info=b"db")
    sub_smtp = derive_subkey(kek, info=b"smtp")
    assert sub_db != sub_smtp


def test_aes_gcm_roundtrip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if sys.platform != "win32":
        monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    kek = ensure_kek(tmp_path / "k.kek")
    subkey = derive_subkey(kek, info=b"smtp")
    plaintext = b"senha-smtp-do-usuario"
    encrypted = aes_gcm_encrypt(subkey, plaintext)
    assert isinstance(encrypted, str) and len(encrypted) > 0
    recovered = aes_gcm_decrypt(subkey, encrypted)
    assert recovered == plaintext


def test_aes_gcm_uses_fresh_nonce_per_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if sys.platform != "win32":
        monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    kek = ensure_kek(tmp_path / "k.kek")
    subkey = derive_subkey(kek, info=b"smtp")
    pt = b"x"
    c1 = aes_gcm_encrypt(subkey, pt)
    c2 = aes_gcm_encrypt(subkey, pt)
    assert c1 != c2, "nonce CSPRNG deve gerar resultados distintos"
    assert aes_gcm_decrypt(subkey, c1) == pt
    assert aes_gcm_decrypt(subkey, c2) == pt


def test_aes_gcm_rejects_wrong_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if sys.platform != "win32":
        monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    kek = ensure_kek(tmp_path / "k.kek")
    subkey_ok = derive_subkey(kek, info=b"smtp")
    subkey_wrong = derive_subkey(kek, info=b"db")
    encrypted = aes_gcm_encrypt(subkey_ok, b"segredo")
    with pytest.raises(InvalidTag):
        aes_gcm_decrypt(subkey_wrong, encrypted)


def test_format_db_cipher_key_is_hex64(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if sys.platform != "win32":
        monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    kek = ensure_kek(tmp_path / "k.kek")
    subkey = derive_subkey(kek, info=b"db")
    hex64 = format_db_cipher_key(subkey)
    assert len(hex64) == 64
    int(hex64, 16)  # raises ValueError se nao for hex valido
```

> Os testes usam `cryptography` (incluído nas runtime deps) e marcam `pytest.skip` para casos plataforma-específicos. O fallback fora do Windows usa `TIMESHEET_ALLOW_PLAIN_KEK=1` para destravar o caminho em CI Linux.

**Refatoração:** Após o green, garantir que mensagens de log de fallback contenham contexto claro ("PLAIN_KEK_FALLBACK ativo — uso apenas em dev"). Nenhuma outra refatoração esperada.

## O que Implementar

### Arquivos a Criar ou Modificar

| Arquivo                              | Ação      | Descrição                                                                                                                |
| ------------------------------------ | --------- | ------------------------------------------------------------------------------------------------------------------------ |
| `apps/api/pyproject.toml`            | Modificar | Adicionar `cryptography==43.*` em `dependencies` (KEK proteção opcional via `pywin32` é runtime extra Windows-only)      |
| `apps/api/app/core/crypto.py`        | Criar     | Módulo com `ensure_kek`, `derive_subkey`, `aes_gcm_encrypt`, `aes_gcm_decrypt`, `format_db_cipher_key`                    |
| `apps/api/tests/test_crypto.py`      | Criar     | Suite acima (10 testes)                                                                                                  |

> `pywin32` **não** é adicionado neste task. Em Windows com DPAPI, importamos via `try/except ImportError` em `app/core/crypto.py` e tratamos ausência como erro só na branch Windows-com-flag-faltando. CI e dev em Linux usam o fallback flag. A instalação real do `pywin32` fica para a Phase 6 (empacotamento Windows) — aqui é opcional.

### Detalhamento Técnico

**1. Dependências (`apps/api/pyproject.toml`):**

```toml
dependencies = [
  "fastapi==0.115.*",
  "uvicorn[standard]==0.32.*",
  "pydantic==2.9.*",
  "pydantic-settings==2.6.*",
  "structlog==24.4.*",
  "sqlalchemy==2.0.*",
  "alembic==1.13.*",
  "aiosqlite==0.20.*",
  "cryptography==43.*",
]
```

(Manter exatamente o que TASK-007 deixou + adicionar `cryptography`.)

**2. `apps/api/app/core/crypto.py`:**

```python
"""Cryptographic primitives for at-rest protection.

KEK lifecycle:
- Generated once at install time (32 bytes CSPRNG).
- Protected by DPAPI on Windows (production); plain bytes on disk in dev fallback.
- Never derived from user password (immutable by design).

Subkeys (32 bytes each) are derived via HKDF-Expand(SHA-256) with distinct
``info`` contexts so that compromise of one context does not expose the other:

- ``info=b"db"`` -> SQLCipher PRAGMA key.
- ``info=b"smtp"`` -> AES-GCM key for ``smtp_config.username_enc`` and
  ``smtp_config.password_enc``.
"""

from __future__ import annotations

import base64
import logging
import os
import secrets
import sys
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDFExpand

logger = logging.getLogger(__name__)

KEK_SIZE = 32  # 256 bits
NONCE_SIZE = 12  # 96 bits, AES-GCM recommended
SUBKEY_SIZE = 32  # 256 bits


def ensure_kek(path: Path) -> bytes:
    """Return the KEK at ``path``, generating + persisting it if absent.

    On Windows uses DPAPI (CryptProtectData) when available.
    On non-Windows, requires ``TIMESHEET_ALLOW_PLAIN_KEK=1`` env var; otherwise
    raises ``RuntimeError`` to prevent accidental plain storage in production.
    """
    path = Path(path)
    if path.exists():
        return _read_kek(path)

    kek = secrets.token_bytes(KEK_SIZE)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_kek(path, kek)
    return kek


def derive_subkey(kek: bytes, info: bytes) -> bytes:
    """HKDF-Expand(SHA-256) of the KEK, namespaced by ``info``."""
    if len(kek) != KEK_SIZE:
        raise ValueError(f"KEK must be {KEK_SIZE} bytes, got {len(kek)}")
    hkdf = HKDFExpand(algorithm=hashes.SHA256(), length=SUBKEY_SIZE, info=info)
    return hkdf.derive(kek)


def aes_gcm_encrypt(subkey: bytes, plaintext: bytes) -> str:
    """Encrypt ``plaintext`` under ``subkey``.

    Returns a base64-urlsafe string (no padding) of ``nonce || ciphertext || tag``.
    """
    if len(subkey) != SUBKEY_SIZE:
        raise ValueError(f"subkey must be {SUBKEY_SIZE} bytes")
    nonce = os.urandom(NONCE_SIZE)
    aesgcm = AESGCM(subkey)
    ct_and_tag = aesgcm.encrypt(nonce, plaintext, None)
    return base64.urlsafe_b64encode(nonce + ct_and_tag).decode("ascii").rstrip("=")


def aes_gcm_decrypt(subkey: bytes, encoded: str) -> bytes:
    """Decrypt the base64-urlsafe blob produced by :func:`aes_gcm_encrypt`."""
    if len(subkey) != SUBKEY_SIZE:
        raise ValueError(f"subkey must be {SUBKEY_SIZE} bytes")
    pad = "=" * (-len(encoded) % 4)
    raw = base64.urlsafe_b64decode(encoded + pad)
    if len(raw) < NONCE_SIZE + 16:
        raise ValueError("ciphertext too short")
    nonce, ct_and_tag = raw[:NONCE_SIZE], raw[NONCE_SIZE:]
    aesgcm = AESGCM(subkey)
    return aesgcm.decrypt(nonce, ct_and_tag, None)


def format_db_cipher_key(subkey: bytes) -> str:
    """Hex-encode the SQLCipher key (PRAGMA expects ``x'<hex>'`` form)."""
    if len(subkey) != SUBKEY_SIZE:
        raise ValueError(f"subkey must be {SUBKEY_SIZE} bytes")
    return subkey.hex()


# -------- internals --------

def _read_kek(path: Path) -> bytes:
    blob = path.read_bytes()
    if sys.platform == "win32":
        try:
            return _dpapi_unprotect(blob)
        except RuntimeError:
            # Fallback path for dev on Windows without pywin32 installed.
            if os.environ.get("TIMESHEET_ALLOW_PLAIN_KEK") == "1":
                logger.warning("PLAIN_KEK_FALLBACK ativo — lendo KEK em claro (dev only)")
                return blob
            raise
    # Non-Windows path
    if os.environ.get("TIMESHEET_ALLOW_PLAIN_KEK") != "1":
        raise RuntimeError(
            "DPAPI indisponivel: defina TIMESHEET_ALLOW_PLAIN_KEK=1 apenas em dev"
        )
    return blob


def _write_kek(path: Path, kek: bytes) -> None:
    if sys.platform == "win32":
        try:
            protected = _dpapi_protect(kek)
            path.write_bytes(protected)
            return
        except RuntimeError:
            if os.environ.get("TIMESHEET_ALLOW_PLAIN_KEK") != "1":
                raise
            logger.warning("PLAIN_KEK_FALLBACK ativo — escrevendo KEK em claro (dev only)")
            path.write_bytes(kek)
            return
    # Non-Windows path
    if os.environ.get("TIMESHEET_ALLOW_PLAIN_KEK") != "1":
        raise RuntimeError(
            "DPAPI ausente: configure TIMESHEET_ALLOW_PLAIN_KEK=1 apenas em dev"
        )
    path.write_bytes(kek)
    _restrict_permissions(path)


def _restrict_permissions(path: Path) -> None:
    if sys.platform == "win32":
        return  # DPAPI ja protegeu
    os.chmod(path, 0o600)


def _dpapi_protect(data: bytes) -> bytes:
    try:
        import win32crypt  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("pywin32 indisponivel") from exc
    return win32crypt.CryptProtectData(data, None, None, None, None, 0)


def _dpapi_unprotect(blob: bytes) -> bytes:
    try:
        import win32crypt  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("pywin32 indisponivel") from exc
    _desc, plain = win32crypt.CryptUnprotectData(blob, None, None, None, 0)
    return plain
```

Decisões:
- `HKDFExpand` (não `HKDF` completo) é usado porque a KEK já é de alta entropia — não precisa de extract step. Equivalente a `HKDF` com `salt=None`.
- Base64 url-safe sem padding mantém o blob curto em coluna SQLite e seguro em URLs/JSON.
- DPAPI via `pywin32` (`win32crypt.CryptProtectData`) é o caminho padrão Windows; a importação é `try/except` para permitir testes em Linux sem `pywin32`.
- O fallback **não silencia** o risco: emite `WARNING` via stdlib logging e exige opt-in explícito por env var.
- `0o600` aplicado apenas em POSIX (Windows usa NTFS ACL via DPAPI).

## Contratos com camadas adjacentes

```
Produz para:
  - Phase 3 modulo smtp_config: aes_gcm_encrypt/aes_gcm_decrypt para username_enc/password_enc.
  - Phase 5 (empacotamento): ensure_kek + format_db_cipher_key derivam a chave SQLCipher consumida pelo TIMESHEET_DB_CIPHER_KEY que a TASK-008 ja le.

Consome de:
  - TASK-006: TIMESHEET_KEK_PATH (default ./data/key.kek) declarado em .env.example; data/ via make data-dir.
  - Sistema operacional: DPAPI em Windows (via pywin32); fallback CSPRNG + arquivo 0o600 em POSIX com opt-in explicito.

Erros:
  - DPAPI ausente sem opt-in -> RuntimeError clara (mensagem aponta para a var de opt-in).
  - KEK de tamanho errado em derive_subkey -> ValueError.
  - Tag AES-GCM invalida em decrypt -> InvalidTag (do pacote cryptography); chamador trata como ataque/corrupcao.
```

**Validação obrigatória pelo executor antes de marcar done:**

1. `cd apps/api && pip install -e ".[dev]"`.
2. `cd apps/api && pytest tests/test_crypto.py -v` — 10 testes passam (em CI Linux com `TIMESHEET_ALLOW_PLAIN_KEK=1` setado pelos próprios testes via `monkeypatch`; em Windows com `pywin32` instalado, os testes Linux-only via `pytest.skip` saem do escopo).
3. `cd apps/api && pytest tests/ -v` — toda a suite continua passando.
4. `cd apps/api && ruff check .` sem warnings.
5. `cd apps/api && mypy --strict app` sem erros.
6. `make smoke` (Phase 1) continua passando.

> Executor DEVE rodar 1–6 e garantir saída 0 antes de retornar. Falha = task não concluída.

**Refatoração:** Caso o helper de fallback de plataforma cresça, extrair para `app/core/_platform.py`. Por ora, mantido inline em `crypto.py` para coesão local.
