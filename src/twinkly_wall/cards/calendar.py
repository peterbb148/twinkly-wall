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
    """

    card_type = "calendar"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.format: str = self.config.get("format", "full")
        self.color: RGB = tuple(self.config.get("color", (255, 255, 255)))  # type: ignore
        self.highlight_weekend: bool = self.config.get("highlight_weekend", True)
        self.weekend_color: RGB = tuple(self.config.get("weekend_color", (255, 165, 0)))  # type: ignore

    def _render_frame(self, now: datetime) -> Frame:
        """Render the calendar display."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        day_name = DAYS[now.weekday()]
        month_name = MONTHS[now.month - 1]
        day_num = now.day

        # Choose color based on weekend
        is_weekend = now.weekday() >= 5  # Saturday=5, Sunday=6
        text_color = self.weekend_color if (is_weekend and self.highlight_weekend) else self.color

        if self.format == "day":
            # Just the day name
            w = text_width(day_name)
            x = (WIDTH - w) // 2
            y = (HEIGHT - 5) // 2
            draw_text(canvas, x, y, day_name, text_color)

        elif self.format == "date":
            # Just the date number
            date_str = str(day_num)
            w = text_width(date_str)
            x = (WIDTH - w) // 2
            y = (HEIGHT - 5) // 2
            draw_text(canvas, x, y, date_str, text_color)

        else:  # full
            # Day name on top, date below
            # Top line: DAY
            w1 = text_width(day_name)
            x1 = (WIDTH - w1) // 2
            draw_text(canvas, x1, 0, day_name, text_color)

            # Bottom line: DD MMM
            date_str = f"{day_num} {month_name}"
            w2 = text_width(date_str)
            x2 = (WIDTH - w2) // 2
            draw_text(canvas, x2, 5, date_str, text_color)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate calendar frames."""
        start_time = time.time()
        frame_delay = 1.0  # Update once per second

        while time.time() - start_time < self.duration:
            now = datetime.now()
            frame = self._render_frame(now)
            yield frame, frame_delay
