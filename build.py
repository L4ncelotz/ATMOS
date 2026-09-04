"""Build a standalone atmos binary via PyInstaller.

Run from the repo root:
    pip install -e ".[build]"
    python build.py

Output:
    dist/atmos.exe      (Windows)
    dist/atmos          (Linux / macOS; +x)

The console subsystem is required on Windows so blessed receives
keystrokes. This is not a hidden-window app; users run it from a
real terminal.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path


# build.py lives at the repo root, so ROOT is the directory holding
# build.py. The binary is written to ROOT/dist/.
ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
ENTRY = ROOT / "src" / "atmos" / "app.py"


def _is_windows() -> bool:
    return os.name == "nt"


def build(clean: bool = True) -> Path:
    """Invoke PyInstaller programmatically. Returns path to the artifact."""
    try:
        import PyInstaller.__main__ as pyi_main
    except ImportError as exc:
        raise SystemExit(
            "atmos: pyinstaller not installed; run `pip install -e .[build]` first"
        ) from exc

    if clean and DIST.exists():
        shutil.rmtree(DIST)
    args: list[str] = [
        str(ENTRY),
        "--name=atmos",
        "--onefile",
        "--noupx",
        "--collect-all=blessed",
        "--collect-submodules=atmos",
        "--console",
        "--log-level=WARN",
        # Pin output paths so behavior is independent of cwd.
        f"--distpath={DIST}",
        f"--workpath={ROOT / 'build'}",
    ]
    try:
        pyi_main.run(args)
    except SystemExit as exc:
        raise SystemExit(
            f"atmos: pyinstaller failed (exit code {exc.code})"
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(f"atmos: pyinstaller raised {type(exc).__name__}: {exc}") from exc

    artifact = DIST / ("atmos.exe" if _is_windows() else "atmos")
    if not artifact.exists():
        # PyInstaller sometimes writes to a build/ subdir; walk for the file.
        candidates = sorted(DIST.rglob("atmos*"))
        for c in candidates:
            if c.is_file() and c.suffix in (".exe", ""):
                return c
        raise SystemExit(f"atmos: build artifact not found under {DIST}")

    if not _is_windows():
        # POSIX needs it executable.
        mode = artifact.stat().st_mode
        artifact.chmod(mode | 0o111)

    return artifact


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="atmos-build")
    parser.add_argument("--no-clean", action="store_true", help="do not wipe dist/")
    ns = parser.parse_args(argv)

    artifact = build(clean=not ns.no_clean)
    size = artifact.stat().st_size
    print(f"atmos: built {artifact} ({size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())