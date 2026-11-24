"""Vertical score tower leaderboard card."""

from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..fonts import CHAR_HEIGHT, draw_text, text_width
from ..types import GOLD, PORTRAIT_HEIGHT, PORTRAIT_WIDTH, RGB, WHITE, Frame
from .base import Card, CardContext, CardLayout, register_card


@register_card
class ScoreTowerCard(Card):
    """Stacked leaderboard / score tower.

    This card shows a compact leaderboard stacked from top to bottom. It is
    intended for vertical layouts where a traditional horizontal scroll
    does not fit as well.

    Config options:
        entries: List of {"name": str, "score": int} dicts
        title: Optional title at the top
        name_color: Color for names (default: white)
        score_color: Color for scores (default: gold)
        show_rank: Show position numbers (default: true)
        repeats: How many cycles to loop (default: 1)
    """

    card_type = "score_tower"
    layout = CardLayout.portrait

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.entries: list[dict[str, Any]] = list(self.config.get("entries", []))
        self.title: str = self.config.get("title", "")
        self.name_color: RGB = tuple(self.config.get("name_color", WHITE))  # type: ignore
        self.score_color: RGB = tuple(self.config.get("score_color", GOLD))  # type: ignore
        self.show_rank: bool = bool(self.config.get("show_rank", True))
        self.repeats: int = int(self.config.get("repeats", 1))

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate stacked leaderboard frames."""
        row_height = CHAR_HEIGHT + 1
        rows_per_page = PORTRAIT_HEIGHT // row_height
        rows = []
        if self.title:
            rows.append((self.title, self.name_color))
        if not self.entries:
            rows.append(("NO DATA", (255, 0, 0)))

        # Reserve two lines per entry so scores never get clipped by the name.
        pages: list[list[tuple[str, RGB]]] = []
        for rank, entry in enumerate(self.entries, start=1):
            if len(rows) + 2 > rows_per_page:
                pages.append(rows)
                rows = []
            name = str(entry.get("name", ""))
            label = f"{rank}. {name}" if self.show_rank else name
            rows.extend(((label, self.name_color), (str(entry.get("score", 0)), self.score_color)))
        if rows:
            pages.append(rows)

        for _ in range(self.repeats):
            for page in pages:
                widths = [text_width(text) for text, _ in page]
                overflow = max(0, max(widths) - PORTRAIT_WIDTH)
                for offset in range(overflow + 1):
                    canvas = Canvas(PORTRAIT_WIDTH, PORTRAIT_HEIGHT)
                    for index, ((text, color), width) in enumerate(zip(page, widths, strict=True)):
                        if width <= PORTRAIT_WIDTH:
                            x = (PORTRAIT_WIDTH - width) // 2
                        else:
                            x = -min(offset, width - PORTRAIT_WIDTH)
                        draw_text(canvas, x, index * row_height, text, color)
                    delay = 0.5 if offset in (0, overflow) else 0.12
                    yield canvas.copy(), delay
