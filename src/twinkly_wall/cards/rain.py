"""Vertical rain / waterfall card."""

import math
import random
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..types import BLACK, BLUE, HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card


@register_card
class RainCard(Card):
    """Rain / waterfall animation.

    This card is designed for vertical layouts, but also works horizontally.

    Config options:
        color: RGB tuple for raindrop color (default: blue)
        tail_length: Length of each drop tail in pixels (default: 4)
        density: Fraction of active columns 0-1 (default: 0.4)
        speed: Drop speed factor (default: 1.0)
    """

    card_type = "rain"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.color: RGB = tuple(self.config.get("color", BLUE))  # type: ignore
        self.tail_length: int = int(self.config.get("tail_length", 4))
        self.density: float = float(self.config.get("density", 0.4))
        self.speed: float = float(self.config.get("speed", 1.0))

        # Precompute random phase offsets per column so motion feels organic
        active_columns = max(1, int(WIDTH * self.density))
        active_indices = set(random.sample(range(WIDTH), active_columns))
        self._column_offsets: list[int] = [
            random.randint(0, HEIGHT + self.tail_length) if x in active_indices else -1
            for x in range(WIDTH)
        ]

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate rain / waterfall frames."""
        frame_delay = 1.0 / 30.0
        total_frames = max(1, int(self.duration / frame_delay))

        for frame_index in range(total_frames):
            canvas = Canvas(WIDTH, HEIGHT)
            canvas.clear(BLACK)

            for x in range(WIDTH):
                offset = self._column_offsets[x]
                if offset < 0:
                    continue

                # Head of drop moves down the column; wrap with a longer period so columns desync
                period = HEIGHT + self.tail_length + 5
                head = int(
                    (frame_index * self.speed + offset) % period
                ) - self.tail_length

                # Draw head + tail with simple brightness falloff
                for i in range(self.tail_length):
                    y = head - i
                    if 0 <= y < HEIGHT:
                        fade = 1.0 - (i / max(1, self.tail_length))
                        r = int(self.color[0] * fade)
                        g = int(self.color[1] * fade)
                        b = int(self.color[2] * fade)
                        canvas.set_pixel(x, y, (r, g, b))

            yield canvas.copy(), frame_delay

