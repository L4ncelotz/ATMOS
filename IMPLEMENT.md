# IMPLEMENT

The full design and rationale for ATMOS — section by section —
lives in:

```text
IMPLEMENT(20260903-043600).md
```

That document captures the original product brief: what ATMOS is
supposed to feel like, the V1 → V5 development roadmap, the
Definition of Done, and the non-goals. It is the canonical spec
the code is built against.

## Where the design lives in the code

| Spec topic                        | Code                                                |
|-----------------------------------|-----------------------------------------------------|
| Terminal lifecycle                | `atmos/engine/terminal.py`                          |
| Frame buffer + diff               | `atmos/engine/frame_buffer.py`                      |
| Animation loop                    | `atmos/engine/animation.py`                         |
| Particle engine                   | `atmos/engine/particles.py`                         |
| Layout (responsive)               | `atmos/engine/layout.py`                            |
| Day/night lighting                | `atmos/engine/lighting.py`                          |
| Scene transitions                 | `atmos/engine/transition.py`                        |
| Keyboard input                    | `atmos/engine/input.py`                             |
| Scenes                            | `atmos/scenes/*.py`                                 |
| UI overlays                       | `atmos/ui/{overlay,help,forecast,location_search}.py` |
| Weather provider + mapping        | `atmos/weather/{open_meteo,client,mapper}.py`       |
| Geocoding                         | `atmos/weather/geocode.py`, `geocode_async.py`      |
| Weather cache                     | `atmos/weather/cache.py`                            |
| Background refresher              | `atmos/weather/refresher.py`                        |
| Config (TOML)                     | `atmos/config.py`                                   |
| Logging                           | `atmos/utils/logging_setup.py`                      |
| Local time derivation             | `atmos/utils/time.py`                               |

## Why a separate `IMPLEMENT(20260903-043600).md`?

The numbered filename is the immutable original spec. `IMPLEMENT.md`
is a pointer to it. Keeping the dated filename ensures git history
can track which "version" of the design document was in force at
any point — useful for `git blame` on a feature that changed in
response to a revised spec.

ATMOS — by Estellez
