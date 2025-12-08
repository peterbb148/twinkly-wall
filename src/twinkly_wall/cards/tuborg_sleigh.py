"""Tuborg Christmas sleigh animation - Santa and reindeer from the classic commercial."""

import random
import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..types import HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card

# Night sky blue (Tuborg style)
SKY_BLUE: RGB = (20, 30, 80)

# Snow white
SNOW_WHITE: RGB = (255, 255, 255)

# Tuborg sleigh sprite - reindeer pulling Santa with presents
# Color codes:
# 1 = brown (reindeer body)
# 2 = tan (antlers, sleigh body)
# 3 = red (Santa suit, sleigh accent)
# 4 = white (beard, snow, ribbons)
# 5 = skin tone (face)
# 6 = green (presents)
# 7 = dark brown (hooves, reins)
# 8 = orange (Santa hat tip, carrot nose)

TUBORG_SLEIGH: list[list[int]] = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # Empty row
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # Empty row
    [0, 0, 2, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],  # Antlers
    [0, 0, 2, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 3, 0, 0, 6, 4, 6, 0, 0, 0],  # Antlers + hat + present
    [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4, 5, 3, 0, 0, 6, 6, 6, 0, 0, 0],  # Head + face + present
    [0, 0, 1, 1, 8, 0, 7, 7, 7, 7, 7, 0, 0, 0, 4, 4, 3, 3, 0, 4, 6, 4, 0, 0, 0],  # Body + reins + beard + present
    [0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 7, 2, 2, 3, 3, 3, 3, 2, 2, 2, 2, 2, 0, 0],  # Body + sleigh
    [0, 1, 0, 1, 0, 1, 0, 0, 0, 0, 0, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0],  # Legs + sleigh base
]

SLEIGH_COLORS: dict[int, RGB] = {
    1: (139, 90, 50),     # Brown reindeer
    2: (180, 140, 60),    # Tan/gold sleigh and antlers
    3: (200, 30, 30),     # Red Santa suit
    4: (255, 255, 255),   # White beard/ribbons
    5: (255, 200, 150),   # Skin tone
    6: (50, 160, 50),     # Green presents
    7: (80, 50, 30),      # Dark brown hooves/reins
    8: (255, 140, 0),     # Orange (nose)
}


@register_card
class TuborgSleighCard(Card):
    """Tuborg Christmas sleigh scrolling across with falling snow.

    Config options:
        speed: Scroll speed in pixels per second (default: 20)
        snow_density: Number of snowflakes (default: 15)
        snow_accumulation: Show snow at bottom (default: true)
        scroll_complete: Wait for full scroll before ending (default: true)
    """

    card_type = "tuborg_sleigh"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.speed: float = self.config.get("speed", 20.0)
        self.snow_density: int = self.config.get("snow_density", 15)
        self.snow_accumulation: bool = self.config.get("snow_accumulation", True)
        self.scroll_complete: bool = self.config.get("scroll_complete", True)
        self._snowflakes: list[tuple[float, float, float]] = []  # x, y, speed

    def _init_snowflakes(self) -> None:
        """Initialize snowflake positions."""
        self._snowflakes = []
        for _ in range(self.snow_density):
            x = random.uniform(0, WIDTH)
            y = random.uniform(0, HEIGHT)
            speed = random.uniform(0.5, 1.5)
            self._snowflakes.append((x, y, speed))

    def _update_snowflakes(self, dt: float) -> None:
        """Update snowflake positions."""
        new_flakes = []
        for x, y, speed in self._snowflakes:
            # Move down and slightly sideways
            new_y = y + speed * dt * 30
            new_x = x + random.uniform(-0.3, 0.3)

            # Reset if below screen (above snow accumulation)
            max_y = HEIGHT - 1 if self.snow_accumulation else HEIGHT
            if new_y >= max_y:
                new_y = 0
                new_x = random.uniform(0, WIDTH)

            # Wrap horizontally
            if new_x < 0:
                new_x = WIDTH - 1
            elif new_x >= WIDTH:
                new_x = 0

            new_flakes.append((new_x, new_y, speed))
        self._snowflakes = new_flakes

    def _draw_sleigh(self, canvas: Canvas, x: int) -> None:
        """Draw the sleigh sprite at given x position."""
        for sy, row in enumerate(TUBORG_SLEIGH):
            for sx, pixel in enumerate(row):
                if pixel > 0 and pixel in SLEIGH_COLORS:
                    px = x + sx
                    py = sy
                    if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                        canvas.set_pixel(px, py, SLEIGH_COLORS[pixel])

    def _render_frame(self, sleigh_x: int) -> Frame:
        """Render a single frame."""
        canvas = Canvas(WIDTH, HEIGHT)

        # Fill with night sky
        for y in range(HEIGHT):
            for x in range(WIDTH):
                canvas.set_pixel(x, y, SKY_BLUE)

        # Draw snow accumulation at bottom
        if self.snow_accumulation:
            for x in range(WIDTH):
                # Wavy snow line
                canvas.set_pixel(x, HEIGHT - 1, SNOW_WHITE)

        # Draw falling snowflakes
        for x, y, _ in self._snowflakes:
            px, py = int(x), int(y)
            max_y = HEIGHT - 2 if self.snow_accumulation else HEIGHT - 1
            if 0 <= px < WIDTH and 0 <= py <= max_y:
                canvas.set_pixel(px, py, SNOW_WHITE)

        # Draw the sleigh
        self._draw_sleigh(canvas, sleigh_x)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate animation frames."""
        self._init_snowflakes()

        sprite_width = len(TUBORG_SLEIGH[0])
        sleigh_x = WIDTH  # Start off-screen right
        target_x = -sprite_width  # End off-screen left

        frame_delay = 1.0 / 30.0
        start_time = time.time()
        scroll_completed = False

        while True:
            frame = self._render_frame(int(sleigh_x))
            yield frame, frame_delay

            # Move sleigh left
            sleigh_x -= self.speed * frame_delay

            # Update snow
            self._update_snowflakes(frame_delay)

            # Check if scroll completed
            if sleigh_x <= target_x:
                scroll_completed = True
                sleigh_x = WIDTH  # Loop back

            elapsed = time.time() - start_time
            if self.scroll_complete:
                if scroll_completed and elapsed >= self.duration:
                    break
            else:
                if elapsed >= self.duration:
                    break
