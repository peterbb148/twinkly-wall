"""Coffee break animation card."""

import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..fonts import (
    CHAR_WIDTH,
    draw_text,
    draw_text_vertical_stacked,
    text_width,
    vertical_text_height,
)
from ..types import BLACK, HEIGHT, PORTRAIT_HEIGHT, PORTRAIT_WIDTH, RGB, WIDTH, Frame
from .base import Card, CardContext, CardLayout, register_card

# Coffee mug sprite (9x8)
COFFEE_MUG: list[list[int]] = [
    [0, 0, 2, 0, 2, 0, 2, 0, 0],  # Steam
    [0, 0, 0, 2, 0, 2, 0, 0, 0],
    [0, 1, 1, 1, 1, 1, 1, 1, 0],  # Mug top
    [0, 1, 3, 3, 3, 3, 3, 1, 4],  # Coffee + handle
    [0, 1, 3, 3, 3, 3, 3, 1, 4],
    [0, 1, 3, 3, 3, 3, 3, 1, 4],
    [0, 1, 1, 1, 1, 1, 1, 1, 0],  # Mug bottom
    [0, 0, 1, 1, 1, 1, 1, 0, 0],
]

MUG_COLORS: dict[int, RGB] = {
    1: (240, 240, 240),  # White mug
    2: (150, 150, 150),  # Gray steam
    3: (101, 67, 33),  # Brown coffee
    4: (220, 220, 220),  # Handle
}


@register_card
class CoffeeCard(Card):
    """Coffee break animation with steaming mug.

    Config options:
        message: Message to display (default: "COFFEE")
        animate_steam: Animate rising steam (default: true)
        color: Text color (default: white)
    """

    card_type = "coffee"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.message: str = self.config.get("message", "COFFEE")
        self.animate_steam: bool = self.config.get("animate_steam", True)
        self.color: RGB = tuple(self.config.get("color", (255, 255, 255)))  # type: ignore

    def _draw_mug(self, canvas: Canvas, x: int, y: int, frame_num: int) -> None:
        """Draw the coffee mug with animated steam."""
        for sy, row in enumerate(COFFEE_MUG):
            for sx, pixel in enumerate(row):
                if pixel > 0:
                    px = x + sx
                    py = y + sy

                    # Animate steam
                    if pixel == 2 and self.animate_steam:
                        # Steam animation - rises and fades
                        offset = (frame_num // 5) % 3
                        if sy - offset < 0:
                            continue
                        py = y + sy - offset
                        # Fade steam
                        fade = 150 - offset * 40
                        color = (fade, fade, fade)
                    else:
                        color = MUG_COLORS.get(pixel, (255, 255, 255))

                    canvas.set_pixel(px, py, color)

    def _render_frame(self, frame_num: int) -> Frame:
        """Render the coffee break display."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        # Calculate positions
        mug_width = len(COFFEE_MUG[0])
        text_w = text_width(self.message)
        total_width = mug_width + 2 + text_w
        start_x = (WIDTH - total_width) // 2

        # Draw mug
        self._draw_mug(canvas, start_x, 1, frame_num)

        # Draw text next to mug
        text_x = start_x + mug_width + 2
        text_y = (HEIGHT - 5) // 2
        draw_text(canvas, text_x, text_y, self.message, self.color)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate coffee break animation frames."""
        start_time = time.time()
        frame_delay = 1.0 / 15.0  # Slower for relaxed vibe
        frame_num = 0

        while time.time() - start_time < self.duration:
            frame = self._render_frame(frame_num)
            yield frame, frame_delay
            frame_num += 1


@register_card
class CoffeeVerticalCard(CoffeeCard):
    """Show a steaming mug above upright lettering on a portrait wall."""

    card_type = "coffee_vertical"
    layout = CardLayout.portrait

    def _render_frame(self, frame_num: int) -> Frame:
        canvas = Canvas(PORTRAIT_WIDTH, PORTRAIT_HEIGHT)
        self._draw_mug(canvas, (canvas.width - len(COFFEE_MUG[0])) // 2, 1, frame_num)

        text_top = len(COFFEE_MUG) + 3
        caption = Canvas(canvas.width, canvas.height - text_top)
        height = vertical_text_height(self.message)
        overflow = max(0, height - caption.height)
        offset = min(overflow, (frame_num // 2) % (overflow + 15))
        y = max(0, (caption.height - height) // 2) - offset
        draw_text_vertical_stacked(
            caption, (canvas.width - CHAR_WIDTH) // 2, y, self.message, self.color
        )
        canvas.blit(caption.frame, dest_y=text_top)
        return canvas.copy()
