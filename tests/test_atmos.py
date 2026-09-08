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


def test_terminal_context_restores_screen_when_cbreak_init_fails(
    monkeypatch, capsys
) -> None:
    import atmos.engine.terminal as terminal_mod

    class FakeCbreak:
        def __init__(self) -> None:
            self.exit_called = False

        def __enter__(self):
            raise RuntimeError("cbreak unavailable")

        def __exit__(self, exc_type, exc, tb) -> None:
            self.exit_called = True

    cbreak = FakeCbreak()

    class FakeTerminal:
        width = 80
        height = 24

        def cbreak(self):
            return cbreak

    monkeypatch.setattr(terminal_mod.blessed, "Terminal", FakeTerminal)

    with terminal_mod.TerminalContext() as context:
        assert context.ok is False

    output = capsys.readouterr().out
    assert terminal_mod._ENTER_ALT in output
    assert terminal_mod._HIDE_CURSOR in output
    assert terminal_mod._SHOW_CURSOR in output
    assert terminal_mod._EXIT_ALT in output
    assert cbreak.exit_called is True

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


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("q", "quit"),
        ("r", "refresh"),
        ("f", "forecast"),
        ("l", "location"),
        ("h", "help"),
        ("m", "minimal"),
    ],
)
def test_documented_letter_shortcuts_map_to_actions(key: str, expected: str) -> None:
    from atmos.engine.input import _parse, action_for_char

    event = _parse(key)
    assert event.action == "char"
    assert event.char == key
    assert action_for_char(key) == expected


def test_documented_non_letter_shortcuts_map_to_actions() -> None:
    from atmos.engine.input import _parse

    assert _parse(" ").action == "space"
    assert _parse("+").action == "plus"
    assert _parse("=").action == "plus"
    assert _parse("-").action == "minus"
    assert _parse("_").action == "minus"


def test_cli_demo_accepts_all_scene_conditions() -> None:
    from atmos.cli import DEMO_CONDITIONS, parse

    for condition in DEMO_CONDITIONS:
        assert parse(["--demo", condition]).demo_condition == condition


def test_global_shortcuts_change_loop_state() -> None:
    from atmos.app import _handle_global
    from atmos.engine.input import KeyEvent, _parse

    class FakeLoop:
        target_fps = 30
        stopped = False

        def stop(self) -> None:
            self.stopped = True

    class FakeRefresher:
        refresh_requested = False

        def request_refresh(self) -> None:
            self.refresh_requested = True

    loop = FakeLoop()
    refresher = FakeRefresher()
    _handle_global(KeyEvent("plus"), loop=loop, refresher=refresher)
    assert loop.target_fps == 35
    _handle_global(KeyEvent("minus"), loop=loop, refresher=refresher)
    assert loop.target_fps == 30
    _handle_global(_parse("r"), loop=loop, refresher=refresher)
    assert refresher.refresh_requested is True
    _handle_global(_parse("q"), loop=loop, refresher=refresher)
    assert loop.stopped is True

def test_location_mode_preserves_action_letters_as_text() -> None:
    from atmos.app import _handle_global
    from atmos.engine.input import _parse

    class FakeLoop:
        target_fps = 30
        stopped = False

        def stop(self) -> None:
            self.stopped = True

    class FakeRefresher:
        refresh_requested = False

        def request_refresh(self) -> None:
            self.refresh_requested = True

    loop = FakeLoop()
    refresher = FakeRefresher()

    _handle_global(
        _parse("q"),
        loop=loop,
        refresher=refresher,
        allow_action_chars=False,
    )

    _handle_global(
        _parse("r"),
        loop=loop,
        refresher=refresher,
        allow_action_chars=False,
    )

    assert loop.stopped is False
    assert refresher.refresh_requested is False


