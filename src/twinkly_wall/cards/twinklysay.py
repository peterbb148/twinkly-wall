"""Twinklysay card for remote text messages."""

from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..fonts import (
    CHAR_HEIGHT,
    draw_text,
    draw_text_vertical_rotated,
    text_width,
    vertical_text_height,
)
from ..types import BLACK, HEIGHT, RGB, WHITE, WIDTH, Frame
from .base import Card, CardContext, register_card


@register_card
class TwinklysayCard(Card):
    """Display a remote text message (like cowsay for Twinkly).

    This card is designed for one-shot messages sent remotely via the MCP server.
    It scrolls the text once across the display and then finishes.

    Config options:
        text: The message to display (required)
        color: RGB tuple for text color (default: white)
        bgcolor: RGB tuple for background color (default: black)
        scroll_direction: horizontal, vertical_up, vertical_down,
            vertical_rotated_up, or vertical_rotated_down (default: horizontal)
        scroll_speed: Pixels per second for scrolling (default: 30)
    """

    card_type = "twinklysay"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.text: str = self.config.get("text", "")
        self.color: RGB = tuple(self.config.get("color", WHITE))  # type: ignore
        self.bgcolor: RGB = tuple(self.config.get("bgcolor", BLACK))  # type: ignore
        self.scroll_direction: str = self.config.get("scroll_direction", "horizontal")
        self.scroll_speed: float = self.config.get("scroll_speed", 30.0)

    def _render_horizontal_frame(self, offset: int) -> Frame:
        """Render a single frame of horizontally scrolling text."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(self.bgcolor)

        # Text scrolls from right to left
        x = WIDTH - offset
        y = 1  # Vertically centered

        draw_text(canvas, x, y, self.text, self.color)
        return canvas.copy()

    def _render_vertical_frame(self, y_offset: int) -> Frame:
        """Render a single frame of vertically scrolling text."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(self.bgcolor)

        content_width = text_width(self.text)
        x = max(0, (WIDTH - content_width) // 2)
        y = y_offset

        draw_text(canvas, x, y, self.text, self.color)
        return canvas.copy()

    def _render_vertical_rotated_frame(self, y_offset: int) -> Frame:
        """Render a single frame of vertically stacked, rotated text."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(self.bgcolor)

        column_width = CHAR_HEIGHT
        x = max(0, (WIDTH - column_width) // 2)

        draw_text_vertical_rotated(canvas, x, y_offset, self.text, self.color)
        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate scrolling text frames - scrolls once then finishes."""
        if not self.text:
            # Empty message - just show blank briefly
            canvas = Canvas(WIDTH, HEIGHT)
            canvas.clear(self.bgcolor)
            yield canvas.copy(), 0.5
            return

        # Calculate frame timing (~30 FPS)
        pixels_per_frame = self.scroll_speed / 30.0
        frame_delay = 1.0 / 30.0

        if self.scroll_direction == "horizontal":
            content_width = text_width(self.text)
            total_scroll = content_width + WIDTH + 1

            offset = 0.0

            # Scroll until text has completely crossed the display
            while offset < total_scroll:
                frame = self._render_horizontal_frame(int(offset))
                yield frame, frame_delay
                offset += pixels_per_frame
        elif self.scroll_direction in ("vertical_up", "vertical_down"):
            text_height = 7  # Font height
            start_y = HEIGHT
            end_y = -text_height
            total_scroll = start_y - end_y

            offset = 0.0
            while offset < total_scroll:
                if self.scroll_direction == "vertical_up":
                    y = start_y - int(offset)
                else:  # vertical_down
                    y = end_y + int(offset)

                frame = self._render_vertical_frame(y)
                yield frame, frame_delay
                offset += pixels_per_frame
        elif self.scroll_direction in ("vertical_rotated_up", "vertical_rotated_down"):
            text_height = vertical_text_height(self.text)
            start_y = HEIGHT
            end_y = -text_height
            total_scroll = start_y - end_y

            offset = 0.0
            while offset < total_scroll:
                if self.scroll_direction == "vertical_rotated_up":
                    y = start_y - int(offset)
                else:  # vertical_rotated_down
                    y = end_y + int(offset)

                frame = self._render_vertical_rotated_frame(y)
                yield frame, frame_delay
                offset += pixels_per_frame
        else:
            # Fallback to horizontal scrolling
            content_width = text_width(self.text)
            total_scroll = content_width + WIDTH + 1

            offset = 0.0
            while offset < total_scroll:
                frame = self._render_horizontal_frame(int(offset))
                yield frame, frame_delay
                offset += pixels_per_frame
