# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

cli_dir = Path(SPECPATH)  # apps/cli/

a = Analysis(
    [str(cli_dir / "main.py")],
    pathex=[str(cli_dir)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "commands.login",
        "commands.review",
        "auth",
        "client",
        "typer",
        "rich",
        "httpx",
        "platformdirs",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="argus",
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
)
