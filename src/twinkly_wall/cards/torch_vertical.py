"""Vertical torch / fireplace flame effect."""

import math
import random
import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame, blend_color
from .base import Card, CardContext, register_card


@register_card
class TorchVerticalCard(Card):
    """Vertical torch / fireplace style flame.

    A flickering column of flame at the bottom with embers drifting up.

    Config options:
        intensity: Flame intensity 0.5-2.0 (default: 1.0)
        ember_density: Number of drifting embers (default: 10)
    """

    card_type = "torch_vertical"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.intensity: float = float(self.config.get("intensity", 1.0))
        self.ember_density: int = int(self.config.get("ember_density", 10))

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate vertical flame frames."""
        frame_delay = 1.0 / 30.0
        start = time.time()

        # Embers as (x, y, speed)
        embers: list[tuple[float, float, float]] = []
        for _ in range(self.ember_density):
            x = random.uniform(0, WIDTH - 1)
            y = random.uniform(0, HEIGHT // 2)
            speed = random.uniform(0.5, 1.5)
            embers.append((x, y, speed))

        while time.time() - start < self.duration:
            t = time.time() - start
            canvas = Canvas(WIDTH, HEIGHT)
            canvas.clear(BLACK)

            # Base flame at bottom using noise-like sin waves
            for y in range(HEIGHT // 2, HEIGHT):
                vertical = (y - HEIGHT // 2) / (HEIGHT // 2)
                for x in range(WIDTH):
                    nx = x / WIDTH
                    noise = math.sin((nx * 5 + t * 5) * self.intensity)
                    height_mask = max(0.0, 1.0 - vertical * 1.5)
                    strength = max(0.0, noise * 0.5 + height_mask)

                    base: RGB = (255, 120, 20)
                    hot: RGB = (255, 230, 100)
                    color = blend_color(base, hot, strength)
                    if strength > 0.05:
                        canvas.set_pixel(x, y, color)

            # Update and draw embers
            new_embers: list[tuple[float, float, float]] = []
            for x, y, speed in embers:
                y -= speed * frame_delay * 15
                x += random.uniform(-0.2, 0.2)
                if x < 0:
                    x = 0
                if x >= WIDTH:
                    x = WIDTH - 1
                if y < 0:
                    # Respawn near base of flame
                    x = random.uniform(0, WIDTH - 1)
                    y = random.uniform(HEIGHT // 2, HEIGHT - 2)
                    speed = random.uniform(0.5, 1.5)

                new_embers.append((x, y, speed))
                ix, iy = int(x), int(y)
                canvas.set_pixel(ix, iy, (255, 200, 120))

            embers = new_embers

            yield canvas.copy(), frame_delay

