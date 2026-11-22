"""Aurora / Northern Lights vertical ambient effect."""

import math
import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..types import BLACK, PORTRAIT_HEIGHT, PORTRAIT_WIDTH, RGB, Frame, blend_color
from .base import Card, CardContext, register_card


@register_card
class AuroraCard(Card):
    """Aurora / Northern Lights style animation.

    Soft vertical bands of color that flow and shimmer.

    Config options:
        speed: Animation speed factor (default: 1.0)
        brightness: Overall brightness 0-1 (default: 0.8)
    """

    card_type = "aurora"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.speed: float = float(self.config.get("speed", 1.0))
        self.brightness: float = float(self.config.get("brightness", 0.8))

    def _color_at(self, x: float, y: float, t: float) -> RGB:
        """Calculate aurora color at a given position and time."""
        # Two layered sine waves across width and height
        nx = x / PORTRAIT_WIDTH
        ny = y / PORTRAIT_HEIGHT

        wave1 = math.sin(2 * math.pi * (nx * 1.2 + t * 0.1 * self.speed))
        wave2 = math.sin(2 * math.pi * (ny * 0.7 - t * 0.07 * self.speed))
        intensity = (wave1 + wave2) * 0.5

        # Base colors: green / teal / purple
        base1: RGB = (0, 180, 120)
        base2: RGB = (40, 80, 255)
        base3: RGB = (140, 40, 200)

        # Blend based on intensity
        if intensity > 0:
            color = blend_color(base1, base2, intensity)
        else:
            color = blend_color(base1, base3, -intensity)

        # Fade out toward bottom
        fade = ny
        color = blend_color(BLACK, color, fade)

        # Apply overall brightness
        return (
            int(color[0] * self.brightness),
            int(color[1] * self.brightness),
            int(color[2] * self.brightness),
        )

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate aurora frames."""
        frame_delay = 1.0 / 25.0
        start = time.time()

        while time.time() - start < self.duration:
            t = time.time() - start
            canvas = Canvas(PORTRAIT_WIDTH, PORTRAIT_HEIGHT)
            canvas.clear(BLACK)

            for y in range(PORTRAIT_HEIGHT):
                for x in range(PORTRAIT_WIDTH):
                    canvas.set_pixel(x, y, self._color_at(x, y, t))

            yield canvas.copy(), frame_delay
