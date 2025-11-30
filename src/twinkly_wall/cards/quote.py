"""Quote of the day card."""

import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..datasources.quotes import QuoteData, QuoteDataSource, QuoteError
from ..fonts import draw_text, text_width
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card


@register_card
class QuoteCard(Card):
    """Display a scrolling quote of the day.

    Config options:
        color: RGB tuple for text (default: warm white)
        author_color: RGB tuple for author (default: dimmer)
        show_author: Show author attribution (default: true)
        scroll_speed: Pixels per second (default: 30)
    """

    card_type = "quote"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.color: RGB = tuple(self.config.get("color", (255, 230, 180)))  # type: ignore
        self.author_color: RGB = tuple(self.config.get("author_color", (150, 140, 120)))  # type: ignore
        self.show_author: bool = self.config.get("show_author", True)
        self.scroll_speed: float = self.config.get("scroll_speed", 30.0)

    def _render_frame(self, text: str, offset: int, color: RGB) -> Frame:
        """Render a frame with scrolling text."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        x = WIDTH - offset
        y = 1

        draw_text(canvas, x, y, text, color)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate quote display frames."""
        # Get or create quote datasource
        quote_ds = ctx.datasources.get("quote")
        if not quote_ds:
            # Create a default datasource
            quote_ds = QuoteDataSource()

        # Fetch quote
        try:
            quote_data = quote_ds.get_quote()
            quote_text = quote_data.quote
            author = quote_data.author
        except QuoteError:
            quote_text = "Wisdom comes to those who seek it."
            author = "Ancient Proverb"

        # Build display text
        if self.show_author:
            full_text = f'"{quote_text}" - {author}'
        else:
            full_text = f'"{quote_text}"'

        content_width = text_width(full_text)
        total_scroll = content_width + WIDTH

        frame_delay = 1.0 / 30.0  # 30 FPS
        pixels_per_frame = self.scroll_speed / 30.0

        start_time = time.time()
        offset = 0.0
        scroll_completed = False

        while True:
            frame = self._render_frame(full_text, int(offset), self.color)
            yield frame, frame_delay

            offset += pixels_per_frame

            if offset >= total_scroll:
                scroll_completed = True
                offset = 0.0

            elapsed = time.time() - start_time
            if scroll_completed and elapsed >= self.duration:
                break
