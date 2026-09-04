"""Animation loop: target FPS, delta-time clamp, graceful stop."""

from __future__ import annotations

import time
from typing import Callable


class AnimationLoop:
    """Monotonic 30 FPS loop.

    dt is clamped to 0.05 max so a stalled frame (debug breakpoint, terminal
    drag) does not teleport particles across the screen.
    """

    def __init__(self, target_fps: int = 30) -> None:
        if target_fps < 1:
            target_fps = 1
        self.target_fps = target_fps
        self._running = False

    @property
    def frame_time(self) -> float:
        return 1.0 / self.target_fps

    def stop(self) -> None:
        self._running = False

    def run(self, step: Callable[[float], None]) -> None:
        self._running = True
        last = time.monotonic()
        while self._running:
            now = time.monotonic()
            dt = now - last
            last = now
            if dt > 0.05:
                dt = 0.05
            try:
                step(dt)
            except StopIteration:
                self._running = False
                break
            elapsed = time.monotonic() - now
            remaining = self.frame_time - elapsed
            if remaining > 0:
                time.sleep(remaining)