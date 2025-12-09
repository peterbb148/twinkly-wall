"""Pac-Man being chased by ghosts animation card."""

from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card
from .pacman import PACMAN_CLOSED, PACMAN_OPEN, SPRITE_GHOST, draw_sprite

# Pac-Man facing left (mouth on left side)
PACMAN_OPEN_LEFT: list[list[int]] = [
    [0, 0, 1, 1, 1, 0, 0],
    [0, 1, 1, 1, 1, 1, 0],
    [0, 0, 0, 1, 1, 1, 1],
    [0, 0, 0, 0, 1, 1, 1],
    [0, 0, 0, 1, 1, 1, 1],
    [0, 1, 1, 1, 1, 1, 0],
    [0, 0, 1, 1, 1, 0, 0],
]

PACMAN_CLOSED_LEFT: list[list[int]] = PACMAN_CLOSED  # Closed is symmetrical

PACMAN_COLOR: RGB = (255, 255, 0)  # Yellow
GHOST_RED: RGB = (255, 0, 0)
GHOST_PINK: RGB = (255, 184, 255)
GHOST_CYAN: RGB = (0, 255, 255)
GHOST_ORANGE: RGB = (255, 184, 82)


@register_card
class PacmanChaseCard(Card):
    """Pac-Man being chased by ghosts from right to left.

    Config options:
        num_ghosts: Number of ghosts chasing (1-4, default: 3)
        ghost_colors: List of RGB colors for ghosts (default: classic colors)
        speed: Pixels per second (default: 20)
        ghost_spacing: Pixels between ghosts (default: 12)
        animation_complete: Wait for animation to complete before ending (default: true)
    """

    card_type = "pacman_chase"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.num_ghosts: int = min(4, max(1, self.config.get("num_ghosts", 3)))
        self.speed: float = self.config.get("speed", 20.0)
        self.ghost_spacing: int = self.config.get("ghost_spacing", 12)
        self.repeats: int = self.config.get("repeats", 1)

        # Ghost colors - default to classic arcade colors (all variations of red)
        default_colors = [GHOST_RED, GHOST_PINK, GHOST_CYAN, GHOST_ORANGE]
        ghost_colors_config = self.config.get("ghost_colors")
        if ghost_colors_config:
            self.ghost_colors = [tuple(c) for c in ghost_colors_config]
        else:
            self.ghost_colors = default_colors[: self.num_ghosts]

    def _render_frame(
        self,
        pacman_x: float,
        ghost_positions: list[float],
        mouth_open: bool,
    ) -> Frame:
        """Render a single frame of the chase animation."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        # Draw Pac-Man (facing left, running away)
        pacman_sprite = PACMAN_OPEN_LEFT if mouth_open else PACMAN_CLOSED_LEFT
        pacman_color_map = {1: PACMAN_COLOR}
        draw_sprite(canvas, pacman_sprite, int(pacman_x), 1, pacman_color_map)

        # Draw ghosts chasing
        for i, gx in enumerate(ghost_positions):
            color = self.ghost_colors[i % len(self.ghost_colors)]
            ghost_color_map = {
                1: color,  # Ghost body
                2: (255, 255, 255),  # White eyes
            }
            draw_sprite(canvas, SPRITE_GHOST, int(gx), 1, ghost_color_map)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate chase animation frames."""
        # Start positions - Pac-Man on right, ghosts following from further right
        pacman_x = float(WIDTH)
        ghost_positions = [
            float(WIDTH + 10 + i * self.ghost_spacing) for i in range(self.num_ghosts)
        ]

        mouth_open = True
        mouth_timer = 0.0
        cycles_done = 0

        frame_delay = 1.0 / 30.0  # 30 FPS

        while cycles_done < self.repeats:
            # Render frame
            frame = self._render_frame(pacman_x, ghost_positions, mouth_open)
            yield frame, frame_delay

            # Move everything left
            movement = self.speed * frame_delay
            pacman_x -= movement
            ghost_positions = [gx - movement for gx in ghost_positions]

            # Loop when everything is off-screen left
            if ghost_positions[-1] < -10:
                cycles_done += 1
                if cycles_done < self.repeats:
                    pacman_x = float(WIDTH)
                    ghost_positions = [
                        float(WIDTH + 10 + i * self.ghost_spacing)
                        for i in range(self.num_ghosts)
                    ]

            # Animate mouth (toggle every 0.12s - faster when running!)
            mouth_timer += frame_delay
            if mouth_timer >= 0.12:
                mouth_open = not mouth_open
                mouth_timer = 0.0
