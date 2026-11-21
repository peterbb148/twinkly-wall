"""Santa sleigh flying across animation card."""

from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card

# Santa sleigh sprite (facing right, 16x7)
# 1 = red (santa/sleigh), 2 = skin, 3 = white (beard/trim), 4 = brown (reindeer), 5 = yellow (stars)
SANTA_SLEIGH: list[list[int]] = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 0, 0, 0, 5, 0],
    [4, 0, 4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [4, 4, 4, 4, 0, 0, 0, 0, 3, 3, 3, 0, 0, 0, 0, 0],
    [0, 4, 0, 4, 0, 0, 0, 1, 2, 3, 3, 1, 0, 0, 0, 0],
    [0, 4, 0, 4, 4, 4, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0, 0],
]

SANTA_COLORS: dict[int, RGB] = {
    1: (200, 0, 0),  # Red suit/sleigh
    2: (255, 200, 150),  # Skin
    3: (255, 255, 255),  # White beard/trim
    4: (139, 90, 43),  # Brown reindeer
    5: (255, 255, 100),  # Yellow stars
}


@register_card
class SantaCard(Card):
    """Santa sleigh flying across the screen.

    Config options:
        speed: Pixels per second (default: 15)
        y_pos: Vertical position (default: 1)
        trail_stars: Show twinkling star trail (default: true)
    """

    card_type = "santa"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.speed: float = self.config.get("speed", 15.0)
        self.y_pos: int = self.config.get("y_pos", 1)
        self.trail_stars: bool = self.config.get("trail_stars", True)
        self.repeats: int = self.config.get("repeats", 1)

    def _draw_santa(self, canvas: Canvas, x: int, y: int) -> None:
        """Draw the Santa sleigh sprite."""
        for sy, row in enumerate(SANTA_SLEIGH):
            for sx, pixel in enumerate(row):
                if pixel > 0 and pixel in SANTA_COLORS:
                    px = x + sx
                    py = y + sy
                    if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                        canvas.set_pixel(px, py, SANTA_COLORS[pixel])

    def _render_frame(self, santa_x: float, frame_num: int) -> Frame:
        """Render a single frame."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        # Draw twinkling background stars
        if self.trail_stars:
            import random

            random.seed(42)  # Consistent star positions
            for _ in range(8):
                sx = random.randint(0, WIDTH - 1)
                sy = random.randint(0, HEIGHT - 1)
                # Twinkle effect
                if (frame_num + sx + sy) % 10 < 7:
                    brightness = 100 + ((frame_num + sx) % 3) * 50
                    canvas.set_pixel(sx, sy, (brightness, brightness, brightness))

        # Draw Santa
        self._draw_santa(canvas, int(santa_x), self.y_pos)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate Santa animation frames."""
        sprite_width = len(SANTA_SLEIGH[0])
        santa_x = float(-sprite_width)  # Start off-screen left

        frame_delay = 1.0 / 30.0
        frame_num = 0
        cycles_done = 0

        while cycles_done < self.repeats:
            frame = self._render_frame(santa_x, frame_num)
            yield frame, frame_delay

            santa_x += self.speed * frame_delay

            # Check if cycle completed (off-screen right)
            if santa_x > WIDTH:
                cycles_done += 1
                if cycles_done < self.repeats:
                    santa_x = float(-sprite_width)

            frame_num += 1
