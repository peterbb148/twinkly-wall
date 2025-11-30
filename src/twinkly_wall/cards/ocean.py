"""Ocean waves animation card."""

import math
import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card

# Ocean color palette
DEEP_WATER: RGB = (0, 20, 80)
MID_WATER: RGB = (0, 50, 120)
SHALLOW_WATER: RGB = (0, 100, 180)
FOAM: RGB = (200, 220, 255)


@register_card
class OceanCard(Card):
    """Ocean waves rolling animation.

    Config options:
        wave_speed: Wave movement speed (default: 1.0)
        wave_height: Wave amplitude (default: 2)
        foam: Show foam on wave crests (default: true)
    """

    card_type = "ocean"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.wave_speed: float = self.config.get("wave_speed", 1.0)
        self.wave_height: int = self.config.get("wave_height", 2)
        self.foam: bool = self.config.get("foam", True)

    def _render_frame(self, t: float) -> Frame:
        """Render ocean waves."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(DEEP_WATER)

        # Multiple wave layers for depth
        for x in range(WIDTH):
            # Primary wave
            wave1 = math.sin(x * 0.15 + t * 2 * self.wave_speed) * self.wave_height
            # Secondary wave (slower, different phase)
            wave2 = math.sin(x * 0.08 + t * 1.2 * self.wave_speed + 2) * self.wave_height * 0.7
            # Combined wave height
            wave = wave1 + wave2

            # Calculate wave surface position
            base_y = HEIGHT // 2
            surface_y = int(base_y + wave)

            # Draw water column
            for y in range(HEIGHT):
                if y < surface_y - 1:
                    # Sky/air - leave black or could add sky
                    pass
                elif y == surface_y - 1 and self.foam:
                    # Foam on wave crest (only on rising part)
                    slope = math.cos(x * 0.15 + t * 2 * self.wave_speed)
                    if slope > 0.3:
                        canvas.set_pixel(x, y, FOAM)
                elif y == surface_y:
                    # Surface
                    canvas.set_pixel(x, y, SHALLOW_WATER)
                elif y < surface_y + 2:
                    # Near surface
                    canvas.set_pixel(x, y, MID_WATER)
                else:
                    # Deep water - gradient darker
                    depth_factor = min(1.0, (y - surface_y) / (HEIGHT - surface_y))
                    r = int(DEEP_WATER[0] * (1 - depth_factor * 0.5))
                    g = int(DEEP_WATER[1] * (1 - depth_factor * 0.3))
                    b = int(DEEP_WATER[2] * (1 - depth_factor * 0.2))
                    canvas.set_pixel(x, y, (r, g, b))

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate ocean animation frames."""
        start_time = time.time()
        frame_delay = 1.0 / 30.0

        while time.time() - start_time < self.duration:
            t = time.time() - start_time
            frame = self._render_frame(t)
            yield frame, frame_delay
