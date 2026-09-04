"""Open-Meteo weather provider.

Endpoint: https://api.open-meteo.com/v1/forecast
No API key required. Field list tuned to WeatherState fields.

Raises WeatherError on network failure or malformed payload; the caller
(WeatherRefresher) decides whether to fall back to cache.
"""

from __future__ import annotations

import httpx

from atmos.weather.client import WeatherError
from atmos.weather.forecast import ForecastDay
from atmos.weather.location import Location
from atmos.weather.mapper import parse_daily_payload, to_weather_state
from atmos.weather.models import WeatherState

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_S = 8.0

CURRENT_FIELDS = (
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
    "wind_direction_10m",
    "cloud_cover",
    "weather_code",
)

DAILY_FIELDS = (
    "temperature_2m_min",
    "temperature_2m_max",
    "precipitation_sum",
    "precipitation_probability_max",
    "weather_code",
)


class OpenMeteoProvider:
    def __init__(self, *, client: httpx.Client | None = None) -> None:
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=TIMEOUT_S)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "OpenMeteoProvider":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def current(self, location: Location) -> WeatherState:
        try:
            resp = self._client.get(
                FORECAST_URL,
                params={
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                    "current": ",".join(CURRENT_FIELDS),
                    "daily": "sunrise,sunset",
                    "timezone": "auto",
                    "wind_speed_unit": "kmh",
                },
            )
            resp.raise_for_status()
            payload = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise WeatherError(f"open-meteo request failed: {exc}") from exc

        state = to_weather_state(
            payload,
            location_name=location.name,
            country_code=location.country,
            location_tz=location.timezone,
        )
        if state is None:
            raise WeatherError("open-meteo payload missing required fields")
        return state

    def forecast(self, location: Location, days: int = 5) -> list[ForecastDay]:
        try:
            resp = self._client.get(
                FORECAST_URL,
                params={
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                    "daily": ",".join(DAILY_FIELDS),
                    "timezone": "auto",
                    "forecast_days": max(1, min(16, days)),
                },
            )
            resp.raise_for_status()
            payload = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise WeatherError(f"open-meteo forecast failed: {exc}") from exc

        return parse_daily_payload(payload)