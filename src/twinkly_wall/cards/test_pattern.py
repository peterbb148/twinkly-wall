"""Test pattern card for debugging LED layout."""

import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..types import HEIGHT, WIDTH, Frame
from .base import Card, CardContext, register_card


@register_card
class TestPatternCard(Card):
    """Test pattern for debugging LED wiring layout.

    Config options:
        mode: Pattern mode - rows, cols, corners, gradient, numbers (default: rows)
    """

    card_type = "test_pattern"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.mode: str = self.config.get("mode", "rows")

    def _render_rows(self) -> Frame:
        """Each row a different color."""
        canvas = Canvas(WIDTH, HEIGHT)
        colors = [
            (255, 0, 0),      # Row 0: Red
            (255, 128, 0),    # Row 1: Orange
            (255, 255, 0),    # Row 2: Yellow
            (128, 255, 0),    # Row 3: Lime
            (0, 255, 0),      # Row 4: Green
            (0, 255, 255),    # Row 5: Cyan
            (0, 128, 255),    # Row 6: Light Blue
            (0, 0, 255),      # Row 7: Blue
            (128, 0, 255),    # Row 8: Purple
            (255, 0, 255),    # Row 9: Magenta
        ]
        for y in range(HEIGHT):
            color = colors[y % len(colors)]
            for x in range(WIDTH):
                canvas.set_pixel(x, y, color)
        return canvas.copy()

    def _render_cols(self) -> Frame:
        """Columns with gradient."""
        canvas = Canvas(WIDTH, HEIGHT)
        for x in range(WIDTH):
            # Gradient from red to blue across width
            r = int(255 * (1 - x / WIDTH))
            b = int(255 * (x / WIDTH))
            for y in range(HEIGHT):
                canvas.set_pixel(x, y, (r, 0, b))
        return canvas.copy()

    def _render_corners(self) -> Frame:
        """Mark the four corners with different colors."""
        canvas = Canvas(WIDTH, HEIGHT)
        # Fill with dim white
        for y in range(HEIGHT):
            for x in range(WIDTH):
                canvas.set_pixel(x, y, (20, 20, 20))

        # Top-left: Red
        for y in range(3):
            for x in range(5):
                canvas.set_pixel(x, y, (255, 0, 0))

        # Top-right: Green
        for y in range(3):
            for x in range(WIDTH - 5, WIDTH):
                canvas.set_pixel(x, y, (0, 255, 0))

        # Bottom-left: Blue
        for y in range(HEIGHT - 3, HEIGHT):
            for x in range(5):
                canvas.set_pixel(x, y, (0, 0, 255))

        # Bottom-right: Yellow
        for y in range(HEIGHT - 3, HEIGHT):
            for x in range(WIDTH - 5, WIDTH):
                canvas.set_pixel(x, y, (255, 255, 0))

        return canvas.copy()

    def _render_gradient(self) -> Frame:
        """Diagonal gradient."""
        canvas = Canvas(WIDTH, HEIGHT)
        for y in range(HEIGHT):
            for x in range(WIDTH):
                r = int(255 * x / WIDTH)
                g = int(255 * y / HEIGHT)
                b = 128
                canvas.set_pixel(x, y, (r, g, b))
        return canvas.copy()

    def _render_numbers(self) -> Frame:
        """Show row numbers."""
        from ..fonts import draw_text
        canvas = Canvas(WIDTH, HEIGHT)
        # Draw row numbers on left side
        for y in range(HEIGHT):
            color = (255, 255, 255) if y < 5 else (255, 255, 0)
            draw_text(canvas, 0, y, str(y), color)
        return canvas.copy()

    def _render_single_row(self, row: int) -> Frame:
        """Light up a single row."""
        canvas = Canvas(WIDTH, HEIGHT)
        for x in range(WIDTH):
            canvas.set_pixel(x, row, (255, 255, 255))
        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate test pattern frames."""
        start_time = time.time()

        if self.mode == "rows":
            # Show each row one at a time
            while time.time() - start_time < self.duration:
                for row in range(HEIGHT):
                    if time.time() - start_time >= self.duration:
                        break
                    yield self._render_single_row(row), 1.0
        elif self.mode == "all_rows":
            # Show all rows with different colors
            frame = self._render_rows()
            while time.time() - start_time < self.duration:
                yield frame, 0.1
        elif self.mode == "cols":
            frame = self._render_cols()
            while time.time() - start_time < self.duration:
                yield frame, 0.1
        elif self.mode == "corners":
            frame = self._render_corners()
            while time.time() - start_time < self.duration:
                yield frame, 0.1
        elif self.mode == "gradient":
            frame = self._render_gradient()
            while time.time() - start_time < self.duration:
                yield frame, 0.1
        elif self.mode == "numbers":
            frame = self._render_numbers()
            while time.time() - start_time < self.duration:
                yield frame, 0.1
        else:
            # Default: cycle through all patterns
            patterns = [
                self._render_rows(),
                self._render_cols(),
                self._render_corners(),
                self._render_gradient(),
            ]
            while time.time() - start_time < self.duration:
                for pattern in patterns:
                    if time.time() - start_time >= self.duration:
                        break
                    yield pattern, 2.0
