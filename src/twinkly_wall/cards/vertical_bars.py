"""Vertical bar meter card."""

import math
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..types import BLACK, GREEN, PORTRAIT_HEIGHT, PORTRAIT_WIDTH, RGB, Frame
from .base import Card, CardContext, CardLayout, register_card


@register_card
class VerticalBarsCard(Card):
    """Animated vertical bars / meter.

    This card is useful as a generic "activity" or sound-level style meter.

    Config options:
        bar_width: Width of each bar in pixels (default: 3)
        gap: Gap between bars in pixels (default: 1)
        color: RGB tuple for bar color (default: green)
        speed: Animation speed factor (default: 1.0)
    """

    card_type = "vertical_bars"
    layout = CardLayout.portrait

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.bar_width: int = int(self.config.get("bar_width", 3))
        self.gap: int = int(self.config.get("gap", 1))
        self.color: RGB = tuple(self.config.get("color", GREEN))  # type: ignore
        self.speed: float = float(self.config.get("speed", 1.0))

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate vertical bar frames."""
        frame_delay = 1.0 / 30.0
        total_frames = max(1, int(self.duration / frame_delay))

        bars_span = self.bar_width + self.gap
        bar_count = max(1, PORTRAIT_WIDTH // bars_span)

        for frame_index in range(total_frames):
            canvas = Canvas(PORTRAIT_WIDTH, PORTRAIT_HEIGHT)
            canvas.clear(BLACK)

            for i in range(bar_count):
                # Phase-shifted sine waves for each bar height
                phase = (frame_index * self.speed / 10.0) + (i * 0.8)
                value = (math.sin(phase) + 1.0) / 2.0  # 0..1
                bar_height = max(1, int(value * PORTRAIT_HEIGHT))

                x_start = i * bars_span
                for x in range(x_start, min(x_start + self.bar_width, PORTRAIT_WIDTH)):
                    for y in range(PORTRAIT_HEIGHT - bar_height, PORTRAIT_HEIGHT):
                        canvas.set_pixel(x, y, self.color)

            yield canvas.copy(), frame_delay
