"""Heavy rain scene: dense, fast rain + splash particles near the floor.

Distinct from Storm (which adds lightning). HeavyRain is just more rain.
Splashes are short-lived horizontal marks at the bottom row when a rain
particle reaches the floor.
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
    if a < 2.0:
        return "│"
    if vx > 0:
        return "╲"
    return "╱"


class HeavyRainScene(SceneBase):
    def __init__(self) -> None:
        self.rain = ParticleSystem()
        self.splash = ParticleSystem()
        self.width = 0
        self.height = 0
        self.spawn_cooldown = 0.0
        self._rng = random.Random()

    def enter(self, weather: WeatherState) -> None:
        self.weather = weather
        self.rain.clear()
        self.splash.clear()
        self._rng = random.Random(weather.location_name + "_heavy")

    def update(self, dt: float, weather: WeatherState, width: int, height: int, lighting: "LightingState | None" = None) -> None:
        self.width = width
        self.height = height
        self.rain.step(dt, width, height)
        self.splash.step(dt, width, height)

        rad = math.radians(weather.wind_direction)
        wind_vx = math.sin(rad) * (weather.wind_speed / 6.0)
        wind_vx = max(-7.0, min(7.0, wind_vx))

        # Capped at 300: the user reported 1,235 particles in a 120x30
        # storm frame. Visually equivalent at 30 FPS, and keeps terminal
        # output under ~50 KB/s once the frame-buffer coalescing from
        # Step 5 is in place. Do NOT raise this without re-profiling.
        target = min(300, max(40, int((weather.precipitation + 1.0) * 32)))
        precip_norm = min(1.0, weather.precipitation / 6.0)
        # Capped at 4: dampens per-frame churn without changing
        # steady-state particle count.
        per_tick = 2 + int(precip_norm * 2)  # 2..4 per tick
        self.spawn_cooldown -= dt
        spawn_interval = 0.005
        while self.spawn_cooldown <= 0:
            self.spawn_cooldown += spawn_interval
            for _ in range(per_tick):
                if len(self.rain.particles) >= target:
                    break
                vy = self._rng.uniform(34.0, 48.0)
                vx = wind_vx + self._rng.uniform(-1.2, 1.2)
                self.rain.spawn(
                    Particle(
                        x=self._rng.uniform(0, max(1, width - 1)),
                        y=self._rng.uniform(-2, 0),
                        vx=vx,
                        vy=vy,
                        age=0.0,
                        lifetime=self._rng.uniform(1.6, 2.6),
                        char=_char_for(vx),
                    )
                )

    def draw(self, buf: FrameBuffer, lighting: "LightingState | None" = None, dim: float = 1.0) -> None:
        rain_style = "bright_blue" if dim >= 1.0 else "240"
        splash_style = "blue" if dim >= 1.0 else "240"
        self.rain.draw(buf, rain_style)
        self.splash.draw(buf, splash_style)

    def exit(self) -> None:
        self.rain.clear()
        self.splash.clear()