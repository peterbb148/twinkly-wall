"""Clock display card showing time with blinking colon."""

import time
from collections.abc import Iterator
from datetime import datetime
from typing import Any

from ..canvas import Canvas
from ..fonts import draw_text, text_width
from ..types import HEIGHT, RGB, WHITE, WIDTH, Frame
from .base import Card, CardContext, register_card


@register_card
class ClockCard(Card):
    """Display current time with blinking colon.

    Config options:
        color: RGB tuple for text color (default: white)
        format_24h: Use 24-hour format (default: True)
        show_seconds: Show seconds (default: False)
        blink_colon: Blink the colon every second (default: True)
    """

    card_type = "clock"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.color: RGB = tuple(self.config.get("color", WHITE))  # type: ignore
        self.format_24h: bool = self.config.get("format_24h", True)
        self.show_seconds: bool = self.config.get("show_seconds", False)
        self.blink_colon: bool = self.config.get("blink_colon", True)

    def _format_time(self, dt: datetime, show_colon: bool = True) -> str:
        """Format time string based on config."""
        if self.format_24h:
            hour = dt.hour
        else:
            hour = dt.hour % 12
            if hour == 0:
                hour = 12

        colon = ":" if show_colon else " "

        if self.show_seconds:
            return f"{hour:2d}{colon}{dt.minute:02d}{colon}{dt.second:02d}"
        else:
            return f"{hour:2d}{colon}{dt.minute:02d}"

    def _render_time(self, time_str: str) -> Frame:
        """Render time string to a frame."""
        canvas = Canvas(WIDTH, HEIGHT)

        # Calculate width and center horizontally
        tw = text_width(time_str)
        x = max(0, (WIDTH - tw) // 2)

        # Center vertically (font height is 7, display height is 10)
        y = 1

        draw_text(canvas, x, y, time_str, self.color)
        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate clock frames with blinking colon.

        Yields frames at ~2Hz to handle colon blinking.
        """
        start_time = time.time()
        duration = self.duration

        while time.time() - start_time < duration:
            now = datetime.now()

            if self.blink_colon:
                # Show colon for first half of each second
                show_colon = now.microsecond < 500000
            else:
                show_colon = True

            time_str = self._format_time(now, show_colon)
            frame = self._render_time(time_str)

            # Yield frame with 0.1s delay for smooth blinking
            yield frame, 0.1
