"""Present a dated lunch menu on the portrait wall."""

import json
import unicodedata
from collections.abc import Iterator
from datetime import date
from pathlib import Path

from ..canvas import Canvas
from ..fonts import CHAR_SPACING, CHAR_WIDTH, draw_char_rotated_cw, text_width
from ..types import GOLD, PORTRAIT_HEIGHT, PORTRAIT_WIDTH, RGB, WHITE, Frame
from .base import Card, CardContext, CardLayout, register_card

_GLYPH_STRIDE = CHAR_WIDTH + CHAR_SPACING
_MAX_SCROLL_SPEED = 20  # Pixels per second


def _read_menu(path: Path) -> tuple[date, str, str]:
    """Read the dated record anew on every play."""
    try:
        menu = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not read lunch menu {path}: {error}") from error
    if not isinstance(menu, dict):
        raise ValueError(f"{path}: expected a lunch menu JSON object")
    for field in ("date", "name", "description"):
        value = menu.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{path}: '{field}' must be a nonempty string")
    try:
        menu_date = date.fromisoformat(menu["date"])
        if menu_date.isoformat() != menu["date"]:
            raise ValueError("date format")
    except ValueError as error:
        raise ValueError(f"{path}: 'date' must be a valid YYYY-MM-DD date") from error
    name, description = (
        unicodedata.normalize("NFC", " ".join(menu[field].upper().split()))
        for field in ("name", "description")
    )
    return menu_date, name, description


def _menu_frame(text: str, offset: int, color: RGB) -> Frame:
    """Lay out one sideways line and draw just the glyphs in view."""
    canvas = Canvas(PORTRAIT_WIDTH, PORTRAIT_HEIGHT)
    start = max(0, offset // _GLYPH_STRIDE)
    end = (offset + PORTRAIT_HEIGHT - 1) // _GLYPH_STRIDE + 1
    for index, glyph in enumerate(text[start:end], start):
        y = PORTRAIT_HEIGHT - CHAR_WIDTH - index * _GLYPH_STRIDE + offset
        draw_char_rotated_cw(canvas, 1, y, glyph, color)
    return canvas.copy()


@register_card
class LunchVerticalCard(Card):
    """Show LUNCH, date, meal name, and description from a local JSON menu."""

    card_type = "lunch_vertical"
    layout = CardLayout.portrait

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Present each field in full, allowing extra time for long text."""
        menu_path = self.config.get("menu_path")
        if not isinstance(menu_path, str) or not menu_path.strip():
            raise ValueError("lunch_vertical requires a 'menu_path' to a JSON menu file")
        menu_date, name, description = _read_menu(Path(menu_path).expanduser())
        fields = (
            ("LUNCH", GOLD, 1.25),
            (menu_date.strftime("%d/%m/%y"), WHITE, 1.5),
            (name, GOLD, 2.0),
            (description, WHITE, 2.75),
        )
        stages = []
        for text, color, hold in fields:
            width = text_width(text)
            travel = max(0, width - PORTRAIT_HEIGHT)
            stages.append((text, color, hold, travel, (width - PORTRAIT_HEIGHT) // 2))
        minimum = sum(hold + travel / _MAX_SCROLL_SPEED for _, _, hold, travel, _ in stages)
        extra = max(0.0, self.duration - minimum) / len(stages)
        for text, color, hold, travel, center in stages:
            if not travel:
                yield _menu_frame(text, center, color), hold + extra
                continue
            yield _menu_frame(text, 0, color), (hold + extra) / 2
            for offset in range(1, travel):
                yield _menu_frame(text, offset, color), 1 / _MAX_SCROLL_SPEED
            yield _menu_frame(text, travel, color), (hold + extra) / 2 + 1 / _MAX_SCROLL_SPEED
