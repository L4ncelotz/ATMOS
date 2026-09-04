"""Base scene interface — all scenes share these four hooks."""

from __future__ import annotations

from typing import Protocol

from atmos.engine.frame_buffer import FrameBuffer
from atmos.engine.lighting import LightingState
from atmos.weather.models import WeatherState


class BaseScene(Protocol):
    def enter(self, weather: WeatherState) -> None: ...
    def update(
        self,
        dt: float,
        weather: WeatherState,
        width: int,
        height: int,
        lighting: LightingState | None = None,
    ) -> None: ...
    def draw(
        self,
        buf: FrameBuffer,
        lighting: LightingState | None = None,
        dim: float = 1.0,
    ) -> None: ...
    def exit(self) -> None: ...


class SceneBase:
    """Concrete base. Subclasses override hooks. Default impls are no-ops."""

    def enter(self, weather: WeatherState) -> None:
        self.weather = weather

    def update(
        self,
        dt: float,
        weather: WeatherState,
        width: int,
        height: int,
        lighting: LightingState | None = None,
    ) -> None:
        return

    def draw(
        self,
        buf: FrameBuffer,
        lighting: LightingState | None = None,
        dim: float = 1.0,
    ) -> None:
        return

