"""Matrix digital rain animation card."""

import random
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from ..canvas import Canvas
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card

# Matrix green shades
MATRIX_BRIGHT: RGB = (150, 255, 150)
MATRIX_MEDIUM: RGB = (0, 200, 0)
MATRIX_DIM: RGB = (0, 100, 0)
MATRIX_DARK: RGB = (0, 50, 0)


@dataclass
class MatrixDrop:
    """A falling column of characters."""

    x: int
    y: float
    speed: float
    length: int
    chars: list[int]  # Random character codes


@register_card
class MatrixCard(Card):
    """Matrix-style digital rain effect.

    Config options:
        density: Number of drops (default: 15)
        speed: Fall speed multiplier (default: 1.0)
        color: Base color RGB (default: green)
    """

    card_type = "matrix"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.density: int = self.config.get("density", 15)
        self.speed: float = self.config.get("speed", 1.0)
        base_color = self.config.get("color", [0, 255, 0])
        self.base_color: RGB = tuple(base_color)  # type: ignore

    def _create_drop(self, start_y: float | None = None) -> MatrixDrop:
        """Create a new matrix drop."""
        length = random.randint(3, HEIGHT)
        return MatrixDrop(
            x=random.randint(0, WIDTH - 1),
            y=start_y if start_y is not None else random.uniform(-HEIGHT, 0),
            speed=random.uniform(0.2, 0.5) * self.speed,
            length=length,
            chars=[random.randint(0, 9) for _ in range(length)],
        )

    def _render_frame(self, drops: list[MatrixDrop]) -> Frame:
        """Render the matrix rain."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        for drop in drops:
            head_y = int(drop.y)

            for i in range(drop.length):
                char_y = head_y - i
                if 0 <= char_y < HEIGHT:
                    # Calculate brightness based on position in drop
                    if i == 0:
                        # Head is brightest (white-ish)
                        color = (
                            min(255, self.base_color[0] + 100),
                            min(255, self.base_color[1] + 100),
                            min(255, self.base_color[2] + 100),
                        )
                    elif i < drop.length // 3:
                        # Near head - bright
                        color = self.base_color
                    elif i < 2 * drop.length // 3:
                        # Middle - medium
                        color = (
                            self.base_color[0] // 2,
                            self.base_color[1] // 2,
                            self.base_color[2] // 2,
                        )
                    else:
                        # Tail - dim
                        color = (
                            self.base_color[0] // 4,
                            self.base_color[1] // 4,
                            self.base_color[2] // 4,
                        )

                    canvas.set_pixel(drop.x, char_y, color)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate matrix rain animation frames."""
        # Initialize drops
        drops = [self._create_drop(random.uniform(-HEIGHT, HEIGHT)) for _ in range(self.density)]

        start_time = time.time()
        frame_delay = 1.0 / 30.0

        while time.time() - start_time < self.duration:
            # Update drops
            for drop in drops:
                drop.y += drop.speed

                # Randomly change characters
                if random.random() < 0.1:
                    idx = random.randint(0, len(drop.chars) - 1)
                    drop.chars[idx] = random.randint(0, 9)

            # Reset drops that have fallen off screen
            for i, drop in enumerate(drops):
                if drop.y - drop.length > HEIGHT:
                    drops[i] = self._create_drop(-random.randint(1, 5))

            frame = self._render_frame(drops)
            yield frame, frame_delay
