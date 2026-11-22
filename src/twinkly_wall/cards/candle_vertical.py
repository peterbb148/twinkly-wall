"""Vertical Christmas candle with falling snow and accumulation."""

import random
import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..types import BLACK, PORTRAIT_HEIGHT, PORTRAIT_WIDTH, RGB, Frame
from .base import Card, CardContext, register_card

CANDLE_BODY: RGB = (230, 230, 255)
CANDLE_OUTLINE: RGB = (200, 200, 230)
FLAME_YELLOW: RGB = (255, 220, 120)
FLAME_ORANGE: RGB = (255, 140, 40)
FLAME_WHITE: RGB = (255, 255, 255)
SNOW_WHITE: RGB = (255, 255, 255)
SNOW_LIGHT: RGB = (210, 230, 255)


@register_card
class CandleVerticalCard(Card):
    """Vertical candle with flickering flame and falling snow.

    This card is designed for a vertically mounted panel (use
    twinkly.orientation=vertical_left/right for the wall, and
    --orientation with twinklysay preview).

    Config options:
        snow_density: Approximate number of snowflakes (default: 20)
        wind: Horizontal wind component -1..1 (default: 0.0)
        accumulate: Whether snow should accumulate at the base (default: True)
    """

    card_type = "candle_vertical"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.snow_density: int = int(self.config.get("snow_density", 20))
        self.wind: float = float(self.config.get("wind", 0.0))
        self.accumulate: bool = bool(self.config.get("accumulate", True))

    def _init_snow(self) -> list[tuple[float, float, float]]:
        """Create initial snowflakes as (x, y, speed)."""
        flakes: list[tuple[float, float, float]] = []
        for _ in range(self.snow_density):
            x = random.uniform(0, PORTRAIT_WIDTH - 1)
            y = random.uniform(0, PORTRAIT_HEIGHT - 1)
            speed = random.uniform(0.6, 1.4)
            flakes.append((x, y, speed))
        return flakes

    def _draw_candle(self, canvas: Canvas, time_offset: float) -> None:
        """Draw candle body and flickering flame in the center."""
        # Make a narrow candle in the horizontal center
        candle_width = 6
        x0 = (PORTRAIT_WIDTH - candle_width) // 2
        x1 = x0 + candle_width - 1

        # Body (bottom half of display)
        for y in range(PORTRAIT_HEIGHT // 2, PORTRAIT_HEIGHT):
            for x in range(x0, x1 + 1):
                color = CANDLE_BODY
                if x == x0 or x == x1:
                    color = CANDLE_OUTLINE
                canvas.set_pixel(x, y, color)

        # Flame position (just above body)
        flame_base_y = PORTRAIT_HEIGHT // 2 - 1
        flame_x = (x0 + x1) // 2

        # Simple flicker: small vertical jitter and color variation
        jitter = int((time_offset * 10) % 2)  # 0 or 1

        # Outer flame (orange)
        for dy in range(-2 - jitter, 1):
            width = 1 + max(0, -dy)
            for dx in range(-width, width + 1):
                canvas.set_pixel(flame_x + dx, flame_base_y + dy, FLAME_ORANGE)

        # Inner flame (yellow/white)
        canvas.set_pixel(flame_x, flame_base_y - 2 - jitter, FLAME_WHITE)
        canvas.set_pixel(flame_x, flame_base_y - 1 - jitter, FLAME_YELLOW)

    def _render_frame(
        self,
        snowflakes: list[tuple[float, float, float]],
        accumulation: list[int],
        time_offset: float,
    ) -> Frame:
        """Render a single frame with candle, snow, and accumulation."""
        canvas = Canvas(PORTRAIT_WIDTH, PORTRAIT_HEIGHT)
        canvas.clear(BLACK)

        # Draw candle + flame first
        self._draw_candle(canvas, time_offset)

        # Draw accumulation at base
        if self.accumulate:
            for x, height in enumerate(accumulation):
                for y in range(PORTRAIT_HEIGHT - height, PORTRAIT_HEIGHT):
                    color = SNOW_LIGHT if (x + y) % 3 == 0 else SNOW_WHITE
                    canvas.set_pixel(x, y, color)

        # Draw snowflakes
        for x, y, _ in snowflakes:
            ix = int(x)
            iy = int(y)
            if 0 <= ix < PORTRAIT_WIDTH and 0 <= iy < PORTRAIT_HEIGHT:
                color = SNOW_WHITE if (ix + iy) % 2 == 0 else SNOW_LIGHT
                canvas.set_pixel(ix, iy, color)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate candle with snowfall frames."""
        snowflakes = self._init_snow()
        accumulation: list[int] = [0] * PORTRAIT_WIDTH
        max_accum = 3

        start_time = time.time()
        frame_delay = 1.0 / 30.0
        t = 0.0

        while time.time() - start_time < self.duration:
            # Update snowflakes
            new_flakes: list[tuple[float, float, float]] = []
            for x, y, speed in snowflakes:
                y += speed * frame_delay
                x += (self.wind + random.uniform(-0.3, 0.3)) * frame_delay

                if x < 0:
                    x += PORTRAIT_WIDTH
                elif x >= PORTRAIT_WIDTH:
                    x -= PORTRAIT_WIDTH

                bottom_limit = PORTRAIT_HEIGHT - 1
                col = int(x)
                if self.accumulate and 0 <= col < PORTRAIT_WIDTH:
                    bottom_limit = PORTRAIT_HEIGHT - 1 - accumulation[col]

                if y >= bottom_limit:
                    if (
                        self.accumulate
                        and 0 <= col < PORTRAIT_WIDTH
                        and accumulation[col] < max_accum
                    ):
                        if random.random() < 0.15:
                            accumulation[col] += 1

                    # Respawn at top
                    x = random.uniform(0, PORTRAIT_WIDTH - 1)
                    y = 0.0
                    speed = random.uniform(0.6, 1.4)

                new_flakes.append((x, y, speed))

            snowflakes = new_flakes

            frame = self._render_frame(snowflakes, accumulation, t)
            yield frame, frame_delay

            t += frame_delay