def test_demo_disables_network_shortcuts() -> None:
    from atmos.app import _activate_location_search, _handle_global
    from atmos.engine.input import KeyEvent
    from atmos.ui.location_search import LocationSearchState

    class FakeLoop:
        target_fps = 30

        def stop(self) -> None:
            pass

    class FakeRefresher:
        refresh_requested = False

        def request_refresh(self) -> None:
            self.refresh_requested = True

    refresher = FakeRefresher()
    _handle_global(
        KeyEvent("refresh"),
        loop=FakeLoop(),
        refresher=refresher,
        allow_network=False,
    )
    assert refresher.refresh_requested is False

    search = LocationSearchState()
    assert _activate_location_search(search, demo=True) is False
    assert search.active is False


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


def test_moon_draw_uses_phase_glyph() -> None:
    from atmos.engine.frame_buffer import FrameBuffer
    from atmos.engine.lighting import LightingPhase, LightingState
    from atmos.scenes._atmosphere import draw_moon

    buf = FrameBuffer.empty(20, 10)
    draw_moon(
        buf,
        LightingState(phase=LightingPhase.NIGHT, sun_visible=False),
        center_x=10,
    )
    assert buf.get(2, 10) == ("◐", "bright_yellow")


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


def test_snow_particles_fall_visibly() -> None:
    from atmos.scenes.snow import SnowScene
    from atmos.weather.models import WeatherState

    state = WeatherState(
        location_name="London",
        country_code="GB",
        temperature=1.0,
        feels_like=-2.0,
        humidity=90,
        wind_speed=8.0,
        wind_direction=180.0,
        precipitation=0.0,
        precipitation_probability=90.0,
        cloud_coverage=95.0,
        condition="snow",
        local_time=datetime(2026, 1, 7, 10, 0, 0),
    )
    scene = SnowScene()
    scene.enter(state)
    scene.update(0.0, state, 80, 24)
    before = scene.system.particles[0].y
    scene.update(0.2, state, 80, 24)
    assert any(p.y > before for p in scene.system.particles)
    assert all(1.5 <= p.vy <= 4.5 for p in scene.system.particles)


# --- smoke: the app entry point imports without NameError ---


def test_app_entry_point_imports_required_names() -> None:
    import atmos.app as app_mod

    assert hasattr(app_mod, "LayoutManager")
    assert hasattr(app_mod, "InputManager")
    assert hasattr(app_mod, "KeyEvent")
    assert hasattr(app_mod, "is_action_char")


# --- weather companion (new ambient detail) ---


def test_weather_companion_uses_weather_specific_sprite() -> None:
    from atmos.engine.companion import WeatherCompanion

    companion = WeatherCompanion(x=10)
    companion.update(0.1, 80, "heavy_rain")
    assert companion.kind == "rain"

    old_x = companion.x
    companion.update(1.0, 80, "heavy_rain", paused=True)
    assert companion.x == old_x


@pytest.mark.parametrize(
    ("condition", "clothing_mark"),
    [("rain", "#"), ("snow", "#"), ("wind", "="), ("fog", "-")],
)
def test_weather_companion_clothing_matches_weather(
    condition: str, clothing_mark: str
) -> None:
    from atmos.engine.companion import WeatherCompanion
    from atmos.engine.frame_buffer import FrameBuffer

    companion = WeatherCompanion(x=10)
    companion.update(0.1, 80, condition)
    buf = FrameBuffer.empty(80, 24)
    companion.draw(buf, floor_y=18)
    rendered = "".join(char for row in buf.cells for char, _ in row)
    assert clothing_mark in rendered


def test_weather_companion_draws_into_frame_buffer() -> None:
    from atmos.engine.companion import WeatherCompanion
    from atmos.engine.frame_buffer import FrameBuffer

    companion = WeatherCompanion(x=10)
    companion.update(0.1, 80, "snow")
    buf = FrameBuffer.empty(80, 24)
    companion.draw(buf, floor_y=18)
    assert any(
        char != " " and style == "bright_white"
        for row in buf.cells
        for char, style in row
    )


