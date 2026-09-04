"""Scene transition: blend parameters rather than hard-swapping scenes.

When the weather condition changes (e.g. clear → rain), we don't want the
screen to flip instantly. Instead, we keep the old scene running in
"fading out" mode while the new scene fades in. After the duration, the
old scene is dropped.

This module holds the per-frame state. Callers (app.main) advance it.

Practical model:
  - `from_scene`: scene being phased out
  - `to_scene`: scene being phased in
  - `progress`: 0..1 over `duration_s`
  - Both scenes receive update() calls every frame; render layer fades
    the from_scene by overriding its draw() to use dim style, and only
    fully commits to to_scene at progress >= 1.

For V5 we choose: the simpler "overlap for a moment then switch" approach.
At progress < 0.5 we draw only `from_scene`. At 0.5..1.0 we draw only
`to_scene` with style "240" until the end, then full style. This avoids
the visual confusion of two scenes overlapping while still giving a
smooth handoff (the to_scene particles start populating during the fade).

This is intentionally minimal; if V5 needs richer transitions, swap the
implementation here without touching scenes or app.
"""

from __future__ import annotations

from dataclasses import dataclass

from atmos.scenes.base import SceneBase


@dataclass
class SceneTransition:
    from_scene: SceneBase | None = None
    to_scene: SceneBase | None = None
    elapsed_s: float = 0.0
    duration_s: float = 2.5

    @property
    def progress(self) -> float:
        if self.duration_s <= 0:
            return 1.0
        return max(0.0, min(1.0, self.elapsed_s / self.duration_s))

    @property
    def active(self) -> bool:
        return self.from_scene is not None and self.to_scene is not None and self.elapsed_s < self.duration_s

    def advance(self, dt: float) -> None:
        if self.from_scene is None or self.to_scene is None:
            return
        self.elapsed_s += dt
        if self.elapsed_s >= self.duration_s:
            # Clean up the from_scene; commit fully to to_scene.
            try:
                self.from_scene.exit()
            except Exception:  # noqa: BLE001
                pass
            self.from_scene = None
            self.elapsed_s = self.duration_s

    def cancel(self) -> None:
        """Drop any pending from_scene immediately."""
        if self.from_scene is not None:
            try:
                self.from_scene.exit()
            except Exception:  # noqa: BLE001
                pass
            self.from_scene = None
            self.elapsed_s = self.duration_s


def blend_intensity(progress: float) -> tuple[float, float]:
    """Return (from_weight, to_weight) for a transition at `progress`.

    Linear fade: the outgoing scene starts at full strength and decays
    to 0; the incoming scene grows from 0 to 1. The renderer can
    multiply the outgoing scene's style or skip its draw entirely when
    the weight is at the edges.
    """
    p = max(0.0, min(1.0, progress))
    return (1.0 - p, p)


__all__ = ["SceneTransition", "blend_intensity"]