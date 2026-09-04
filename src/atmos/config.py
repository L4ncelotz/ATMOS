"""TOML config persistence.

Path: platformdirs.user_config_dir("atmos", appauthor=False) / "config.toml"

Read on startup; written on change. Missing file → defaults. Malformed
file → defaults + warning logged to stderr (not over the animation).

Schema (v1):

    location = "Bangkok"
    fps = 30
    minimal = false
    sound = false
    units = "metric"
    refresh_minutes = 15

    [last_location]
    name = "Bangkok"
    country = "Thailand"
    latitude = 13.75398
    longitude = 100.50144
    timezone = "Asia/Bangkok"
"""

from __future__ import annotations

import sys
import tomllib
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

import platformdirs


_CONFIG_DIR = Path(platformdirs.user_config_dir("atmos", appauthor=False))
CONFIG_FILE = _CONFIG_DIR / "config.toml"


@dataclass
class ResolvedLocation:
    """A fully-resolved city persisted between launches so that the cache
    is reachable without the geocoder being online."""

    name: str
    country: str
    latitude: float
    longitude: float
    timezone: str


@dataclass
class Config:
    location: str = "Bangkok"
    fps: int = 30
    minimal: bool = False
    sound: bool = False
    units: str = "metric"
    refresh_minutes: int = 15
    last_location: ResolvedLocation | None = None

    def with_overrides(self, **kwargs: Any) -> "Config":
        return replace(self, **kwargs)


DEFAULTS = Config()


def _config_path() -> Path:
    return CONFIG_FILE


def _coerce_resolved_location(raw: Any) -> ResolvedLocation | None:
    if not isinstance(raw, dict):
        return None
    try:
        return ResolvedLocation(
            name=str(raw["name"]),
            country=str(raw.get("country", "")),
            latitude=float(raw["latitude"]),
            longitude=float(raw["longitude"]),
            timezone=str(raw.get("timezone", "UTC")),
        )
    except (KeyError, TypeError, ValueError):
        return None


def load() -> Config:
    path = _config_path()
    if not path.exists():
        return Config()
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        sys.stderr.write(f"atmos: ignoring malformed config ({exc}); using defaults\n")
        return Config()
    if not isinstance(data, dict):
        return Config()
    cfg = Config()
    if isinstance(data.get("location"), str):
        cfg = replace(cfg, location=data["location"])
    if isinstance(data.get("fps"), int) and 5 <= data["fps"] <= 60:
        cfg = replace(cfg, fps=data["fps"])
    if isinstance(data.get("minimal"), bool):
        cfg = replace(cfg, minimal=data["minimal"])
    if isinstance(data.get("sound"), bool):
        cfg = replace(cfg, sound=data["sound"])
    if isinstance(data.get("units"), str) and data["units"] in {"metric", "imperial"}:
        cfg = replace(cfg, units=data["units"])
    if isinstance(data.get("refresh_minutes"), int) and 1 <= data["refresh_minutes"] <= 1440:
        cfg = replace(cfg, refresh_minutes=data["refresh_minutes"])
    last_loc = _coerce_resolved_location(data.get("last_location"))
    if last_loc is not None:
        cfg = replace(cfg, last_location=last_loc)
    return cfg


def _toml_value(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return f'"{v}"'
    return str(v)


def save(cfg: Config) -> None:
    path = _config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return
    body_lines = [
        "# atmos configuration",
        "",
    ]
    for k, v in asdict(cfg).items():
        if k == "last_location":
            continue
        body_lines.append(f"{k} = {_toml_value(v)}")
    if cfg.last_location is not None:
        body_lines.append("")
        body_lines.append("[last_location]")
        for k, v in asdict(cfg.last_location).items():
            body_lines.append(f"{k} = {_toml_value(v)}")
    body = "\n".join(body_lines) + "\n"
    try:
        path.write_text(body, encoding="utf-8")
    except OSError:
        sys.stderr.write(f"atmos: could not write config to {path}\n")


def update_resolved_location(loc) -> Config:
    """Persist a freshly-resolved city so the next launch can hit the
    cache without the geocoder.

    `loc` is an `atmos.weather.location.Location` (kept out of the
    function signature to avoid a config → weather import; structural
    typing is enough).
    """
    cfg = load()
    last = ResolvedLocation(
        name=loc.name,
        country=loc.country,
        latitude=loc.latitude,
        longitude=loc.longitude,
        timezone=loc.timezone,
    )
    cfg = replace(cfg, last_location=last, location=loc.name)
    save(cfg)
    return cfg


__all__ = [
    "Config",
    "DEFAULTS",
    "ResolvedLocation",
    "load",
    "save",
    "update_resolved_location",
    "CONFIG_FILE",
]