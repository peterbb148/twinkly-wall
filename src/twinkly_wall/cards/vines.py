"""Growing vines / ivy effect for vertical layouts."""

import random
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from ..canvas import Canvas
from ..types import BLACK, PORTRAIT_HEIGHT, PORTRAIT_WIDTH, RGB, Frame
from .base import Card, CardContext, register_card

VINE_GREEN: RGB = (0, 160, 80)
LEAF_GREEN: RGB = (0, 200, 120)


@dataclass
class Vine:
    """A single vine segment growing upward."""

    x: int
    y: int
    age: float
    speed: float


@register_card
class VinesCard(Card):
    """Simple ivy / vine growth animation.

    Vines grow upward from the bottom, occasionally sprouting leaves.

    Config options:
        count: Number of vines (default: 4)
        speed: Growth speed factor (default: 1.0)
    """

    card_type = "vines"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.count: int = int(self.config.get("count", 4))
        self.speed: float = float(self.config.get("speed", 1.0))

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate vine growth frames."""
        frame_delay = 1.0 / 15.0
        start = time.time()

        vines: list[Vine] = []
        for _ in range(self.count):
            x = random.randint(1, PORTRAIT_WIDTH - 2)
            vines.append(Vine(x=x, y=PORTRAIT_HEIGHT - 1, age=0.0, speed=self.speed))

        while time.time() - start < self.duration:
            canvas = Canvas(PORTRAIT_WIDTH, PORTRAIT_HEIGHT)
            canvas.clear(BLACK)

            # Draw and update vines
            for vine in vines:
                # Draw the vine up to its current y
                for y in range(vine.y, PORTRAIT_HEIGHT):
                    canvas.set_pixel(vine.x, y, VINE_GREEN)

                # Random leaves
                if random.random() < 0.2:
                    side = random.choice([-1, 1])
                    lx = max(0, min(PORTRAIT_WIDTH - 1, vine.x + side))
                    ly = min(PORTRAIT_HEIGHT - 1, vine.y + random.randint(-1, 1))
                    canvas.set_pixel(lx, ly, LEAF_GREEN)

                # Grow upward
                vine.age += frame_delay * vine.speed
                if vine.y > 0 and vine.age > 0.5:
                    vine.y -= 1
                    vine.age = 0.0

            yield canvas.copy(), frame_delay
