"""Clear scene: sun arc + drifting motes + stars at night + rare shooting stars.

See README.md "Features → Scenes" for the visual specification.
"""

from __future__ import annotations

import math
import random

from atmos.engine.frame_buffer import FrameBuffer
from atmos.engine.lighting import LightingPhase, LightingState
from atmos.engine.particles import Particle, ParticleSystem
from atmos.scenes._atmosphere import Stars, draw_moon, draw_stars, draw_sun, init_stars
from atmos.scenes.base import SceneBase
from atmos.weather.models import WeatherState


class ClearScene(SceneBase):
    def __init__(self) -> None:
        self.system = ParticleSystem()
        self.stars = Stars()
        self.width = 0
        self.height = 0
        self.center_x = 0
        self.spawn_cooldown = 0.0
        self._rng = random.Random()
        # Shooting-star scheduling.
        self._next_shooting = 0.0
        self._shooting: list[tuple[float, float, float, float, str]] = []  # x,y,vx,vy,char
        self._time_s = 0.0

    def enter(self, weather: WeatherState) -> None:
        self.weather = weather
        self.system.clear()
        self.stars.points = []
        self._shooting = []
        self._next_shooting = self._rng.uniform(15.0, 40.0)

    def update(
        self,
        dt: float,
        weather: WeatherState,
        width: int,
        height: int,
        lighting: LightingState | None = None,
    ) -> None:
        self.width = width
        self.height = height
        self.center_x = width // 2
        self._time_s += dt
        self.system.step(dt, width, height)

        rad = math.radians(weather.wind_direction)
        vx = math.sin(rad) * max(0.0, (weather.wind_speed - 12.0) / 6.0)
        vy = 0.2

        target = max(1, min(6, int(weather.wind_speed / 4.0)))
        self.spawn_cooldown -= dt
        if self.spawn_cooldown <= 0 and len(self.system.particles) < target:
            self.spawn_cooldown = 0.45
            self.system.spawn(
                Particle(
                    x=random.uniform(0, max(1, width - 1)),
                    y=random.uniform(0, max(1, height - 1)),
                    vx=vx,
                    vy=vy,
                    age=0.0,
                    lifetime=random.uniform(6.0, 10.0),
                    char="·",
                )
            )

        # Stars: init when lighting transitions to a phase that has them.
        if lighting is not None and lighting.star_density > 0:
            if not self.stars.points:
                init_stars(
                    self.stars,
                    density=lighting.star_density,
                    width=width,
                    height=height,
                    seed=weather.location_name + "_clear",
                )
        else:
            self.stars.points = []

        # Shooting star: only in the 02-04 window AND clear skies.
        if (
            lighting is not None
            and lighting.is_shooting_star_window
            and lighting.star_density > 20
        ):
            self._next_shooting -= dt
            if self._next_shooting <= 0 and not self._shooting:
                # Spawn one streak across upper third.
                start_x = self._rng.uniform(-10, width * 0.4)
                y = self._rng.uniform(2, max(3, height // 3))
                # Trajectory: down-right.
                self._shooting = [
                    (start_x, y, 30.0, 8.0, "*"),
                    (start_x - 1.0, y - 1.0, 30.0, 8.0, "\\"),
                ]
                self._next_shooting = self._rng.uniform(20.0, 60.0)

        # Advance shooting star particles; remove when off-screen.
        if self._shooting:
            alive: list[tuple[float, float, float, float, str]] = []
            for sx, sy, svx, svy, ch in self._shooting:
                sx += svx * dt
                sy += svy * dt
                if sx > width + 2 or sy > height:
                    continue
                alive.append((sx, sy, svx, svy, ch))
            self._shooting = alive

    def draw(
        self,
        buf: FrameBuffer,
        lighting: LightingState | None = None,
        dim: float = 1.0,
    ) -> None:
        if self.width <= 0 or self.height <= 0:
            return
        # Sun (or moon, depending on phase).
        if lighting is not None and lighting.sun_visible:
            draw_sun(buf, lighting, self.center_x)
        elif lighting is not None:
            draw_moon(buf, lighting, self.center_x)
        # Stars only at night (or dawn/dusk partial).
        if lighting is not None and lighting.star_density > 0:
            star_style = "white" if dim >= 1.0 else "240"
            draw_stars(buf, self.stars, self._time_s, style=star_style)
        # Motes.
        mote_style = "white" if dim >= 1.0 else "240"
        self.system.draw(buf, mote_style)
        # Shooting star overlay (drawn last so it sits on top).
        for sx, sy, _vx, _vy, ch in self._shooting:
            ix, iy = int(sx), int(sy)
            if 0 <= ix < buf.width and 0 <= iy < buf.height:
                buf.set(iy, ix, ch, "bright_white")

    def exit(self) -> None:
        self.system.clear()
        self.stars.points = []