"""Diagonal meteor shower / starfall effect."""

import random
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from ..canvas import Canvas
from ..types import BLACK, PORTRAIT_HEIGHT, PORTRAIT_WIDTH, RGB, Frame
from .base import Card, CardContext, register_card


@dataclass
class Meteor:
    """Single meteor streak."""

    x: float
    y: float
    speed_x: float
    speed_y: float
    length: int


@register_card
class MeteorShowerCard(Card):
    """Diagonal meteor shower across the panel.

    Config options:
        density: Number of simultaneous meteors (default: 6)
        speed: Base speed factor (default: 12.0)
        length: Base trail length in pixels (default: 5)
    """

    card_type = "meteor_shower"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.density: int = int(self.config.get("density", 6))
        self.speed: float = float(self.config.get("speed", 12.0))
        self.base_length: int = int(self.config.get("length", 5))

    def _new_meteor(self) -> Meteor:
        """Create a new meteor entering from top or left edge."""
        if random.random() < 0.5:
            # From top
            x = random.uniform(0, PORTRAIT_WIDTH - 1)
            y = -1.0
        else:
            # From left
            x = -1.0
            y = random.uniform(0, PORTRAIT_HEIGHT - 1)

        speed_x = self.speed * random.uniform(0.7, 1.3)
        speed_y = self.speed * random.uniform(0.5, 1.0)
        length = max(3, int(self.base_length * random.uniform(0.7, 1.3)))
        return Meteor(x=x, y=y, speed_x=speed_x, speed_y=speed_y, length=length)

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate meteor shower frames."""
        frame_delay = 1.0 / 30.0
        start = time.time()

        meteors: list[Meteor] = [self._new_meteor() for _ in range(self.density)]

        while time.time() - start < self.duration:
            canvas = Canvas(PORTRAIT_WIDTH, PORTRAIT_HEIGHT)
            canvas.clear(BLACK)

            # Draw and update meteors
            new_meteors: list[Meteor] = []
            for meteor in meteors:
                # Draw trail (bright head, dimmer tail)
                for i in range(meteor.length):
                    fx = meteor.x - meteor.speed_x * frame_delay * i
                    fy = meteor.y - meteor.speed_y * frame_delay * i
                    ix, iy = int(fx), int(fy)
                    if 0 <= ix < PORTRAIT_WIDTH and 0 <= iy < PORTRAIT_HEIGHT:
                        brightness = max(0.2, 1.0 - i / meteor.length)
                        color: RGB = (
                            int(255 * brightness),
                            int(255 * brightness),
                            int(255 * (0.6 + 0.4 * brightness)),
                        )
                        canvas.set_pixel(ix, iy, color)

                # Update head
                meteor.x += meteor.speed_x * frame_delay
                meteor.y += meteor.speed_y * frame_delay

                if (
                    meteor.x > PORTRAIT_WIDTH + meteor.length
                    or meteor.y > PORTRAIT_HEIGHT + meteor.length
                ):
                    meteor = self._new_meteor()

                new_meteors.append(meteor)

            meteors = new_meteors

            yield canvas.copy(), frame_delay
