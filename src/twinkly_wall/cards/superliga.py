"""Danish Superliga standings card."""

import logging
import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..datasources.superliga import SuperligaDataSource, SuperligaError
from ..fonts import draw_text, text_width
from ..types import BLACK, HEIGHT, RGB, WHITE, WIDTH, Frame
from .base import Card, CardContext, register_card

logger = logging.getLogger(__name__)

# Team colors and short names mapping
# Key: Full team name from API, Value: (short_name, RGB color)
TEAM_INFO: dict[str, tuple[str, RGB]] = {
    "FC Midtjylland": ("FCM", (255, 50, 50)),      # Red
    "FC Copenhagen": ("FCK", (255, 255, 255)),     # White
    "AGF Aarhus": ("AGF", (255, 255, 255)),        # White
    "AGF": ("AGF", (255, 255, 255)),               # White (alt name)
    "Randers FC": ("RFC", (135, 206, 250)),        # Light blue
    "Randers": ("RFC", (135, 206, 250)),           # Light blue (alt)
    "Brondby IF": ("BIF", (255, 220, 0)),          # Yellow
    "Brøndby": ("BIF", (255, 220, 0)),             # Yellow (alt)
    "Silkeborg IF": ("SIF", (50, 200, 50)),        # Green
    "Silkeborg": ("SIF", (50, 200, 50)),           # Green (alt)
    "FC Nordsjaelland": ("FCN", (255, 140, 0)),    # Orange
    "FC Nordsjælland": ("FCN", (255, 140, 0)),     # Orange (alt)
    "Aalborg BK": ("AaB", (255, 50, 50)),          # Red
    "AaB": ("AaB", (255, 50, 50)),                 # Red (alt)
    "Viborg FF": ("VFF", (50, 200, 50)),           # Green
    "Viborg": ("VFF", (50, 200, 50)),              # Green (alt)
    "Lyngby BK": ("LBK", (0, 100, 255)),           # Blue
    "Lyngby": ("LBK", (0, 100, 255)),              # Blue (alt)
    "Vejle BK": ("VB", (255, 50, 50)),             # Red
    "Vejle": ("VB", (255, 50, 50)),                # Red (alt)
    "OB": ("OB", (0, 100, 255)),                   # Blue
    "Odense Boldklub": ("OB", (0, 100, 255)),      # Blue (alt)
    "SonderjyskE": ("SJF", (0, 100, 255)),         # Blue
    "Sønderjyske": ("SJF", (0, 100, 255)),         # Blue (alt)
    "Hvidovre IF": ("HIF", (255, 50, 50)),         # Red
    "Hvidovre": ("HIF", (255, 50, 50)),            # Red (alt)
    "AC Horsens": ("ACH", (255, 220, 0)),          # Yellow
    "Horsens": ("ACH", (255, 220, 0)),             # Yellow (alt)
    "FC Fredericia": ("FCF", (255, 50, 50)),       # Red
    "Fredericia": ("FCF", (255, 50, 50)),          # Red (alt)
}

# Fallback color for unknown teams
DEFAULT_COLOR: RGB = (255, 255, 255)


def get_team_display(team_name: str) -> tuple[str, RGB]:
    """Get short name and color for a team.

    Args:
        team_name: Full team name from API.

    Returns:
        Tuple of (short_name, color).
    """
    if team_name in TEAM_INFO:
        return TEAM_INFO[team_name]

    # Try partial match for teams with slight name variations
    for full_name, info in TEAM_INFO.items():
        if full_name.lower() in team_name.lower() or team_name.lower() in full_name.lower():
            return info

    # Generate short name from first 3 chars
    short = team_name[:3].upper()
    return (short, DEFAULT_COLOR)


