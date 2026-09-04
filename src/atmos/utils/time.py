"""Local-time derivation.

`WeatherState.local_time` is captured when the weather API responds
(typically every ~15 min). Rendering a clock from that field leaves
the user-visible HH:MM string stuck for long stretches. This module
provides `local_now(location)` so the renderer can derive a current
local time on every frame.

Result is naive (no tzinfo) on purpose — the renderer only uses
`.strftime` and `.hour` and a naive datetime is what `WeatherState`
already stores.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def local_now(location) -> datetime:
    """Return the current wall-clock time in `location.timezone`.

    `location` is duck-typed: anything with a `.timezone: str` attribute
    works (e.g. `atmos.weather.location.Location` or the persisted
    `atmos.config.ResolvedLocation`).

    Returns a naive datetime (tzinfo stripped) to match the shape of
    `WeatherState.local_time` from the API; `compute_lighting` does
    naive-vs-naive comparisons.

    Falls back to UTC if the timezone string is unknown. Never raises.
    """
    tz_name = getattr(location, "timezone", "UTC") or "UTC"
    try:
        return datetime.now(ZoneInfo(tz_name)).replace(tzinfo=None)
    except (ZoneInfoNotFoundError, ValueError):
        return datetime.utcnow()


__all__ = ["local_now"]