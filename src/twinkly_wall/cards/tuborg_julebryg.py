"""Tuborg Julebryg promotional card."""

from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..fonts import draw_text, text_width
from ..types import HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card

# Tuborg blue background
TUBORG_BLUE: RGB = (0, 51, 160)

# Small Santa sprite (7x8) - fits on 10px display
SPRITE_SANTA: list[list[int]] = [
    [0, 0, 1, 1, 1, 0, 0],  # Hat top
    [0, 0, 1, 1, 1, 3, 0],  # Hat with pompom (3 = white)
    [0, 0, 2, 2, 2, 0, 0],  # Face (2 = skin)
    [0, 0, 3, 2, 3, 0, 0],  # Beard
    [0, 1, 1, 1, 1, 1, 0],  # Body top
    [0, 1, 3, 1, 3, 1, 0],  # Body with buttons
    [0, 1, 1, 1, 1, 1, 0],  # Body bottom
    [0, 0, 4, 0, 4, 0, 0],  # Boots (4 = black)
]

SANTA_COLORS: dict[int, RGB] = {
    1: (200, 0, 0),  # Red suit
    2: (255, 200, 150),  # Skin
    3: (255, 255, 255),  # White beard/buttons/pompom
    4: (40, 40, 40),  # Black boots
}


@register_card
class TuborgJulebryg(Card):
    """Tuborg Julebryg promotional scrolling text with Santas.

    Config options:
        text: Message text (default: "Tuborg Snebajer 0.0% NUL JUL - Driving home for Christmas")
        scroll_speed: Pixels per second (default: 30)
        num_santas: Number of Santa sprites following (default: 3)
        santa_spacing: Pixels between Santas (default: 10)
    """

    card_type = "tuborg_julebryg"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.text: str = self.config.get(
            "text", "Tuborg Snebajer 0.0% NUL JUL - Driving home for Christmas"
        )
        self.scroll_speed: float = self.config.get("scroll_speed", 30.0)
        self.num_santas: int = self.config.get("num_santas", 3)
        self.santa_spacing: int = self.config.get("santa_spacing", 10)
        self.repeats: int = self.config.get("repeats", 1)

    def _get_content_width(self) -> int:
        """Get total width of text plus Santas."""
        text_w = text_width(self.text)
        sprite_width = len(SPRITE_SANTA[0])
        santas_width = self.num_santas * sprite_width + (self.num_santas - 1) * self.santa_spacing
        return text_w + 4 + santas_width  # 4 = gap between text and santas

    def _draw_santa(self, canvas: Canvas, x: int, y: int) -> None:
        """Draw a Santa sprite on the canvas."""
        for row_idx, row in enumerate(SPRITE_SANTA):
            for col_idx, pixel in enumerate(row):
                if pixel != 0:
                    color = SANTA_COLORS.get(pixel, (255, 255, 255))
                    px = x + col_idx
                    py = y + row_idx
                    if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                        canvas.set_pixel(px, py, color)

    def _render_frame(self, offset: int) -> Frame:
        """Render a single frame."""
        canvas = Canvas(WIDTH, HEIGHT)
        # Fill with Tuborg blue
        for y in range(HEIGHT):
            for x in range(WIDTH):
                canvas.set_pixel(x, y, TUBORG_BLUE)

        # Calculate text position
        x = WIDTH - offset

        # Draw text in white
        draw_text(canvas, x, 1, self.text, (255, 255, 255))

        # Draw Santas after text
        text_w = text_width(self.text)
        sprite_width = len(SPRITE_SANTA[0])
        santa_start_x = x + text_w + 4

        for i in range(self.num_santas):
            santa_x = santa_start_x + i * (sprite_width + self.santa_spacing)
            self._draw_santa(canvas, santa_x, 1)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate animation frames."""
        pixels_per_frame = self.scroll_speed / 30.0
        frame_delay = 1.0 / 30.0

        content_width = self._get_content_width()
        total_scroll = content_width + WIDTH + 1

        offset = 0.0
        scrolls_done = 0

        while scrolls_done < self.repeats:
            frame = self._render_frame(int(offset))
            yield frame, frame_delay

            offset += pixels_per_frame

            # Check if scroll completed
            if offset >= total_scroll:
                scrolls_done += 1
                offset = 0.0
