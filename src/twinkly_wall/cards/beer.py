"""Beer bubbles animation card."""

import random
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from ..canvas import Canvas
from ..types import HEIGHT, RGB, WIDTH, Frame, blend_color
from .base import Card, CardContext, register_card

# Beer colors
BEER_GOLD: RGB = (255, 198, 41)
BEER_DARK: RGB = (180, 120, 20)
FOAM_WHITE: RGB = (255, 250, 240)
FOAM_CREAM: RGB = (255, 245, 220)
BUBBLE_COLOR: RGB = (255, 255, 200)


@dataclass
class Bubble:
    """A single rising bubble."""

    x: float
    y: float
    speed: float
    size: int  # 1 = small dot, 2 = larger


@register_card
class BeerCard(Card):
    """Beer with rising bubbles animation.

    Config options:
        bubble_count: Number of bubbles (default: 8)
        bubble_speed: Base speed of bubbles (default: 3.0)
        foam_height: Height of foam layer in pixels (default: 2)
        wobble: Enable horizontal wobble (default: True)
    """

    card_type = "beer"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.bubble_count: int = self.config.get("bubble_count", 8)
        self.bubble_speed: float = self.config.get("bubble_speed", 3.0)
        self.foam_height: int = self.config.get("foam_height", 2)
        self.wobble: bool = self.config.get("wobble", True)

    def _create_bubble(self) -> Bubble:
        """Create a new bubble at the bottom."""
        return Bubble(
            x=random.uniform(1, WIDTH - 2),
            y=float(HEIGHT - 1),
            speed=self.bubble_speed * random.uniform(0.7, 1.3),
            size=random.choice([1, 1, 1, 2]),  # Mostly small bubbles
        )

    def _render_frame(self, bubbles: list[Bubble], time_offset: float) -> Frame:
        """Render a single frame of the animation."""
        canvas = Canvas(WIDTH, HEIGHT)

        # Draw beer gradient background (darker at bottom)
        for y in range(self.foam_height, HEIGHT):
            # Gradient from light to dark
            t = (y - self.foam_height) / (HEIGHT - self.foam_height)
            color = blend_color(BEER_GOLD, BEER_DARK, t * 0.5)
            for x in range(WIDTH):
                canvas.set_pixel(x, y, color)

        # Draw foam at top with slight variation
        for y in range(self.foam_height):
            for x in range(WIDTH):
                # Alternate colors for texture
                if (x + y + int(time_offset * 2)) % 3 == 0:
                    canvas.set_pixel(x, y, FOAM_CREAM)
                else:
                    canvas.set_pixel(x, y, FOAM_WHITE)

        # Draw bubbles
        for bubble in bubbles:
            bx = int(bubble.x)
            by = int(bubble.y)

            if by >= self.foam_height:  # Only draw below foam
                if bubble.size == 1:
                    canvas.set_pixel(bx, by, BUBBLE_COLOR)
                else:
                    # 2x2 bubble
                    canvas.set_pixel(bx, by, BUBBLE_COLOR)
                    canvas.set_pixel(bx + 1, by, BUBBLE_COLOR)
                    canvas.set_pixel(bx, by - 1, BUBBLE_COLOR)
                    canvas.set_pixel(bx + 1, by - 1, BUBBLE_COLOR)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate beer bubbles animation frames."""
        # Initialize bubbles at random positions
        bubbles: list[Bubble] = []
        for _ in range(self.bubble_count):
            bubble = self._create_bubble()
            bubble.y = random.uniform(self.foam_height + 1, HEIGHT - 1)
            bubbles.append(bubble)

        start_time = time.time()
        frame_delay = 1.0 / 30.0  # 30 FPS
        time_offset = 0.0

        while time.time() - start_time < self.duration:
            # Update bubbles
            for bubble in bubbles:
                # Move up
                bubble.y -= bubble.speed * frame_delay

                # Horizontal wobble
                if self.wobble:
                    bubble.x += random.uniform(-0.3, 0.3)
                    bubble.x = max(1, min(WIDTH - 2, bubble.x))

                # Reset if reached foam
                if bubble.y < self.foam_height:
                    bubble.x = random.uniform(1, WIDTH - 2)
                    bubble.y = float(HEIGHT - 1)
                    bubble.speed = self.bubble_speed * random.uniform(0.7, 1.3)

            # Render
            frame = self._render_frame(bubbles, time_offset)
            yield frame, frame_delay

            time_offset += frame_delay
