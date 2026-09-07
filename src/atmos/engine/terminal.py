"""Terminal lifecycle: alt-screen + cursor hide + restore on exit.

blessed >=1.49 returns context managers / NullCallableString for many
attributes that older versions returned as plain strings. We bypass blessed
for control sequences and emit raw CSI directly. blessed is still used for
size queries (term.width / term.height) and for non-blocking key input.
"""

from __future__ import annotations

import os
import sys
from types import TracebackType

import blessed


# CSI sequences. Documented in ECMA-48.
_ENTER_ALT = "\033[?1049h"      # switch to alternate screen buffer
_EXIT_ALT = "\033[?1049l"       # switch back to primary screen buffer
_HIDE_CURSOR = "\033[?25l"
_SHOW_CURSOR = "\033[?25h"
_RESET_SGR = "\033[0m"


class TerminalContext:
    """Enter alt-screen, hide cursor; reverse both on exit.

    Usage:
        with TerminalContext() as ctx:
            if not ctx.ok:
                return 1
            term = ctx.term
            ...

    No os.system('cls') — alt-screen buffer is switched via CSI ?1049.
    """

    def __init__(self) -> None:
        self.term: blessed.Terminal | None = None
        self.ok: bool = False
        self._entered: bool = False
        self._cbreak = None

    def __enter__(self) -> "TerminalContext":
        try:
            self.term = blessed.Terminal()
            # Detect a minimally capable terminal. blessed.Terminal never
            # raises on init; cap test by seeing whether width/height are
            # nonzero on a real terminal.
            if not self.term.width or not self.term.height:
                sys.stderr.write(
                    "atmos: cannot determine terminal size; "
                    "needs Windows Terminal, iTerm2, gnome-terminal, alacritty, etc.\n"
                )
                return self
            sys.stdout.write(_ENTER_ALT)
            sys.stdout.write(_HIDE_CURSOR)
            sys.stdout.write(_RESET_SGR)
            sys.stdout.flush()
            # Disable canonical input and terminal echo while ATMOS owns the
            # screen. Without cbreak, typed characters can be echoed into the
            # animation instead of being consumed by InputManager. The
            # context is explicitly closed in __exit__ to restore the shell.
            self._cbreak = self.term.cbreak()
            self._cbreak.__enter__()
            self._entered = True
            self.ok = True
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"atmos: terminal init failed: {exc}\n")
            self.ok = False
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self.term is None:
            return
        if self._entered:
            try:
                if self._cbreak is not None:
                    self._cbreak.__exit__(exc_type, exc, tb)
                    self._cbreak = None
                sys.stdout.write(_RESET_SGR)
                sys.stdout.write(_SHOW_CURSOR)
                sys.stdout.write(_EXIT_ALT)
                sys.stdout.flush()
            except Exception:  # noqa: BLE001
                try:
                    sys.stdout.write(f"{_RESET_SGR}{_SHOW_CURSOR}{_EXIT_ALT}")
                    sys.stdout.flush()
                except Exception:
                    pass
        # Modern terminals (WT) accept these; legacy cmd.exe ignored.
        if os.name == "nt":
            try:
                os.system("")  # no-op, just to anchor shell state on Windows
            except Exception:
                pass
