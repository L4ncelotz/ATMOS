"""Core regression tests for ATMOS.

These tests pin the bugs the project has already fixed so a future
refactor cannot silently regress them. They are not exhaustive —
they cover the user-reported issues and the load-bearing behavior
of the rendering pipeline.

Run with:
    pip install -e .[dev]
    pytest
"""

from __future__ import annotations

from datetime import datetime

import pytest

# --- input parsing (regression: location-typing ate letter keys) ---


def test_letter_keys_parsed_as_char() -> None:
    from atmos.engine.input import _parse

    for ch in "qrfhlmptokyo":
        ev = _parse(ch)
        assert ev.action == "char", f"letter {ch!r} was mapped to action={ev.action!r}"
        assert ev.char == ch


def test_special_keys_keep_named_actions() -> None:
    from atmos.engine.input import _parse

    assert _parse(" ").action == "space"
    assert _parse("\x1b").action == "esc"
    assert _parse("\r").action == "enter"
    assert _parse("\x7f").action == "backspace"
    assert _parse("+").action == "plus"
    assert _parse("=").action == "plus"
    assert _parse("-").action == "minus"
    assert _parse("_").action == "minus"
    assert _parse("KEY_UP").action == "up"
    assert _parse("\x1b[A").action == "up"


def test_action_letters_have_single_source_of_truth() -> None:
    from atmos.engine.input import ACTION_CHARS, is_action_char, action_for_char

    assert ACTION_CHARS == frozenset("qrfhlm")
    for ch in "qrfhlm":
        assert is_action_char(ch)
        assert action_for_char(ch) in {"quit", "refresh", "forecast", "location", "help", "minimal"}
    for ch in "pstokyo":
        assert not is_action_char(ch)
        assert action_for_char(ch) == "unknown"


# --- night-phase bug (regression: 0 stars between sunset and midnight) ---


def _state(now: datetime, sunset: datetime, sunrise: datetime | None = None):
    from atmos.weather.models import WeatherState

    return WeatherState(
        location_name="X",
        country_code=None,
        temperature=20.0,
        feels_like=20.0,
        humidity=50,
        wind_speed=5.0,
        wind_direction=180.0,
        precipitation=0.0,
        precipitation_probability=None,
        cloud_coverage=10.0,
        condition="clear",
        local_time=now,
        sunrise=sunrise or datetime(now.year, now.month, now.day, 6, 0, 0),
        sunset=sunset,
    )


def test_post_sunset_phase_progression() -> None:
    from atmos.engine.lighting import LightingPhase, compute_lighting

    sunset = datetime(2026, 9, 3, 18, 30, 0)
    # 19:00 = 30 min after sunset -> TWILIGHT
    ls = compute_lighting(_state(datetime(2026, 9, 3, 19, 0, 0), sunset))
    assert ls.phase == LightingPhase.TWILIGHT
    assert ls.star_density > 0
    # 21:00 = 2.5 hours after sunset -> NIGHT
    ls = compute_lighting(_state(datetime(2026, 9, 3, 21, 0, 0), sunset))
    assert ls.phase == LightingPhase.NIGHT
    assert ls.star_density > 0
    # 23:30 -> NIGHT
    ls = compute_lighting(_state(datetime(2026, 9, 3, 23, 30, 0), sunset))
    assert ls.phase == LightingPhase.NIGHT
    # 12:00 -> DAY
    ls = compute_lighting(_state(datetime(2026, 9, 3, 12, 0, 0), sunset))
    assert ls.phase == LightingPhase.DAY
    assert ls.star_density == 0
    # 18:00 (before sunset) -> SUNSET
    ls = compute_lighting(_state(datetime(2026, 9, 3, 18, 0, 0), sunset))
    assert ls.phase == LightingPhase.SUNSET


# --- config round-trip (regression: cfg never loaded; --minimal ignored) ---


def test_config_loads_and_round_trips(tmp_path, monkeypatch) -> None:
    from atmos import config as cfg_mod

    # Redirect the config file to a temp location.
    test_path = tmp_path / "config.toml"
    monkeypatch.setattr(cfg_mod, "CONFIG_FILE", test_path)

    # Save a known configuration.
    saved = cfg_mod.Config(
        location="Tokyo",
        fps=15,
        minimal=True,
        sound=False,
        units="metric",
        refresh_minutes=10,
    )
    cfg_mod.save(saved)

    loaded = cfg_mod.load()
    assert loaded.location == "Tokyo"
    assert loaded.fps == 15
    assert loaded.minimal is True
    assert loaded.refresh_minutes == 10
    # last_location absent -> None (backward compat)
    assert loaded.last_location is None


def test_resolved_location_round_trip(tmp_path, monkeypatch) -> None:
    from atmos import config as cfg_mod
    from atmos.weather.location import Location

    test_path = tmp_path / "config.toml"
    monkeypatch.setattr(cfg_mod, "CONFIG_FILE", test_path)

    loc = Location(
        name="Tokyo",
        country="Japan",
        latitude=35.6762,
        longitude=139.6503,
        timezone="Asia/Tokyo",
    )
    cfg_mod.update_resolved_location(loc)
    loaded = cfg_mod.load()
    assert loaded.location == "Tokyo"
    assert loaded.last_location is not None
    assert loaded.last_location.country == "Japan"
    assert abs(loaded.last_location.latitude - 35.6762) < 1e-6


