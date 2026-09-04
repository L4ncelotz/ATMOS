"""Cloudy scene: 2-5 horizontal cloud bands drifting with wind.

Behavior:
  cloud_coverage → band count (0-100% maps to 0-5 bands)
  cloud_coverage → band width (higher coverage → wider bands)
  wind_speed + wind_direction → drift
"""

from __future__ import annotations

import math
import random

from atmos.engine.frame_buffer import FrameBuffer
from atmos.scenes.base import SceneBase
from atmos.weather.models import WeatherState


def _band(width: int, coverage: float, rng: random.Random) -> tuple[int, list[str]]:
    """Return (length, chars) for one band. Width scales with coverage."""
    min_len = max(6, width // 5)
    max_len = max(min_len + 4, int(width * 0.85))
    # Scale max length by coverage; at 100% we get the full 85% width.
    scaled_max = int(min_len + (max_len - min_len) * (coverage / 100.0))
    length = rng.randint(min_len, max(min_len + 1, scaled_max))
    chars: list[str] = []
    for _ in range(length):
        r = rng.random()
        if r < 0.85:
            chars.append("~")
        elif r < 0.95:
            chars.append("─")
        else:
            chars.append(".")
    return length, chars


class CloudyScene(SceneBase):
    def __init__(self) -> None:
        self.bands: list[dict] = []
        self._rng = random.Random()
        self.width = 0
        self.height = 0

    def enter(self, weather: WeatherState) -> None:
        self.weather = weather
        self.bands = []
        self._rng = random.Random(weather.location_name)

    def update(self, dt: float, weather: WeatherState, width: int, height: int, lighting: "LightingState | None" = None) -> None:
        self.width = width
        self.height = height

        rad = math.radians(weather.wind_direction)
        # Clouds drift a bit faster than scene visualization but slower than rain.
        drift = math.sin(rad) * (weather.wind_speed / 12.0)

        # Coverage → number of bands (0..5).
        target_bands = max(0, min(5, int(weather.cloud_coverage / 20.0)))
        if not self.bands or len(self.bands) != target_bands:
            self._init_bands(target_bands, width, height, weather.cloud_coverage)
        for b in self.bands:
            b["x"] += drift * dt
            if drift >= 0 and b["x"] > width:
                b["x"] = -b["length"]
            elif drift < 0 and b["x"] + b["length"] < 0:
                b["x"] = float(width)

    def _init_bands(self, count: int, width: int, height: int, coverage: float) -> None:
        self.bands = []
        upper = max(3, int(height * 0.55))
        for i in range(count):
            length, chars = _band(width, coverage, self._rng)
            y = max(2, (upper * (i + 1)) // (count + 1))
            self.bands.append(
                {
                    "x": self._rng.uniform(-length, max(1, width - 1)),
                    "y": y,
                    "length": length,
                    "chars": chars,
                }
            )

    def draw(self, buf: FrameBuffer, lighting: "LightingState | None" = None, dim: float = 1.0) -> None:
        style = "white" if dim >= 1.0 else "240"
        for b in self.bands:
            start_x = int(b["x"])
            y = b["y"]
            if y < 0 or y >= buf.height:
                continue
            for i, ch in enumerate(b["chars"]):
                x = start_x + i
                if 0 <= x < buf.width:
                    buf.set(y, x, ch, style)

    def exit(self) -> None:
        self.bands = []