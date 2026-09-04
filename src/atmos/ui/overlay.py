"""Top-level UI: header (location + time), info (temp + condition),
status row (humidity / wind / date). Kept minimal per IMPLEMENT.md §16.
"""

from __future__ import annotations

from atmos.engine.frame_buffer import FrameBuffer
from atmos.engine.layout import Layout
from atmos.weather.models import WeatherState


def _format_time(dt) -> str:
    return dt.strftime("%H:%M")


def _format_date(dt) -> str:
    return dt.strftime("%d %b").upper()


def draw_header(buf: FrameBuffer, lay: Layout, weather: WeatherState) -> None:
    name = weather.location_name.upper()
    time_s = _format_time(weather.local_time)
    left = name
    right = time_s
    # Top row, padded.
    pad = max(1, lay.width - len(left) - len(right))
    buf.write_line(0, 0, left, "white")
    buf.write_line(0, lay.width - len(right), right, "white")


def draw_info(buf: FrameBuffer, lay: Layout, weather: WeatherState) -> None:
    temp_s = f"{weather.temperature:.0f}°"
    cond_s = weather.condition
    buf.write_centered(lay.info_y, temp_s, "bright_white")
    buf.write_centered(lay.info_y + 1, cond_s, "white")


def draw_status(buf: FrameBuffer, lay: Layout, weather: WeatherState) -> None:
    left = f"humidity {weather.humidity}%"
    mid = f"wind {weather.wind_speed:.0f} km/h"
    right = _format_date(weather.local_time)
    # Spread across the bottom.
    if lay.width >= 60:
        buf.write_line(lay.status_y, 0, left, "white")
        mid_x = max(0, (lay.width - len(mid)) // 2)
        buf.write_line(lay.status_y, mid_x, mid, "white")
        buf.write_line(lay.status_y, lay.width - len(right), right, "white")
    else:
        buf.write_line(lay.status_y, 0, left, "white")
        buf.write_line(lay.status_y + 1, 0, mid, "white")