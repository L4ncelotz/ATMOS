"""Storm scene: very fast rain + randomized lightning bolts.

Per IMPLEMENT.md §Thunderstorm:
  - randomized lightning (50-100ms flash + bolt glyph)
  - variable rain intensity driven by precipitation
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
    if a < 1.5:
        return "│"
    if vx > 0:
        return "╲"
    return "╱"


class StormScene(SceneBase):
    def __init__(self) -> None:
        self.system = ParticleSystem()
        self.width = 0
        self.height = 0
        self.spawn_cooldown = 0.0
        self._rng = random.Random()
        self._next_flash = 0.0
        self._flash_timer = 0.0
        self._bolt_y_top = 0
        self._bolt_x_offset = 0

    def enter(self, weather: WeatherState) -> None:
        self.weather = weather
        self.system.clear()
        self._rng = random.Random(weather.location_name + "_storm")
        self._next_flash = self._rng.uniform(2.0, 6.0)
        self._flash_timer = 0.0

    def update(self, dt: float, weather: WeatherState, width: int, height: int, lighting: "LightingState | None" = None) -> None:
        self.width = width
        self.height = height
        self.system.step(dt, width, height)

        rad = math.radians(weather.wind_direction)
        wind_vx = math.sin(rad) * (weather.wind_speed / 5.0)
        wind_vx = max(-12.0, min(12.0, wind_vx))

        target = max(50, int((weather.precipitation + 1.0) * 38))
        precip_norm = min(1.0, weather.precipitation / 6.0)
        per_tick = 2 + int(precip_norm * 4)  # 2..6 per tick
        self.spawn_cooldown -= dt
        spawn_interval = 0.006
        while self.spawn_cooldown <= 0:
            self.spawn_cooldown += spawn_interval
            for _ in range(per_tick):
                if len(self.system.particles) >= target * 5:
                    break
                vy = self._rng.uniform(36.0, 50.0)
                vx = wind_vx + self._rng.uniform(-1.5, 1.5)
                self.system.spawn(
                    Particle(
                        x=self._rng.uniform(0, max(1, width - 1)),
                        y=self._rng.uniform(-2, 0),
                        vx=vx,
                        vy=vy,
                        age=0.0,
                        lifetime=self._rng.uniform(1.5, 2.5),
                        char=_char_for(vx),
                    )
                )

        if self._flash_timer > 0:
            self._flash_timer -= dt
        else:
            self._next_flash -= dt
            if self._next_flash <= 0:
                self._flash_timer = self._rng.uniform(0.05, 0.10)
                self._bolt_x_offset = self._rng.randint(-5, 5)
                self._bolt_y_top = self._rng.randint(1, max(2, height // 3))
                self._next_flash = self._rng.uniform(2.5, 7.5)

    def draw(self, buf: FrameBuffer, lighting: "LightingState | None" = None, dim: float = 1.0) -> None:
        raining_style = "bright_white" if self._flash_timer > 0 else ("bright_blue" if dim >= 1.0 else "240")
        self.system.draw(buf, raining_style)
        if self._flash_timer > 0 and self.width > 8 and self.height > 6:
            cx = self.width // 2 + self._bolt_x_offset
            y = self._bolt_y_top
            x = cx
            for i in range(min(10, self.height - y - 2)):
                yy = y + i
                if yy >= self.height:
                    break
                ch = "╲" if i % 2 == 0 else "╱"
                if 0 <= x < self.width:
                    buf.set(yy, x, ch, "bright_white")
                x += 1 if i % 2 == 0 else -1

    def exit(self) -> None:
        self.system.clear()