def test_partly_cloudy_draws_sprite_cells_not_entire_rows() -> None:
    from atmos.engine.frame_buffer import FrameBuffer
    from atmos.scenes.partly_cloudy import PartlyCloudyScene
    from atmos.weather.models import WeatherState

    state = WeatherState(
        location_name="Seattle",
        country_code="US",
        temperature=17.0,
        feels_like=17.0,
        humidity=66,
        wind_speed=7.0,
        wind_direction=180.0,
        precipitation=0.0,
        precipitation_probability=10.0,
        cloud_coverage=45.0,
        condition="partly_cloudy",
        local_time=datetime(2026, 9, 7, 21, 0, 0),
    )
    scene = PartlyCloudyScene()
    scene.enter(state)
    scene.update(0.0, state, 80, 24)
    buf = FrameBuffer.empty(80, 24)
    scene.draw(buf)
    assert all(len(char) == 1 for row in buf.cells for char, _ in row)


def test_fog_draws_layer_characters_into_frame_buffer() -> None:
    from atmos.engine.frame_buffer import FrameBuffer
    from atmos.scenes.fog import FogScene
    from atmos.weather.models import WeatherState

    state = WeatherState(
        location_name="Seattle",
        country_code="US",
        temperature=12.0,
        feels_like=12.0,
        humidity=98,
        wind_speed=3.0,
        wind_direction=180.0,
        precipitation=0.0,
        precipitation_probability=0.0,
        cloud_coverage=80.0,
        condition="fog",
        local_time=datetime(2026, 9, 7, 21, 0, 0),
    )
    scene = FogScene()
    scene.enter(state)
    scene.update(0.0, state, 80, 24)
    buf = FrameBuffer.empty(80, 24)
    scene.draw(buf)

    assert any(
        char != " " and style == "240"
        for row in buf.cells
        for char, style in row
    )


def test_fog_layers_move_at_different_speeds() -> None:
    from atmos.scenes.fog import FogScene
    from atmos.weather.models import WeatherState

    state = WeatherState(
        location_name="Seattle",
        country_code="US",
        temperature=12.0,
        feels_like=12.0,
        humidity=98,
        wind_speed=15.0,
        wind_direction=90.0,
        precipitation=0.0,
        precipitation_probability=0.0,
        cloud_coverage=80.0,
        condition="fog",
        local_time=datetime(2026, 9, 7, 21, 0, 0),
    )
    scene = FogScene()
    scene.enter(state)
    scene.update(0.0, state, 80, 24)
    assert len(scene.layers) >= 3

    # Reset positions to a known baseline to avoid wrapping during update
    for layer in scene.layers:
        layer["x"] = 0.0

    scene.update(1.0, state, 80, 24)

    # Lower-index layers (distant, top) must drift less than higher-index layers (foreground, bottom)
    for i in range(len(scene.layers) - 1):
        assert scene.layers[i]["layer"].speed < scene.layers[i + 1]["layer"].speed
        assert scene.layers[i]["x"] < scene.layers[i + 1]["x"]


def test_environment_state_initialized_from_weather() -> None:
    from atmos.engine.environment import EnvironmentState
    from atmos.weather.models import WeatherState

    weather = WeatherState(
        location_name="Seattle",
        country_code="US",
        temperature=12.0,
        feels_like=12.0,
        humidity=98,
        wind_speed=15.0,
        wind_direction=180.0,
        precipitation=5.0,
        precipitation_probability=80.0,
        cloud_coverage=75.0,
        condition="rain",
        local_time=datetime(2026, 9, 7, 21, 0, 0),
    )
    env = EnvironmentState.from_weather(weather)
    assert 0.0 <= env.cloud_intensity <= 1.0
    assert 0.0 <= env.precipitation_intensity <= 1.0
    assert 0.0 <= env.wind_intensity <= 1.0
    assert 0.0 <= env.fog_intensity <= 1.0
    assert env.cloud_intensity == pytest.approx(0.75)
    assert env.precipitation_intensity == pytest.approx(0.5)
    assert env.wind_intensity == pytest.approx(0.5)
    assert env.fog_intensity == 0.0

    fog_weather = weather.model_copy(update={"condition": "fog", "cloud_coverage": 90.0})
    fog_env = EnvironmentState.from_weather(fog_weather)
    assert fog_env.fog_intensity == pytest.approx(0.9)

    # High-value extreme weather: normalization must clamp all values to <= 1.0
    extreme_weather = WeatherState(
        location_name="Typhoon Zone",
        country_code="PH",
        temperature=28.0,
        feels_like=35.0,
        humidity=100,
        wind_speed=150.0,
        wind_direction=270.0,
        precipitation=75.0,
        precipitation_probability=100.0,
        cloud_coverage=120.0,
        condition="fog",
        local_time=datetime(2026, 9, 7, 12, 0, 0),
    )
    extreme_env = EnvironmentState.from_weather(extreme_weather)
    assert extreme_env.cloud_intensity == 1.0
    assert extreme_env.precipitation_intensity == 1.0
    assert extreme_env.wind_intensity == 1.0
    assert extreme_env.fog_intensity == 1.0


