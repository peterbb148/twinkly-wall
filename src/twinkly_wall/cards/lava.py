"""Lava lamp blob animation card."""

import math
import random
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from ..canvas import Canvas
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card


@dataclass
class Blob:
    """A lava lamp blob."""

    x: float
    y: float
    radius: float
    vx: float
    vy: float
    color: RGB


@register_card
class LavaCard(Card):
    """Lava lamp blob effect.

    Config options:
        num_blobs: Number of blobs (default: 5)
        color1: First blob color (default: red)
        color2: Second blob color (default: orange)
        speed: Movement speed (default: 1.0)
    """

    card_type = "lava"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.num_blobs: int = self.config.get("num_blobs", 5)
        self.color1: RGB = tuple(self.config.get("color1", (255, 50, 0)))  # type: ignore
        self.color2: RGB = tuple(self.config.get("color2", (255, 150, 0)))  # type: ignore
        self.speed: float = self.config.get("speed", 1.0)

    def _create_blob(self) -> Blob:
        """Create a new blob."""
        color = self.color1 if random.random() < 0.5 else self.color2
        return Blob(
            x=random.uniform(2, WIDTH - 2),
            y=random.uniform(2, HEIGHT - 2),
            radius=random.uniform(1.5, 3.0),
            vx=random.uniform(-0.3, 0.3) * self.speed,
            vy=random.uniform(-0.3, 0.3) * self.speed,
            color=color,
        )

    def _render_frame(self, blobs: list[Blob], t: float) -> Frame:
        """Render the lava lamp effect using metaballs."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        for y in range(HEIGHT):
            for x in range(WIDTH):
                # Calculate metaball field value
                field = 0.0
                r_total = 0.0
                g_total = 0.0
                b_total = 0.0

                for blob in blobs:
                    # Distance from pixel to blob center
                    dx = x - blob.x
                    dy = y - blob.y
                    dist_sq = dx * dx + dy * dy + 0.1  # Avoid division by zero

                    # Metaball formula
                    influence = (blob.radius * blob.radius) / dist_sq
                    field += influence

                    # Weight colors by influence
                    r_total += blob.color[0] * influence
                    g_total += blob.color[1] * influence
                    b_total += blob.color[2] * influence

                # Threshold for blob surface
                if field > 0.6:
                    # Normalize colors
                    brightness = min(1.0, field - 0.6) * 2
                    r = int(min(255, r_total / field * brightness))
                    g = int(min(255, g_total / field * brightness))
                    b = int(min(255, b_total / field * brightness))
                    canvas.set_pixel(x, y, (r, g, b))

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate lava lamp animation frames."""
        blobs = [self._create_blob() for _ in range(self.num_blobs)]

        start_time = time.time()
        frame_delay = 1.0 / 20.0  # Slower for smoother lava feel

        while time.time() - start_time < self.duration:
            t = time.time() - start_time

            # Update blob positions
            for blob in blobs:
                # Add some sine wave motion for organic feel
                blob.x += blob.vx + math.sin(t * 2 + blob.y) * 0.05
                blob.y += blob.vy + math.cos(t * 1.5 + blob.x) * 0.05

                # Bounce off walls
                if blob.x <= blob.radius or blob.x >= WIDTH - blob.radius:
                    blob.vx = -blob.vx
                    blob.x = max(blob.radius, min(WIDTH - blob.radius, blob.x))

                if blob.y <= blob.radius or blob.y >= HEIGHT - blob.radius:
                    blob.vy = -blob.vy
                    blob.y = max(blob.radius, min(HEIGHT - blob.radius, blob.y))

                # Slowly change velocity for variation
                blob.vx += random.uniform(-0.02, 0.02) * self.speed
                blob.vy += random.uniform(-0.02, 0.02) * self.speed

                # Limit velocity
                max_v = 0.5 * self.speed
                blob.vx = max(-max_v, min(max_v, blob.vx))
                blob.vy = max(-max_v, min(max_v, blob.vy))

            frame = self._render_frame(blobs, t)
            yield frame, frame_delay
