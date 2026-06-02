# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for timesheet-backend.exe
# Produces a single-file executable that:
#   1. Loads KEK (DPAPI) → derives SQLCipher key
#   2. Runs Alembic migrations
#   3. Serves the React SPA + FastAPI on 127.0.0.1:<port>
#
# Build: pyinstaller timesheet-backend.spec
# Output: dist/timesheet-backend.exe

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)

# ── WeasyPrint native libs (libpango, libcairo, libgobject, libfontconfig, GTK) ──
weasyprint_binaries = collect_dynamic_libs("weasyprint")
cffi_binaries = collect_dynamic_libs("cffi")

# ── Data files ───────────────────────────────────────────────────────────────────
weasyprint_data = collect_data_files("weasyprint")

datas = [
    # React SPA build output (copied by build-backend.ps1 before pyinstaller)
    ("app/static", "static"),
    # Jinja2 PDF templates
    ("app/modules/relatorios/templates", "app/modules/relatorios/templates"),
    # Alembic migration scripts + ini
    ("alembic", "alembic"),
    ("alembic.ini", "."),
]
datas += weasyprint_data

binaries = weasyprint_binaries + cffi_binaries

# ── Hidden imports ────────────────────────────────────────────────────────────────
hiddenimports = [
    # async sqlite driver
    "aiosqlite",
    # APScheduler jobstore + triggers used at runtime
    "apscheduler.jobstores.sqlalchemy",
    "apscheduler.triggers.cron",
    "apscheduler.triggers.interval",
    "apscheduler.triggers.date",
    # passlib argon2 backend
    "passlib.handlers.argon2",
    # application routers (imported dynamically via include_router)
    "app.modules.atividades.router",
    "app.modules.auditoria.router",
    "app.modules.auth.router",
    "app.modules.jornadas.router",
    "app.modules.justificativas.router",
    "app.modules.marcacoes.router",
    "app.modules.privacidade.router",
    "app.modules.relatorios.router",
    "app.modules.sistema.router",
    "app.modules.smtp.router",
    "app.modules.terceiros.router",
    # models registration
    "app.models",
    # alembic env needs Base.metadata
    "app.core.base",
    # SQLAlchemy dialects used at runtime
    "sqlalchemy.dialects.sqlite",
]
hiddenimports += collect_submodules("sqlalchemy")

a = Analysis(
    ["app/launcher.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="timesheet-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Single-file (--onefile): all data/binaries packed into the exe
    onefile=True,
)
