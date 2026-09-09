"""Rain scene: density + speed + lean from real weather values.

Behavior:
  precipitation → particle density (linear from 5 → 180 across precip 0..6mm)
  precipitation → fall speed (12..28 cells/sec across precip 0..6mm)
  wind_speed + wind_direction → particle vx (no hard cap, scaled)
"""

from __future__ import annotations

import math
import random

from atmos.engine.environment import EnvironmentState
from atmos.engine.frame_buffer import FrameBuffer
from atmos.engine.layout import scene_floor_y
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
        self.ripples: list[dict] = []
        self.width = 0
        self.height = 0
        self.floor_y: int | None = None
        self.spawn_cooldown = 0.0
        self._rng = random.Random()

    def enter(self, weather: WeatherState) -> None:
        self.weather = weather
        self.system.clear()
        self.ripples = []
        self._rng = random.Random(weather.location_name)
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

        env = EnvironmentState.from_weather(weather)

        # Detect raindrops landing on the ground to spawn ripples
        ground_y = max(0, min(height - 1, floor_y))
        reaction_chance = 0.25 + 0.5 * env.precipitation_intensity
        max_ripples = min(25, max(4, int(width * 0.15 + env.precipitation_intensity * 10)))
        for p in self.system.particles:
            if p.y + p.vy * dt >= ground_y and 0 <= p.x < width:
                if len(self.ripples) < max_ripples and self._rng.random() < reaction_chance:
                    self.ripples.append(
                        {
                            "x": int(p.x),
                            "y": ground_y,
                            "age": 0.0,
                            "lifetime": self._rng.uniform(0.35, 0.55),
                        }
                    )
        # Advance ripples
        alive_ripples: list[dict] = []
        for r in self.ripples:
            r["age"] += dt
            if r["age"] < r["lifetime"] and r["y"] < height:
                alive_ripples.append(r)
        self.ripples = alive_ripples

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


    def draw(
        self,
        buf: FrameBuffer,
        lighting: "LightingState | None" = None,
        dim: float = 1.0,
        floor_y: int | None = None,
    ) -> None:
        style = "blue" if dim >= 1.0 else "240"
        self.system.draw(buf, style)

        # Ground ripples and splash reactions
        ripple_style = "bright_blue" if dim >= 1.0 else "240"
        for r in self.ripples:
            x = r["x"]
            y = r["y"]
            if y < 0 or y >= buf.height:
                continue
            progress = r["age"] / r["lifetime"] if r["lifetime"] > 0 else 1.0
            if progress < 0.3:
                # Impact point
                if 0 <= x < buf.width:
                    buf.set(y, x, "·", ripple_style)
            elif progress < 0.7:
                # Puddle ripple expanding: ( )
                if 0 <= x - 1 < buf.width:
                    buf.set(y, x - 1, "(", ripple_style)
                if 0 <= x < buf.width:
                    buf.set(y, x, " ", ripple_style)
                if 0 <= x + 1 < buf.width:
                    buf.set(y, x + 1, ")", ripple_style)
            else:
                # Settling ripple
                if 0 <= x < buf.width:
                    buf.set(y, x, "~", ripple_style)

    def exit(self) -> None:
        self.system.clear()
        self.ripples = []