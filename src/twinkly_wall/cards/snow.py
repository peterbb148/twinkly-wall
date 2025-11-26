"""Snowfall animation card."""

import random
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from ..canvas import Canvas
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card

# Snow colors
SNOW_WHITE: RGB = (255, 255, 255)
SNOW_LIGHT: RGB = (200, 220, 255)  # Slight blue tint


@dataclass
class Snowflake:
    """A single falling snowflake."""

    x: float
    y: float
    speed: float
    drift: float  # Horizontal drift direction
    brightness: float  # 0.5 to 1.0


@register_card
class SnowCard(Card):
    """Snowfall animation.

    Config options:
        density: Number of snowflakes (default: 15)
        speed: Base fall speed (default: 4.0)
        drift: Horizontal drift amount (default: 0.5)
        wind: Constant wind direction -1 to 1 (default: 0)
        accumulate: Show snow accumulation at bottom (default: False)
    """

    card_type = "snow"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.density: int = self.config.get("density", 15)
        self.speed: float = self.config.get("speed", 4.0)
        self.drift: float = self.config.get("drift", 0.5)
        self.wind: float = self.config.get("wind", 0.0)
        self.accumulate: bool = self.config.get("accumulate", False)

    def _create_snowflake(self, at_top: bool = True) -> Snowflake:
        """Create a new snowflake."""
        return Snowflake(
            x=random.uniform(0, WIDTH - 1),
            y=0.0 if at_top else random.uniform(0, HEIGHT - 1),
            speed=self.speed * random.uniform(0.6, 1.4),
            drift=random.uniform(-1, 1),
            brightness=random.uniform(0.5, 1.0),
        )

    def _get_snow_color(self, brightness: float) -> RGB:
        """Get snowflake color based on brightness."""
        r = int(200 + 55 * brightness)
        g = int(220 + 35 * brightness)
        b = 255
        return (r, g, b)

    def _render_frame(self, snowflakes: list[Snowflake], accumulation: list[int]) -> Frame:
        """Render a single frame of the animation."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        # Draw accumulation at bottom
        if self.accumulate:
            for x, height in enumerate(accumulation):
                for y in range(HEIGHT - height, HEIGHT):
                    # Slight variation in snow pile color
                    if (x + y) % 3 == 0:
                        canvas.set_pixel(x, y, SNOW_LIGHT)
                    else:
                        canvas.set_pixel(x, y, SNOW_WHITE)

        # Draw snowflakes
        for flake in snowflakes:
            fx = int(flake.x)
            fy = int(flake.y)
            if 0 <= fx < WIDTH and 0 <= fy < HEIGHT:
                color = self._get_snow_color(flake.brightness)
                canvas.set_pixel(fx, fy, color)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate snowfall animation frames."""
        # Initialize snowflakes at random positions
        snowflakes: list[Snowflake] = [
            self._create_snowflake(at_top=False) for _ in range(self.density)
        ]

        # Accumulation heights per column
        accumulation: list[int] = [0] * WIDTH
        max_accumulation = 2  # Max snow pile height

        start_time = time.time()
        frame_delay = 1.0 / 30.0  # 30 FPS

        while time.time() - start_time < self.duration:
            # Update snowflakes
            for flake in snowflakes:
                # Fall down
                flake.y += flake.speed * frame_delay

                # Horizontal drift + wind
                drift_amount = (flake.drift * self.drift + self.wind) * frame_delay
                flake.x += drift_amount

                # Wrap horizontally
                if flake.x < 0:
                    flake.x = WIDTH - 1
                elif flake.x >= WIDTH:
                    flake.x = 0

                # Check if reached bottom or accumulation
                bottom_limit = HEIGHT - 1
                if self.accumulate:
                    col = int(flake.x)
                    if 0 <= col < WIDTH:
                        bottom_limit = HEIGHT - 1 - accumulation[col]

                if flake.y >= bottom_limit:
                    # Add to accumulation
                    if self.accumulate:
                        col = int(flake.x)
                        if 0 <= col < WIDTH and accumulation[col] < max_accumulation:
                            # Random chance to accumulate
                            if random.random() < 0.1:
                                accumulation[col] += 1

                    # Reset snowflake at top
                    flake.x = random.uniform(0, WIDTH - 1)
                    flake.y = 0.0
                    flake.speed = self.speed * random.uniform(0.6, 1.4)
                    flake.drift = random.uniform(-1, 1)
                    flake.brightness = random.uniform(0.5, 1.0)

            # Render
            frame = self._render_frame(snowflakes, accumulation)
            yield frame, frame_delay
