"""Help overlay: list of keyboard controls.

Drawn fullscreen when the user presses H. Any key dismisses.
"""

from __future__ import annotations

from atmos.engine.frame_buffer import FrameBuffer
from atmos.engine.layout import Layout


_HELP_LINES: tuple[tuple[str, str], ...] = (
    ("ATMOS", "ambient weather for your terminal"),
    ("", ""),
    ("F", "forecast (next 5 days)"),
    ("L", "search / change location"),
    ("M", "minimal mode"),
    ("Space", "pause / resume animation"),
    ("R", "refresh weather"),
    ("H", "this help"),
    ("Q", "quit"),
    ("+ / -", "target FPS up / down"),
    ("", ""),
    ("press any key to dismiss", ""),
)


def draw_help(buf: FrameBuffer, lay: Layout) -> None:
    if lay.height < 10 or lay.width < 30:
        return
    # Center the block vertically. Each row is a (key, desc) pair.
    block_h = len(_HELP_LINES)
    start_y = max(2, (lay.height - block_h) // 2)
    max_key_w = max(len(k) for k, _ in _HELP_LINES if k)
    col_key = max(2, (lay.width - (max_key_w + 2 + 30)) // 2)
    col_desc = col_key + max_key_w + 2
    for i, (key, desc) in enumerate(_HELP_LINES):
        y = start_y + i
        if y >= lay.height:
            break
        if key == "" and desc == "":
            continue
        if key:
            buf.write_line(y, col_key, key, "bright_white")
            buf.write_line(y, col_desc, desc, "white")
        else:
            buf.write_line(y, col_key, desc, "240")
