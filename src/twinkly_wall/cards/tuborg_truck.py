"""Tuborg Christmas truck animation inspired by the classic commercial scene."""

import random
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..types import HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card

# Colors
SKY_BLUE: RGB = (20, 30, 80)
SNOW_WHITE: RGB = (255, 255, 255)
TRUCK_RED: RGB = (210, 70, 40)
TRAILER_WHITE: RGB = (245, 245, 245)
GIFT_GREEN: RGB = (0, 150, 60)
GIFT_RED: RGB = (200, 40, 40)
GOLD: RGB = (245, 180, 60)
WHEEL_BLACK: RGB = (20, 20, 20)
WINDOW_BLUE: RGB = (200, 220, 255)
FACE_SKIN: RGB = (255, 200, 150)

@register_card
class TuborgTruckCard(Card):
    """Tuborg truck rolling through the snow with falling flakes.

    Config options:
        speed: Scroll speed in pixels per second (default: 18)
        snow_density: Number of snowflakes (default: 16)
        snow_accumulation: Show snow at bottom (default: true)
        repeats: How many times to run the animation (default: 1)
    """

    card_type = "tuborg_truck"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.speed: float = self.config.get("speed", 18.0)
        self.snow_density: int = self.config.get("snow_density", 16)
        self.snow_accumulation: bool = self.config.get("snow_accumulation", True)
        self.repeats: int = self.config.get("repeats", 1)
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
        new_flakes: list[tuple[float, float, float]] = []
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

            new_flakes.append((new_x, new_y, speed))
        self._snowflakes = new_flakes

    def _draw_truck(self, canvas: Canvas, x: int) -> None:
        """Draw the Tuborg truck sprite at x."""
        base_y = HEIGHT - 3  # chassis height
        trailer_top = 1
        trailer_height = 6
        trailer_width = 20  # shorter trailer for more natural proportions
        trailer_offset = 8  # distance from cab nose to trailer front
        trailer_x = x + trailer_offset

        cab_width = 9
        cab_height = 5
        cab_x = x
        cab_y = base_y - cab_height + 1

        wheel_y = base_y + 1

        # Trailer box (simple white box, no lettering)
        canvas.fill_rect(trailer_x, trailer_top, trailer_width, trailer_height, TRAILER_WHITE)

        # Trailer underside / hitch
        canvas.fill_rect(trailer_x, base_y, trailer_width, 1, TRUCK_RED)

        # Cab body
        canvas.fill_rect(cab_x, cab_y, cab_width, cab_height, TRUCK_RED)
        # Cab roof
        canvas.fill_rect(cab_x + 1, cab_y - 1, cab_width - 2, 1, TRAILER_WHITE)
        # Window and driver
        canvas.fill_rect(cab_x + 2, cab_y, 3, 2, WINDOW_BLUE)
        canvas.set_pixel(cab_x + 3, cab_y + 1, FACE_SKIN)
        # Headlight
        canvas.set_pixel(cab_x + cab_width - 1, base_y - 1, TRAILER_WHITE)

        # Gifts stacked behind the cab
        gift_pixels = [
            (cab_x - 2, trailer_top + 2, GIFT_GREEN),
            (cab_x - 1, trailer_top + 2, GIFT_RED),
            (cab_x - 2, trailer_top + 3, GOLD),
            (cab_x - 1, trailer_top + 3, GIFT_GREEN),
            (cab_x - 2, trailer_top + 1, GIFT_RED),
        ]
        for gx, gy, color in gift_pixels:
            canvas.set_pixel(gx, gy, color)
        # Gift ribbons
        canvas.set_pixel(cab_x - 2, trailer_top + 2, SNOW_WHITE)
        canvas.set_pixel(cab_x - 1, trailer_top + 3, SNOW_WHITE)

        # Chassis link
        canvas.draw_line(cab_x + cab_width, base_y, trailer_x, base_y, TRUCK_RED)

        # Wheels
        wheel_centers = [cab_x + 2, trailer_x + 6, trailer_x + 15]
        for wx in wheel_centers:
            for dy in range(2):
                for dx in range(2):
                    canvas.set_pixel(wx + dx, wheel_y + dy - 1, WHEEL_BLACK)

    def _render_frame(self, truck_x: int) -> Frame:
        """Render a single frame."""
        canvas = Canvas(WIDTH, HEIGHT)

        # Sky
        for y in range(HEIGHT):
            for x in range(WIDTH):
                canvas.set_pixel(x, y, SKY_BLUE)

        # Snow accumulation
        if self.snow_accumulation:
            for x in range(WIDTH):
                canvas.set_pixel(x, HEIGHT - 1, SNOW_WHITE)

        # Falling snow
        for x, y, _ in self._snowflakes:
            px, py = int(x), int(y)
            max_y = HEIGHT - 2 if self.snow_accumulation else HEIGHT - 1
            if 0 <= px < WIDTH and 0 <= py <= max_y:
                canvas.set_pixel(px, py, SNOW_WHITE)

        # Truck
        self._draw_truck(canvas, truck_x)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate animation frames."""
        self._init_snowflakes()

        trailer_offset = 8
        trailer_width = 20
        # Include a small overhang for the gift stack in front of the cab
        sprite_width = trailer_offset + trailer_width + 2

        truck_x = float(WIDTH)
        target_x = -sprite_width

        frame_delay = 1.0 / 30.0
        cycles_done = 0

        while cycles_done < self.repeats:
            frame = self._render_frame(int(truck_x))
            yield frame, frame_delay

            truck_x -= self.speed * frame_delay
            self._update_snowflakes(frame_delay)

            if truck_x <= target_x:
                cycles_done += 1
                truck_x = float(WIDTH)
