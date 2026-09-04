"""File + optional-stderr logging for ATMOS.

Per IMPLEMENT.md §29 + §FINAL:
- Logs go to a file, never to the animation surface.
- File path is resolved via platformdirs.user_log_dir.
- Stderr is silent by default; gated on ATMOS_DEBUG=1 so a developer can
  opt in without ever printing debug output over a running scene.

Usage:
    from atmos.utils.logging_setup import setup_log
    log = setup_log("atmos")
    log.info("startup")
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import platformdirs


_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
_DATEFMT = "%Y-%m-%dT%H:%M:%S"
_MAX_BYTES = 512_000
_BACKUP_COUNT = 2


# Track which logger ids we have already attached handlers to, by id().
# stdlib loggers are singletons per name, so id() is stable for the
# lifetime of the process — safe to use as a registry.
_attached: set[int] = set()


def _log_dir() -> Path:
    return Path(platformdirs.user_log_dir("atmos", appauthor=False))


def log_file_path() -> Path:
    """Return the path where ATMOS writes its log file. The file may not
    exist yet (it is created on the first log call)."""
    return _log_dir() / "atmos.log"


def setup_log(name: str = "atmos") -> logging.Logger:
    """Configure and return a logger for `name`.

    Idempotent: calling setup_log more than once for the same name does
    not attach duplicate handlers.
    """
    logger = logging.getLogger(name)
    if id(logger) in _attached:
        return logger
    _attached.add(id(logger))

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter(_FORMAT, datefmt=_DATEFMT)

    # File sink — must never write to the terminal.
    log_path = log_file_path()
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(
            log_path,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        fh.setFormatter(fmt)
        fh.setLevel(logging.INFO)
        logger.addHandler(fh)
    except OSError:
        # The log file is best-effort — if it cannot be opened, the app
        # must still run.
        pass

    # Optional stderr sink — only active under ATMOS_DEBUG=1. Never
    # active by default because stderr would render over the scene on a
    # TTY.
    if os.environ.get("ATMOS_DEBUG") == "1":
        sh = logging.StreamHandler(stream=sys.stderr)
        sh.setFormatter(fmt)
        sh.setLevel(logging.DEBUG)
        logger.addHandler(sh)
        logger.setLevel(logging.DEBUG)

    logger.propagate = False
    return logger


__all__ = ["setup_log", "log_file_path"]