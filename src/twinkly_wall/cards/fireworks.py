"""Fireworks explosion animation card."""

import random
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from ..canvas import Canvas
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card


@dataclass
class Particle:
    """A single firework particle."""

    x: float
    y: float
    vx: float
    vy: float
    color: RGB
    life: float
    max_life: float


@dataclass
class Firework:
    """A firework that rises then explodes."""

    x: float
    y: float
    vy: float
    color: RGB
    exploded: bool = False
    particles: list[Particle] | None = None


FIREWORK_COLORS: list[RGB] = [
    (255, 0, 0),  # Red
    (0, 255, 0),  # Green
    (0, 100, 255),  # Blue
    (255, 255, 0),  # Yellow
    (255, 0, 255),  # Magenta
    (0, 255, 255),  # Cyan
    (255, 128, 0),  # Orange
    (255, 255, 255),  # White
]


@register_card
class FireworksCard(Card):
    """Fireworks explosion animation.

    Config options:
        num_fireworks: Number of concurrent fireworks (default: 3)
        particle_count: Particles per explosion (default: 12)
        gravity: Gravity strength (default: 0.15)
    """

    card_type = "fireworks"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.num_fireworks: int = self.config.get("num_fireworks", 3)
        self.particle_count: int = self.config.get("particle_count", 12)
        self.gravity: float = self.config.get("gravity", 0.15)

    def _create_firework(self) -> Firework:
        """Create a new rising firework."""
        return Firework(
            x=random.uniform(5, WIDTH - 5),
            y=HEIGHT,
            vy=-random.uniform(1.5, 2.5),
            color=random.choice(FIREWORK_COLORS),
        )

    def _explode(self, fw: Firework) -> None:
        """Explode a firework into particles."""
        fw.exploded = True
        fw.particles = []
        for _ in range(self.particle_count):
            _angle = random.uniform(0, 6.28)
            speed = random.uniform(0.5, 1.5)
            fw.particles.append(
                Particle(
                    x=fw.x,
                    y=fw.y,
                    vx=speed * random.uniform(-1, 1),
                    vy=speed * random.uniform(-1.5, 0.5),
                    color=fw.color,
                    life=1.0,
                    max_life=1.0,
                )
            )

    def _render_frame(self, fireworks: list[Firework]) -> Frame:
        """Render current state of all fireworks."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        for fw in fireworks:
            if not fw.exploded:
                # Draw rising firework
                if 0 <= int(fw.x) < WIDTH and 0 <= int(fw.y) < HEIGHT:
                    canvas.set_pixel(int(fw.x), int(fw.y), fw.color)
            elif fw.particles:
                # Draw explosion particles
                for p in fw.particles:
                    if 0 <= int(p.x) < WIDTH and 0 <= int(p.y) < HEIGHT:
                        # Fade color based on life
                        brightness = p.life / p.max_life
                        color = (
                            int(p.color[0] * brightness),
                            int(p.color[1] * brightness),
                            int(p.color[2] * brightness),
                        )
                        canvas.set_pixel(int(p.x), int(p.y), color)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate fireworks animation frames."""
        fireworks: list[Firework] = []
        start_time = time.time()
        frame_delay = 1.0 / 30.0

        while time.time() - start_time < self.duration:
            # Spawn new fireworks
            while len(fireworks) < self.num_fireworks:
                fireworks.append(self._create_firework())

            # Update fireworks
            for fw in fireworks:
                if not fw.exploded:
                    fw.y += fw.vy
                    # Explode at random height
                    if fw.y <= random.uniform(1, HEIGHT // 2):
                        self._explode(fw)
                elif fw.particles:
                    # Update particles
                    for p in fw.particles:
                        p.x += p.vx
                        p.y += p.vy
                        p.vy += self.gravity
                        p.life -= 0.03

            # Remove dead fireworks
            fireworks = [
                fw
                for fw in fireworks
                if not fw.exploded or (fw.particles and any(p.life > 0 for p in fw.particles))
            ]

            frame = self._render_frame(fireworks)
            yield frame, frame_delay
