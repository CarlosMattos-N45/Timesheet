from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

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


# ---------------------------------------------------------------------------
# Novos testes: build_server, run_server e roteamento main()
# ---------------------------------------------------------------------------


def test_build_server_quando_chamado_deve_usar_settings_host_port_single_worker() -> None:
    from app import launcher

    server = launcher.build_server()
    cfg = server.config
    from app.core.config import settings

    assert cfg.host == settings.host
    assert cfg.port == settings.port
    assert cfg.workers == 1
    assert cfg.log_config is None


def test_build_server_quando_should_exit_setado_deve_permitir_shutdown_programatico() -> None:
    from app import launcher

    server = launcher.build_server()
    # mecanismo nativo de shutdown gracioso do uvicorn, sem sinais do SO
    server.should_exit = True
    assert server.should_exit is True


def test_main_quando_argv_service_deve_rotear_para_dispatcher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "argv", ["timesheet-backend.exe", "service"])
    monkeypatch.setattr(sys, "platform", "win32")
    fake_servicemanager = MagicMock()
    spies = {
        "prepare_runtime": MagicMock(),
        "run_migrations": MagicMock(),
        "serve": MagicMock(),
    }
    with patch.dict(sys.modules, {"servicemanager": fake_servicemanager}):
        from app import launcher

        monkeypatch.setattr(launcher, "prepare_runtime", spies["prepare_runtime"])
        monkeypatch.setattr(launcher, "run_migrations", spies["run_migrations"])
        monkeypatch.setattr(launcher, "serve", spies["serve"])
        # TimesheetBackendService deve ser resolvido a partir do módulo (lazy import win32)
        with patch.object(launcher, "_run_service") as run_service:
            launcher.main()
            run_service.assert_called_once()
    # nenhum código privilegiado no path do dispatcher
    spies["prepare_runtime"].assert_not_called()
    spies["run_migrations"].assert_not_called()
    spies["serve"].assert_not_called()


def test_main_quando_sem_argumento_deve_rotear_para_console(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "argv", ["timesheet-backend.exe"])
    from app import launcher

    calls: list[str] = []
    monkeypatch.setattr(launcher, "prepare_runtime", lambda s: calls.append("prepare"))
    monkeypatch.setattr(launcher, "run_migrations", lambda: calls.append("migrate"))
    monkeypatch.setattr(launcher, "serve", lambda: calls.append("serve"))
    monkeypatch.setattr(
        "app.core.logging.configure_logging", lambda: calls.append("log")
    )
    launcher.main()
    assert calls == ["log", "prepare", "migrate", "serve"]


def test_main_quando_argv_service_em_nao_windows_deve_cair_em_console(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "argv", ["timesheet-backend.exe", "service"])
    monkeypatch.setattr(sys, "platform", "linux")
    from app import launcher

    calls: list[str] = []
    monkeypatch.setattr(launcher, "prepare_runtime", lambda s: calls.append("prepare"))
    monkeypatch.setattr(launcher, "run_migrations", lambda: calls.append("migrate"))
    monkeypatch.setattr(launcher, "serve", lambda: calls.append("serve"))
    monkeypatch.setattr(
        "app.core.logging.configure_logging", lambda: calls.append("log")
    )
    launcher.main()
    # caiu no console, nunca tentou dispatcher
    assert "serve" in calls


# ---------------------------------------------------------------------------
# Testes da classe TimesheetBackendService (mockada via win32)
# ---------------------------------------------------------------------------


def _make_service() -> object:  # noqa: ANN201
    """Instancia TimesheetBackendService com todas as dependências win32 mockadas."""
    import importlib

    fake_win32event = MagicMock()
    fake_win32service = MagicMock()
    fake_win32serviceutil = MagicMock()
    fake_servicemanager = MagicMock()

    # win32serviceutil.ServiceFramework precisa ser uma classe base real
    fake_win32serviceutil.ServiceFramework = object

    with patch.dict(
        sys.modules,
        {
            "win32event": fake_win32event,
            "win32service": fake_win32service,
            "win32serviceutil": fake_win32serviceutil,
            "servicemanager": fake_servicemanager,
        },
    ):
        # Recarregar launcher com mocks injetados
        import app.launcher as _launcher

        importlib.reload(_launcher)

        svc = _launcher.TimesheetBackendService.__new__(_launcher.TimesheetBackendService)  # type: ignore[attr-defined]
        svc._stop_event = MagicMock()
        svc._server = None
        svc._thread = None
        svc.ReportServiceStatus = MagicMock()
        svc._svc_name_ = "TimesheetBackend"

    return svc  # type: ignore[return-value]


@pytest.mark.skipif(sys.platform != "win32", reason="win32 only")
def test_service_svc_name_e_display_name() -> None:
    from app.launcher import TimesheetBackendService

    assert TimesheetBackendService._svc_name_ == "TimesheetBackend"
    assert TimesheetBackendService._svc_display_name_ == "Timesheet Backend"


