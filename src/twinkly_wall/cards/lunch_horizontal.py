"""Scroll the meal for the current Copenhagen date on a landscape wall."""

import re
from collections.abc import Iterator
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from PIL import ImageColor

from ..canvas import Canvas
from ..fonts import CHAR_HEIGHT, CHAR_SPACING, CHAR_WIDTH, draw_text, text_width
from ..types import HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card

_BROWN: RGB = (180, 116, 62)
_WORD = re.compile(r"\b[^\W\d_]+\b")


def _meal_strip(meal: str) -> Frame:
    """Draw the whole line once, with one screen of padding at each end."""
    strip = Canvas(2 * WIDTH + text_width(meal), HEIGHT)
    y = (HEIGHT - CHAR_HEIGHT) // 2
    draw_text(strip, WIDTH, y, meal, _BROWN)
    for match in _WORD.finditer(meal):
        rgb = ImageColor.colormap.get(match.group().lower())
        if rgb is not None:
            x = WIDTH + match.start() * (CHAR_WIDTH + CHAR_SPACING)
            draw_text(strip, x, y, match.group(), ImageColor.getrgb(rgb))
    return strip.frame


@register_card
class LunchHorizontalCard(Card):
    """Scroll one full pass of today's meal, or skip when no meal is listed."""

    card_type = "lunch_horizontal"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        menu = self.config.get("menu")
        if not isinstance(menu, dict):
            raise ValueError("lunch_horizontal requires a 'menu' mapping of dates to meals")

        self.menu: dict[date, str] = {}
        for key, meal in menu.items():
            date_text = str(key)
            try:
                day = date.fromisoformat(date_text)
                if day.isoformat() != date_text:
                    raise ValueError("date format")
            except ValueError as error:
                raise ValueError(
                    f"Invalid lunch menu date {date_text!r}; use YYYY-MM-DD"
                ) from error
            if not isinstance(meal, str) or not meal.strip():
                raise ValueError(f"Lunch menu entry {date_text} must be a nonempty string")
            self.menu[day] = meal

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Select the meal at playback time and scroll it right to left."""
        meal = self.menu.get(datetime.now(ZoneInfo("Europe/Copenhagen")).date())
        if meal is None:
            return

        strip = _meal_strip(meal)
        for offset in range(len(strip[0]) - WIDTH + 1):
            yield [row[offset : offset + WIDTH] for row in strip], 1 / 25