def test_cloud_bands_move_at_different_speeds() -> None:
    from atmos.scenes.cloudy import CloudyScene
    from atmos.weather.models import WeatherState

    state = WeatherState(
        location_name="Bangkok",
        country_code="TH",
        temperature=29.0,
        feels_like=31.0,
        humidity=68,
        wind_speed=12.0,
        wind_direction=90.0,
        precipitation=0.0,
        precipitation_probability=10.0,
        cloud_coverage=80.0,
        condition="cloudy",
        local_time=datetime(2026, 9, 7, 12, 0, 0),
    )
    scene = CloudyScene()
    scene.enter(state)
    scene.update(0.0, state, 80, 24)
    assert len(scene.bands) >= 2

    for b in scene.bands:
        b["x"] = 0.0

    scene.update(1.0, state, 80, 24)
    assert scene.bands[0]["layer"].speed < scene.bands[-1]["layer"].speed
    assert scene.bands[0]["x"] < scene.bands[-1]["x"]


def test_partly_cloudy_parallax_layers() -> None:
    from atmos.scenes.partly_cloudy import PartlyCloudyScene
    from atmos.weather.models import WeatherState

    # Coverage >= 55 creates 2 bands (distant and foreground)
    state = WeatherState(
        location_name="Bangkok",
        country_code="TH",
        temperature=31.0,
        feels_like=33.0,
        humidity=65,
        wind_speed=18.0,
        wind_direction=90.0,
        precipitation=0.0,
        precipitation_probability=10.0,
        cloud_coverage=70.0,
        condition="partly_cloudy",
        local_time=datetime(2026, 9, 7, 12, 0, 0),
    )
    scene = PartlyCloudyScene()
    scene.enter(state)
    scene.update(0.0, state, 80, 24)

    assert len(scene.bands) == 2
    distant_band, foreground_band = scene.bands[0], scene.bands[1]

    # Distant (top) and foreground (lower) bands must use different layer speeds and depths
    assert distant_band["layer"].speed < foreground_band["layer"].speed
    assert distant_band["layer"].depth < foreground_band["layer"].depth
    assert distant_band["layer"].speed == 0.25
    assert distant_band["layer"].depth == 0.25
    assert foreground_band["layer"].speed == 0.5
    assert foreground_band["layer"].depth == 0.5

    # Reset positions to test movement
    distant_band["x"] = 0.0
    foreground_band["x"] = 0.0

    scene.update(1.0, state, 80, 24)
    assert distant_band["x"] < foreground_band["x"]


def test_rain_ground_ripples_spawn_and_render() -> None:
    from atmos.engine.frame_buffer import FrameBuffer
    from atmos.engine.particles import Particle
    from atmos.scenes.rain import RainScene
    from atmos.weather.models import WeatherState

    state = WeatherState(
        location_name="Portland",
        country_code="US",
        temperature=15.0,
        feels_like=15.0,
        humidity=85,
        wind_speed=10.0,
        wind_direction=180.0,
        precipitation=4.0,
        precipitation_probability=90.0,
        cloud_coverage=80.0,
        condition="rain",
        local_time=datetime(2026, 9, 8, 14, 0, 0),
    )
    scene = RainScene()
    scene.enter(state)
    scene.update(0.0, state, 80, 24)

    # Place particles hitting the ground
    for i in range(10):
        scene.system.spawn(
            Particle(x=float(10 + i * 5), y=23.0, vx=0.0, vy=10.0, age=0.0, lifetime=2.0, char="│")
        )
    scene.update(0.05, state, 80, 24)
    assert len(scene.ripples) > 0

    buf = FrameBuffer.empty(80, 24)
    scene.draw(buf)
    ground_chars = {buf.cells[23][x][0] for x in range(80)}
    assert any(ch in ("·", "(", ")", "~") for ch in ground_chars)


