"""Leaderboard display card."""

import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..fonts import draw_text, text_width
from ..types import BLACK, GOLD, HEIGHT, RGB, WHITE, WIDTH, Frame
from .base import Card, CardContext, register_card

# Podium colors
GOLD_COLOR: RGB = (255, 215, 0)
SILVER_COLOR: RGB = (192, 192, 192)
BRONZE_COLOR: RGB = (205, 127, 50)


@register_card
class LeaderboardCard(Card):
    """Display a scrolling leaderboard.

    Config options:
        entries: List of {"name": str, "score": int} dicts
        title: Optional title to show before entries
        name_color: Color for names (default: white)
        score_color: Color for scores (default: gold)
        scroll_speed: Pixels per second (default: 30)
        show_rank: Show position numbers (default: true)
        podium_colors: Use gold/silver/bronze for top 3 (default: true)
    """

    card_type = "leaderboard"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.entries: list[dict] = self.config.get("entries", [])
        self.title: str = self.config.get("title", "")
        self.name_color: RGB = tuple(self.config.get("name_color", WHITE))  # type: ignore
        self.score_color: RGB = tuple(self.config.get("score_color", GOLD_COLOR))  # type: ignore
        self.scroll_speed: float = self.config.get("scroll_speed", 30.0)
        self.repeats: int = self.config.get("repeats", 1)
        self.show_rank: bool = self.config.get("show_rank", True)
        self.podium_colors: bool = self.config.get("podium_colors", True)

    def _get_rank_color(self, rank: int) -> RGB:
        """Get color for rank position."""
        if not self.podium_colors:
            return self.name_color
        if rank == 1:
            return GOLD_COLOR
        elif rank == 2:
            return SILVER_COLOR
        elif rank == 3:
            return BRONZE_COLOR
        return self.name_color

    def _build_scroll_text(self) -> str:
        """Build the full scrolling text for the leaderboard."""
        parts = []

        if self.title:
            parts.append(self.title)
            parts.append("  ")

        for i, entry in enumerate(self.entries):
            rank = i + 1
            name = entry.get("name", "???")
            score = entry.get("score", 0)

            if self.show_rank:
                parts.append(f"{rank}.")
            parts.append(f"{name} {score}")
            parts.append("  ")  # Spacing between entries

        return "".join(parts)

    def _render_frame(self, offset: int) -> Frame:
        """Render a single frame of scrolling leaderboard."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        # Build colored segments
        x_pos = WIDTH - offset
        y = 1

        if self.title:
            draw_text(canvas, x_pos, y, self.title, self.name_color)
            x_pos += text_width(self.title) + text_width("  ")

        for i, entry in enumerate(self.entries):
            rank = i + 1
            name = entry.get("name", "???")
            score = entry.get("score", 0)
            rank_color = self._get_rank_color(rank)

            # Draw rank number
            if self.show_rank:
                rank_str = f"{rank}."
                draw_text(canvas, x_pos, y, rank_str, rank_color)
                x_pos += text_width(rank_str)

            # Draw name
            draw_text(canvas, x_pos, y, name, rank_color)
            x_pos += text_width(name)

            # Draw score
            score_str = f" {score}"
            draw_text(canvas, x_pos, y, score_str, self.score_color)
            x_pos += text_width(score_str)

            # Spacing
            x_pos += text_width("  ")

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate leaderboard frames."""
        if not self.entries:
            # No entries, show placeholder
            canvas = Canvas(WIDTH, HEIGHT)
            draw_text(canvas, 0, 1, "NO DATA", (255, 0, 0))
            frame = canvas.copy()
            start_time = time.time()
            while time.time() - start_time < self.duration:
                yield frame, 1.0
            return

        # Calculate total scroll distance
        full_text = self._build_scroll_text()
        content_width = text_width(full_text)
        total_scroll = content_width + WIDTH + 1

        # Animation parameters
        pixels_per_frame = self.scroll_speed / 30.0
        frame_delay = 1.0 / 30.0

        offset = 0.0
        scrolls_done = 0

        while scrolls_done < self.repeats:
            frame = self._render_frame(int(offset))
            yield frame, frame_delay

            offset += pixels_per_frame

            if offset >= total_scroll:
                scrolls_done += 1
                offset = 0.0
