"""Tetris game animation card."""

import random
import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card

# Tetris pieces (rotations not implemented for simplicity)
PIECES = [
    # I piece
    {"shape": [(0, 0), (1, 0), (2, 0), (3, 0)], "color": (0, 255, 255)},
    # O piece
    {"shape": [(0, 0), (1, 0), (0, 1), (1, 1)], "color": (255, 255, 0)},
    # T piece
    {"shape": [(0, 0), (1, 0), (2, 0), (1, 1)], "color": (128, 0, 128)},
    # L piece
    {"shape": [(0, 0), (0, 1), (0, 2), (1, 2)], "color": (255, 165, 0)},
    # J piece
    {"shape": [(1, 0), (1, 1), (1, 2), (0, 2)], "color": (0, 0, 255)},
    # S piece
    {"shape": [(1, 0), (2, 0), (0, 1), (1, 1)], "color": (0, 255, 0)},
    # Z piece
    {"shape": [(0, 0), (1, 0), (1, 1), (2, 1)], "color": (255, 0, 0)},
]


@register_card
class TetrisCard(Card):
    """Tetris game animation.

    Config options:
        speed: Game speed multiplier (default: 1.0)
        well_width: Width of the playing well (default: 10)
    """

    card_type = "tetris"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.speed: float = self.config.get("speed", 1.0)
        self.well_width: int = self.config.get("well_width", 10)

    def _spawn_piece(self) -> dict:
        """Spawn a new random piece."""
        piece = random.choice(PIECES)
        return {
            "shape": piece["shape"].copy(),
            "color": piece["color"],
            "x": random.randint(0, self.well_width - 4),
            "y": 0,
        }

    def _can_move(
        self, piece: dict, grid: list[list[RGB | None]], dx: int, dy: int
    ) -> bool:
        """Check if piece can move in direction."""
        for bx, by in piece["shape"]:
            new_x = piece["x"] + bx + dx
            new_y = piece["y"] + by + dy

            if new_x < 0 or new_x >= self.well_width:
                return False
            if new_y >= HEIGHT:
                return False
            if new_y >= 0 and grid[new_y][new_x] is not None:
                return False

        return True

    def _place_piece(self, piece: dict, grid: list[list[RGB | None]]) -> None:
        """Place piece on the grid."""
        for bx, by in piece["shape"]:
            x = piece["x"] + bx
            y = piece["y"] + by
            if 0 <= y < HEIGHT and 0 <= x < self.well_width:
                grid[y][x] = piece["color"]

    def _clear_lines(self, grid: list[list[RGB | None]]) -> int:
        """Clear completed lines and return count."""
        lines_cleared = 0
        y = HEIGHT - 1

        while y >= 0:
            if all(grid[y][x] is not None for x in range(self.well_width)):
                # Clear this line
                lines_cleared += 1
                # Move everything down
                for move_y in range(y, 0, -1):
                    grid[move_y] = grid[move_y - 1].copy()
                grid[0] = [None] * self.well_width
            else:
                y -= 1

        return lines_cleared

    def _render_frame(
        self, grid: list[list[RGB | None]], piece: dict | None, well_offset: int
    ) -> Frame:
        """Render the current game state."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        # Draw well borders
        border_color = (50, 50, 50)
        for y in range(HEIGHT):
            if well_offset > 0:
                canvas.set_pixel(well_offset - 1, y, border_color)
            if well_offset + self.well_width < WIDTH:
                canvas.set_pixel(well_offset + self.well_width, y, border_color)

        # Draw grid
        for y in range(HEIGHT):
            for x in range(self.well_width):
                if grid[y][x] is not None:
                    canvas.set_pixel(well_offset + x, y, grid[y][x])

        # Draw current piece
        if piece:
            for bx, by in piece["shape"]:
                px = well_offset + piece["x"] + bx
                py = piece["y"] + by
                if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                    canvas.set_pixel(px, py, piece["color"])

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate Tetris animation frames."""
        # Center the well
        well_offset = (WIDTH - self.well_width) // 2

        # Initialize grid
        grid: list[list[RGB | None]] = [
            [None] * self.well_width for _ in range(HEIGHT)
        ]

        current_piece = self._spawn_piece()
        drop_timer = 0.0
        drop_interval = 0.5 / self.speed
        move_timer = 0.0
        move_interval = 0.1

        start_time = time.time()
        frame_delay = 1.0 / 30.0

        while time.time() - start_time < self.duration:
            drop_timer += frame_delay
            move_timer += frame_delay

            # Random horizontal movement
            if move_timer >= move_interval:
                move_timer = 0
                if random.random() < 0.5:
                    dx = random.choice([-1, 0, 0, 1])  # Bias towards staying
                    if self._can_move(current_piece, grid, dx, 0):
                        current_piece["x"] += dx

            # Drop piece
            if drop_timer >= drop_interval:
                drop_timer = 0

                if self._can_move(current_piece, grid, 0, 1):
                    current_piece["y"] += 1
                else:
                    # Place piece
                    self._place_piece(current_piece, grid)
                    self._clear_lines(grid)

                    # Spawn new piece
                    current_piece = self._spawn_piece()

                    # Check game over
                    if not self._can_move(current_piece, grid, 0, 0):
                        # Clear grid and restart
                        grid = [[None] * self.well_width for _ in range(HEIGHT)]

            frame = self._render_frame(grid, current_piece, well_offset)
            yield frame, frame_delay