def test_heavy_rain_splashes_and_ripples() -> None:
    from atmos.engine.frame_buffer import FrameBuffer
    from atmos.engine.particles import Particle
    from atmos.scenes.heavy_rain import HeavyRainScene
    from atmos.weather.models import WeatherState

    state = WeatherState(
        location_name="Miami",
        country_code="US",
        temperature=27.0,
        feels_like=30.0,
        humidity=92,
        wind_speed=15.0,
        wind_direction=180.0,
        precipitation=8.0,
        precipitation_probability=95.0,
        cloud_coverage=95.0,
        condition="heavy_rain",
        local_time=datetime(2026, 9, 8, 16, 0, 0),
    )
    scene = HeavyRainScene()
    scene.enter(state)
    scene.update(0.0, state, 80, 24)

    # Spawn particles at the floor row
    for i in range(15):
        scene.rain.spawn(
            Particle(x=float(5 + i * 4), y=23.0, vx=0.0, vy=30.0, age=0.0, lifetime=1.0, char="│")
        )
    scene.update(0.02, state, 80, 24)
    assert len(scene.splash.particles) > 0 or len(scene.ripples) > 0
    assert len(scene.splash.particles) <= 45

    buf = FrameBuffer.empty(80, 24)
    scene.draw(buf)
    assert len(buf.cells) == 24


def test_snow_ground_accumulation() -> None:
    from atmos.engine.frame_buffer import FrameBuffer
    from atmos.engine.particles import Particle
    from atmos.scenes.snow import SnowScene
    from atmos.weather.models import WeatherState

    state = WeatherState(
        location_name="Sapporo",
        country_code="JP",
        temperature=-3.0,
        feels_like=-7.0,
        humidity=88,
        wind_speed=5.0,
        wind_direction=180.0,
        precipitation=2.0,
        precipitation_probability=85.0,
        cloud_coverage=90.0,
        condition="snow",
        local_time=datetime(2026, 1, 15, 12, 0, 0),
    )
    scene = SnowScene()
    scene.enter(state)
    scene.update(0.0, state, 80, 24)

    # Drop a snowflake onto column 30
    scene.system.spawn(
        Particle(x=30.0, y=23.0, vx=0.0, vy=2.0, age=0.0, lifetime=5.0, char="*")
    )
    scene.update(0.05, state, 80, 24)
    assert scene.accumulation[30] > 0.0

    buf = FrameBuffer.empty(80, 24)
    scene.draw(buf)
    assert buf.cells[23][30][0] in ("·", ".", "_")


def test_wind_ambient_debris_spawns_and_moves() -> None:
    from atmos.scenes.wind import WindScene, _DEBRIS_CHARS
    from atmos.weather.models import WeatherState

    state = WeatherState(
        location_name="Chicago",
        country_code="US",
        temperature=18.0,
        feels_like=18.0,
        humidity=50,
        wind_speed=35.0,
        wind_direction=90.0,
        precipitation=0.0,
        precipitation_probability=0.0,
        cloud_coverage=10.0,
        condition="wind",
        local_time=datetime(2026, 9, 8, 14, 0, 0),
    )
    scene = WindScene()
    scene.enter(state)
    scene.update(0.1, state, 80, 24)

    assert len(scene.debris) > 0
    assert all(d["char"] in _DEBRIS_CHARS for d in scene.debris)

    x0 = scene.debris[0]["x"]
    scene.update(0.2, state, 80, 24)
    assert scene.debris[0]["x"] != x0