@register_card
class SuperligaCard(Card):
    """Display Danish Superliga standings.

    Config options:
        season: Season to display (e.g., "2024-2025"). Default: current season.
        max_teams: Maximum teams to show (default: 12 for full league).
        scroll_speed: Pixels per second (default: 30).
        show_points: Show points after team name (default: true).
        separator: Text between entries (default: " ").
        scroll_complete: Wait for full scroll before ending (default: true).
    """

    card_type = "superliga"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.season: str | None = self.config.get("season")
        self.max_teams: int = self.config.get("max_teams", 12)
        self.scroll_speed: float = self.config.get("scroll_speed", 30.0)
        self.show_points: bool = self.config.get("show_points", True)
        self.separator: str = self.config.get("separator", " ")
        self.scroll_complete: bool = self.config.get("scroll_complete", True)
        self._datasource: SuperligaDataSource | None = None

    def _get_datasource(self, ctx: CardContext) -> SuperligaDataSource:
        """Get or create the datasource."""
        if self._datasource is None:
            # Check if provided in context
            ds = ctx.datasources.get("superliga")
            if ds is not None:
                self._datasource = ds
            else:
                self._datasource = SuperligaDataSource(season=self.season)
        return self._datasource

    def _render_frame(
        self,
        offset: int,
        entries: list[tuple[int, str, int, RGB]],
    ) -> Frame:
        """Render a single frame of scrolling standings.

        Args:
            offset: Current scroll offset in pixels.
            entries: List of (rank, short_name, points, color) tuples.
        """
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        x_pos = WIDTH - offset
        y = 1

        for rank, name, points, color in entries:
            # Draw rank
            rank_str = f"{rank}."
            draw_text(canvas, x_pos, y, rank_str, color)
            x_pos += text_width(rank_str)

            # Draw team name
            draw_text(canvas, x_pos, y, name, color)
            x_pos += text_width(name)

            # Draw points if enabled
            if self.show_points:
                pts_str = f" {points}"
                draw_text(canvas, x_pos, y, pts_str, color)
                x_pos += text_width(pts_str)

            # Add separator
            x_pos += text_width(self.separator)

        return canvas.copy()

    def _calculate_content_width(
        self, entries: list[tuple[int, str, int, RGB]]
    ) -> int:
        """Calculate total width of scrolling content."""
        total = 0
        for rank, name, points, _ in entries:
            total += text_width(f"{rank}.")
            total += text_width(name)
            if self.show_points:
                total += text_width(f" {points}")
            total += text_width(self.separator)
        return total

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate Superliga standings frames."""
        # Try to fetch standings
        try:
            ds = self._get_datasource(ctx)
            data = ds.get_standings()
            standings = data.standings[: self.max_teams]
        except SuperligaError as e:
            logger.error(f"Failed to get Superliga standings: {e}")
            # Show error message
            canvas = Canvas(WIDTH, HEIGHT)
            draw_text(canvas, 0, 1, "SUPERLIGA", (255, 0, 0))
            frame = canvas.copy()
            start_time = time.time()
            while time.time() - start_time < self.duration:
                yield frame, 1.0
            return

        if not standings:
            canvas = Canvas(WIDTH, HEIGHT)
            draw_text(canvas, 0, 1, "NO DATA", (255, 0, 0))
            frame = canvas.copy()
            start_time = time.time()
            while time.time() - start_time < self.duration:
                yield frame, 1.0
            return

        # Build display entries: (rank, short_name, points, color)
        entries: list[tuple[int, str, int, RGB]] = []
        for standing in standings:
            short_name, color = get_team_display(standing.team_name)
            entries.append((standing.rank, short_name, standing.points, color))

        # Calculate scroll parameters
        content_width = self._calculate_content_width(entries)
        total_scroll = content_width + WIDTH

        # Animation parameters
        pixels_per_frame = self.scroll_speed / 30.0
        frame_delay = 1.0 / 30.0

        start_time = time.time()
        offset = 0.0
        scroll_completed = False

        while True:
            frame = self._render_frame(int(offset), entries)
            yield frame, frame_delay

            offset += pixels_per_frame

            if offset >= total_scroll:
                scroll_completed = True
                offset = 0.0

            elapsed = time.time() - start_time
            if self.scroll_complete:
                # Wait for at least one complete scroll AND duration
                if scroll_completed and elapsed >= self.duration:
                    break
            else:
                # Just respect duration
                if elapsed >= self.duration:
                    break
