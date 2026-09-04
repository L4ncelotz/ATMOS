"""Frame buffer: 2D char grid + diff-rendered ANSI writes.

The terminal is never cleared wholesale. Each cell stores (char, style);
render_diff() compares against the previous frame and writes only changed
cells using hand-composed CSI sequences (blessed >=1.49 returns
context managers for term.location(), so we build the escapes ourselves).

Style names map to blessed's color palette. Unknown styles fall back to no
SGR. Style "" means default; "" never emits a color SGR.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Iterable

import blessed

Cell = tuple[str, str]  # (char, style) — style is a blessed style name


# Style name -> SGR code. Blessed exposes these via term.color but for
# blessed 1.49+ that returns a context manager; we use a small fixed table
# that covers the styles referenced by V1 scenes. Extend as needed.
STYLE_TABLE: dict[str, str] = {
    "": "",  # default
    "reset": "0",
    "bold": "1",
    "white": "37",
    "bright_white": "97",
    "black": "30",
    "red": "31",
    "bright_red": "91",
    "green": "32",
    "yellow": "33",
    "bright_yellow": "93",
    "blue": "34",
    "bright_blue": "94",
    "cyan": "36",
    "magenta": "35",
    "240": "38;5;240",  # dim grey
}


def _sgr(style: str) -> str:
    """Return SGR code for a blessed-style name, or '' if default."""
    if not style:
        return ""
    return STYLE_TABLE.get(style, "")


def _move(x: int, y: int) -> str:
    """CSI row;col H — moves cursor to (y, x) 0-indexed."""
    # CUP (Cursor Position): \033[y+1;x+1 H
    return f"\033[{y + 1};{x + 1}H"


@dataclass
class FrameBuffer:
    width: int
    height: int
    cells: list[list[Cell]] = field(default_factory=list)

    @classmethod
    def empty(cls, width: int, height: int) -> "FrameBuffer":
        if width < 1 or height < 1:
            return cls(width=1, height=1, cells=[[(" ", "")]])
        cells = [[(" ", "") for _ in range(width)] for _ in range(height)]
        return cls(width=width, height=height, cells=cells)

    def clear(self, char: str = " ", style: str = "") -> None:
        for row in self.cells:
            for x in range(self.width):
                row[x] = (char, style)

    def set(self, y: int, x: int, char: str, style: str = "") -> None:
        if 0 <= y < self.height and 0 <= x < self.width:
            self.cells[y][x] = (char, style)

    def get(self, y: int, x: int) -> Cell | None:
        if 0 <= y < self.height and 0 <= x < self.width:
            return self.cells[y][x]
        return None

    def write_line(self, y: int, x: int, text: str, style: str = "") -> None:
        if y < 0 or y >= self.height:
            return
        start = max(0, x)
        end = min(self.width, x + len(text))
        if end <= start:
            return
        offset = start - x
        for i in range(end - start):
            self.cells[y][start + i] = (text[offset + i], style)

    def write_centered(self, y: int, text: str, style: str = "") -> None:
        x = max(0, (self.width - len(text)) // 2)
        self.write_line(y, x, text, style)

    def blit(self, other: "FrameBuffer", y: int, x: int) -> None:
        for oy in range(other.height):
            ty = y + oy
            if ty < 0 or ty >= self.height:
                continue
            for ox in range(other.width):
                tx = x + ox
                if tx < 0 or tx >= self.width:
                    continue
                ch, st = other.cells[oy][ox]
                if ch != " ":
                    self.cells[ty][tx] = (ch, st)

    def render_diff(
        self,
        prev: "FrameBuffer | None",
        term: blessed.Terminal | None = None,  # kept for API symmetry, unused
        out: "Iterable[str] | None" = None,
    ) -> "FrameBuffer":
        """Write only cells whose (char, style) changed vs prev.

        Adjacent changed cells in the same row with the same style are
        coalesced into a single cursor-position escape followed by a
        single multi-character write. This reduces terminal I/O from
        one CUP per cell to one CUP per (row, style-change) — a
        typical heavy-rain frame drops from ~1,430 escapes to a few
        dozen.

        Returns a snapshot (self) — caller should rebind `prev` for next frame.
        """
        sink = out if out is not None else sys.stdout
        _ = term  # unused; kept for future diagnostic hooks

        # Reset style on exit.
        RESET = "\033[0m"

        if prev is None or prev.width != self.width or prev.height != self.height:
            # First frame or resized — full repaint, coalesced by row.
            last_style: str | None = None
            for y in range(self.height):
                row = self.cells[y]
                x = 0
                while x < self.width:
                    ch, st = row[x]
                    if st != last_style:
                        sgr = _sgr(st)
                        if sgr:
                            sink.write(f"\033[{sgr}m")
                        last_style = st
                    sink.write(_move(x, y))
                    # Find the end of the run, batching same-style cells.
                    run_start = x
                    x += 1
                    while x < self.width and row[x][1] == st:
                        x += 1
                    sink.write("".join(c for c, _ in row[run_start:x]))
            sink.write(RESET)
            sink.flush()
            return self

        # Diff path: only write changed cells, coalesced by (row, style).
        last_style: str | None = None
        any_write = False
        for y in range(self.height):
            row_prev = prev.cells[y]
            row_cur = self.cells[y]
            x = 0
            while x < self.width:
                if row_cur[x] == row_prev[x]:
                    x += 1
                    continue
                # Found a changed cell. Find the end of the run with
                # the same style.
                ch, st = row_cur[x]
                run_start = x
                x += 1
                while x < self.width and row_cur[x] != row_prev[x] and row_cur[x][1] == st:
                    x += 1
                if not any_write:
                    any_write = True
                sink.write(_move(run_start, y))
                if st != last_style:
                    sgr = _sgr(st)
                    if sgr:
                        sink.write(f"\033[{sgr}m")
                    last_style = st
                sink.write("".join(c for c, _ in row_cur[run_start:x]))
        if any_write:
            sink.write(RESET)
            sink.flush()
        return self