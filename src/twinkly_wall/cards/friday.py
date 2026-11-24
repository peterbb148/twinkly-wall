"""Friday detector celebration card."""

import random
import time
from collections.abc import Iterator
from datetime import datetime
from typing import Any

from ..canvas import Canvas
from ..fonts import (
    CHAR_WIDTH,
    draw_text,
    draw_text_vertical_stacked,
    text_width,
    vertical_text_height,
)
from ..types import BLACK, HEIGHT, PORTRAIT_HEIGHT, PORTRAIT_WIDTH, RGB, WIDTH, Frame
from .base import Card, CardContext, CardLayout, register_card

PARTY_COLORS: list[RGB] = [
    (255, 0, 0),
    (255, 165, 0),
    (255, 255, 0),
    (0, 255, 0),
    (0, 255, 255),
    (0, 0, 255),
    (255, 0, 255),
]


def _countdown_message(days: int) -> str:
    return "1 DAY TO FRIDAY" if days == 1 else f"{days} DAYS TO FRIDAY"


@register_card
class FridayCard(Card):
    """Friday detector with celebration effect.

    Shows "FRIDAY!" with party effects on Fridays,
    or a countdown to Friday on other days.

    Config options:
        always_friday: Always show Friday celebration (default: false)
        message: Custom Friday message (default: "FRIDAY!")
    """

    card_type = "friday"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.always_friday: bool = self.config.get("always_friday", False)
        self.message: str = self.config.get("message", "FRIDAY!")
        self.repeats: int = self.config.get("repeats", 1)

    def _is_friday(self) -> bool:
        """Check if today is Friday."""
        return self.always_friday or datetime.now().weekday() == 4

    def _days_until_friday(self) -> int:
        """Calculate days until Friday."""
        today = datetime.now().weekday()
        if today == 4:  # Friday
            return 0
        elif today < 4:
            return 4 - today
        else:
            return 4 + (7 - today)

    def _render_friday(self, frame_num: int) -> Frame:
        """Render Friday celebration."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        # Rainbow cycling text color
        color_idx = (frame_num // 3) % len(PARTY_COLORS)
        text_color = PARTY_COLORS[color_idx]

        # Draw main text
        text_w = text_width(self.message)
        text_x = (WIDTH - text_w) // 2
        text_y = 2
        draw_text(canvas, text_x, text_y, self.message, text_color)

        # Add party confetti/sparkles
        random.seed(frame_num // 2)  # Consistent but changing pattern
        for _ in range(8):
            x = random.randint(0, WIDTH - 1)
            y = random.randint(0, HEIGHT - 1)
            color = random.choice(PARTY_COLORS)
            canvas.set_pixel(x, y, color)

        return canvas.copy()

    def _render_countdown(self, days: int, offset: int) -> Frame:
        """Render countdown to Friday as scrolling text."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        x_pos = WIDTH - offset
        draw_text(canvas, x_pos, 1, _countdown_message(days), (255, 255, 0))

        return canvas.copy()

    def _countdown_scroll_length(self, days: int) -> int:
        return text_width(_countdown_message(days)) + WIDTH + 1

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate Friday detector frames."""
        start_time = time.time()
        frame_num = 0

        if self._is_friday():
            frame_delay = 1.0 / 15.0  # Faster for party effect
            while time.time() - start_time < self.duration:
                frame = self._render_friday(frame_num)
                yield frame, frame_delay
                frame_num += 1
        else:
            # Scrolling countdown
            days = self._days_until_friday()
            total_scroll = self._countdown_scroll_length(days)
            scroll_speed = 30.0
            frame_delay = 1.0 / 30.0
            offset = 0.0
            scrolls_done = 0

            while scrolls_done < self.repeats:
                frame = self._render_countdown(days, int(offset))
                yield frame, frame_delay
                offset += scroll_speed * frame_delay
                if offset >= total_scroll:
                    scrolls_done += 1
                    offset = 0


@register_card
class FridayVerticalCard(FridayCard):
    """Show an upright Friday celebration or countdown on a portrait wall."""

    card_type = "friday_vertical"
    layout = CardLayout.portrait

    def _render_friday(self, frame_num: int) -> Frame:
        canvas = Canvas(PORTRAIT_WIDTH, PORTRAIT_HEIGHT)
        x = (canvas.width - CHAR_WIDTH) // 2
        height = vertical_text_height(self.message, spacing=0)
        overflow = max(0, height - canvas.height)
        offset = min(overflow, (frame_num // 2) % (overflow + 15))
        y = max(0, (canvas.height - height) // 2) - offset
        color = PARTY_COLORS[(frame_num // 3) % len(PARTY_COLORS)]
        draw_text_vertical_stacked(canvas, x, y, self.message, color, spacing=0)

        sparkles = random.Random(frame_num // 2)
        edge_columns = [*range(x), *range(x + CHAR_WIDTH, canvas.width)]
        for _ in range(8):
            canvas.set_pixel(
                sparkles.choice(edge_columns),
                sparkles.randrange(canvas.height),
                sparkles.choice(PARTY_COLORS),
            )
        return canvas.copy()

    def _render_countdown(self, days: int, offset: int) -> Frame:
        canvas = Canvas(PORTRAIT_WIDTH, PORTRAIT_HEIGHT)
        x = (canvas.width - CHAR_WIDTH) // 2
        draw_text_vertical_stacked(
            canvas, x, canvas.height - offset, _countdown_message(days), (255, 255, 0)
        )
        return canvas.copy()

    def _countdown_scroll_length(self, days: int) -> int:
        return vertical_text_height(_countdown_message(days)) + PORTRAIT_HEIGHT + 1
