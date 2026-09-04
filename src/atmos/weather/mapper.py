"""WMO weather code → normalized condition string + daily forecast parser.

Open-Meteo returns WMO 4677 codes in `current.weather_code` and
`daily.weather_code`. Reference: https://open-meteo.com/en/docs

Returns one of:
  clear | partly_cloudy | cloudy | rain | heavy_rain | storm |
  snow | fog | wind

`wind` is reserved for "windy without precipitation"; we trigger it when
wind_speed exceeds a threshold even if the WMO code is "clear".
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from atmos.weather.forecast import ForecastDay


# WMO → condition. Anything not listed falls back to "cloudy" as a safe default.
_WMO_TABLE: dict[int, str] = {
    0: "clear",
    1: "partly_cloudy",
    2: "partly_cloudy",
    3: "cloudy",
    45: "fog",
    48: "fog",
    51: "rain",
    53: "rain",
    55: "rain",
    56: "rain",
    57: "rain",
    61: "rain",
    63: "rain",
    65: "heavy_rain",
    66: "rain",
    67: "heavy_rain",
    71: "snow",
    73: "snow",
    75: "snow",
    77: "snow",
    80: "rain",
    81: "rain",
    82: "heavy_rain",
    85: "snow",
    86: "snow",
    95: "storm",
    96: "storm",
    99: "storm",
}


def wmo_to_condition(code: int | None) -> str:
    if code is None:
        return "cloudy"
    return _WMO_TABLE.get(int(code), "cloudy")


def upgrade_for_wind(condition: str, wind_speed: float) -> str:
    """Promote 'clear' to 'wind' when wind is strong and sky is clear."""
    if condition == "clear" and wind_speed >= 25.0:
        return "wind"
    return condition


def parse_iso(dt_str: str | None) -> datetime | None:
    """Parse Open-Meteo ISO8601 timestamps. None → None."""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str)
    except ValueError:
        return None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def to_weather_state(
    payload: dict,
    *,
    location_name: str,
    country_code: str = "",
    location_tz: str = "UTC",
) -> "WeatherState | None":
    """Convert an Open-Meteo /v1/forecast response to WeatherState.

    Returns None if the payload is missing required fields. The caller is
    responsible for raising WeatherError.
    """
    from atmos.weather.models import WeatherState  # local to avoid cycle

    current = payload.get("current") or {}
    daily = payload.get("daily") or {}
    try:
        temperature = float(current["temperature_2m"])
        feels_like = float(current["apparent_temperature"])
        humidity = int(current["relative_humidity_2m"])
        wind_speed = float(current["wind_speed_10m"])
        wind_direction = float(current["wind_direction_10m"])
        precipitation = float(current.get("precipitation", 0.0))
        cloud_coverage = float(current.get("cloud_cover", 0.0))
        code = current.get("weather_code")
    except (KeyError, TypeError, ValueError):
        return None

    condition = wmo_to_condition(code if isinstance(code, int) else None)
    condition = upgrade_for_wind(condition, wind_speed)

    local_time = parse_iso(current.get("time")) or _utcnow()
    sunrise = None
    sunset = None
    sunrises = daily.get("sunrise") or []
    sunsets = daily.get("sunset") or []
    if sunrises:
        sunrise = parse_iso(sunrises[0])
    if sunsets:
        sunset = parse_iso(sunsets[0])

    return WeatherState(
        location_name=location_name,
        country_code=country_code or None,
        temperature=temperature,
        feels_like=feels_like,
        humidity=humidity,
        wind_speed=wind_speed,
        wind_direction=wind_direction,
        precipitation=precipitation,
        precipitation_probability=None,
        cloud_coverage=cloud_coverage,
        condition=condition,
        local_time=local_time,
        sunrise=sunrise,
        sunset=sunset,
    )


def parse_daily_payload(payload: dict) -> list[ForecastDay]:
    """Convert the `daily` block of an Open-Meteo /v1/forecast response
    into a list of ForecastDay, parallel to `time[]`.

    Missing or malformed entries are silently dropped; an empty list is
    possible if the payload has no `daily` block.
    """
    daily = payload.get("daily") or {}
    times = daily.get("time") or []
    tmin = daily.get("temperature_2m_min") or []
    tmax = daily.get("temperature_2m_max") or []
    psum = daily.get("precipitation_sum") or []
    pprob = daily.get("precipitation_probability_max") or []
    codes = daily.get("weather_code") or []

    out: list[ForecastDay] = []
    for i, ts in enumerate(times):
        try:
            d = date.fromisoformat(ts[:10])
        except (ValueError, IndexError):
            continue
        try:
            mn = float(tmin[i]) if i < len(tmin) else 0.0
            mx = float(tmax[i]) if i < len(tmax) else 0.0
            ps = float(psum[i]) if i < len(psum) else 0.0
        except (TypeError, ValueError):
            continue
        pp = None
        if i < len(pprob) and pprob[i] is not None:
            try:
                pp = float(pprob[i])
            except (TypeError, ValueError):
                pp = None
        code = codes[i] if i < len(codes) else None
        cond = wmo_to_condition(code if isinstance(code, int) else None)
        out.append(
            ForecastDay(
                date=d,
                temp_min=mn,
                temp_max=mx,
                precipitation=ps,
                precipitation_probability=pp,
                condition=cond,
            )
        )
    return out