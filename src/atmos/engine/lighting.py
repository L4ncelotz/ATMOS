"""Day/night lighting engine.

Computes a LightingState from WeatherState. The renderer uses this for:
  - sun position (vertical arc through sunrise→sunset)
  - star visibility (NIGHT phase + low cloud coverage)
  - color palette (white vs dim grey for clouds)
  - rare events (shooting stars 02-04 local time)

When if sunrise/sunset are unavailable, fall back to coarse time-of-day
buckets so the app still behaves sensibly.
"""

from __future__ import annotations

import enum
import math
from dataclasses import dataclass
from datetime import datetime, time, timedelta


class LightingPhase(enum.Enum):
    NIGHT = "night"
    SUNRISE = "sunrise"
    MORNING = "morning"
    DAY = "day"
    SUNSET = "sunset"
    TWILIGHT = "twilight"
    EVENING = "evening"


@dataclass
class LightingState:
    phase: LightingPhase
    sun_y: float = -1.0       # row where sun is drawn; -1 = below horizon / not drawn
    sun_visible: bool = False
    star_density: int = 0      # number of stars to render
    is_shooting_star_window: bool = False  # 02:00-04:00 local

_SUNRISE_WINDOW = timedelta(minutes=30)
_SUNSET_WINDOW = timedelta(minutes=30)
_TWILIGHT_WINDOW = timedelta(minutes=60)

def _phase_from_time_only(t: datetime) -> LightingPhase:
    """Coarse phase from time-of-day, when sunrise/sunset are unknown."""
    h = t.hour
    if h < 5 or h >= 22:
        return LightingPhase.NIGHT
    if h < 7:
        return LightingPhase.SUNRISE
    if h < 10:
        return LightingPhase.MORNING
    if h < 16:
        return LightingPhase.DAY
    if h < 19:
        return LightingPhase.SUNSET
    return LightingPhase.EVENING


def _interpolate_sun_y(now: datetime, sunrise: datetime, sunset: datetime) -> float:
    """Sun y position: high at sunrise, low at sunset, arc upward in middle.

    Map progress (0..1) over daylight to a value that puts the sun roughly in
    the upper third of the screen during midday.
    """
    span = (sunset - sunrise).total_seconds()
    if span <= 0:
        return -1.0
    elapsed = (now - sunrise).total_seconds()
    progress = max(0.0, min(1.0, elapsed / span))
    # Arc: y = -cos(progress * pi) maps 0 → -1 → 1.
    arc = -math.cos(progress * math.pi)
    # Convert arc range [-1, 1] to row range [4 (top), 20 (bottom-ish)].
    # At progress=0 (sunrise), arc=-1 → y=4 (high). At progress=1 (sunset),
    # arc=-1 → y=4. Wait, that's wrong; both ends are arc=-1.
    # We want: sunrise y=4, sunset y=20, midday y=2 (highest).
    # So: y = sunrise_y + (sunset_y - sunrise_y) * progress,
    # with a midday bump of -2 cells.
    base = 4.0 + (20.0 - 4.0) * progress
    midday_bump = -2.0 * math.sin(progress * math.pi)
    return max(0.0, base + midday_bump)


def compute_lighting(weather: WeatherState) -> LightingState:
    """Derive a LightingState from the current weather."""
    now = weather.local_time
    sunrise = weather.sunrise
    sunset = weather.sunset

    # Shooting-star window: 02:00-04:00 local time.
    is_shooting_window = 2 <= now.hour < 4

    # Star density: only at night; suppressed by cloud cover.
    base_density = 60
    cloud_factor = max(0.0, 1.0 - (weather.cloud_coverage / 100.0))

    # Default phase: time-of-day only.
    phase = _phase_from_time_only(now)
    sun_y = -1.0
    sun_visible = False

    if sunrise is not None and sunset is not None:
        if now < sunrise:
            phase = LightingPhase.NIGHT
        elif now < sunrise + _SUNRISE_WINDOW:
            phase = LightingPhase.SUNRISE
            sun_y = 4.0
            sun_visible = True
        elif now < sunset - _SUNSET_WINDOW:
            # Daytime; pick morning vs day vs evening by hour.
            if now.hour < 10:
                phase = LightingPhase.MORNING
            elif now.hour >= 16:
                phase = LightingPhase.EVENING
            else:
                phase = LightingPhase.DAY
            sun_y = _interpolate_sun_y(now, sunrise, sunset)
            sun_visible = True
        elif now < sunset:
            phase = LightingPhase.SUNSET
            sun_y = 18.0
            sun_visible = True
        elif now < sunset + _TWILIGHT_WINDOW:
            # Civil twilight: sun is just below the horizon; sky still
            # has color and stars are dim but visible.
            phase = LightingPhase.TWILIGHT
            sun_y = -1.0
            sun_visible = False
        else:
            phase = LightingPhase.NIGHT
            sun_y = -1.0
            sun_visible = False

    # Star visibility: night phases only; density scales with cloud.
    if phase in (
        LightingPhase.NIGHT,
        LightingPhase.TWILIGHT,
        LightingPhase.SUNSET,
        LightingPhase.SUNRISE,
    ):
        star_density = int(base_density * cloud_factor)
        if phase == LightingPhase.SUNRISE:
            # Dawn: stars fade out.
            star_density = int(star_density * 0.3)
        elif phase == LightingPhase.TWILIGHT:
            # Dusk: stars are appearing, dim.
            star_density = int(star_density * 0.3)
    else:
        star_density = 0

    return LightingState(
        phase=phase,
        sun_y=sun_y,
        sun_visible=sun_visible,
        star_density=star_density,
        is_shooting_star_window=is_shooting_window,
    )


__all__ = ["LightingPhase", "LightingState", "compute_lighting"]