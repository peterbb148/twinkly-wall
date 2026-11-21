"""Static and scrolling text card."""

import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..fonts import (
    CHAR_HEIGHT,
    draw_text,
    draw_text_vertical_stacked,
    text_width,
    vertical_text_height,
)
from ..types import BLACK, HEIGHT, RGB, WHITE, WIDTH, Frame
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
    1: (0, 180, 0),  # Green tree
    2: (139, 69, 19),  # Brown trunk
    3: (255, 215, 0),  # Gold star
}

AVAILABLE_SPRITES: dict[str, tuple[list[list[int]], dict[int, RGB]]] = {
    "tree": (SPRITE_TREE, TREE_COLORS),
}


@register_card
class TextCard(Card):
    """Display static or scrolling text.

    Config options:
        text: The message to display (required)
        color: RGB tuple for text color (default: white)
        bgcolor: RGB tuple for background color (default: black)
        scroll: Enable scrolling for long text (default: auto)
        scroll_direction: horizontal, vertical_up, vertical_down,
            vertical_rotated_up, or vertical_rotated_down (default: horizontal)
        scroll_speed: Pixels per second for scrolling (default: 30)
        scroll_complete: Wait for text to fully scroll before ending (default: true)
        align: Text alignment - left, center, right (default: center)
        prefix_sprite: Sprite to show before text - tree (default: none)
        suffix_sprite: Sprite to show after text - tree (default: none)
    """

    card_type = "text"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.text: str = self.config.get("text", "")
        self.color: RGB = tuple(self.config.get("color", WHITE))  # type: ignore
        self.bgcolor: RGB = tuple(self.config.get("bgcolor", BLACK))  # type: ignore
        self.scroll: bool | str = self.config.get("scroll", "auto")
        self.scroll_direction: str = self.config.get("scroll_direction", "horizontal")
        self.scroll_speed: float = self.config.get("scroll_speed", 30.0)
        self.scroll_complete: bool = self.config.get("scroll_complete", True)
        self.repeats: int = self.config.get("repeats", 1)
        self.align: str = self.config.get("align", "center")
        self.prefix_sprite: str | None = self.config.get("prefix_sprite", None)
        self.suffix_sprite: str | None = self.config.get("suffix_sprite", None)

    def _should_scroll(self) -> bool:
        """Determine if text should scroll."""
        if self.scroll == "auto":
            return self._get_content_width() > WIDTH
        return bool(self.scroll)

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

    def _get_content_width(self) -> int:
        """Get total width of content including sprites."""
        width = text_width(self.text)
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

    def _render_static(self) -> Frame:
        """Render static (non-scrolling) text."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(self.bgcolor)

        tw = text_width(self.text)

        # Calculate x position based on alignment
        if self.align == "left":
            x = 0
        elif self.align == "right":
            x = max(0, WIDTH - tw)
        else:  # center
            x = max(0, (WIDTH - tw) // 2)

        # Center vertically
        y = 1

        draw_text(canvas, x, y, self.text, self.color)
        return canvas.copy()

    def _render_vertical_frame(self, y_offset: int) -> Frame:
        """Render a single frame of vertically scrolling text.

        Args:
            y_offset: Top y position of the text.

        Returns:
            Frame with text drawn at the given vertical offset.
        """
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(self.bgcolor)

        tw = text_width(self.text)

        # Horizontal position based on alignment
        if self.align == "left":
            x = 0
        elif self.align == "right":
            x = max(0, WIDTH - tw)
        else:
            x = max(0, (WIDTH - tw) // 2)

        draw_text(canvas, x, y_offset, self.text, self.color)
        return canvas.copy()

    def _render_vertical_rotated_frame(self, y_offset: int) -> Frame:
        """Render a single frame of vertically stacked text (one char per row)."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(self.bgcolor)

        column_width = CHAR_HEIGHT
        x = max(0, (WIDTH - column_width) // 2)

        draw_text_vertical_stacked(canvas, x, y_offset, self.text, self.color)
        return canvas.copy()

    def _render_scrolling_frame(self, offset: int, content_width: int) -> Frame:
        """Render a single frame of scrolling text.

        Args:
            offset: Current scroll offset (0 = text starts at right edge)
            content_width: Total width of the text content
        """
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(self.bgcolor)

        # Content starts off-screen to the right, scrolls left
        x = WIDTH - offset

        # Draw prefix sprite
        if self.prefix_sprite:
            sprite_data = self._get_sprite(self.prefix_sprite)
            if sprite_data:
                sprite, colors = sprite_data
                sprite_w = self._draw_sprite(canvas, x, sprite, colors)
                x += sprite_w + 2  # sprite + spacing

        # Draw text (center vertically)
        y = 1
        draw_text(canvas, x, y, self.text, self.color)
        x += text_width(self.text)

        # Draw suffix sprite
        if self.suffix_sprite:
            sprite_data = self._get_sprite(self.suffix_sprite)
            if sprite_data:
                sprite, colors = sprite_data
                x += 2  # spacing before sprite
                self._draw_sprite(canvas, x, sprite, colors)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate text frames, scrolling if needed."""
        if not self._should_scroll():
            # Static display
            frame = self._render_static()
            start_time = time.time()
            while time.time() - start_time < self.duration:
                yield frame, 0.5  # Update every 0.5s for static
        elif self.scroll_direction == "horizontal":
            # Scrolling display
            content_width = self._get_content_width()
            total_scroll = content_width + WIDTH + 1  # Full scroll distance

            # Calculate frame timing
            pixels_per_frame = self.scroll_speed / 30.0  # ~30 FPS target
            frame_delay = 1.0 / 30.0

            offset = 0.0
            scrolls_done = 0

            while scrolls_done < self.repeats:
                frame = self._render_scrolling_frame(int(offset), content_width)
                yield frame, frame_delay

                offset += pixels_per_frame

                # Check if scroll completed
                if offset >= total_scroll:
                    scrolls_done += 1
                    offset = 0.0
        elif self.scroll_direction in ("vertical_up", "vertical_down"):
            # Vertical scrolling display (text moves along Y-axis, horizontal glyphs)
            text_height = 7  # Font height in pixels
            start_y = HEIGHT  # Start just below the bottom
            end_y = -text_height  # End just above the top
            total_scroll = start_y - end_y

            pixels_per_frame = self.scroll_speed / 30.0  # ~30 FPS
            frame_delay = 1.0 / 30.0

            scrolls_done = 0

            while scrolls_done < self.repeats:
                offset = 0.0
                while offset < total_scroll:
                    if self.scroll_direction == "vertical_up":
                        y = start_y - int(offset)
                    else:  # vertical_down
                        y = end_y + int(offset)

                    frame = self._render_vertical_frame(y)
                    yield frame, frame_delay
                    offset += pixels_per_frame

                scrolls_done += 1
        elif self.scroll_direction in ("vertical_rotated_up", "vertical_rotated_down"):
            # Vertical scrolling with rotated glyphs stacked along Y-axis
            text_height = vertical_text_height(self.text)
            start_y = HEIGHT
            end_y = -text_height
            total_scroll = start_y - end_y

            pixels_per_frame = self.scroll_speed / 30.0  # ~30 FPS
            frame_delay = 1.0 / 30.0

            scrolls_done = 0

            while scrolls_done < self.repeats:
                offset = 0.0
                while offset < total_scroll:
                    if self.scroll_direction == "vertical_rotated_up":
                        y = start_y - int(offset)
                    else:  # vertical_rotated_down
                        y = end_y + int(offset)

                    frame = self._render_vertical_rotated_frame(y)
                    yield frame, frame_delay
                    offset += pixels_per_frame

                scrolls_done += 1
        else:
            # Fallback to horizontal scrolling
            content_width = self._get_content_width()
            total_scroll = content_width + WIDTH + 1  # Full scroll distance

            pixels_per_frame = self.scroll_speed / 30.0  # ~30 FPS target
            frame_delay = 1.0 / 30.0

            offset = 0.0
            scrolls_done = 0

            while scrolls_done < self.repeats:
                frame = self._render_scrolling_frame(int(offset), content_width)
                yield frame, frame_delay

                offset += pixels_per_frame

                # Check if scroll completed
                if offset >= total_scroll:
                    scrolls_done += 1
                    offset = 0.0
