"""A tiny weather-aware ASCII companion for the ambient scene."""

from __future__ import annotations

from dataclasses import dataclass

from atmos.engine.frame_buffer import FrameBuffer


_SPRITES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "default": (
        (" /\\_/\\ ", "( o.o )", " /|_|\\ ", "  / \\  "),
        (" /\\_/\\ ", "( o.o )", " /|_|\\ ", "   /\\  "),
    ),
    "rain": (
        (" .----. ", "/______\\", "   |/\\_/\\", "  ( o.o )", "  /|#|\\ ", "   / \\  "),
        ("  .----. ", " /______\\", "    |/\\_/\\", "   ( o.o )", "   \\|#|/ ", "    /\\   "),
    ),
    "snow": (
        ("  .--.  ", " ( o o ) ", "~|###|~", " |#####| ", "  /   \\ "),
        ("  .--.  ", " ( o o ) ", "~\\###/~", " |#####| ", "   / \\  "),
    ),
    "wind": (
        (" ~~~>  ", " /\\_/\\ ", "( o.o )", " /|==|> ", "  / \\  "),
        ("  <~~~ ", " /\\_/\\ ", "( o.o )", " <|==|\\ ", "  / \\  "),
    ),
    "fog": (
        ("  .---. ", " / -.- \\", "( /|_|\\ )", "  /   \\ "),
        ("  .---. ", " \\ -.- /", "( \\|_|/ )", "   / \\  "),
    ),
}

_STYLES = {
    "rain": "blue",
    "snow": "bright_white",
    "wind": "cyan",
    "fog": "240",
    "clear": "bright_yellow",
    "partly_cloudy": "bright_yellow",
    "cloudy": "white",
    "default": "white",
}


def _kind(condition: str) -> str:
    if condition in {"rain", "heavy_rain", "storm"}:
        return "rain"
    if condition == "snow":
        return "snow"
    if condition == "wind":
        return "wind"
    if condition == "fog":
        return "fog"
    if condition in {"clear", "partly_cloudy"}:
        return "clear"
    if condition == "cloudy":
        return "cloudy"
    return "default"


@dataclass
class WeatherCompanion:
    """Small looping walker that reacts to the normalized weather condition."""

    x: float = -8.0
    elapsed: float = 0.0
    frame: int = 0
    kind: str = "default"

    def update(
        self,
        dt: float,
        width: int,
        condition: str,
        *,
        paused: bool = False,
    ) -> None:
        if paused:
            return
        self.elapsed += max(0.0, dt)
        if self.elapsed >= 0.22:
            self.elapsed = 0.0
            self.frame = (self.frame + 1) % 2
        self.kind = _kind(condition)
        # A slow walk keeps the companion atmospheric rather than distracting.
        self.x += max(0.0, dt) * 4.0
        sprite = _SPRITES.get(self.kind, _SPRITES["default"])[self.frame]
        if self.x > width + 2:
            self.x = -max(4, len(sprite[0]))

    def draw(
        self,
        buf: FrameBuffer,
        *,
        dim: float = 1.0,
        floor_y: int | None = None,
    ) -> None:
        sprites = _SPRITES.get(self.kind, _SPRITES["default"])
        sprite = sprites[self.frame]
        style = "240" if dim < 1.0 else _STYLES.get(self.kind, "white")
        # Keep a dedicated walking lane below the weather card. The caller
        # supplies the floor from Layout so the companion cannot drift into
        # the scene's cloud/particle area on short terminals.
        if floor_y is None:
            floor_y = buf.height - 5
        top = max(0, floor_y - len(sprite) + 1)
        left = int(self.x)
        for row, text in enumerate(sprite):
            for col, char in enumerate(text):
                if char != " " and 0 <= left + col < buf.width:
                    buf.set(top + row, left + col, char, style)
