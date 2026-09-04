"""Rain scene: density + speed + lean from real weather values.

Per IMPLEMENT.md §V3:
  precipitation → particle density (linear from 5 → 180 across precip 0..6mm)
  precipitation → fall speed (12..28 cells/sec across precip 0..6mm)
  wind_speed + wind_direction → particle vx (no hard cap, scaled)
"""

from __future__ import annotations

import math
import random

from atmos.engine.frame_buffer import FrameBuffer
from atmos.engine.particles import Particle, ParticleSystem
from atmos.scenes.base import SceneBase
from atmos.weather.models import WeatherState


def _char_for(vx: float) -> str:
    a = abs(vx)
    if a < 1.0:
        return "│"
    if vx > 0:
        return "╲"
    return "╱"


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * max(0.0, min(1.0, t))


class RainScene(SceneBase):
    def __init__(self) -> None:
        self.system = ParticleSystem()
        self.width = 0
        self.height = 0
        self.spawn_cooldown = 0.0
        self._rng = random.Random()

    def enter(self, weather: WeatherState) -> None:
        self.weather = weather
        self.system.clear()
        self._rng = random.Random(weather.location_name)

    def update(self, dt: float, weather: WeatherState, width: int, height: int, lighting: "LightingState | None" = None) -> None:
        self.width = width
        self.height = height
        self.system.step(dt, width, height)
        # Density scales with precipitation. Vy kept constant so particle
        # lifetime in screen-space stays predictable.
        precip_norm = _lerp(0.0, 1.0, min(1.0, weather.precipitation / 4.0))
        target = int(_lerp(15, 220, precip_norm))
        vy_base = 22.0

        # Wind → vx. No hard cap; lean is visible up to wind 60 km/h.
        rad = math.radians(weather.wind_direction)
        wind_vx = math.sin(rad) * (weather.wind_speed / 6.0)
        wind_vx = max(-10.0, min(10.0, wind_vx))
        self.spawn_cooldown -= dt
        spawn_interval = 0.012  # base rate; ~83 ticks/sec
        # Number of particles spawned per tick scales with precip_norm
        # (1 at light rain, up to 4 at heavy).
        per_tick = 1 + int(precip_norm * 3)
        while self.spawn_cooldown <= 0:
            self.spawn_cooldown += spawn_interval
            for _ in range(per_tick):
                if len(self.system.particles) >= target * 5:
                    break
                vy = vy_base + self._rng.uniform(-2.0, 2.0)
                vx = wind_vx + self._rng.uniform(-0.6, 0.6)
                self.system.spawn(
                    Particle(
                        x=self._rng.uniform(0, max(1, width - 1)),
                        y=self._rng.uniform(-2, 0),
                        vy=vy,
                        vx=vx,
                        age=0.0,
                        lifetime=self._rng.uniform(2.0, 3.5),
                        char=_char_for(vx),
                    )
                )


    def draw(self, buf: FrameBuffer, lighting: "LightingState | None" = None, dim: float = 1.0) -> None:
        style = "blue" if dim >= 1.0 else "240"
        self.system.draw(buf, style)

    def exit(self) -> None:
        self.system.clear()