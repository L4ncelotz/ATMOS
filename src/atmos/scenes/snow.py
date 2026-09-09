"""Snow scene: slow falling particles with lateral drift and varied speeds.

Chars: · * + (visual convention: small motes, asterisks, plus marks).
Vertical velocity 1.5..4.5 cells/sec for a gentle ambient fall.
vx jitter so the field doesn't look uniform.
"""

from __future__ import annotations

import math
import random

from atmos.engine.frame_buffer import FrameBuffer
from atmos.engine.layout import scene_floor_y
from atmos.engine.particles import Particle, ParticleSystem
from atmos.scenes.base import SceneBase
from atmos.weather.models import WeatherState

_SNOW_CHARS = ("·", "*", "+")


class SnowScene(SceneBase):
    def __init__(self) -> None:
        self.system = ParticleSystem()
        self.accumulation: list[float] = []
        self.width = 0
        self.height = 0
        self.floor_y: int | None = None
        self.spawn_cooldown = 0.0
        self._rng = random.Random()

    def enter(self, weather: WeatherState) -> None:
        self.weather = weather
        self.system.clear()
        self.accumulation = []
        self._rng = random.Random(weather.location_name + "_snow")
    def update(
        self,
        dt: float,
        weather: WeatherState,
        width: int,
        height: int,
        lighting: "LightingState | None" = None,
        floor_y: int | None = None,
    ) -> None:
        self.width = width
        self.height = height
        if floor_y is None:
            floor_y = self.floor_y if self.floor_y is not None else scene_floor_y(height)
        self.floor_y = floor_y

        # Safe resize handling: preserve existing accumulation if resizing
        if len(self.accumulation) != width:
            if not self.accumulation:
                self.accumulation = [0.0] * width
            elif len(self.accumulation) < width:
                self.accumulation.extend([0.0] * (width - len(self.accumulation)))
            else:
                self.accumulation = self.accumulation[:width]

        # Detect snow landing on the ground floor to build accumulation slowly
        ground_y = max(0, min(height - 1, floor_y))
        for p in self.system.particles:
            if p.y + p.vy * dt >= ground_y and 0 <= p.x < width:
                col = int(p.x)
                if 0 <= col < width:
                    self.accumulation[col] = min(1.0, self.accumulation[col] + 0.04)
                    if col > 0:
                        self.accumulation[col - 1] = min(1.0, self.accumulation[col - 1] + 0.01)
                    if col < width - 1:
                        self.accumulation[col + 1] = min(1.0, self.accumulation[col + 1] + 0.01)

        self.system.step(dt, width, height)

        rad = math.radians(weather.wind_direction)
        wind_vx = math.sin(rad) * (weather.wind_speed / 18.0)
        wind_vx = max(-2.5, min(2.5, wind_vx))

        target = max(10, int(weather.cloud_coverage * 0.6))
        coverage_norm = weather.cloud_coverage / 100.0
        per_tick = 1 + int(coverage_norm * 3)  # 1..4 per tick
        self.spawn_cooldown -= dt
        spawn_interval = 0.04
        while self.spawn_cooldown <= 0:
            self.spawn_cooldown += spawn_interval
            for _ in range(per_tick):
                if len(self.system.particles) >= target * 6:
                    break
                vy = self._rng.uniform(1.5, 4.5)
                vx = wind_vx + self._rng.uniform(-0.6, 0.6)
                char = self._rng.choice(_SNOW_CHARS)
                self.system.spawn(
                    Particle(
                        x=self._rng.uniform(0, max(1, width - 1)),
                        y=self._rng.uniform(-2, 0),
                        vx=vx,
                        vy=vy,
                        age=0.0,
                        lifetime=self._rng.uniform(6.0, 12.0),
                        char=char,
                    )
                )

    def draw(
        self,
        buf: FrameBuffer,
        lighting: "LightingState | None" = None,
        dim: float = 1.0,
        floor_y: int | None = None,
    ) -> None:
        style = "white" if dim >= 1.0 else "240"
        self.system.draw(buf, style)

        # Ground snow accumulation rendered at layout-aware floor_y
        if floor_y is None:
            floor_y = self.floor_y if self.floor_y is not None else scene_floor_y(buf.height)
        ground_row = max(0, min(buf.height - 1, floor_y))
        if buf.height > 0 and self.accumulation:
            for x, depth in enumerate(self.accumulation[:buf.width]):
                if depth >= 0.65:
                    buf.set(ground_row, x, "_", style)
                elif depth >= 0.35:
                    buf.set(ground_row, x, ".", style)
                elif depth >= 0.1:
                    buf.set(ground_row, x, "·", style)

    def exit(self) -> None:
        self.system.clear()
        self.accumulation = []
        self.floor_y = None
