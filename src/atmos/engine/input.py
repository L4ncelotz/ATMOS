"""Non-blocking keyboard input via blessed.

Returns a KeyEvent with canonical action so app.py can dispatch on mode.
None when nothing was pressed.

Parsing rule:
  - This module does NOT decide which letters are "actions". The dispatcher
    in app.py looks at the current Mode and at `is_action_char(key.char)`
    to decide. Letters q r f l h m come through here as plain `char`
    events; the dispatcher routes them.
  - Keys that cannot be confused with text content (whitespace, control
    codes, arrow keys, +/-) keep their named actions.

Special keys:
  Space               → 'space'
  Ctrl-C              → 'quit'   (blessed maps Ctrl-C to this string)
  Esc                 → 'esc'
  Enter               → 'enter'
  Backspace           → 'backspace'
  Arrow keys          → 'up' / 'down' / 'left' / 'right'
  + / =               → 'plus'
  - / _               → 'minus'
  Other printable     → 'char' carrying the character
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import blessed


# Letters that mean an action in AMBIENT mode. Single source of truth so
# the dispatch layer and the help text agree.
ACTION_CHARS: frozenset[str] = frozenset("qrfhlm")

# Pause uses Space, never the `p` letter. The legacy `p -> space` mapping
# was deleted so `p` types into the location-search query like any other
# letter. The dispatcher checks the named `space` action (real Space bar)
# for pause.
PAUSE_KEYS: frozenset[str] = frozenset({"space"})


def is_action_char(ch: str) -> bool:
    """True if `ch` is a letter that means an action in AMBIENT mode.

    In Mode.LOCATION the dispatcher lets these through as text instead.
    """
    return ch in ACTION_CHARS


def action_for_char(ch: str) -> str:
    """Map an action letter to its named action.

    Returns 'unknown' for letters not in ACTION_CHARS. Caller is
    expected to check `is_action_char` first.
    """
    return {
        "q": "quit",
        "r": "refresh",
        "f": "forecast",
        "l": "location",
        "h": "help",
        "m": "minimal",
    }.get(ch, "unknown")


@dataclass
class KeyEvent:
    action: str
    char: Optional[str] = None


def _parse(s: str) -> KeyEvent:
    if s == " ":
        return KeyEvent("space")
    if s == "\x1b":
        return KeyEvent("esc")
    if s in ("\r", "\n"):
        return KeyEvent("enter")
    if s in ("\x7f", "\x08"):
        return KeyEvent("backspace")
    if s in ("+", "="):
        return KeyEvent("plus")
    if s in ("-", "_"):
        return KeyEvent("minus")
    if s == "KEY_UP" or s == "\x1b[A":
        return KeyEvent("up")
    if s == "KEY_DOWN" or s == "\x1b[B":
        return KeyEvent("down")
    if s == "\x1b[C":
        return KeyEvent("right")
    if s == "\x1b[D":
        return KeyEvent("left")
    if len(s) == 1 and s.isprintable():
        return KeyEvent("char", char=s)
    return KeyEvent("unknown")


class InputManager:
    def __init__(self, term: blessed.Terminal) -> None:
        self.term = term

    def read(self, dt: float = 0.0) -> KeyEvent | None:
        _ = dt
        key = self.term.inkey(timeout=0)
        if not key:
            return None
        s = str(key)
        if not s:
            return None
        return _parse(s)

    def read_blocking(self) -> KeyEvent:
        """Blocking read used for dismissing help."""
        key = self.term.inkey(timeout=None)
        if not key:
            return KeyEvent("space")
        return _parse(str(key))


__all__ = [
    "InputManager",
    "KeyEvent",
    "ACTION_CHARS",
    "PAUSE_KEYS",
    "is_action_char",
    "action_for_char",
]