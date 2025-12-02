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
        scroll: Enable scrolling (default: auto - scrolls if text wider than display)
        scroll_speed: Pixels per second for scrolling (default: 30)
    """

    card_type = "countdown"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.target_str: str = self.config.get("target", "")
        self.label: str = self.config.get("label", "")
        self.color: RGB = tuple(self.config.get("color", (255, 255, 255)))  # type: ignore
        self.show_seconds: bool | None = self.config.get("show_seconds", None)
        self.scroll: bool | str = self.config.get("scroll", "auto")
        self.scroll_speed: float = self.config.get("scroll_speed", 30.0)

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

    def _get_display_text(self, countdown_text: str) -> str:
        """Get full display text with label."""
        if self.label:
            return f"{self.label} {countdown_text}"
        return countdown_text

    def _should_scroll(self, countdown_text: str) -> bool:
        """Determine if text should scroll."""
        if self.scroll == "auto":
            return text_width(self._get_display_text(countdown_text)) > WIDTH
        return bool(self.scroll)

    def _render_frame(self, countdown_text: str, offset: int = 0) -> Frame:
        """Render the countdown display."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        display_text = self._get_display_text(countdown_text)
        tw = text_width(display_text)

        if offset > 0:
            # Scrolling mode
            x = WIDTH - offset
        else:
            # Centered mode
            x = (WIDTH - tw) // 2

        y = 1  # Vertically centered

        if self.label:
            # Draw label in gray, countdown in color
            draw_text(canvas, x, y, self.label, (150, 150, 150))
            label_w = text_width(self.label + " ")
            draw_text(canvas, x + label_w, y, countdown_text, self.color)
        else:
            draw_text(canvas, x, y, countdown_text, self.color)

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

        # Get initial countdown to check if scrolling needed
        now = datetime.now()
        remaining = (self.target - now).total_seconds()
        countdown_text = self._format_countdown(remaining)

        if self._should_scroll(countdown_text):
            # Scrolling mode
            pixels_per_frame = self.scroll_speed / 30.0
            frame_delay = 1.0 / 30.0

            start_time = time.time()
            offset = 0.0
            scroll_completed = False

            while True:
                now = datetime.now()
                remaining = (self.target - now).total_seconds()
                countdown_text = self._format_countdown(remaining)

                content_width = text_width(self._get_display_text(countdown_text))
                total_scroll = content_width + WIDTH

                frame = self._render_frame(countdown_text, int(offset))
                yield frame, frame_delay

                offset += pixels_per_frame

                if offset >= total_scroll:
                    scroll_completed = True
                    offset = 0.0

                elapsed = time.time() - start_time
                if scroll_completed and elapsed >= self.duration:
                    break
        else:
            # Static mode
            start_time = time.time()
            frame_delay = 0.5  # Update twice per second

            while time.time() - start_time < self.duration:
                now = datetime.now()
                remaining = (self.target - now).total_seconds()

                countdown_text = self._format_countdown(remaining)
                frame = self._render_frame(countdown_text)
                yield frame, frame_delay
