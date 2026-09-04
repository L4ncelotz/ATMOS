# PyInstaller spec for ATMOS.
#
# Used by `python build.py` (which calls PyInstaller.__main__.run
# programmatically). This file is kept for users who prefer
# `pyinstaller atmos.spec` directly.
#
# Output: dist/atmos.exe (Windows) or dist/atmos (POSIX, +x).
# A console subsystem is required so blessed receives keystrokes.

# -*- mode: python ; coding: utf-8 -*-

import platform
import os
from pathlib import Path

block_cipher = None

# Locate the entry point relative to this spec file.
HERE = Path(SPECPATH).resolve()
ENTRY = HERE / "src" / "atmos" / "app.py"

# Console subsystem is mandatory: this is a TUI app that reads
# keyboard input via blessed, which requires a real terminal.
console = True


a = Analysis(
    [str(ENTRY)],
    pathex=[str(HERE / "src")],
    binaries=[],
    datas=[],
    hiddenimports=[
        # blessed bundles terminal capability data files; PyInstaller's
        # --collect-all already covers them, but listing the import
        # path makes the dependency explicit.
        "blessed",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="atmos",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=console,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
