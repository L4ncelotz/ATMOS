"""Mock WeatherState presets — one per V1 scene.

Hand-picked values that make each scene visually distinct:
  - clear:  calm, low cloud, no precip
  - cloudy: medium wind, heavy cloud coverage
  - rain:   moderate precip, wind from south-east
  - storm:  heavy precip, strong wind, dense cloud
"""

from __future__ import annotations

from datetime import datetime

from atmos.weather.models import WeatherState

_NOON = datetime(2026, 9, 3, 12, 0, 0)

MOCK: dict[str, WeatherState] = {
    "clear": WeatherState(
        location_name="Bangkok",
        country_code="TH",
        temperature=32.0,
        feels_like=34.0,
        humidity=55,
        wind_speed=6.0,
        wind_direction=180.0,
        precipitation=0.0,
        precipitation_probability=0.0,
        cloud_coverage=5.0,
        condition="clear",
        local_time=_NOON,
    ),
    "cloudy": WeatherState(
        location_name="Bangkok",
        country_code="TH",
        temperature=29.0,
        feels_like=31.0,
        humidity=68,
        wind_speed=10.0,
        wind_direction=45.0,
        precipitation=0.0,
        precipitation_probability=10.0,
        cloud_coverage=75.0,
        condition="cloudy",
        local_time=_NOON,
    ),
    "rain": WeatherState(
        location_name="Bangkok",
        country_code="TH",
        temperature=29.0,
        feels_like=33.0,
        humidity=78,
        wind_speed=12.0,
        wind_direction=120.0,
        precipitation=3.2,
        precipitation_probability=80.0,
        cloud_coverage=90.0,
        condition="rain",
        local_time=_NOON,
    ),
    "storm": WeatherState(
        location_name="Bangkok",
        country_code="TH",
        temperature=26.0,
        feels_like=29.0,
        humidity=92,
        wind_speed=28.0,
        wind_direction=200.0,
        precipitation=8.5,
        precipitation_probability=95.0,
        cloud_coverage=98.0,
        condition="storm",
        local_time=_NOON,
    ),
}

# Additional presets used by the local `--demo` CLI mode. They intentionally
# stay deterministic so every scene can be reviewed without a network call.
MOCK.update(
    {
        "partly_cloudy": MOCK["cloudy"].model_copy(
            update={
                "temperature": 31.0,
                "feels_like": 33.0,
                "cloud_coverage": 42.0,
                "condition": "partly_cloudy",
            }
        ),
        "heavy_rain": MOCK["rain"].model_copy(
            update={
                "temperature": 27.0,
                "feels_like": 29.0,
                "precipitation": 8.0,
                "cloud_coverage": 98.0,
                "condition": "heavy_rain",
            }
        ),
        "snow": WeatherState(
            location_name="Oslo",
            country_code="NO",
            temperature=-2.0,
            feels_like=-7.0,
            humidity=88,
            wind_speed=12.0,
            wind_direction=240.0,
            precipitation=1.5,
            precipitation_probability=90.0,
            cloud_coverage=94.0,
            condition="snow",
            local_time=_NOON,
        ),
        "fog": MOCK["cloudy"].model_copy(
            update={
                "temperature": 20.0,
                "humidity": 96,
                "cloud_coverage": 100.0,
                "condition": "fog",
            }
        ),
        "wind": MOCK["clear"].model_copy(
            update={
                "temperature": 24.0,
                "wind_speed": 32.0,
                "wind_direction": 270.0,
                "condition": "wind",
            }
        ),
    }
)
