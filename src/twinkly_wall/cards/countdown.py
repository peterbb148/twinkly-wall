"""Countdown timer card."""

import time
from collections.abc import Iterator
from datetime import datetime
from typing import Any

from ..canvas import Canvas
from ..fonts import draw_text, text_width
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card


@register_card
class CountdownCard(Card):
    """Countdown to a target date/time.

    Config options:
        target: Target datetime string "YYYY-MM-DD" or "YYYY-MM-DD HH:MM" (required)
        label: Short label to display (default: none)
        color: RGB color for numbers (default: white)
        show_seconds: Show seconds in countdown (default: false for days, true for hours)
    """

    card_type = "countdown"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.target_str: str = self.config.get("target", "")
        self.label: str = self.config.get("label", "")
        self.color: RGB = tuple(self.config.get("color", (255, 255, 255)))  # type: ignore
        self.show_seconds: bool | None = self.config.get("show_seconds", None)

        # Parse target date
        self.target: datetime | None = None
        if self.target_str:
            try:
                if " " in self.target_str:
                    self.target = datetime.strptime(self.target_str, "%Y-%m-%d %H:%M")
                else:
                    self.target = datetime.strptime(self.target_str, "%Y-%m-%d")
            except ValueError:
                pass

    def _format_countdown(self, seconds: float) -> str:
        """Format seconds into countdown string."""
        if seconds <= 0:
            return "NOW!"

        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        # Determine format based on time remaining
        show_secs = self.show_seconds
        if show_secs is None:
            show_secs = days == 0

        if days > 0:
            if days > 99:
                return f"{days}D"
            return f"{days}D {hours:02d}H"
        elif hours > 0:
            if show_secs:
                return f"{hours}:{minutes:02d}:{secs:02d}"
            return f"{hours}H {minutes:02d}M"
        else:
            if show_secs:
                return f"{minutes}:{secs:02d}"
            return f"{minutes}M"

    def _render_frame(self, countdown_text: str) -> Frame:
        """Render the countdown display."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        # Draw label if present (top line)
        if self.label:
            label_w = text_width(self.label)
            label_x = (WIDTH - label_w) // 2
            draw_text(canvas, label_x, 0, self.label, (150, 150, 150))

            # Draw countdown below
            count_w = text_width(countdown_text)
            count_x = (WIDTH - count_w) // 2
            draw_text(canvas, count_x, 5, countdown_text, self.color)
        else:
            # Center countdown vertically
            count_w = text_width(countdown_text)
            count_x = (WIDTH - count_w) // 2
            count_y = (HEIGHT - 5) // 2  # Approximate text height
            draw_text(canvas, count_x, count_y, countdown_text, self.color)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate countdown frames."""
        if not self.target:
            # No valid target, show error
            canvas = Canvas(WIDTH, HEIGHT)
            draw_text(canvas, 0, 2, "NO DATE", (255, 0, 0))
            frame = canvas.copy()
            start_time = time.time()
            while time.time() - start_time < self.duration:
                yield frame, 1.0
            return

        start_time = time.time()
        frame_delay = 0.5  # Update twice per second

        while time.time() - start_time < self.duration:
            now = datetime.now()
            remaining = (self.target - now).total_seconds()

            countdown_text = self._format_countdown(remaining)
            frame = self._render_frame(countdown_text)
            yield frame, frame_delay
