"""Calendar/date display card."""

import time
from collections.abc import Iterator
from datetime import datetime
from typing import Any

from ..canvas import Canvas
from ..fonts import draw_text, text_width
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card

# Day abbreviations
DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

# Month abbreviations
MONTHS = [
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"
]


@register_card
class CalendarCard(Card):
    """Display current date.

    Config options:
        format: Display format - "full", "day", "date" (default: full)
        color: RGB color for text (default: white)
        highlight_weekend: Highlight weekends in different color (default: true)
        weekend_color: Color for weekends (default: orange)
        scroll: Enable scrolling (default: auto - scrolls if text wider than display)
        scroll_speed: Pixels per second for scrolling (default: 30)
    """

    card_type = "calendar"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.format: str = self.config.get("format", "full")
        self.color: RGB = tuple(self.config.get("color", (255, 255, 255)))  # type: ignore
        self.highlight_weekend: bool = self.config.get("highlight_weekend", True)
        self.weekend_color: RGB = tuple(self.config.get("weekend_color", (255, 165, 0)))  # type: ignore
        self.scroll: bool | str = self.config.get("scroll", "auto")
        self.scroll_speed: float = self.config.get("scroll_speed", 30.0)
        self.repeats: int = self.config.get("repeats", 1)

    def _get_date_text(self, now: datetime) -> str:
        """Get the date text based on format."""
        day_name = DAYS[now.weekday()]
        month_name = MONTHS[now.month - 1]
        day_num = now.day

        if self.format == "day":
            return day_name
        elif self.format == "date":
            return str(day_num)
        else:  # full
            return f"{day_name} {day_num} {month_name}"

    def _should_scroll(self, date_text: str) -> bool:
        """Determine if text should scroll."""
        if self.scroll == "auto":
            return text_width(date_text) > WIDTH
        return bool(self.scroll)

    def _render_frame(self, now: datetime, offset: int = 0) -> Frame:
        """Render the calendar display."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        date_text = self._get_date_text(now)
        content_width = text_width(date_text)

        # Choose color based on weekend
        is_weekend = now.weekday() >= 5  # Saturday=5, Sunday=6
        text_color = self.weekend_color if (is_weekend and self.highlight_weekend) else self.color

        if offset > 0:
            # Scrolling mode
            x = WIDTH - offset
        else:
            # Centered mode
            x = (WIDTH - content_width) // 2

        y = 1  # Vertically centered
        draw_text(canvas, x, y, date_text, text_color)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate calendar frames."""
        now = datetime.now()
        date_text = self._get_date_text(now)

        if self._should_scroll(date_text):
            # Scrolling mode
            pixels_per_frame = self.scroll_speed / 30.0
            frame_delay = 1.0 / 30.0

            offset = 0.0
            scrolls_done = 0

            while scrolls_done < self.repeats:
                now = datetime.now()
                date_text = self._get_date_text(now)
                content_width = text_width(date_text)
                total_scroll = content_width + WIDTH

                frame = self._render_frame(now, int(offset))
                yield frame, frame_delay

                offset += pixels_per_frame

                if offset >= total_scroll:
                    scrolls_done += 1
                    offset = 0.0
        else:
            # Static mode
            start_time = time.time()
            frame_delay = 1.0  # Update once per second

            while time.time() - start_time < self.duration:
                now = datetime.now()
                frame = self._render_frame(now)
                yield frame, frame_delay
