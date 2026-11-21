"""Vertical beer glass filling with bubbles and foam."""

import random
import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame, blend_color
from .base import Card, CardContext, register_card

BEER_GOLD: RGB = (255, 198, 41)
BEER_DARK: RGB = (180, 120, 20)
FOAM_WHITE: RGB = (255, 250, 240)
FOAM_CREAM: RGB = (255, 245, 220)
BUBBLE_COLOR: RGB = (255, 255, 220)
GLASS_OUTLINE: RGB = (200, 200, 220)


@register_card
class BeerVerticalCard(Card):
    """Vertical beer glass filling with bubbles and foam.

    Designed for use with a vertically mounted wall (via twinkly.orientation),
    but previewable in the terminal with --orientation.

    Config options:
        fill_time: Seconds it takes to fill the glass (default: 6)
        bubble_count: Number of bubbles (default: 10)
        wobble: Horizontal bubble wobble (default: True)
    """

    card_type = "beer_vertical"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.fill_time: float = float(self.config.get("fill_time", 6.0))
        self.bubble_count: int = int(self.config.get("bubble_count", 10))
        self.wobble: bool = bool(self.config.get("wobble", True))

    def _glass_bounds(self) -> tuple[int, int]:
        """Return (x0, x1) inclusive bounds of the glass interior."""
        glass_width = 10
        x0 = (WIDTH - glass_width) // 2
        x1 = x0 + glass_width - 1
        return x0, x1

    def _draw_glass_outline(self, canvas: Canvas) -> None:
        """Draw a simple beer glass outline."""
        x0, x1 = self._glass_bounds()
        for y in range(HEIGHT):
            canvas.set_pixel(x0, y, GLASS_OUTLINE)
            canvas.set_pixel(x1, y, GLASS_OUTLINE)

    def _init_bubbles(self) -> list[tuple[float, float, float]]:
        """Create initial bubbles as (x, y, speed)."""
        x0, x1 = self._glass_bounds()
        bubbles: list[tuple[float, float, float]] = []
        for _ in range(self.bubble_count):
            x = random.uniform(x0 + 1, x1 - 1)
            y = random.uniform(0, HEIGHT - 1)
            speed = random.uniform(1.5, 3.0)
            bubbles.append((x, y, speed))
        return bubbles

    def _render_frame(
        self,
        fill_ratio: float,
        bubbles: list[tuple[float, float, float]],
        time_offset: float,
    ) -> Frame:
        """Render a single frame for the beer glass animation."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        x0, x1 = self._glass_bounds()
        beer_height = int((HEIGHT - 2) * fill_ratio)

        # Draw beer inside glass
        for y in range(HEIGHT - 1, HEIGHT - 1 - beer_height, -1):
            t = (HEIGHT - 1 - y) / max(1, beer_height)
            color = blend_color(BEER_GOLD, BEER_DARK, t * 0.5)
            for x in range(x0 + 1, x1):
                canvas.set_pixel(x, y, color)

        # Draw foam at top of beer
        if beer_height > 0:
            foam_y = HEIGHT - 1 - beer_height
            for x in range(x0 + 1, x1):
                c = FOAM_WHITE if (x + int(time_offset * 5)) % 3 == 0 else FOAM_CREAM
                canvas.set_pixel(x, foam_y, c)

        # Draw bubbles only inside beer region
        for x, y, _ in bubbles:
            ix = int(x)
            iy = int(y)
            if x0 + 1 <= ix < x1 and iy >= HEIGHT - beer_height:
                canvas.set_pixel(ix, iy, BUBBLE_COLOR)

        # Draw glass outline on top
        self._draw_glass_outline(canvas)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate frames for vertical beer glass with filling animation."""
        bubbles = self._init_bubbles()
        start_time = time.time()
        frame_delay = 1.0 / 30.0

        while True:
            elapsed = time.time() - start_time
            if elapsed > self.duration:
                break

            # Fill ratio goes 0->1 over fill_time, then stays full
            if self.fill_time > 0:
                fill_ratio = min(1.0, elapsed / self.fill_time)
            else:
                fill_ratio = 1.0

            # Update bubbles
            x0, x1 = self._glass_bounds()
            max_beer_y = HEIGHT - 1
            beer_height = int((HEIGHT - 2) * fill_ratio)
            beer_top_y = max_beer_y - beer_height

            new_bubbles: list[tuple[float, float, float]] = []
            for x, y, speed in bubbles:
                # Move up only if inside beer
                if y >= beer_top_y:
                    y -= speed * frame_delay
                    if self.wobble:
                        x += random.uniform(-0.3, 0.3)
                        x = max(x0 + 1, min(x1 - 1, x))
                else:
                    # Respawn near bottom of beer
                    x = random.uniform(x0 + 1, x1 - 1)
                    y = random.uniform(max_beer_y - beer_height, max_beer_y)
                    speed = random.uniform(1.5, 3.0)

                new_bubbles.append((x, y, speed))

            bubbles = new_bubbles

            frame = self._render_frame(fill_ratio, bubbles, elapsed)
            yield frame, frame_delay
