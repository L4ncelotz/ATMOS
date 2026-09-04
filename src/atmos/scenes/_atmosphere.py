"""Atmosphere helpers shared by sky scenes (Clear, PartlyCloudy).

Sun, moon, stars — drawing routines that read LightingState.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from atmos.engine.frame_buffer import FrameBuffer
from atmos.engine.lighting import LightingPhase, LightingState


# Sun glyph + rays, relative coordinates around the sun center.
SUN_RAYS: tuple[tuple[int, int, str], ...] = (
    (-2, -2, "╲"), (-2, 0, "│"), (-2, 2, "╱"),
    ( 0, -3, "─"),                  ( 0, 3, "─"),
    ( 2, -2, "╱"), ( 2, 0, "│"), ( 2, 2, "╲"),
)

MOON_GLYPHS = ("◐", "◑", "◒", "●")


@dataclass
class Stars:
    """Star field — fixed list of (x, y, char, twinkle_phase)."""
    points: list[tuple[float, float, str, float]] = field(default_factory=list)


def init_stars(stars: Stars, density: int, width: int, height: int, seed: str) -> None:
    """Populate the star list with `density` points scattered in the upper
    60% of the screen."""
    if density <= 0 or width <= 0 or height <= 0:
        stars.points = []
        return
    rng = random.Random(seed)
    upper = max(2, int(height * 0.6))
    chars = ("·", "*", "·", "·")  # mostly dim dots
    stars.points = []
    for _ in range(density):
        x = rng.uniform(0, max(1, width - 1))
        y = rng.uniform(0, upper - 1)
        ch = rng.choice(chars)
        twinkle = rng.uniform(0, 6.28)
        stars.points.append((x, y, ch, twinkle))


def draw_stars(buf: FrameBuffer, stars: Stars, time_s: float, style: str = "white") -> None:
    """Draw stars; gentle twinkle by varying the cell style.

    We don't actually swap styles (that would flicker terminal output); we
    just keep them as bright_white. Twinkle is implicit via the time_s
    angle, but not used here to keep the renderer stable.
    """
    for x, y, ch, _twinkle in stars.points:
        ix, iy = int(x), int(y)
        if 0 <= ix < buf.width and 0 <= iy < buf.height:
            buf.set(iy, ix, ch, style)


def draw_sun(buf: FrameBuffer, lighting: LightingState, center_x: int) -> None:
    """Draw the sun at the row specified by lighting.sun_y. Returns nothing."""
    if not lighting.sun_visible:
        return
    cy = int(round(lighting.sun_y))
    if cy < 0:
        return
    # Rays first, then body.
    for dy, dx, ch in SUN_RAYS:
        y = cy + dy
        x = center_x + dx
        if 0 <= x < buf.width and 0 <= y < buf.height:
            buf.set(y, x, ch, "bright_yellow")
    if 0 <= center_x < buf.width and 0 <= cy < buf.height:
        buf.set(cy, center_x, "◉", "bright_yellow")


def moon_glyph_for(lighting: LightingState) -> str:
    """Pick a moon glyph. V5 keeps it simple — full moon at midnight."""
    if lighting.phase in (LightingPhase.NIGHT, LightingPhase.TWILIGHT):
        # Twilight: crescent; full NIGHT: full moon.
        return "●" if lighting.phase == LightingPhase.NIGHT else "◐"
    if lighting.phase in (LightingPhase.SUNRISE, LightingPhase.SUNSET):
        return "◐"
    return ""


def draw_moon(buf: FrameBuffer, lighting: LightingState, center_x: int) -> None:
    """Draw moon when sun is not visible. Same Y as sun would be at noon."""
    if lighting.sun_visible:
        return
    if lighting.phase not in (
        LightingPhase.NIGHT,
        LightingPhase.TWILIGHT,
        LightingPhase.SUNRISE,
        LightingPhase.SUNSET,
        LightingPhase.EVENING,
    ):
        return
    if not glyph:
        return
    # Place moon in upper third of screen.
    y = max(2, buf.height // 4)
    if 0 <= center_x < buf.width and 0 <= y < buf.height:
        buf.set(y, center_x, glyph, "white")