"""Twinklysay card for remote text messages."""

import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..fonts import draw_text, text_width
from ..types import BLACK, HEIGHT, RGB, WHITE, WIDTH, Frame
from .base import Card, CardContext, register_card


@register_card
class TwinklysayCard(Card):
    """Display a remote text message (like cowsay for Twinkly).

    This card is designed for one-shot messages sent remotely via the MCP server.
    It always scrolls the text and has sensible defaults for display.

    Config options:
        text: The message to display (required)
        color: RGB tuple for text color (default: white)
        bgcolor: RGB tuple for background color (default: black)
        scroll_speed: Pixels per second for scrolling (default: 30)
    """

    card_type = "twinklysay"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.text: str = self.config.get("text", "")
        self.color: RGB = tuple(self.config.get("color", WHITE))  # type: ignore
        self.bgcolor: RGB = tuple(self.config.get("bgcolor", BLACK))  # type: ignore
        self.scroll_speed: float = self.config.get("scroll_speed", 30.0)

        # Default duration based on text length if not specified
        if "duration" not in self.config:
            # Estimate: time for text to scroll across + 2 seconds buffer
            tw = text_width(self.text) if self.text else 0
            scroll_time = (tw + WIDTH) / self.scroll_speed
            self.duration = max(5.0, scroll_time + 2.0)

    def _render_frame(self, offset: int) -> Frame:
        """Render a single frame of scrolling text."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(self.bgcolor)

        # Text scrolls from right to left
        x = WIDTH - offset
        y = 1  # Vertically centered

        draw_text(canvas, x, y, self.text, self.color)
        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate scrolling text frames."""
        if not self.text:
            # Empty message - just show blank for a moment
            canvas = Canvas(WIDTH, HEIGHT)
            canvas.clear(self.bgcolor)
            yield canvas.copy(), self.duration
            return

        content_width = text_width(self.text)
        total_scroll = content_width + WIDTH

        # Calculate frame timing (~30 FPS)
        pixels_per_frame = self.scroll_speed / 30.0
        frame_delay = 1.0 / 30.0

        start_time = time.time()
        offset = 0.0
        scroll_completed = False

        while True:
            frame = self._render_frame(int(offset))
            yield frame, frame_delay

            offset += pixels_per_frame

            # Check if scroll completed
            if offset >= total_scroll:
                scroll_completed = True
                offset = 0.0

            # Exit when scroll completes and duration met
            elapsed = time.time() - start_time
            if scroll_completed and elapsed >= self.duration:
                break
