"""Barley field animation card - golden barley swaying in the wind."""

import math
import random
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from ..canvas import Canvas
from ..types import HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card

# Colors for barley field
SKY_BLUE: RGB = (135, 180, 220)
BARLEY_GOLD: RGB = (218, 165, 32)  # Golden wheat color
BARLEY_LIGHT: RGB = (240, 200, 80)  # Lighter gold for highlights
BARLEY_DARK: RGB = (180, 130, 20)  # Darker gold for depth
STEM_GREEN: RGB = (120, 140, 60)  # Greenish stem
AWN_COLOR: RGB = (200, 170, 100)  # Barley awns (whiskers)


@dataclass
class BarleyStalk:
    """A single barley stalk."""

    x: int  # Base x position
    height: int  # Stalk height
    phase: float  # Animation phase offset
    color: RGB  # Head color


@register_card
class BarleyFieldCard(Card):
    """Golden barley field swaying in the wind.

    Config options:
        num_stalks: Number of barley stalks (default: 20)
        wind_speed: Wind animation speed (default: 1.0)
        wind_strength: How much stalks sway (default: 2.0)
        sky_visible: Show sky at top (default: true)
    """

    card_type = "barley_field"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.num_stalks: int = self.config.get("num_stalks", 20)
        self.wind_speed: float = self.config.get("wind_speed", 1.0)
        self.wind_strength: float = self.config.get("wind_strength", 2.0)
        self.sky_visible: bool = self.config.get("sky_visible", True)
        self.repeats: int = self.config.get("repeats", 1)  # Wind cycles
        self._stalks: list[BarleyStalk] = []

    def _init_stalks(self) -> None:
        """Initialize barley stalks at random positions."""
        self._stalks = []
        colors = [BARLEY_GOLD, BARLEY_LIGHT, BARLEY_DARK]

        for i in range(self.num_stalks):
            x = int((i / self.num_stalks) * WIDTH) + random.randint(-1, 1)
            x = max(0, min(WIDTH - 1, x))

            self._stalks.append(
                BarleyStalk(
                    x=x,
                    height=random.randint(5, 8),
                    phase=random.uniform(0, 2 * math.pi),
                    color=random.choice(colors),
                )
            )

        # Sort by x position for proper layering
        self._stalks.sort(key=lambda s: s.x)

    def _draw_stalk(self, canvas: Canvas, stalk: BarleyStalk, wind_offset: float) -> None:
        """Draw a single barley stalk with wind sway."""
        # Calculate sway based on wind
        sway = math.sin(wind_offset + stalk.phase) * self.wind_strength

        base_y = HEIGHT - 1
        top_y = base_y - stalk.height

        # Draw stem (slightly curved due to wind)
        for y in range(base_y, top_y, -1):
            # Progressive sway - more at top
            progress = (base_y - y) / stalk.height
            x_offset = int(sway * progress * progress)
            px = stalk.x + x_offset

            if 0 <= px < WIDTH:
                # Stem color - greener at bottom, golden at top
                if progress < 0.3:
                    canvas.set_pixel(px, y, STEM_GREEN)
                else:
                    canvas.set_pixel(px, y, stalk.color)

        # Draw barley head (the grain part with awns)
        head_x = stalk.x + int(sway)
        head_y = top_y

        if 0 <= head_x < WIDTH and 0 <= head_y < HEIGHT:
            # Main head
            canvas.set_pixel(head_x, head_y, stalk.color)

            # Awns (whiskers) extending from head
            if head_y > 0:
                # Awn going up-left
                awn_x = head_x - 1 + int(sway * 0.3)
                if 0 <= awn_x < WIDTH:
                    canvas.set_pixel(awn_x, head_y - 1, AWN_COLOR)

                # Awn going up-right
                awn_x = head_x + 1 + int(sway * 0.3)
                if 0 <= awn_x < WIDTH:
                    canvas.set_pixel(awn_x, head_y - 1, AWN_COLOR)

    def _render_frame(self, t: float) -> Frame:
        """Render a single frame."""
        canvas = Canvas(WIDTH, HEIGHT)

        # Draw sky gradient at top
        if self.sky_visible:
            for y in range(3):
                # Gradient from lighter to darker blue
                brightness = 1.0 - (y * 0.1)
                color = (
                    int(SKY_BLUE[0] * brightness),
                    int(SKY_BLUE[1] * brightness),
                    int(SKY_BLUE[2] * brightness),
                )
                for x in range(WIDTH):
                    canvas.set_pixel(x, y, color)

        # Calculate wind offset
        wind_offset = t * self.wind_speed * 3

        # Draw all stalks
        for stalk in self._stalks:
            self._draw_stalk(canvas, stalk, wind_offset)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate animation frames."""
        self._init_stalks()

        frame_delay = 1.0 / 30.0
        t = 0.0

        # One cycle = 2*pi / wind_speed seconds
        cycle_duration = (2 * math.pi) / (self.wind_speed * 3)
        cycles_done = 0

        while cycles_done < self.repeats:
            frame = self._render_frame(t)
            yield frame, frame_delay

            t += frame_delay

            # Check if we completed a wind cycle
            if t >= cycle_duration * (cycles_done + 1):
                cycles_done += 1
