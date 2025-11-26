"""Static and scrolling text card."""

import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..fonts import draw_text, text_width
from ..types import BLACK, HEIGHT, RGB, WHITE, WIDTH, Frame
from .base import Card, CardContext, register_card


@register_card
class TextCard(Card):
    """Display static or scrolling text.

    Config options:
        text: The message to display (required)
        color: RGB tuple for text color (default: white)
        bgcolor: RGB tuple for background color (default: black)
        scroll: Enable scrolling for long text (default: auto)
        scroll_speed: Pixels per second for scrolling (default: 30)
        align: Text alignment - left, center, right (default: center)
    """

    card_type = "text"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.text: str = self.config.get("text", "")
        self.color: RGB = tuple(self.config.get("color", WHITE))  # type: ignore
        self.bgcolor: RGB = tuple(self.config.get("bgcolor", BLACK))  # type: ignore
        self.scroll: bool | str = self.config.get("scroll", "auto")
        self.scroll_speed: float = self.config.get("scroll_speed", 30.0)
        self.align: str = self.config.get("align", "center")

    def _should_scroll(self) -> bool:
        """Determine if text should scroll."""
        if self.scroll == "auto":
            return text_width(self.text) > WIDTH
        return bool(self.scroll)

    def _render_static(self) -> Frame:
        """Render static (non-scrolling) text."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(self.bgcolor)

        tw = text_width(self.text)

        # Calculate x position based on alignment
        if self.align == "left":
            x = 0
        elif self.align == "right":
            x = max(0, WIDTH - tw)
        else:  # center
            x = max(0, (WIDTH - tw) // 2)

        # Center vertically
        y = 1

        draw_text(canvas, x, y, self.text, self.color)
        return canvas.copy()

    def _render_scrolling_frame(self, offset: int, content_width: int) -> Frame:
        """Render a single frame of scrolling text.

        Args:
            offset: Current scroll offset (0 = text starts at right edge)
            content_width: Total width of the text content
        """
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(self.bgcolor)

        # Text starts off-screen to the right, scrolls left
        # offset=0 means text is just off the right edge
        # offset=content_width+WIDTH means text has scrolled completely off left
        x = WIDTH - offset

        # Center vertically
        y = 1

        draw_text(canvas, x, y, self.text, self.color)
        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate text frames, scrolling if needed."""
        if not self._should_scroll():
            # Static display
            frame = self._render_static()
            start_time = time.time()
            while time.time() - start_time < self.duration:
                yield frame, 0.5  # Update every 0.5s for static
        else:
            # Scrolling display
            content_width = text_width(self.text)
            total_scroll = content_width + WIDTH  # Full scroll distance

            # Calculate frame timing
            pixels_per_frame = self.scroll_speed / 30.0  # ~30 FPS target
            frame_delay = 1.0 / 30.0

            start_time = time.time()
            offset = 0.0

            while time.time() - start_time < self.duration:
                frame = self._render_scrolling_frame(int(offset), content_width)
                yield frame, frame_delay

                offset += pixels_per_frame

                # Loop the scroll
                if offset >= total_scroll:
                    offset = 0.0
