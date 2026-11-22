"""Vertical countdown ruler / progress bar."""

import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..types import BLACK, GREEN, PORTRAIT_HEIGHT, PORTRAIT_WIDTH, WHITE, Frame
from .base import Card, CardContext, register_card


@register_card
class CountdownRulerCard(Card):
    """Vertical countdown / progress ruler.

    Config options:
        total_seconds: Total countdown length (default: duration)
        color: Bar color (default: green)
        direction: up or down (default: down)
    """

    card_type = "countdown_ruler"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.total_seconds: float = float(self.config.get("total_seconds", self.duration))
        self.color = tuple(self.config.get("color", GREEN))  # type: ignore
        self.direction: str = self.config.get("direction", "down")

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate countdown ruler frames."""
        start_time = time.time()
        frame_delay = 0.1

        while True:
            now = time.time()
            elapsed = now - start_time
            if elapsed > self.duration:
                break

            ratio = max(0.0, 1.0 - min(elapsed, self.total_seconds) / max(0.1, self.total_seconds))
            filled = int(ratio * PORTRAIT_HEIGHT)

            canvas = Canvas(PORTRAIT_WIDTH, PORTRAIT_HEIGHT)
            canvas.clear(BLACK)

            # Draw ruler border
            for y in range(PORTRAIT_HEIGHT):
                canvas.set_pixel(0, y, WHITE)
                canvas.set_pixel(PORTRAIT_WIDTH - 1, y, WHITE)

            # Draw filled bar
            if self.direction == "down":
                for y in range(PORTRAIT_HEIGHT - filled, PORTRAIT_HEIGHT):
                    for x in range(1, PORTRAIT_WIDTH - 1):
                        canvas.set_pixel(x, y, self.color)
            else:
                for y in range(0, filled):
                    for x in range(1, PORTRAIT_WIDTH - 1):
                        canvas.set_pixel(x, y, self.color)

            yield canvas.copy(), frame_delay
