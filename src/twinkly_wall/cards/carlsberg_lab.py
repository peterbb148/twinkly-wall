"""Carlsberg Research Laboratory branding card."""

import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..fonts import draw_text, text_width
from ..types import HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card

# Carlsberg Hop logo sprite (9x9) - three overlapping leaf shapes
# Based on the Carlsberg brand mark with three hop leaves
SPRITE_HOP: list[list[int]] = [
    [0, 0, 0, 0, 1, 0, 0, 0, 0],  # top leaf tip
    [0, 0, 0, 1, 1, 1, 0, 0, 0],  # top leaf
    [0, 0, 1, 1, 1, 1, 1, 0, 0],  # top leaf base
    [0, 1, 1, 0, 1, 0, 1, 1, 0],  # side leaves start
    [1, 1, 1, 0, 0, 0, 1, 1, 1],  # side leaves middle
    [1, 1, 0, 0, 0, 0, 0, 1, 1],  # side leaves
    [1, 1, 0, 0, 0, 0, 0, 1, 1],  # side leaves
    [0, 1, 1, 0, 0, 0, 1, 1, 0],  # side leaves taper
    [0, 0, 1, 0, 0, 0, 1, 0, 0],  # side leaf tips
]

# Colors
WHITE: RGB = (255, 255, 255)
BLACK: RGB = (0, 0, 0)
CARLSBERG_GREEN: RGB = (40, 74, 65)  # #284a41


def draw_sprite(
    canvas: Canvas, sprite: list[list[int]], x: int, y: int, color: RGB
) -> None:
    """Draw a sprite on the canvas."""
    for sy, row in enumerate(sprite):
        for sx, pixel in enumerate(row):
            if pixel:
                px, py = x + sx, y + sy
                if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                    canvas.set_pixel(px, py, color)


@register_card
class CarlsbergLabCard(Card):
    """Carlsberg Research Laboratory branding card.

    Shows scrolling "Carlsberg Research Laboratory" text in black on white
    background (inverted), followed by the Carlsberg hop logo in black.

    Config options:
        scroll_speed: Pixels per second (default: 30)
        text_color: RGB for text (default: black)
        bg_color: RGB for background (default: white)
        hop_color: RGB for hop logo (default: black)
        show_hop: Show hop logo after text (default: true)
    """

    card_type = "carlsberg_lab"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.scroll_speed: float = self.config.get("scroll_speed", 30.0)
        self.repeats: int = self.config.get("repeats", 1)
        self.text_color: RGB = tuple(self.config.get("text_color", BLACK))  # type: ignore
        self.bg_color: RGB = tuple(self.config.get("bg_color", WHITE))  # type: ignore
        self.hop_color: RGB = tuple(self.config.get("hop_color", BLACK))  # type: ignore
        self.show_hop: bool = self.config.get("show_hop", True)

    def _render_frame(self, offset: int, total_text_width: int) -> Frame:
        """Render a frame with scrolling text and hop logo."""
        canvas = Canvas(WIDTH, HEIGHT)

        # Fill with background color (white for inverted look)
        for y in range(HEIGHT):
            for x in range(WIDTH):
                canvas.set_pixel(x, y, self.bg_color)

        text = "Carlsberg Research Laboratory"
        x = WIDTH - offset
        y = 1  # Vertically centered for 10px height

        # Draw the text
        draw_text(canvas, x, y, text, self.text_color)

        # Draw hop logo after the text
        if self.show_hop:
            hop_x = x + total_text_width + 10  # 10px gap after text
            hop_y = 0  # Top aligned (sprite is 9px tall, display is 10px)
            draw_sprite(canvas, SPRITE_HOP, hop_x, hop_y, self.hop_color)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate Carlsberg Lab branding frames."""
        text = "Carlsberg Research Laboratory"
        total_text_width = text_width(text)

        # Total content width includes text + gap + hop sprite
        hop_width = 9 if self.show_hop else 0
        gap = 10 if self.show_hop else 0
        content_width = total_text_width + gap + hop_width

        total_scroll = content_width + WIDTH

        frame_delay = 1.0 / 30.0  # 30 FPS
        pixels_per_frame = self.scroll_speed / 30.0

        offset = 0.0
        scrolls_done = 0

        while scrolls_done < self.repeats:
            frame = self._render_frame(int(offset), total_text_width)
            yield frame, frame_delay

            offset += pixels_per_frame

            if offset >= total_scroll:
                scrolls_done += 1
                offset = 0.0
