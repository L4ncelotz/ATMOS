"""Fog scene: horizontal drifting layers, no vertical motion.

Layers are short rows of ─ characters drifting slowly. Density (number of
layers) tracks weather.cloud_coverage as a proxy (fog is a low cloud).

Subtle by design — fog should not visually overwhelm.
"""

from __future__ import annotations

import math
import random

from atmos.engine.environment import EnvironmentState
from atmos.engine.frame_buffer import FrameBuffer
from atmos.engine.layers import Layer
from atmos.scenes.base import SceneBase
from atmos.weather.models import WeatherState


class FogScene(SceneBase):
    def __init__(self) -> None:
        self.layers: list[dict] = []
        self._rng = random.Random()
        self.width = 0
        self.height = 0

    def enter(self, weather: WeatherState) -> None:
        self.weather = weather
        self.layers = []
        self._rng = random.Random(weather.location_name + "_fog")

    def update(self, dt: float, weather: WeatherState, width: int, height: int, lighting: "LightingState | None" = None) -> None:
        self.width = width
        self.height = height

        # Wind → drift speed. Fog drifts but slowly compared to clouds.
        rad = math.radians(weather.wind_direction)
        drift = math.sin(rad) * max(0.4, weather.wind_speed / 25.0)

        # Environment state → number + thickness of layers.
        env = EnvironmentState.from_weather(weather)
        fog_density = env.fog_intensity if env.fog_intensity > 0 else env.cloud_intensity
        target = max(3, min(8, int(fog_density * 8)))
        if not self.layers or len(self.layers) != target:
            self._init_layers(target, width, height)
        for layer in self.layers:
            layer_speed = layer["layer"].speed if "layer" in layer else 1.0
            layer["x"] += drift * layer_speed * dt
            if drift >= 0 and layer["x"] > width:
                layer["x"] = -layer["length"]
            elif drift < 0 and layer["x"] + layer["length"] < 0:
                layer["x"] = float(width)

    def _init_layers(self, count: int, width: int, height: int) -> None:
        self.layers = []
        # Spread layers through the middle 70% of the screen.
        top = max(2, int(height * 0.15))
        bottom = min(height - 4, int(height * 0.85))
        span = max(1, bottom - top)
        for i in range(count):
            length = self._rng.randint(max(8, width // 6), max(12, width // 3))
            chars = ["─"] * length
            y = top + (span * i) // max(1, count - 1) if count > 1 else (top + bottom) // 2
            ratio = i / (count - 1) if count > 1 else 0.5
            speed = 0.4 + 0.4 * ratio
            depth = 0.5 + 0.5 * ratio
            self.layers.append(
                {
                    "x": self._rng.uniform(-length, max(1, width - 1)),
                    "y": y,
                    "length": length,
                    "chars": chars,
                    "layer": Layer(speed=speed, depth=depth),
                }
            )

    def draw(self, buf: FrameBuffer, lighting: "LightingState | None" = None, dim: float = 1.0) -> None:
        # Fog is already drawn in dim grey; dim only suppresses
        # drawing entirely when it is near 0.
        if dim <= 0.0:
            return
        for layer in self.layers:
            start_x = int(layer["x"])
            y = int(layer["y"])
            if y < 0 or y >= buf.height:
                continue
            depth = layer["layer"].depth if "layer" in layer else 1.0
            style = "238" if depth < 0.75 else "240"
            for offset, char in enumerate(layer["chars"]):
                x = start_x + offset
                if 0 <= x < buf.width and char != " ":
                    buf.set(y, x, char, style)
