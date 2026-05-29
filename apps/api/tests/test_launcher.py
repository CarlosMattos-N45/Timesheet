from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.crypto import derive_subkey, ensure_kek, format_db_cipher_key


def test_derive_db_cipher_key_hex_matches_crypto(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    kek_path = tmp_path / "key.kek"
    kek = ensure_kek(kek_path)
    from app.launcher import derive_db_cipher_key_hex

    expected = format_db_cipher_key(derive_subkey(kek, info=b"db"))
    got = derive_db_cipher_key_hex(kek_path)
    assert got == expected
    assert len(got) == 64
    assert derive_db_cipher_key_hex(kek_path) == got  # determinístico (KEK imutável)


def test_prepare_runtime_sets_db_cipher_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TIMESHEET_ALLOW_PLAIN_KEK", "1")
    from app.core.config import Settings

    s = Settings(kek_path=str(tmp_path / "key.kek"), db_cipher_key=None)
    from app.launcher import prepare_runtime

    prepare_runtime(s)
    assert s.db_cipher_key is not None
    assert len(s.db_cipher_key) == 64


def test_spa_fallback_serves_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # static dir com index.html mínimo
    from app import launcher

    static = launcher.static_dir_for_bundle()
    Path(static).mkdir(parents=True, exist_ok=True)
    (Path(static) / "index.html").write_text(
        "<!doctype html><title>app</title>", encoding="utf-8"
    )
    from app.main import create_app

    client = TestClient(create_app(), base_url="http://localhost")
    assert client.get("/").status_code == 200
    # rota não-API desconhecida → SPA fallback (index.html)
    r = client.get("/jornadas")
    assert r.status_code == 200
    assert "<title>app</title>" in r.text
    # rota da API tem precedência
    assert client.get("/api/v1/health").json()["status"] == "ok"
