"""Pac-Man being chased by ghosts animation card."""

from collections.abc import Iterator
from typing import Any, Literal

from ..canvas import Canvas
from ..types import PORTRAIT_HEIGHT, PORTRAIT_WIDTH, RGB, WIDTH, Frame
from .base import Card, CardContext, CardLayout, register_card
from .pacman import PACMAN_CLOSED, PACMAN_OPEN_DOWN, PACMAN_OPEN_UP, SPRITE_GHOST, draw_sprite

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
    """Pac-Man being chased by ghosts along the display's long axis.

    Config options:
        num_ghosts: Number of ghosts chasing (1-4, default: 3)
        ghost_colors: List of RGB colors for ghosts (default: classic colors)
        speed: Pixels per second (default: 20)
        ghost_spacing: Pixels between ghosts (default: 12)
        repeats: Number of complete chases (default: 1)
    """

    card_type = "pacman_chase"
    portrait_direction: Literal["up", "down"] | None = None
    open_sprite = PACMAN_OPEN_LEFT

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

    def _sprite_position(self, position: float, sprite: list[list[int]]) -> tuple[int, int]:
        """Place the sprite along the chase axis in viewer coordinates."""
        along_axis = int(position)
        if self.portrait_direction is None:
            return along_axis, 1

        x = (PORTRAIT_WIDTH - len(sprite[0])) // 2
        if self.portrait_direction == "down":
            along_axis = PORTRAIT_HEIGHT - len(sprite) - along_axis
        return x, along_axis

    def _render_frame(
        self,
        pacman_position: float,
        ghost_positions: list[float],
        mouth_open: bool,
    ) -> Frame:
        """Render a single frame of the chase animation."""
        canvas = Canvas(PORTRAIT_WIDTH, PORTRAIT_HEIGHT) if self.portrait_direction else Canvas()

        pacman_sprite = self.open_sprite if mouth_open else PACMAN_CLOSED_LEFT
        pacman_color_map = {1: PACMAN_COLOR}
        x, y = self._sprite_position(pacman_position, pacman_sprite)
        draw_sprite(canvas, pacman_sprite, x, y, pacman_color_map)

        # Draw ghosts chasing
        for i, position in enumerate(ghost_positions):
            color = self.ghost_colors[i % len(self.ghost_colors)]
            ghost_color_map = {
                1: color,  # Ghost body
                2: (255, 255, 255),  # White eyes
            }
            x, y = self._sprite_position(position, SPRITE_GHOST)
            draw_sprite(canvas, SPRITE_GHOST, x, y, ghost_color_map)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate chase animation frames."""
        track_length = PORTRAIT_HEIGHT if self.portrait_direction else WIDTH
        pacman_position = float(track_length)
        ghost_starts = [
            float(track_length + 10 + i * self.ghost_spacing) for i in range(self.num_ghosts)
        ]
        ghost_positions = ghost_starts

        mouth_open = True
        mouth_timer = 0.0
        cycles_done = 0

        frame_delay = 1.0 / 30.0  # 30 FPS

        while cycles_done < self.repeats:
            # Render frame
            frame = self._render_frame(pacman_position, ghost_positions, mouth_open)
            yield frame, frame_delay

            # Each direction uses the same descending chase coordinate.
            movement = self.speed * frame_delay
            pacman_position -= movement
            ghost_positions = [position - movement for position in ghost_positions]

            # Restart after the last ghost exits.
            if ghost_positions[-1] < -10:
                cycles_done += 1
                if cycles_done < self.repeats:
                    pacman_position = float(track_length)
                    ghost_positions = ghost_starts

            # Animate mouth (toggle every 0.12s - faster when running!)
            mouth_timer += frame_delay
            if mouth_timer >= 0.12:
                mouth_open = not mouth_open
                mouth_timer = 0.0


@register_card
class PacmanChaseUpCard(PacmanChaseCard):
    """Chase from the bottom to the top of a portrait wall."""

    card_type = "pacman_chase_up"
    layout = CardLayout.portrait
    portrait_direction = "up"
    open_sprite = PACMAN_OPEN_UP


@register_card
class PacmanChaseDownCard(PacmanChaseCard):
    """Chase from the top to the bottom of a portrait wall."""

    card_type = "pacman_chase_down"
    layout = CardLayout.portrait
    portrait_direction = "down"
    open_sprite = PACMAN_OPEN_DOWN
