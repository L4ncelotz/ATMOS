"""Cloudy scene: layered, puffy cloud formations drifting with wind.

Behavior:
  cloud_coverage → band count (0-100% maps to 0-5 bands)
  cloud_coverage → band width (higher coverage → wider bands)
  wind_speed + wind_direction → drift
"""

from __future__ import annotations

import math
import random

from atmos.engine.environment import EnvironmentState
from atmos.engine.frame_buffer import FrameBuffer
from atmos.engine.layers import Layer
from atmos.engine.lighting import LightingPhase, LightingState
from atmos.scenes.base import SceneBase
from atmos.weather.models import WeatherState


def _band(width: int, coverage: float, rng: random.Random) -> tuple[int, list[str]]:
    """Return (length, sprite rows) for one cloud formation.

    The old implementation drew a single row of ``~`` characters. A cloud
    now has a few overlapping puffs and a broad underside, while retaining a
    variable width driven by cloud coverage.
    """
    min_len = max(6, width // 5)
    max_len = max(min_len + 4, int(width * 0.85))
    # Scale max length by coverage; at 100% we get the full 85% width.
    scaled_max = int(min_len + (max_len - min_len) * (coverage / 100.0))
    length = rng.randint(min_len, max(min_len + 1, scaled_max))
    length = max(16, length)
    rows = [[" "] * length for _ in range(4)]
    puff_count = max(2, min(5, length // 10))
    centers = [
        int((i + 0.5) * length / puff_count + rng.randint(-2, 2))
        for i in range(puff_count)
    ]

    def paint(row: int, center: int, text: str) -> None:
        start = center - len(text) // 2
        for offset, char in enumerate(text):
            x = start + offset
            if 0 <= x < length:
                rows[row][x] = char

    for center in centers:
        paint(0, center, ".--.")
        paint(1, center, ".-(    )-.")
        paint(2, center, "(        )")

    # A continuous underside makes the separate puffs read as one cloud.
    rows[3][0] = "("
    rows[3][-1] = ")"
    for x in range(1, length - 1):
        rows[3][x] = "_"

    return length, ["".join(row) for row in rows]


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

        # Environment state cloud intensity → number of bands (0..5).
        env = EnvironmentState.from_weather(weather)
        target_bands = max(0, min(5, int(env.cloud_intensity * 5.0)))
        if not self.bands or len(self.bands) != target_bands:
            self._init_bands(target_bands, width, height, weather.cloud_coverage)
        for b in self.bands:
            layer_speed = b["layer"].speed if "layer" in b else 1.0
            b["x"] += drift * layer_speed * dt
            if drift >= 0 and b["x"] > width:
                b["x"] = -b["length"]
            elif drift < 0 and b["x"] + b["length"] < 0:
                b["x"] = float(width)

    def _init_bands(self, count: int, width: int, height: int, coverage: float) -> None:
        self.bands = []
        upper = max(4, int(height * 0.55))
        for i in range(count):
            length, sprite = _band(width, coverage, self._rng)
            # Keep the formations inside the upper sky and leave enough
            # vertical separation for their four sprite rows.
            available = max(1, upper - 4)
            y = 2 + (available * i) // max(1, count - 1) if count > 1 else 2
            if count <= 1:
                layer = Layer(speed=0.35, depth=0.35)
            elif i / (count - 1) < 0.5:
                layer = Layer(speed=0.25, depth=0.25)
            else:
                layer = Layer(speed=0.5, depth=0.5)
            self.bands.append(
                {
                    "x": self._rng.uniform(-length, max(1, width - 1)),
                    "y": y,
                    "length": length,
                    "sprite": sprite,
                    "layer": layer,
                }
            )

    @staticmethod
    def _palette(
        lighting: LightingState | None, depth: float, dim: float
    ) -> tuple[str, str, str, str]:
        """Return styles for cloud top, puffs, body, and underside."""
        if dim < 1.0:
            return ("240", "240", "240", "240")

        phase = lighting.phase if lighting is not None else LightingPhase.DAY
        if phase in (LightingPhase.SUNSET, LightingPhase.SUNRISE):
            palette = ("bright_yellow", "yellow", "white", "240")
        elif phase in (
            LightingPhase.NIGHT,
            LightingPhase.TWILIGHT,
            LightingPhase.EVENING,
        ):
            palette = ("bright_blue", "blue", "blue", "240")
        else:
            palette = ("bright_white", "white", "blue", "white")

        # Higher/distant clouds sit farther away and are slightly quieter.
        if depth < 0.4:
            return (palette[1], palette[2], palette[2], palette[3])
        return palette

    def draw(
        self,
        buf: FrameBuffer,
        lighting: LightingState | None = None,
        dim: float = 1.0,
    ) -> None:
        for b in self.bands:
            start_x = int(b["x"])
            y = b["y"]
            if y < 0 or y >= buf.height:
                continue
            for row, line in enumerate(b["sprite"]):
                if y + row >= buf.height:
                    break
                for i, ch in enumerate(line):
                    x = start_x + i
                    if ch != " " and 0 <= x < buf.width:
                        depth = b["layer"].depth if "layer" in b else 0.5
                        style = self._palette(lighting, depth, dim)[row]
                        buf.set(y + row, x, ch, style)

    def exit(self) -> None:
        self.bands = []
