"""CLI parsing. Entry point used by pyproject.toml's [project.scripts].

Usage:
  atmos                       # use last/configured location
  atmos Bangkok               # one-off location query
  atmos --minimal             # start in minimal mode
  atmos --fps 20              # set target FPS
  atmos --version             # print version and exit

Unknown flags are an error. We deliberately keep it small per §25.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, replace

from atmos import __version__ as _atmos_version
from atmos.config import DEFAULTS, load

DEMO_CONDITIONS = (
    "clear",
    "partly_cloudy",
    "cloudy",
    "rain",
    "heavy_rain",
    "storm",
    "snow",
    "fog",
    "wind",
)


@dataclass
class CliArgs:
    location_override: str | None
    config: Config
    demo_condition: str | None


def parse(argv: list[str] | None = None) -> CliArgs:
    parser = argparse.ArgumentParser(
        prog="atmos",
        description="Ambient weather for your terminal.",
        add_help=True,
    )
    parser.add_argument(
        "--version", action="version", version=f"atmos {_atmos_version}"
    )
    parser.add_argument(
        "location",
        nargs="?",
        default=None,
        help="city name (overrides configured location)",
    )
    parser.add_argument(
        "--minimal",
        action="store_true",
        help="start in minimal mode (toggle with M while running)",
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=DEFAULTS.fps,
        help="target FPS (5-60)",
    )
    parser.add_argument(
        "--demo",
        choices=DEMO_CONDITIONS,
        metavar="CONDITION",
        help="run a local visual demo without contacting the weather API",
    )

    ns = parser.parse_args(argv)
    cfg = load()
    if ns.fps != DEFAULTS.fps:
        if 5 <= ns.fps <= 60:
            cfg = replace(cfg, fps=ns.fps)
        else:
            sys.stderr.write(f"atmos: ignoring --fps {ns.fps} (must be 5..60)\n")
    if ns.minimal:
        cfg = replace(cfg, minimal=True)
    return CliArgs(
        location_override=ns.location,
        config=cfg,
        demo_condition=ns.demo,
    )
