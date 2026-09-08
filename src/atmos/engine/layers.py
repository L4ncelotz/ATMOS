"""Parallax layer abstraction for multi-depth scene rendering."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Layer:
    """Parallax multiplier tracking speed and depth across visual elements."""

    speed: float = 1.0
    depth: float = 1.0


__all__ = ["Layer"]