# --- no-mock guarantee (regression: app displayed fake Bangkok weather) ---


def test_resolve_initial_returns_none_on_total_failure(monkeypatch) -> None:
    import atmos.app as app_mod
    import atmos.weather.geocode as geocode_mod
    from atmos.config import Config
    from atmos.weather.client import WeatherError

    def boom(_):
        raise ValueError("offline")

    monkeypatch.setattr(geocode_mod, "first_location", boom)

    class FakeProvider:
        def current(self, loc):
            raise WeatherError("no network")

        def forecast(self, loc, days=5):
            raise WeatherError("no network")

        def close(self):
            pass

    state, forecast, location, reason = app_mod._resolve_initial(
        Config(), location_override="NowhereVille", provider=FakeProvider()
    )
    assert state is None
    assert location is None
    # Reason must reflect the geocoder failure path, not be a success.
    assert "location" in (reason or "").lower() or "no" in (reason or "").lower()


# --- continuous local time (regression: clock stuck for ~15 min) ---


def test_local_now_returns_naive_datetime() -> None:
    from atmos.utils.time import local_now
    from atmos.weather.location import Location

    loc = Location(
        name="Tokyo",
        country="Japan",
        latitude=35.6762,
        longitude=139.6503,
        timezone="Asia/Tokyo",
    )
    t = local_now(loc)
    assert t.tzinfo is None
    assert isinstance(t, datetime)


def test_local_now_advances_between_samples() -> None:
    import time as _time
    from atmos.utils.time import local_now
    from atmos.weather.location import Location

    loc = Location(
        name="Tokyo",
        country="Japan",
        latitude=35.6762,
        longitude=139.6503,
        timezone="Asia/Tokyo",
    )
    t1 = local_now(loc)
    _time.sleep(0.05)
    t2 = local_now(loc)
    assert t2 > t1


# --- async geocode (regression: UI thread blocked ~8 s) ---


def test_geocode_worker_submits_non_blocking() -> None:
    import time as _time
    from atmos.weather.geocode_async import GeocodeWorker
    from atmos.weather.location import Location

    w = GeocodeWorker()
    t0 = _time.monotonic()
    req = w.submit("tokyo")
    elapsed = _time.monotonic() - t0
    assert elapsed < 0.05  # submit must not block
    # poll immediately returns None while the worker is still working.
    assert w.poll() is None
    # No real network call here; the worker is a daemon thread.
    _ = Location  # silence linter
    _ = req


# --- frame buffer coalesce (regression: ~1 CUP per changed cell) ---


def test_frame_buffer_coalesces_adjacent_cells() -> None:
    import io
    import re

    from atmos.engine.frame_buffer import FrameBuffer

    buf = FrameBuffer.empty(20, 3)
    # Six changed cells, two style groups (blue, red) on the same row.
    buf.set(1, 2, "X", "blue")
    buf.set(1, 3, "X", "blue")
    buf.set(1, 4, "X", "blue")
    buf.set(1, 5, "Y", "blue")
    buf.set(1, 6, "Y", "blue")
    buf.set(1, 8, "Z", "red")

    prev = FrameBuffer.empty(20, 3)
    out = io.StringIO()
    buf.render_diff(prev, out=out)
    output = out.getvalue()
    cups = re.findall(r"\033\[\d+;\d+H", output)
    # Two CUPs total — one per style group, not one per cell.
    assert len(cups) == 2, f"expected 2 CUPs, got {len(cups)}: {output!r}"


# --- scene transition blend ---


def test_blend_intensity_linear_fade() -> None:
    from atmos.engine.transition import blend_intensity

    assert blend_intensity(0.0) == (1.0, 0.0)
    assert blend_intensity(1.0) == (0.0, 1.0)
    assert blend_intensity(0.5) == (0.5, 0.5)


# --- heavy rain density cap ---


def test_heavy_rain_caps_at_300_particles() -> None:
    from atmos.scenes.heavy_rain import HeavyRainScene
    from atmos.weather.models import WeatherState

    state = WeatherState(
        location_name="X",
        country_code=None,
        temperature=20.0,
        feels_like=20.0,
        humidity=80,
        wind_speed=10.0,
        wind_direction=120.0,
        precipitation=10.0,
        precipitation_probability=95.0,
        cloud_coverage=98.0,
        condition="heavy_rain",
        local_time=datetime(2026, 9, 4, 18, 0, 0),
    )
    scene = HeavyRainScene()
    scene.enter(state)
    for _ in range(120):
        scene.update(0.016, state, 120, 30)
    assert len(scene.rain.particles) <= 300


# --- smoke: the app entry point imports without NameError ---


def test_app_entry_point_imports_required_names() -> None:
    import atmos.app as app_mod

    assert hasattr(app_mod, "LayoutManager")
    assert hasattr(app_mod, "InputManager")
    assert hasattr(app_mod, "KeyEvent")
    assert hasattr(app_mod, "is_action_char")
