"""Countdown timer card."""

import time
from collections.abc import Iterator
from datetime import datetime
from typing import Any

from ..canvas import Canvas
from ..fonts import draw_text, text_width
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card

# Small Christmas tree sprite (5x7) - fits in 10px display
SPRITE_TREE: list[list[int]] = [
    [0, 0, 3, 0, 0],  # 3 = gold star
    [0, 0, 1, 0, 0],
    [0, 1, 1, 1, 0],
    [0, 1, 1, 1, 0],
    [1, 1, 1, 1, 1],
    [0, 0, 2, 0, 0],  # 2 = brown trunk
    [0, 0, 2, 0, 0],
]

TREE_COLORS: dict[int, RGB] = {
    1: (0, 180, 0),    # Green tree
    2: (139, 69, 19),  # Brown trunk
    3: (255, 215, 0),  # Gold star
}

AVAILABLE_SPRITES: dict[str, tuple[list[list[int]], dict[int, RGB]]] = {
    "tree": (SPRITE_TREE, TREE_COLORS),
}


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
        prefix_sprite: Sprite to show before text - tree (default: none)
        suffix_sprite: Sprite to show after text - tree (default: none)
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
        self.repeats: int = self.config.get("repeats", 1)
        self.prefix_sprite: str | None = self.config.get("prefix_sprite", None)
        self.suffix_sprite: str | None = self.config.get("suffix_sprite", None)

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

    def _get_sprite(self, name: str) -> tuple[list[list[int]], dict[int, RGB]] | None:
        """Get sprite data by name."""
        return AVAILABLE_SPRITES.get(name)

    def _get_sprite_width(self, name: str | None) -> int:
        """Get width of a sprite (including spacing)."""
        if not name:
            return 0
        sprite_data = self._get_sprite(name)
        if not sprite_data:
            return 0
        sprite, _ = sprite_data
        return len(sprite[0]) + 2  # sprite width + spacing

    def _get_content_width(self, countdown_text: str) -> int:
        """Get total width of content including sprites."""
        width = text_width(self._get_display_text(countdown_text))
        width += self._get_sprite_width(self.prefix_sprite)
        width += self._get_sprite_width(self.suffix_sprite)
        return width

    def _draw_sprite(
        self, canvas: Canvas, x: int, sprite: list[list[int]], colors: dict[int, RGB]
    ) -> int:
        """Draw a sprite on the canvas, return width drawn."""
        sprite_height = len(sprite)
        sprite_width = len(sprite[0]) if sprite else 0

        # Center vertically
        y_offset = (HEIGHT - sprite_height) // 2

        for row_idx, row in enumerate(sprite):
            for col_idx, pixel in enumerate(row):
                if pixel != 0:
                    color = colors.get(pixel, (255, 255, 255))
                    px = x + col_idx
                    py = y_offset + row_idx
                    if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                        canvas.set_pixel(px, py, color)

        return sprite_width

    def _should_scroll(self, countdown_text: str) -> bool:
        """Determine if text should scroll."""
        if self.scroll == "auto":
            return self._get_content_width(countdown_text) > WIDTH
        return bool(self.scroll)

    def _render_frame(self, countdown_text: str, offset: int = 0) -> Frame:
        """Render the countdown display."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        content_width = self._get_content_width(countdown_text)

        if offset > 0:
            # Scrolling mode
            x = WIDTH - offset
        else:
            # Centered mode
            x = (WIDTH - content_width) // 2

        # Draw prefix sprite
        if self.prefix_sprite:
            sprite_data = self._get_sprite(self.prefix_sprite)
            if sprite_data:
                sprite, colors = sprite_data
                sprite_w = self._draw_sprite(canvas, x, sprite, colors)
                x += sprite_w + 2  # sprite + spacing

        y = 1  # Vertically centered

        if self.label:
            # Draw label in gray, countdown in color
            draw_text(canvas, x, y, self.label, (150, 150, 150))
            label_w = text_width(self.label + " ")
            draw_text(canvas, x + label_w, y, countdown_text, self.color)
            x += text_width(self._get_display_text(countdown_text))
        else:
            draw_text(canvas, x, y, countdown_text, self.color)
            x += text_width(countdown_text)

        # Draw suffix sprite
        if self.suffix_sprite:
            sprite_data = self._get_sprite(self.suffix_sprite)
            if sprite_data:
                sprite, colors = sprite_data
                x += 2  # spacing before sprite
                self._draw_sprite(canvas, x, sprite, colors)

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

            offset = 0.0
            scrolls_done = 0

            while scrolls_done < self.repeats:
                now = datetime.now()
                remaining = (self.target - now).total_seconds()
                countdown_text = self._format_countdown(remaining)

                content_width = self._get_content_width(countdown_text)
                total_scroll = content_width + WIDTH

                frame = self._render_frame(countdown_text, int(offset))
                yield frame, frame_delay

                offset += pixels_per_frame

                if offset >= total_scroll:
                    scrolls_done += 1
                    offset = 0.0
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
