"""Confetti falling animation card."""

import random
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from ..canvas import Canvas
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card


@dataclass
class ConfettiPiece:
    """A single piece of confetti."""

    x: float
    y: float
    vy: float
    vx: float
    color: RGB
    wobble_phase: float
    wobble_speed: float


CONFETTI_COLORS: list[RGB] = [
    (255, 0, 0),      # Red
    (0, 255, 0),      # Green
    (0, 100, 255),    # Blue
    (255, 255, 0),    # Yellow
    (255, 0, 255),    # Magenta
    (0, 255, 255),    # Cyan
    (255, 128, 0),    # Orange
    (255, 192, 203),  # Pink
    (255, 215, 0),    # Gold
]


@register_card
class ConfettiCard(Card):
    """Falling confetti celebration animation.

    Config options:
        density: Number of confetti pieces (default: 25)
        speed: Fall speed multiplier (default: 1.0)
        wind: Horizontal wind (-1 to 1, default: 0)
    """

    card_type = "confetti"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.density: int = self.config.get("density", 25)
        self.speed: float = self.config.get("speed", 1.0)
        self.wind: float = self.config.get("wind", 0.0)

    def _create_piece(self, start_y: float | None = None) -> ConfettiPiece:
        """Create a new confetti piece."""
        return ConfettiPiece(
            x=random.uniform(0, WIDTH),
            y=start_y if start_y is not None else random.uniform(-HEIGHT, 0),
            vy=random.uniform(0.3, 0.8) * self.speed,
            vx=random.uniform(-0.2, 0.2) + self.wind * 0.3,
            color=random.choice(CONFETTI_COLORS),
            wobble_phase=random.uniform(0, 6.28),
            wobble_speed=random.uniform(0.1, 0.3),
        )

    def _render_frame(self, pieces: list[ConfettiPiece]) -> Frame:
        """Render current confetti state."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        for piece in pieces:
            px = int(piece.x)
            py = int(piece.y)
            if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                canvas.set_pixel(px, py, piece.color)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate confetti animation frames."""
        # Initialize confetti spread across the screen
        pieces = [self._create_piece(random.uniform(-2, HEIGHT)) for _ in range(self.density)]

        start_time = time.time()
        frame_delay = 1.0 / 30.0
        time_elapsed = 0.0

        while time.time() - start_time < self.duration:
            # Update pieces
            for piece in pieces:
                piece.y += piece.vy
                piece.wobble_phase += piece.wobble_speed
                piece.x += piece.vx + 0.3 * random.uniform(-0.5, 0.5)

                # Wrap horizontally
                if piece.x < 0:
                    piece.x = WIDTH - 1
                elif piece.x >= WIDTH:
                    piece.x = 0

                # Reset at bottom
                if piece.y >= HEIGHT:
                    piece.y = -1
                    piece.x = random.uniform(0, WIDTH)
                    piece.color = random.choice(CONFETTI_COLORS)

            frame = self._render_frame(pieces)
            yield frame, frame_delay
            time_elapsed += frame_delay
