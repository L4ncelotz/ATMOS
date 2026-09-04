"""WeatherProvider: provider abstraction.

The renderer never sees Open-Meteo response shapes. Providers normalize
their payload into WeatherState / ForecastDay (see weather/models.py)
before returning.

Two implementations ship:
  - OpenMeteoProvider: live network, Open-Meteo API.
  - CachedProvider:    reads last successful state from cache file.

WeatherRefresher (weather/refresher.py) tries the live provider first,
falls back to cache on failure, and surfaces results via a queue.
"""

from __future__ import annotations

from typing import Protocol

from atmos.weather.forecast import ForecastDay
from atmos.weather.location import Location
from atmos.weather.models import WeatherState


class WeatherProvider(Protocol):
    def current(self, location: Location) -> WeatherState: ...

    def forecast(self, location: Location, days: int = 5) -> list[ForecastDay]: ...


class WeatherError(Exception):
    """Raised by providers on network / parse failure."""