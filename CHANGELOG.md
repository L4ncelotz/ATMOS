# Changelog

ATMOS — by Estellez

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Weather-aware ASCII companion that walks through the scene and changes
  clothing for rain, snow, wind, fog, and clear weather.
- `--demo CONDITION` CLI mode for deterministic, offline previews of all
  normalized weather scenes.
- Colored star fields with gentle twinkling and a visible crescent moon.
- Shortcut, companion, scene-rendering, and demo-mode regression coverage;
  the suite now contains 32 tests.

### Changed
- Cloud formations now render as layered multi-row sprites with atmospheric
  depth instead of single-line bands.
- Snowfall remains slow and ambient while still advancing between frames.
- Terminal input uses cbreak mode so typed keys are consumed by ATMOS rather
  than echoed into the animation.

### Fixed
- Moon rendering no longer raises `NameError` during clear night scenes.
- Partly-cloudy scenes correctly draw multi-row cloud sprites.
- Location search no longer raises `UnboundLocalError` inside the animation
  loop.

## [0.2.0] — 2026-09-04

### Added
- File-based logging via `atmos.utils.logging_setup` writing to
  `platformdirs.user_log_dir("atmos") / "atmos.log"`. Stderr sink
  gated on `ATMOS_DEBUG=1`.
- `LightingPhase.TWILIGHT` between `SUNSET` and `NIGHT` so the
  star field appears gradually after sunset.
- `GeocodeWorker` daemon thread for non-blocking geocoding.
- `WeatherRefresher.request_location(loc)` for non-blocking city
  changes.
- `Config.last_location` (full resolved `ResolvedLocation`) so
  the cache is reachable without the geocoder.
- `dim` keyword on every `Scene.draw`; transitions now blend by
  drawing both scenes with weights from `blend_intensity`.
- `local_now(location)` derives a per-frame current local time
  via `zoneinfo.ZoneInfo` so the rendered clock advances without
  waiting for the weather refresh.
- Run-length coalescing in `FrameBuffer.render_diff`; one
  cursor-position escape per (row, style-change) instead of per
  cell.
- Heavy-rain scene capped at 300 particles and 4 spawns per tick
  to keep terminal I/O within practical bounds.
- `dist/atmos.exe` standalone binary build via `python build.py`.
- GitHub Actions release workflow on tag push.
- 14-test core regression suite under `tests/`.

### Changed
- `InputManager._parse` no longer maps `q r f l h m p` to action
  keys; the dispatch layer decides based on the current `Mode`.
- `engine/input.py` exposes `ACTION_CHARS`, `is_action_char`, and
  `action_for_char` as the single source of truth.
- `WeatherRefresher._fetch_once` persists the resolved `Location`
  to the user config on every successful fetch.
- `_resolve_initial` returns `state=None` on total failure (live
  + cache miss) and never fabricates a `WeatherState`. The main
  loop renders a retry prompt instead.
- The first launch is now Python 3.12+ in `pyproject.toml`
  (was 3.11).
- The `--forecast` CLI flag is removed; forecast is reachable in
  the running app via `F`.
- `Engine`/renderer no longer runs any synchronous network call.
- The frame buffer no longer emits one CUP per changed cell.
- The package version is `0.2.0`; this is a pre-1.0 release
  inviting early feedback.

### Fixed
- `app.py` no longer crashes on launch with `NameError: name
  'LayoutManager' is not defined` (the two engine imports were
  dropped in a prior edit and are now restored).
- Location-typing in `Mode.LOCATION` no longer drops the letters
  `m l r f h p q`; the previous greedy mapping in
  `InputManager._parse` was removed.
- `--minimal` and the persisted `config.toml` are now honored on
  startup; `Config()` is replaced with `load()` in `cli.parse`.
- Offline startup no longer fabricates a Bangkok-shaped mock
  `WeatherState`; if the cache and the network both fail, the
  app shows the retry prompt and never invents data.
- The clear-night star field is no longer missing for ~3 hours
  after sunset; the post-sunset branch now walks through
  `TWILIGHT` → `NIGHT` instead of jumping to `EVENING`.
- The rendered clock is no longer stuck for up to 15 minutes
  between weather refreshes.
- Scene changes no longer hard-cut; the outgoing scene fades
  while the incoming scene ramps up.
- Terminal I/O during heavy rain is no longer ~475 KB/s; the
  coalesced frame buffer plus particle cap drop it well below
  the previous upper bound.
- A latent Unicode `cp874` crash on Windows when the host's
  code page cannot encode box-drawing characters is fixed; the
  app now reconfigures `stdout`/`stderr` to UTF-8 at startup.

## [0.1.0] — 2026-09-03

### Added
- Initial V1–V5 implementation: terminal lifecycle, frame
  buffer, animation loop, particle engine, layout, all 9 scenes
  (clear, partly cloudy, cloudy, rain, heavy rain, storm, snow,
  fog, wind), Open-Meteo provider, geocoding, cache, refresher,
  full keyboard set, forecast, location search, minimal mode,
  pause, day/night, transitions, and shooting stars.

[Unreleased]: https://github.com/L4ncelotz/ATMOS/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/L4ncelotz/ATMOS/releases/tag/v0.2.0
[0.1.0]: https://github.com/L4ncelotz/ATMOS/releases/tag/v0.1.0