@pytest.mark.skipif(sys.platform != "win32", reason="win32 only")
def test_svcDoRun_quando_servidor_inicia_deve_reportar_running(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SvcDoRun: START_PENDING → bootstrap → RUNNING → espera stop_event."""
    import importlib

    import win32service

    fake_servicemanager = MagicMock()
    fake_win32event = MagicMock()
    # WaitForSingleObject retorna imediatamente
    fake_win32event.WaitForSingleObject = MagicMock(return_value=0)
    fake_win32event.INFINITE = 0xFFFFFFFF

    with patch.dict(sys.modules, {"servicemanager": fake_servicemanager}):
        import app.launcher as _launcher

        importlib.reload(_launcher)

        # Criar instância fake
        svc = _launcher.TimesheetBackendService.__new__(_launcher.TimesheetBackendService)  # type: ignore[attr-defined]
        svc._stop_event = fake_win32event.CreateEvent(None, 0, 0, None)
        svc._server = None
        svc._thread = None
        svc.ReportServiceStatus = MagicMock()
        svc._svc_name_ = "TimesheetBackend"

        # Mock do servidor com started=True imediatamente
        mock_server = MagicMock()
        mock_server.started = True

        calls: list[str] = []
        monkeypatch.setattr(_launcher, "prepare_runtime", lambda s: None)
        monkeypatch.setattr(_launcher, "run_migrations", lambda: None)
        monkeypatch.setattr(_launcher, "build_server", lambda: mock_server)

        import win32event as we

        original_wait = we.WaitForSingleObject
        we.WaitForSingleObject = lambda ev, t: None  # type: ignore[assignment]
        try:
            with patch("app.core.logging.configure_logging", lambda: calls.append("log")):
                svc.SvcDoRun()
        finally:
            we.WaitForSingleObject = original_wait

        # Deve ter reportado SERVICE_START_PENDING e SERVICE_RUNNING
        status_calls = [c.args[0] for c in svc.ReportServiceStatus.call_args_list]
        assert win32service.SERVICE_START_PENDING in status_calls
        assert win32service.SERVICE_RUNNING in status_calls


@pytest.mark.skipif(sys.platform != "win32", reason="win32 only")
def test_svcStop_quando_servidor_ativo_deve_setar_should_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SvcStop: seta should_exit, SetEvent, join thread, loga service_stopped."""
    import importlib

    import win32event
    import win32service

    import app.launcher as _launcher

    importlib.reload(_launcher)

    svc = _launcher.TimesheetBackendService.__new__(_launcher.TimesheetBackendService)  # type: ignore[attr-defined]
    svc._stop_event = MagicMock()
    svc.ReportServiceStatus = MagicMock()
    svc._svc_name_ = "TimesheetBackend"

    # Servidor mock
    mock_server = MagicMock()
    mock_server.should_exit = False
    svc._server = mock_server

    # Thread mock que termina imediatamente
    mock_thread = MagicMock()
    mock_thread.is_alive.return_value = False
    svc._thread = mock_thread

    with patch.object(win32event, "SetEvent", MagicMock()):
        svc.SvcStop()

    # should_exit deve ter sido setado
    assert mock_server.should_exit is True
    # join deve ter sido chamado com timeout correto
    mock_thread.join.assert_called_once_with(timeout=_launcher._STOP_JOIN_TIMEOUT_S)
    # ReportServiceStatus deve ter sido chamado com STOP_PENDING
    status_calls = [c.args[0] for c in svc.ReportServiceStatus.call_args_list]
    assert win32service.SERVICE_STOP_PENDING in status_calls


@pytest.mark.skipif(sys.platform != "win32", reason="win32 only")
def test_svcStop_quando_thread_trava_deve_logar_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SvcStop: loga service_stop_timeout (WARNING) se join expira."""
    import importlib
    import logging

    import win32event

    import app.launcher as _launcher

    importlib.reload(_launcher)

    svc = _launcher.TimesheetBackendService.__new__(_launcher.TimesheetBackendService)  # type: ignore[attr-defined]
    svc._stop_event = MagicMock()
    svc.ReportServiceStatus = MagicMock()
    svc._svc_name_ = "TimesheetBackend"
    svc._server = MagicMock()

    # Thread que não termina (simula timeout)
    mock_thread = MagicMock()
    mock_thread.is_alive.return_value = True
    svc._thread = mock_thread

    with (
        patch.object(win32event, "SetEvent", MagicMock()),
        patch.object(logging.getLogger("app.launcher"), "warning") as mock_warning,
    ):
        svc.SvcStop()
        # Deve ter logado warning com event=service_stop_timeout
        warning_calls = mock_warning.call_args_list
        assert len(warning_calls) > 0


@pytest.mark.skipif(sys.platform != "win32", reason="win32 only")
def test_svcDoRun_quando_bootstrap_falha_deve_logar_error_sem_expor_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SvcDoRun: exceção no bootstrap → service_bootstrap_error sem str(exc)."""
    import importlib

    fake_servicemanager = MagicMock()

    with patch.dict(sys.modules, {"servicemanager": fake_servicemanager}):
        import app.launcher as _launcher

        importlib.reload(_launcher)

        svc = _launcher.TimesheetBackendService.__new__(_launcher.TimesheetBackendService)  # type: ignore[attr-defined]
        svc._stop_event = MagicMock()
        svc._server = None
        svc._thread = None
        svc.ReportServiceStatus = MagicMock()
        svc._svc_name_ = "TimesheetBackend"

        secret = "minha_senha_secreta_12345"
        error = ValueError(secret)

        monkeypatch.setattr(_launcher, "prepare_runtime", lambda s: (_ for _ in ()).throw(error))
        monkeypatch.setattr(_launcher, "run_migrations", lambda: None)
        monkeypatch.setattr(_launcher, "build_server", lambda: MagicMock())

        with patch("app.core.logging.configure_logging", lambda: None):
            svc.SvcDoRun()

        # LogErrorMsg deve ter sido chamado com tipo+camada, nunca com str(exc)
        log_calls = fake_servicemanager.LogErrorMsg.call_args_list
        assert len(log_calls) > 0
        msg = log_calls[0].args[0]
        assert secret not in msg, f"Secret exposto no LogErrorMsg: {msg}"
        assert "ValueError" in msg
        assert "camada: launcher" in msg


def test_run_console_quando_excecao_deve_chamar_sys_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_run_console(): exceção no bootstrap → sys.exit(1)."""
    from app import launcher

    monkeypatch.setattr("app.core.logging.configure_logging", lambda: None)

    def _raise(s: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(launcher, "prepare_runtime", _raise)
    monkeypatch.setattr(launcher, "run_migrations", lambda: None)
    monkeypatch.setattr(launcher, "serve", lambda: None)

    with pytest.raises(SystemExit) as exc_info:
        launcher._run_console()
    assert exc_info.value.code == 1


def test_prepare_runtime_quando_ja_configurado_deve_ser_idempotente(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """prepare_runtime() não faz nada se db_cipher_key já está configurado."""
    from app.launcher import prepare_runtime

    class FakeSettings:
        db_cipher_key = "already_set_64char_hex_key_" + "a" * 36

    s = FakeSettings()
    # Não deve lançar exceção nem tentar carregar KEK
    prepare_runtime(s)
    assert s.db_cipher_key == "already_set_64char_hex_key_" + "a" * 36


def test_run_server_deve_chamar_server_run() -> None:
    """run_server() chama server.run() (bloqueante)."""
    from app.launcher import run_server

    mock_server = MagicMock()
    run_server(mock_server)
    mock_server.run.assert_called_once()


def test_serve_deve_chamar_build_e_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """serve() constrói o servidor e chama run_server."""
    from app import launcher

    mock_server = MagicMock()
    monkeypatch.setattr(launcher, "build_server", lambda: mock_server)
    monkeypatch.setattr(launcher, "run_server", lambda s: None)
    launcher.serve()  # deve retornar sem erro


@pytest.mark.skipif(sys.platform != "win32", reason="win32 only")
def test_svcDoRun_quando_timeout_de_start_deve_encerrar_sem_travar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SvcDoRun: server.started nunca vira True → raise RuntimeError → retorna sem travar."""
    import importlib

    fake_servicemanager = MagicMock()

    with patch.dict(sys.modules, {"servicemanager": fake_servicemanager}):
        import app.launcher as _launcher

        importlib.reload(_launcher)

        svc = _launcher.TimesheetBackendService.__new__(_launcher.TimesheetBackendService)  # type: ignore[attr-defined]
        svc._stop_event = MagicMock()
        svc._server = None
        svc._thread = None
        svc.ReportServiceStatus = MagicMock()
        svc._svc_name_ = "TimesheetBackend"

        # Servidor que nunca fica started=True
        mock_server = MagicMock()
        mock_server.started = False
        mock_thread = MagicMock()

        monkeypatch.setattr(_launcher, "prepare_runtime", lambda s: None)
        monkeypatch.setattr(_launcher, "run_migrations", lambda: None)
        monkeypatch.setattr(_launcher, "build_server", lambda: mock_server)
        # Reduzir timeout para o teste ser rápido
        monkeypatch.setattr(_launcher, "_SERVER_STARTED_TIMEOUT_S", 0.3)

        with (
            patch("app.core.logging.configure_logging", lambda: None),
            patch("threading.Thread", return_value=mock_thread),
        ):
            svc.SvcDoRun()

        # Não deve ter reportado RUNNING (falhou antes)
        status_calls = [c.args[0] for c in svc.ReportServiceStatus.call_args_list]
        import win32service

        assert win32service.SERVICE_RUNNING not in status_calls
        # LogErrorMsg deve ter sido chamado
        assert fake_servicemanager.LogErrorMsg.called
