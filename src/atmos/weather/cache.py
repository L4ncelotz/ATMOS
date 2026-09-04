"""JSON cache for last successful weather snapshot.

Path: platformdirs.user_cache_dir("atmos") / "weather_cache.json"

Two keys per location label:
  current: { fetched_at, state }
  forecast: { fetched_at, days: [ForecastDay, ...] }

The cache is intentionally dumb: we never invalidate. Manual refresh
(R key) just overwrites. Future stages may add TTL.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import platformdirs

from atmos.weather.forecast import ForecastDay
from atmos.weather.location import Location
from atmos.weather.models import WeatherState


_CACHE_DIR = Path(platformdirs.user_cache_dir("atmos", appauthor=False))
CACHE_FILE = _CACHE_DIR / "weather_cache.json"


def _cache_path() -> Path:
    return CACHE_FILE


def _ensure_dir(path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        # If we cannot create the cache directory (sandbox, read-only fs),
        # silently skip caching. The caller gets None on read and write is
        # a no-op.
        pass


def read_all() -> dict[str, dict[str, Any]]:
    path = _cache_path()
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        return {}
    except (OSError, json.JSONDecodeError):
        return {}


def _write_payload(data: dict[str, Any]) -> None:
    path = _cache_path()
    _ensure_dir(path)
    if not path.parent.exists():
        return
    try:
        fd, tmp = tempfile.mkstemp(prefix=".atmos_cache_", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f)
            os.replace(tmp, path)
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass
    except OSError:
        pass


def _fetched_at() -> str:
    return datetime.utcnow().isoformat() + "Z"


def write_state(location: Location, state: WeatherState) -> None:
    data = read_all()
    entry = data.get(location.label) or {}
    entry["fetched_at"] = _fetched_at()
    entry["state"] = state.model_dump(mode="json")
    data[location.label] = entry
    _write_payload(data)


def read_for_location(location: Location) -> WeatherState | None:
    data = read_all()
    entry = data.get(location.label)
    if not isinstance(entry, dict):
        return None
    state_raw = entry.get("state")
    if not isinstance(state_raw, dict):
        return None
    try:
        return WeatherState.model_validate(state_raw)
    except Exception:  # noqa: BLE001 — pydantic raises various subclasses
        return None


def write_forecast(location: Location, days: list[ForecastDay]) -> None:
    data = read_all()
    entry = data.get(location.label) or {}
    entry["fetched_at"] = _fetched_at()
    entry["forecast"] = [d.model_dump(mode="json") for d in days]
    data[location.label] = entry
    _write_payload(data)


def read_forecast_for(location: Location) -> list[ForecastDay]:
    data = read_all()
    entry = data.get(location.label)
    if not isinstance(entry, dict):
        return []
    raw = entry.get("forecast")
    if not isinstance(raw, list):
        return []
    out: list[ForecastDay] = []
    for r in raw:
        if not isinstance(r, dict):
            continue
        try:
            out.append(ForecastDay.model_validate(r))
        except Exception:  # noqa: BLE001
            continue
    return out