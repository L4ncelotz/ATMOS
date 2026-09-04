"""Wind scene: directional streaks moving fast horizontally.

Visual:
       ────────→
             ─────────────→
        ─────→

Distinguished from Fog by:
  - much faster horizontal velocity
  - variable streak lengths (10..40 cells)
  - each streak has a slight vertical jitter (yaw) so they don't all
    track the same row
"""

from __future__ import annotations

import math
import random

from atmos.engine.frame_buffer import FrameBuffer
from atmos.scenes.base import SceneBase
from atmos.weather.models import WeatherState


class WindScene(SceneBase):
    def __init__(self) -> None:
        self.streaks: list[dict] = []
        self._rng = random.Random()
        self.width = 0
        self.height = 0
        self.spawn_cooldown = 0.0

    def enter(self, weather: WeatherState) -> None:
        self.weather = weather
        self.streaks = []
        self._rng = random.Random(weather.location_name + "_wind")
        self.spawn_cooldown = 0.0

    def update(self, dt: float, weather: WeatherState, width: int, height: int, lighting: "LightingState | None" = None) -> None:
        self.width = width
        self.height = height

        # Map wind direction → horizontal velocity. Sign by sin(rad).
        rad = math.radians(weather.wind_direction)
        sign = 1.0 if math.sin(rad) >= 0 else -1.0
        speed = max(8.0, min(50.0, weather.wind_speed * 1.6))

        # Spawn new streaks proportional to wind speed.
        self.spawn_cooldown -= dt
        spawn_interval = max(0.03, 0.18 - weather.wind_speed / 200.0)
        if self.spawn_cooldown <= 0:
            self.spawn_cooldown = spawn_interval
            length = self._rng.randint(8, min(40, max(10, int(weather.wind_speed / 1.5))))
            self.streaks.append(
                {
                    "x": -length if sign > 0 else float(width),
                    "y": self._rng.randint(2, max(2, height - 3)),
                    "length": length,
                    "vx": sign * speed,
                    "vy": self._rng.uniform(-0.4, 0.4),
                    "age": 0.0,
                    "lifetime": 3.0,
                }
            )

        # Advance streaks.
        alive: list[dict] = []
        for s in self.streaks:
            s["x"] += s["vx"] * dt
            s["y"] += s["vy"] * dt
            s["age"] += dt
            if s["age"] >= s["lifetime"]:
                continue
            if sign > 0 and s["x"] > width:
                continue
            if sign < 0 and s["x"] + s["length"] < 0:
                continue
            if s["y"] < 0 or s["y"] >= height:
                continue
            alive.append(s)
        self.streaks = alive

    def draw(self, buf: FrameBuffer, lighting: "LightingState | None" = None, dim: float = 1.0) -> None:
        # Wind is already drawn in dim grey; honor `dim` for
        # blend-out by suppressing when near 0.
        if dim <= 0.0:
            return
        for s in self.streaks:

            start_x = int(s["x"])
            y = int(s["y"])
            if y < 0 or y >= buf.height:
                continue
            length = s["length"]
            if start_x < 0:
                length += start_x  # trim
                start_x = 0
            if start_x + length > buf.width:
                length = buf.width - start_x
            for i in range(length):
                buf.set(y, start_x + i, "─", "240")

    def exit(self) -> None:
        self.streaks = []