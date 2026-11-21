"""Menorah with animated candle lighting card."""

import math
import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card

# Menorah base positions (9 candles: 4 left, shamash center higher, 4 right)
# For a 50x10 display, center it nicely
CANDLE_POSITIONS = [
    # (x, base_y, is_shamash)
    (11, 7, False),  # Left 4
    (15, 7, False),
    (19, 7, False),
    (23, 7, False),
    (25, 5, True),  # Shamash (center, higher)
    (27, 7, False),  # Right 4
    (31, 7, False),
    (35, 7, False),
    (39, 7, False),
]

GOLD: RGB = (255, 200, 50)
CANDLE_WHITE: RGB = (240, 240, 255)
FLAME_YELLOW: RGB = (255, 200, 0)
FLAME_ORANGE: RGB = (255, 100, 0)


@register_card
class MenorahCard(Card):
    """Menorah with animated candle flames.

    Config options:
        candles_lit: Number of candles lit 1-8 (default: 8)
        animate_lighting: Animate candles lighting up (default: true)
    """

    card_type = "menorah"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.candles_lit: int = min(8, max(1, self.config.get("candles_lit", 8)))
        self.animate_lighting: bool = self.config.get("animate_lighting", True)

    def _draw_menorah_base(self, canvas: Canvas) -> None:
        """Draw the menorah base/arms."""
        # Draw horizontal base
        for x in range(10, 41):
            canvas.set_pixel(x, 9, GOLD)

        # Draw vertical stems to each candle position
        for x, base_y, is_shamash in CANDLE_POSITIONS:
            for y in range(base_y + 1, 10):
                canvas.set_pixel(x, y, GOLD)

    def _draw_candle(self, canvas: Canvas, x: int, base_y: int, lit: bool, frame: int) -> None:
        """Draw a candle with optional flame."""
        # Candle body (2 pixels tall)
        canvas.set_pixel(x, base_y, CANDLE_WHITE)
        canvas.set_pixel(x, base_y - 1, CANDLE_WHITE)

        if lit:
            # Animated flame
            flame_y = base_y - 2
            # Flicker effect
            flicker = math.sin(frame * 0.3 + x) * 0.5 + 0.5
            if flicker > 0.3:
                canvas.set_pixel(x, flame_y, FLAME_YELLOW)
            if flicker > 0.6 and flame_y - 1 >= 0:
                canvas.set_pixel(x, flame_y - 1, FLAME_ORANGE)

    def _render_frame(self, lit_count: int, frame_num: int) -> Frame:
        """Render the menorah with specified candles lit."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        # Draw base
        self._draw_menorah_base(canvas)

        # Shamash is always lit first (position 4)
        shamash_lit = lit_count > 0

        # Light candles from right to left (traditional)
        # Positions: 0,1,2,3 = left side, 4 = shamash, 5,6,7,8 = right side
        # Lighting order: shamash first, then right to left
        candles_to_light = []
        if shamash_lit:
            candles_to_light.append(4)  # Shamash

        # Add candles right to left (8,7,6,5,3,2,1,0 order)
        right_side = [8, 7, 6, 5]
        left_side = [3, 2, 1, 0]
        all_candles = right_side + left_side

        for i, candle_idx in enumerate(all_candles):
            if i < lit_count:
                candles_to_light.append(candle_idx)

        # Draw all candles
        for i, (x, base_y, is_shamash) in enumerate(CANDLE_POSITIONS):
            lit = i in candles_to_light
            self._draw_candle(canvas, x, base_y, lit, frame_num)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate menorah animation frames."""
        start_time = time.time()
        frame_delay = 1.0 / 20.0
        frame_num = 0

        if self.animate_lighting:
            # Animate candles lighting one by one
            light_interval = min(1.0, self.duration / (self.candles_lit + 2))
            current_lit = 0

            while time.time() - start_time < self.duration:
                elapsed = time.time() - start_time
                target_lit = min(self.candles_lit, int(elapsed / light_interval))

                if target_lit > current_lit:
                    current_lit = target_lit

                frame = self._render_frame(current_lit, frame_num)
                yield frame, frame_delay
                frame_num += 1
        else:
            # All candles lit from start
            while time.time() - start_time < self.duration:
                frame = self._render_frame(self.candles_lit, frame_num)
                yield frame, frame_delay
                frame_num += 1
