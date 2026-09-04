"""Generic particle engine. Scenes spawn their own particles; this just steps."""

from __future__ import annotations

from dataclasses import dataclass, field

from .frame_buffer import FrameBuffer


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    age: float
    lifetime: float
    char: str


@dataclass
class ParticleSystem:
    particles: list[Particle] = field(default_factory=list)

    def spawn(self, p: Particle) -> None:
        self.particles.append(p)

    def extend(self, ps: list[Particle]) -> None:
        self.particles.extend(ps)

    def clear(self) -> None:
        self.particles.clear()

    def step(self, dt: float, width: int, height: int) -> None:
        alive: list[Particle] = []
        for p in self.particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.age += dt
            if p.age >= p.lifetime:
                continue
            if p.x < 0 or p.x >= width or p.y >= height:
                continue
            alive.append(p)
        self.particles = alive

    def draw(self, buf: FrameBuffer, style: str = "") -> None:
        for p in self.particles:
            ix, iy = int(p.x), int(p.y)
            if 0 <= ix < buf.width and 0 <= iy < buf.height:
                buf.set(iy, ix, p.char, style)