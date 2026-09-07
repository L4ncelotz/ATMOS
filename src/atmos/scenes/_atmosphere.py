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
    chars = ("·", "·", "✦", "✧", "*")
    stars.points = []
    for _ in range(density):
        x = rng.uniform(0, max(1, width - 1))
        y = rng.uniform(0, upper - 1)
        ch = rng.choice(chars)
        twinkle = rng.uniform(0, 6.28)
        stars.points.append((x, y, ch, twinkle))


def draw_stars(buf: FrameBuffer, stars: Stars, time_s: float, style: str = "white") -> None:
    """Draw a restrained, colored star field with slow twinkling."""
    import math

    for x, y, ch, twinkle in stars.points:
        ix, iy = int(x), int(y)
        if 0 <= ix < buf.width and 0 <= iy < buf.height:
            pulse = math.sin(time_s * 1.4 + twinkle)
            if ch == "✦":
                star_style = "bright_yellow" if pulse > -0.2 else "bright_white"
            elif ch in ("✧", "*"):
                star_style = "bright_white" if pulse > 0.2 else "white"
            else:
                star_style = "blue" if pulse < -0.65 else style
            buf.set(iy, ix, ch, star_style)


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
    """Pick a moon glyph that reads as a moon instead of a plain dot."""
    if lighting.phase in (LightingPhase.NIGHT, LightingPhase.TWILIGHT):
        return "◐" if lighting.phase == LightingPhase.NIGHT else "◑"
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
    glyph = moon_glyph_for(lighting)
    if not glyph:
        return
    # Place moon in upper third of screen.
    y = max(2, buf.height // 4)
    if 0 <= center_x < buf.width and 0 <= y < buf.height:
        # A dim halo gives the moon some separation from the star field.
        for dx in (-2, 2):
            if 0 <= center_x + dx < buf.width:
                buf.set(y, center_x + dx, "·", "blue")
        buf.set(y, center_x, glyph, "bright_yellow")
