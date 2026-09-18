"""Responsive layout: derives scene coordinates from terminal size.

Three tiers: small (<80 cols), medium (80-120), large (>120).
If terminal is below 60x20, returns LayoutTooSmall — the loop will draw
a 'resize to at least 60x20' notice instead of running the scene.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Literal

import blessed

MIN_W = 60
MIN_H = 20


def scene_floor_y(height: int) -> int:
    """Derive the scene ground floor row from terminal height, above status and footer UI."""
    cy = height // 2
    info_y = cy + 2
    status_y = max(info_y + 3, height - 2)
    return status_y - 2
@dataclass
class Layout:
    width: int
    height: int
    tier: Literal["small", "medium", "large"]
    center_x: int
    center_y: int
    info_y: int
    status_y: int
    too_small: bool = False

    @property
    def particle_area_top(self) -> int:
        # Vertical band reserved for the animated scene.
        return 2

    @property
    def particle_area_bottom(self) -> int:
        # Leave room for info + status rows.
        return max(self.particle_area_top + 1, self.info_y - 2)

    @property
    def floor_y(self) -> int:
        """Scene floor row, positioned above the status and footer area."""
        return self.status_y - 2

@dataclass
class LayoutTooSmall(Layout):
    def __init__(self, width: int, height: int) -> None:
        super().__init__(
            width=max(1, width),
            height=max(1, height),
            tier="small",
            center_x=0,
            center_y=0,
            info_y=0,
            status_y=0,
            too_small=True,
        )


class LayoutManager:
    """Reads terminal size each call to update()."""

    def __init__(self, term: blessed.Terminal) -> None:
        self.term = term

    def update(self) -> Layout:
        w = self.term.width or MIN_W
        h = self.term.height or MIN_H
        if w < MIN_W or h < MIN_H:
            return LayoutTooSmall(w, h)
        if w >= 120:
            tier: Literal["small", "medium", "large"] = "large"
        elif w >= 80:
            tier = "medium"
        else:
            tier = "small"
        cx = w // 2
        cy = h // 2
        info_y = cy + 2
        status_y = max(info_y + 3, h - 2)
        return Layout(
            width=w,
            height=h,
            tier=tier,
            center_x=cx,
            center_y=cy,
            info_y=info_y,
            status_y=status_y,
        )