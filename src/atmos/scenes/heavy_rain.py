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
        self.ripples: list[dict] = []
        self.width = 0
        self.height = 0
        self.spawn_cooldown = 0.0
        self._rng = random.Random()
    def enter(self, weather: WeatherState) -> None:
        self.weather = weather
        self.rain.clear()
        self.splash.clear()
        self.ripples = []
        self._rng = random.Random(weather.location_name + "_heavy")
    def update(self, dt: float, weather: WeatherState, width: int, height: int, lighting: "LightingState | None" = None) -> None:
        self.width = width
        self.height = height

        # Detect heavy raindrops reaching ground to spawn splashes and ripples
        ground_y = max(0, height - 1)
        max_splash = 45
        max_ripples = min(30, max(5, int(width * 0.25)))
        for p in self.rain.particles:
            if p.y + p.vy * dt >= ground_y and 0 <= p.x < width:
                # Spawn upward bouncing splash droplets
                if len(self.splash.particles) < max_splash and self._rng.random() < 0.5:
                    self.splash.spawn(
                        Particle(
                            x=p.x,
                            y=float(ground_y),
                            vx=self._rng.uniform(-2.5, 2.5),
                            vy=self._rng.uniform(-7.0, -14.0),
                            age=0.0,
                            lifetime=self._rng.uniform(0.12, 0.25),
                            char=self._rng.choice(["^", "'", "·", "°"]),
                        )
                    )
                # Spawn puddle ripple
                if len(self.ripples) < max_ripples and self._rng.random() < 0.4:
                    self.ripples.append(
                        {
                            "x": int(p.x),
                            "y": ground_y,
                            "age": 0.0,
                            "lifetime": self._rng.uniform(0.3, 0.5),
                        }
                    )

        # Advance ripples
        alive_ripples: list[dict] = []
        for r in self.ripples:
            r["age"] += dt
            if r["age"] < r["lifetime"] and r["y"] < height:
                alive_ripples.append(r)
        self.ripples = alive_ripples

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

        # Ground puddle ripples
        ripple_style = "cyan" if dim >= 1.0 else "240"
        for r in self.ripples:
            x = r["x"]
            y = r["y"]
            if y < 0 or y >= buf.height:
                continue
            progress = r["age"] / r["lifetime"] if r["lifetime"] > 0 else 1.0
            if progress < 0.3:
                if 0 <= x < buf.width:
                    buf.set(y, x, "·", splash_style)
            elif progress < 0.7:
                # Stronger ripple: (≈)
                if 0 <= x - 1 < buf.width:
                    buf.set(y, x - 1, "(", ripple_style)
                if 0 <= x < buf.width:
                    buf.set(y, x, "≈", ripple_style)
                if 0 <= x + 1 < buf.width:
                    buf.set(y, x + 1, ")", ripple_style)
            else:
                if 0 <= x < buf.width:
                    buf.set(y, x, "≈", ripple_style)

    def exit(self) -> None:
        self.rain.clear()
        self.splash.clear()
        self.ripples = []