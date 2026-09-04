"""Weather models — internal canonical shape.

All providers (Open-Meteo in V2, others later) must normalize into
WeatherState. The renderer never sees provider-specific fields.
"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel

from atmos.weather.forecast import ForecastDay  # re-export


class WeatherState(BaseModel):
    location_name: str
    country_code: str | None = None

    temperature: float
    feels_like: float
    humidity: int

    wind_speed: float
    wind_direction: float  # degrees from north (meteorological convention)

    precipitation: float  # mm (last hour)
    precipitation_probability: float | None = None  # 0..100
    cloud_coverage: float  # 0..100

    condition: str  # normalized: clear|partly_cloudy|cloudy|rain|heavy_rain|storm|snow|fog|wind

    local_time: datetime
    sunrise: datetime | None = None
    sunset: datetime | None = None


__all__ = ["WeatherState", "ForecastDay"]