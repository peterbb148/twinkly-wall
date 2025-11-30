"""RSS news feed ticker card."""

import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..datasources.rss import RSSDataSource, RSSError
from ..fonts import draw_text, text_width
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card

# Default BBC News RSS feed
DEFAULT_FEED = "https://feeds.bbci.co.uk/news/rss.xml"


@register_card
class NewsCard(Card):
    """Display scrolling RSS news headlines.

    Config options:
        feed_url: RSS feed URL (default: BBC News)
        color: RGB tuple for headline text (default: white)
        separator: Text between headlines (default: " +++ ")
        separator_color: RGB tuple for separator (default: red)
        scroll_speed: Pixels per second (default: 30)
        max_headlines: Max headlines to show (default: 5)
    """

    card_type = "news"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.feed_url: str = self.config.get("feed_url", DEFAULT_FEED)
        self.color: RGB = tuple(self.config.get("color", (255, 255, 255)))  # type: ignore
        self.separator: str = self.config.get("separator", " +++ ")
        self.separator_color: RGB = tuple(self.config.get("separator_color", (255, 50, 50)))  # type: ignore
        self.scroll_speed: float = self.config.get("scroll_speed", 30.0)
        self.max_headlines: int = self.config.get("max_headlines", 5)

    def _render_frame(
        self, headlines: list[str], offset: int
    ) -> Frame:
        """Render a frame with scrolling headlines."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        x = WIDTH - offset
        y = 1

        # Build and render the ticker text
        for i, headline in enumerate(headlines):
            if i > 0:
                # Draw separator
                draw_text(canvas, x, y, self.separator, self.separator_color)
                x += text_width(self.separator)

            # Draw headline
            draw_text(canvas, x, y, headline, self.color)
            x += text_width(headline)

        return canvas.copy()

    def _calculate_total_width(self, headlines: list[str]) -> int:
        """Calculate total width of all headlines with separators."""
        total = 0
        for i, headline in enumerate(headlines):
            if i > 0:
                total += text_width(self.separator)
            total += text_width(headline)
        return total

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate news ticker frames."""
        # Get or create RSS datasource
        rss_ds = ctx.datasources.get("rss")
        if not rss_ds:
            # Create a default datasource
            rss_ds = RSSDataSource(self.feed_url, max_items=self.max_headlines)

        # Fetch headlines
        try:
            headlines = rss_ds.get_headlines()[: self.max_headlines]
        except RSSError:
            headlines = ["News feed unavailable"]

        if not headlines:
            headlines = ["No news available"]

        content_width = self._calculate_total_width(headlines)
        total_scroll = content_width + WIDTH

        frame_delay = 1.0 / 30.0  # 30 FPS
        pixels_per_frame = self.scroll_speed / 30.0

        start_time = time.time()
        offset = 0.0
        scroll_completed = False

        while True:
            frame = self._render_frame(headlines, int(offset))
            yield frame, frame_delay

            offset += pixels_per_frame

            if offset >= total_scroll:
                scroll_completed = True
                offset = 0.0

            elapsed = time.time() - start_time
            if scroll_completed and elapsed >= self.duration:
                break
