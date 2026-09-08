"""Environment state representation for rendering behavior."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from atmos.weather.models import WeatherState


@dataclass
class EnvironmentState:
    """Normalized environmental rendering parameters (all in range 0.0 to 1.0)."""

    cloud_intensity: float = 0.0
    precipitation_intensity: float = 0.0
    wind_intensity: float = 0.0
    fog_intensity: float = 0.0

    @classmethod
    def from_weather(cls, weather: WeatherState) -> EnvironmentState:
        """Seed environment state from current weather conditions."""
        cloud_intensity = max(0.0, min(1.0, weather.cloud_coverage / 100.0))

        if weather.precipitation > 0.0:
            precip_intensity = max(0.0, min(1.0, weather.precipitation / 10.0))
        elif weather.condition in ("rain", "heavy_rain", "storm", "snow"):
            precip_intensity = 0.3
        else:
            precip_intensity = 0.0

        wind_intensity = max(0.0, min(1.0, weather.wind_speed / 30.0))

        if weather.condition == "fog":
            fog_intensity = (
                max(0.4, min(1.0, weather.cloud_coverage / 100.0))
                if weather.cloud_coverage > 0.0
                else 1.0
            )
        else:
            fog_intensity = 0.0

        return cls(
            cloud_intensity=cloud_intensity,
            precipitation_intensity=precip_intensity,
            wind_intensity=wind_intensity,
            fog_intensity=fog_intensity,
        )


__all__ = ["EnvironmentState"]
