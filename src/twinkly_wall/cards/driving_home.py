"""Snowy scrolling text card: 'Driving home for Christmas!'."""

import random
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..fonts import draw_text, text_width
from ..types import HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card

# Colors reused from Tuborg truck card
SKY_BLUE: RGB = (20, 30, 80)
SNOW_WHITE: RGB = (255, 255, 255)


@register_card
class DrivingHomeCard(Card):
    """Scrolling snowy text animation.

    Config options:
        text: Message to scroll (default: "Driving home for Christmas!")
        scroll_speed: Pixels per second (default: 25)
        snow_density: Number of snowflakes (default: 16)
        snow_accumulation: Show snow line at bottom (default: true)
        repeats: Number of times to scroll (default: 1)
    """

    card_type = "driving_home"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.text: str = self.config.get("text", "Driving home for Christmas!")
        self.scroll_speed: float = self.config.get("scroll_speed", 25.0)
        self.snow_density: int = self.config.get("snow_density", 16)
        self.snow_accumulation: bool = self.config.get("snow_accumulation", True)
        self.repeats: int = self.config.get("repeats", 1)
        self._snowflakes: list[tuple[float, float, float]] = []  # x, y, speed

    def _init_snowflakes(self) -> None:
        self._snowflakes = []
        for _ in range(self.snow_density):
            x = random.uniform(0, WIDTH)
            y = random.uniform(0, HEIGHT)
            speed = random.uniform(0.5, 1.5)
            self._snowflakes.append((x, y, speed))

    def _update_snowflakes(self, dt: float) -> None:
        updated: list[tuple[float, float, float]] = []
        for x, y, speed in self._snowflakes:
            new_y = y + speed * dt * 30
            new_x = x + random.uniform(-0.3, 0.3)

            max_y = HEIGHT - 1 if self.snow_accumulation else HEIGHT
            if new_y >= max_y:
                new_y = 0
                new_x = random.uniform(0, WIDTH)

            if new_x < 0:
                new_x = WIDTH - 1
            elif new_x >= WIDTH:
                new_x = 0

            updated.append((new_x, new_y, speed))
        self._snowflakes = updated

    def _render_frame(self, offset: int) -> Frame:
        canvas = Canvas(WIDTH, HEIGHT)

        # Sky
        for y in range(HEIGHT):
            for x in range(WIDTH):
                canvas.set_pixel(x, y, SKY_BLUE)

        # Snow accumulation
        if self.snow_accumulation:
            for x in range(WIDTH):
                canvas.set_pixel(x, HEIGHT - 1, SNOW_WHITE)

        # Snowflakes
        for x, y, _ in self._snowflakes:
            px, py = int(x), int(y)
            max_y = HEIGHT - 2 if self.snow_accumulation else HEIGHT - 1
            if 0 <= px < WIDTH and 0 <= py <= max_y:
                canvas.set_pixel(px, py, SNOW_WHITE)

        # Text (scrolling left)
        x_pos = WIDTH - offset
        draw_text(canvas, x_pos, 1, self.text, SNOW_WHITE)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        self._init_snowflakes()

        text_w = text_width(self.text)
        total_scroll = text_w + WIDTH + 1

        frame_delay = 1.0 / 30.0
        pixels_per_frame = self.scroll_speed / 30.0

        offset = 0.0
        scrolls_done = 0

        while scrolls_done < self.repeats:
            frame = self._render_frame(int(offset))
            yield frame, frame_delay

            offset += pixels_per_frame
            self._update_snowflakes(frame_delay)

            if offset >= total_scroll:
                scrolls_done += 1
                offset = 0.0
