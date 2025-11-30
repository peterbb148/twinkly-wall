"""Starfield warp speed animation card."""

import random
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from ..canvas import Canvas
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card


@dataclass
class Star:
    """A star in the starfield."""

    x: float  # -1 to 1 from center
    y: float  # -1 to 1 from center
    z: float  # Depth (0 = far, 1 = close)


@register_card
class StarfieldCard(Card):
    """Starfield warp speed effect.

    Config options:
        num_stars: Number of stars (default: 50)
        speed: Warp speed multiplier (default: 1.0)
        streak: Enable star streaking (default: true)
    """

    card_type = "starfield"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.num_stars: int = self.config.get("num_stars", 50)
        self.speed: float = self.config.get("speed", 1.0)
        self.streak: bool = self.config.get("streak", True)

    def _create_star(self, far: bool = True) -> Star:
        """Create a new star."""
        return Star(
            x=random.uniform(-1, 1),
            y=random.uniform(-1, 1),
            z=random.uniform(0.8, 1.0) if far else random.uniform(0, 1),
        )

    def _project_star(self, star: Star) -> tuple[int, int, float] | None:
        """Project 3D star position to 2D screen coordinates."""
        if star.z <= 0.01:
            return None

        # Perspective projection
        scale = 1.0 / star.z
        screen_x = int(WIDTH / 2 + star.x * scale * WIDTH / 2)
        screen_y = int(HEIGHT / 2 + star.y * scale * HEIGHT / 2)

        if 0 <= screen_x < WIDTH and 0 <= screen_y < HEIGHT:
            return (screen_x, screen_y, star.z)

        return None

    def _render_frame(self, stars: list[Star], prev_positions: dict) -> Frame:
        """Render the starfield."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        for i, star in enumerate(stars):
            pos = self._project_star(star)
            if pos:
                x, y, z = pos

                # Brightness based on depth (closer = brighter)
                brightness = int(255 * (1 - z))
                brightness = max(50, min(255, brightness))

                # Size based on depth
                color: RGB = (brightness, brightness, brightness)

                canvas.set_pixel(x, y, color)

                # Draw streak if enabled and star has previous position
                if self.streak and i in prev_positions:
                    px, py = prev_positions[i]
                    # Simple line from previous to current
                    streak_color = (brightness // 3, brightness // 3, brightness // 3)
                    if abs(x - px) <= 3 and abs(y - py) <= 3:
                        # Draw intermediate points
                        steps = max(abs(x - px), abs(y - py))
                        if steps > 0:
                            for step in range(1, steps):
                                sx = px + (x - px) * step // steps
                                sy = py + (y - py) * step // steps
                                if 0 <= sx < WIDTH and 0 <= sy < HEIGHT:
                                    canvas.set_pixel(sx, sy, streak_color)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate starfield animation frames."""
        stars = [self._create_star(far=False) for _ in range(self.num_stars)]
        prev_positions: dict[int, tuple[int, int]] = {}

        start_time = time.time()
        frame_delay = 1.0 / 30.0

        while time.time() - start_time < self.duration:
            # Store current positions for streaking
            new_prev: dict[int, tuple[int, int]] = {}
            for i, star in enumerate(stars):
                pos = self._project_star(star)
                if pos:
                    new_prev[i] = (pos[0], pos[1])

            # Update stars (move toward viewer)
            for i, star in enumerate(stars):
                star.z -= 0.02 * self.speed

                # Reset star if it passes the viewer
                if star.z <= 0.01:
                    stars[i] = self._create_star(far=True)
                    if i in prev_positions:
                        del prev_positions[i]

            frame = self._render_frame(stars, prev_positions)
            prev_positions = new_prev
            yield frame, frame_delay
