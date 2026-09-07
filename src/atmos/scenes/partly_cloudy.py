"""Partly cloudy scene: sun arc + 1-2 sparse cloud bands + stars at night."""

from __future__ import annotations

import math
import random

from atmos.engine.frame_buffer import FrameBuffer
from atmos.engine.lighting import LightingState
from atmos.scenes._atmosphere import Stars, draw_moon, draw_stars, draw_sun, init_stars
from atmos.scenes.base import SceneBase
from atmos.scenes.cloudy import _band
from atmos.weather.models import WeatherState


class PartlyCloudyScene(SceneBase):
    def __init__(self) -> None:
        self.bands: list[dict] = []
        self.stars = Stars()
        self._rng = random.Random()
        self.width = 0
        self.height = 0
        self.center_x = 0
        self._time_s = 0.0

    def enter(self, weather: WeatherState) -> None:
        self.weather = weather
        self.bands = []
        self.stars.points = []
        self._rng = random.Random(weather.location_name + "_pc")

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

        rad = math.radians(weather.wind_direction)
        drift = math.sin(rad) * (weather.wind_speed / 18.0)

        target_bands = 1 if weather.cloud_coverage < 55 else 2
        if not self.bands or len(self.bands) != target_bands:
            self._init_bands(target_bands, width, height, weather.cloud_coverage)
        for b in self.bands:
            b["x"] += drift * dt
            if drift >= 0 and b["x"] > width:
                b["x"] = -b["length"]
            elif drift < 0 and b["x"] + b["length"] < 0:
                b["x"] = float(width)

        if lighting is not None and lighting.star_density > 0:
            if not self.stars.points:
                init_stars(
                    self.stars,
                    density=lighting.star_density,
                    width=width,
                    height=height,
                    seed=weather.location_name + "_pc",
                )
        else:
            self.stars.points = []

    def _init_bands(self, count: int, width: int, height: int, coverage: float) -> None:
        self.bands = []
        upper = max(4, int(height * 0.55))
        positions = [upper // 3, (upper * 2) // 3] if count >= 2 else [upper // 2]
        for y in positions[:count]:
            length, sprite = _band(width, coverage, self._rng)
            self.bands.append(
                {
                    "x": self._rng.uniform(-length, max(1, width - 1)),
                    "y": y,
                    "length": length,
                    "sprite": sprite,
                }
            )

    def draw(
        self,
        buf: FrameBuffer,
        lighting: LightingState | None = None,
        dim: float = 1.0,
    ) -> None:
        if self.width <= 0 or self.height <= 0:
            return
        # Stars first so clouds draw over them.
        if lighting is not None and lighting.star_density > 0:
            star_style = "white" if dim >= 1.0 else "240"
            draw_stars(buf, self.stars, self._time_s, style=star_style)
        # Sun or moon.
        if lighting is not None and lighting.sun_visible:
            draw_sun(buf, lighting, self.center_x)
        elif lighting is not None:
            draw_moon(buf, lighting, self.center_x)
        # Cloud bands.
        cloud_style = "white" if dim >= 1.0 else "240"
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
                        buf.set(y + row, x, ch, cloud_style)

    def exit(self) -> None:
        self.bands = []
        self.stars.points = []
