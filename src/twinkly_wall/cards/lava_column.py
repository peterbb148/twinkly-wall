"""Vertical lava column (lava lamp style) effect."""

import random
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from ..canvas import Canvas
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card

LAVA_ORANGE: RGB = (255, 140, 60)
LAVA_RED: RGB = (220, 60, 40)
LAVA_DARK: RGB = (80, 10, 20)


@dataclass
class Blob:
    """Simple lava blob moving up and down."""

    x: float
    y: float
    radius: int
    speed: float
    direction: int


@register_card
class LavaColumnCard(Card):
    """Single lava column with blobs rising and falling.

    Config options:
        blobs: Number of blobs (default: 3)
        speed: Animation speed factor (default: 1.0)
    """

    card_type = "lava_column"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.blobs_count: int = int(self.config.get("blobs", 3))
        self.speed: float = float(self.config.get("speed", 1.0))

    def _init_blobs(self) -> list[Blob]:
        blobs: list[Blob] = []
        column_x = WIDTH // 2
        for _ in range(self.blobs_count):
            y = random.uniform(0, HEIGHT - 1)
            radius = random.randint(1, 3)
            speed = random.uniform(0.5, 1.5) * self.speed
            direction = random.choice([-1, 1])
            blobs.append(
                Blob(x=float(column_x), y=y, radius=radius, speed=speed, direction=direction)
            )
        return blobs

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate lava column frames."""
        frame_delay = 1.0 / 20.0
        start = time.time()
        blobs = self._init_blobs()

        while time.time() - start < self.duration:
            canvas = Canvas(WIDTH, HEIGHT)
            canvas.clear(BLACK)

            # Draw blobs
            for blob in blobs:
                for dy in range(-blob.radius, blob.radius + 1):
                    for dx in range(-1, 2):
                        x = int(blob.x + dx)
                        y = int(blob.y + dy)
                        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
                            color = LAVA_ORANGE if abs(dy) < blob.radius else LAVA_RED
                            canvas.set_pixel(x, y, color)

            # Dim background
            for y in range(HEIGHT):
                for x in range(WIDTH):
                    r, g, b = canvas.get_pixel(x, y)
                    if (r, g, b) == (0, 0, 0):
                        canvas.set_pixel(x, y, LAVA_DARK)

            # Update blobs
            for blob in blobs:
                blob.y += blob.direction * blob.speed * frame_delay * 10
                if blob.y < 0:
                    blob.y = 0
                    blob.direction = 1
                elif blob.y > HEIGHT - 1:
                    blob.y = HEIGHT - 1
                    blob.direction = -1

            yield canvas.copy(), frame_delay
