"""Twinklysay card for remote text messages."""

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
    It scrolls the text once across the display and then finishes.

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
        """Generate scrolling text frames - scrolls once then finishes."""
        if not self.text:
            # Empty message - just show blank briefly
            canvas = Canvas(WIDTH, HEIGHT)
            canvas.clear(self.bgcolor)
            yield canvas.copy(), 0.5
            return

        content_width = text_width(self.text)
        total_scroll = content_width + WIDTH

        # Calculate frame timing (~30 FPS)
        pixels_per_frame = self.scroll_speed / 30.0
        frame_delay = 1.0 / 30.0

        offset = 0.0

        # Scroll until text has completely crossed the display
        while offset < total_scroll:
            frame = self._render_frame(int(offset))
            yield frame, frame_delay
            offset += pixels_per_frame
