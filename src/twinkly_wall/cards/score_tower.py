"""Vertical score tower leaderboard card."""

from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..fonts import draw_text
from ..types import BLACK, GOLD, HEIGHT, RGB, WHITE, WIDTH, Frame
from .base import Card, CardContext, register_card


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
        if not self.entries:
            canvas = Canvas(WIDTH, HEIGHT)
            draw_text(canvas, 0, 1, "NO DATA", (255, 0, 0))
            yield canvas.copy(), self.duration
            return

        # Each "page" shows as many rows as fit in the 10px height
        row_height = 2  # One text row + one spacer
        max_rows = max(1, HEIGHT // row_height)

        # Prepare list of pages, each with a slice of entries
        pages: list[list[dict[str, Any]]] = []
        for start in range(0, len(self.entries), max_rows):
            pages.append(self.entries[start : start + max_rows])

        frame_delay = 0.5

        for _ in range(self.repeats):
            for page_index, page in enumerate(pages):
                canvas = Canvas(WIDTH, HEIGHT)
                canvas.clear(BLACK)

                y = 0
                if self.title and page_index == 0:
                    draw_text(canvas, 0, y, self.title, self.name_color)
                    y += row_height

                for i, entry in enumerate(page, start=1):
                    name = str(entry.get("name", ""))[:10]
                    score = entry.get("score", 0)
                    label = name
                    if self.show_rank:
                        rank = (page_index * max_rows) + i
                        label = f"{rank}. {label}"
                    text = f"{label} {score}"
                    draw_text(canvas, 0, y, text, self.name_color)
                    y += row_height

                yield canvas.copy(), frame_delay
