"""Location search overlay: prompt + result list.

Activated by L. User types a city name; results refresh after a short
debounce. Arrow keys move the highlight; Enter selects; Esc cancels.

State machine lives in LocationSearchState (caller-owned); this module
just draws.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from atmos.engine.frame_buffer import FrameBuffer
from atmos.engine.layout import Layout
from atmos.weather.location import Location


@dataclass
class LocationSearchState:
    query: str = ""
    results: list[Location] = field(default_factory=list)
    highlight: int = 0
    last_input_at: float = 0.0
    active: bool = False
    error: str | None = None  # last search error (if any)
    debounce_s: float = 0.30
    request_id: int = 0          # last submitted geocode request id
    pending: bool = False        # True while a request is in flight


def draw_location_search(buf: FrameBuffer, lay: Layout, st: LocationSearchState) -> None:
    if lay.height < 8 or lay.width < 30:
        return
    # Header.
    buf.write_line(2, 2, "location", "white")

    # Prompt row.
    prompt_y = 4
    buf.write_line(prompt_y, 2, ">", "bright_white")
    buf.write_line(prompt_y, 4, st.query + "_", "white")

    # Result list starting two rows below.
    list_y = prompt_y + 2
    if st.error:
        buf.write_line(list_y, 4, f"error: {st.error}", "bright_red")
        list_y += 1
    elif st.pending:
        buf.write_line(list_y, 4, "searching...", "240")
        list_y += 1
    elif not st.results and st.query:
        buf.write_line(list_y, 4, "searching...", "240")
        list_y += 1
    elif not st.query:
        buf.write_line(list_y, 4, "type a city, then Enter", "240")
        list_y += 1
    max_rows = max(1, lay.height - list_y - 2)
    visible = st.results[:max_rows]
    for i, loc in enumerate(visible):
        style = "bright_white" if i == st.highlight else "white"
        prefix = "> " if i == st.highlight else "  "
        buf.write_line(list_y + i, 4, f"{prefix}{loc.label}", style)

    # Footer.
    foot_y = lay.height - 2
    if foot_y > list_y + len(visible):
        buf.write_line(
            foot_y,
            2,
            "Enter select  /  Esc cancel  /  Up Down navigate",
            "240",
        )


def max_results() -> int:
    return 5