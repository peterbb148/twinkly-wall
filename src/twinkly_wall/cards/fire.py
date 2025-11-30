"""Fire/flame effect animation card."""

import random
import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card

# Fire color palette (from hot to cool)
FIRE_PALETTE: list[RGB] = [
    (0, 0, 0),        # Black (coolest)
    (32, 0, 0),
    (64, 0, 0),
    (128, 0, 0),
    (192, 32, 0),
    (224, 64, 0),
    (255, 96, 0),
    (255, 128, 0),
    (255, 160, 32),
    (255, 192, 64),
    (255, 224, 128),
    (255, 255, 192),  # White (hottest)
]


@register_card
class FireCard(Card):
    """Realistic fire/flame effect.

    Config options:
        intensity: Fire intensity 0.5-2.0 (default: 1.0)
        cooling: How fast fire cools (default: 0.4)
        sparking: Chance of new sparks (default: 0.6)
    """

    card_type = "fire"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.intensity: float = self.config.get("intensity", 1.0)
        self.cooling: float = self.config.get("cooling", 0.4)
        self.sparking: float = self.config.get("sparking", 0.6)

    def _render_frame(self, heat: list[list[float]]) -> Frame:
        """Render the fire based on heat map."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        for y in range(HEIGHT):
            for x in range(WIDTH):
                # Map heat value to palette index
                heat_val = heat[y][x]
                palette_idx = int(heat_val * (len(FIRE_PALETTE) - 1))
                palette_idx = max(0, min(len(FIRE_PALETTE) - 1, palette_idx))
                canvas.set_pixel(x, y, FIRE_PALETTE[palette_idx])

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate fire animation frames."""
        # Heat map (0.0 = cold, 1.0 = hot)
        heat: list[list[float]] = [[0.0] * WIDTH for _ in range(HEIGHT)]

        start_time = time.time()
        frame_delay = 1.0 / 30.0

        while time.time() - start_time < self.duration:
            # Spark new fire at the bottom
            for x in range(WIDTH):
                if random.random() < self.sparking * self.intensity:
                    heat[HEIGHT - 1][x] = random.uniform(0.7, 1.0) * self.intensity
                    heat[HEIGHT - 2][x] = random.uniform(0.5, 0.8) * self.intensity

            # Propagate heat upward with cooling
            new_heat: list[list[float]] = [[0.0] * WIDTH for _ in range(HEIGHT)]

            for y in range(HEIGHT - 1):
                for x in range(WIDTH):
                    # Get heat from below with some spread
                    below_heat = 0.0
                    count = 0

                    for dx in [-1, 0, 0, 0, 1]:  # Weighted toward center
                        nx = x + dx
                        if 0 <= nx < WIDTH:
                            below_heat += heat[y + 1][nx]
                            count += 1

                    if count > 0:
                        # Average heat minus cooling
                        avg_heat = below_heat / count
                        cool_amount = random.uniform(0, self.cooling * 0.15)
                        new_heat[y][x] = max(0, avg_heat - cool_amount)

            # Keep bottom row sparking
            for x in range(WIDTH):
                new_heat[HEIGHT - 1][x] = heat[HEIGHT - 1][x]

            heat = new_heat

            frame = self._render_frame(heat)
            yield frame, frame_delay
