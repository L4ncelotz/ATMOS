"""ForecastDay — one row of the multi-day forecast.

Returned by WeatherProvider.forecast(). Mirrors the Open-Meteo daily schema
plus our normalized condition string.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class ForecastDay(BaseModel):
    date: date
    temp_min: float
    temp_max: float
    precipitation: float  # mm total
    precipitation_probability: float | None = None  # 0..100
    condition: str  # normalized condition string