"""Forecast overlay: simple 5-day list.

Drawn over the scene when the user presses F. The forecast is information,
not animation — per IMPLEMENT.md §19, do not animate every day.
"""

from __future__ import annotations

from atmos.engine.frame_buffer import FrameBuffer
from atmos.engine.layout import Layout
from atmos.weather.forecast import ForecastDay


def _format_day_label(d: ForecastDay, today: bool) -> str:
    if today:
        return "TODAY"
    return d.date.strftime("%a").upper()


def draw_forecast(
    buf: FrameBuffer,
    lay: Layout,
    *,
    location_name: str,
    days: list[ForecastDay],
    offline: bool,
) -> None:
    if lay.height < 8 or lay.width < 40:
        return
    w = lay.width
    h = lay.height
    # Title row at top.
    title = f"{location_name.upper()} / NEXT {len(days)} DAYS"
    if offline:
        title += "  (offline)"
    buf.write_centered(2, title, "white")

    # List rows starting at row 4.
    start_y = 4
    if start_y + len(days) + 1 > h:
        max_rows = h - start_y - 1
        days = days[:max_rows]

    # Identify "today" — the first day in the list whose date matches the
    # current local_time. Falls back to the first row if no match.
    today_idx = 0

    for i, d in enumerate(days):
        y = start_y + i
        if y >= h:
            break
        label = _format_day_label(d, i == today_idx)
        tmin = f"{d.temp_min:.0f}°"
        tmax = f"{d.temp_max:.0f}°"
        cond = d.condition
        line = f"{label:<10}  {tmin:>4}  {tmax:>4}   {cond}"
        style = "bright_white" if i == today_idx else "white"
        buf.write_line(y, 4, line, style)

    # Footer hint.
    if h - 2 >= start_y + len(days) + 1:
        buf.write_line(h - 2, 4, "press F or Esc to return", "240")