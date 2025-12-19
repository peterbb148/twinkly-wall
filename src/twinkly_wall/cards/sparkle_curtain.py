"""Sparkling curtain / twinkle effect."""

import random
import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card


@register_card
class SparkleCurtainCard(Card):
    """Soft sparkling curtain effect.

    Config options:
        density: Fraction of pixels that can sparkle (default: 0.15)
        sparkle_chance: Chance for a pixel to sparkle each frame (default: 0.03)
        base_brightness: Background brightness 0-1 (default: 0.2)
    """

    card_type = "sparkle_curtain"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.density: float = float(self.config.get("density", 0.15))
        self.sparkle_chance: float = float(self.config.get("sparkle_chance", 0.03))
        self.base_brightness: float = float(self.config.get("base_brightness", 0.2))

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate sparkling curtain frames."""
        frame_delay = 0.05
        start = time.time()

        # Preselect potential sparkle positions
        candidates: list[tuple[int, int]] = []
        for y in range(HEIGHT):
            for x in range(WIDTH):
                if random.random() < self.density:
                    candidates.append((x, y))

        while time.time() - start < self.duration:
            canvas = Canvas(WIDTH, HEIGHT)

            # Dim base background
            base_value = int(255 * self.base_brightness)
            base_color: RGB = (0, base_value, base_value)
            canvas.clear(base_color)

            # Random sparkles
            for x, y in candidates:
                if random.random() < self.sparkle_chance:
                    # Random cool color
                    color: RGB = (
                        random.randint(180, 255),
                        random.randint(180, 255),
                        255,
                    )
                    canvas.set_pixel(x, y, color)

            yield canvas.copy(), frame_delay

