# ATMOS Agent Guide

## Project overview

ATMOS is a Python 3.12+ terminal weather animation. It queries Open-Meteo, converts provider responses into validated internal weather models, selects a weather scene, and renders an animated character grid with ANSI terminal output.

The main executable is exposed by the `atmos` console script:

```text
atmos.app:main
```

The application is interactive and network-backed. It must never fabricate weather data: when live requests fail, it uses the cache if available; otherwise it stays in a retry/no-data state.

## Repository layout

```text
src/atmos/
  app.py                 application entry point and mode/scene orchestration
  cli.py                 argparse CLI (`location`, `--minimal`, `--fps`, etc.)
  config.py              TOML settings and last-resolved-location persistence
  engine/                animation loop, input, layout, lighting, particles,
                         transitions, frame buffer, and terminal context
  scenes/                self-contained weather scene implementations
  ui/                    help, forecast, location search, and overlays
  weather/               provider client, Open-Meteo integration, geocoding,
                         mapping, models, refresh, and cache
  utils/                 logging and local-time helpers
tests/test_atmos.py      regression and smoke tests
build.py                 PyInstaller one-file build wrapper
```

## Architecture rules

The most important boundary is:

```text
provider payload -> weather/mapper.py -> WeatherState / ForecastDay
                  -> app + scenes + UI
```

Rendering code must not consume raw Open-Meteo/provider payloads or import provider implementation details. New weather providers should implement the provider protocol, normalize their payloads in `weather/mapper.py`, and be wired through `WeatherRefresher`.

Scenes are registered in `SCENE_MAP` in `src/atmos/app.py`. A scene normally subclasses `SceneBase` and implements `enter`, `update`, and `draw`; particle spawning and scene-specific physics belong in the scene. Shared terminal mechanics belong in `engine/`.

Keep terminal rendering efficient: draw into `FrameBuffer`, then render the diff against the previous frame. Avoid per-cell terminal writes and avoid introducing dashboard-like UI, emoji-heavy visuals, or unnecessary dependencies.

## Local setup

Use the existing virtual environment when available:

```bash
source .venv/bin/activate
pip install -e ".[dev]"
```

For standalone builds, install the build extra as well:

```bash
pip install -e ".[dev,build]"
```

## Verification commands

Run the regression suite after Python changes:

```bash
pytest
pytest -q
```

The current suite covers input parsing, lighting/night progression, config persistence, cache/no-data behavior, local time, async geocoding, frame-buffer coalescing, scene transitions, heavy-rain particle limits, and the app import surface.

For a manual smoke test:

```bash
atmos
atmos Bangkok
atmos Tokyo --minimal
atmos --fps 20
atmos --version
```

For packaging changes:

```bash
python build.py
./dist/atmos --version       # POSIX
```

On Windows the artifact is `dist/atmos.exe`.

## Runtime behavior and useful controls

The app uses platform-specific config, cache, and log directories through `platformdirs`. `ATMOS_DEBUG=1` mirrors INFO+ logs to stderr. Important interactive keys are `F` forecast, `L` location, `M` minimal mode, Space pause/resume, `R` refresh, `H` help, `Q` quit, and `+`/`-` target FPS.

Network failures should be tested with a fake provider or monkeypatch; tests must assert cached recovery or `state is None`, never invented weather. Geocoding in the location UI is asynchronous so the main rendering/input loop should not block on network work.

## Change conventions

- Python code belongs under `src/`; tests belong under `tests/`.
- Add or update a regression test for bug fixes and new behavior.
- Preserve Python 3.12 compatibility and cross-platform terminal behavior.
- Prefer small, focused changes and existing dependencies.
- Use lowercase, hyphenated branch names with prefixes such as `feat/`, `fix/`, `test/`, `docs/`, `refactor/`, `build/`, or `ci/`.
- Use Conventional Commits with an imperative subject under 72 characters, for example `fix: preserve cached location offline`.
- Open an Issue before substantial feature work; see `CONTRIBUTING.md` for the full contribution policy.

## Product boundaries

ATMOS is intentionally a calm ambient terminal experience. Keep it minimal, atmospheric, keyboard-first, and terminal-native. Do not turn it into a dashboard, weather website, analytics application, or AI assistant. Known limitations include no sound implementation, no macOS CI release artifact, and varying terminal compatibility.

