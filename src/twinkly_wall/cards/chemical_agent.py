"""Chemical Agent celebration card."""

from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..fonts import draw_text, text_width
from ..types import BLACK, HEIGHT, RGB, WHITE, WIDTH, Frame
from .base import Card, CardContext, register_card

# Simple test tube sprite (5x7), intended to evoke a test tube emoji.
# 0 = transparent, 1 = glass outline, 2 = liquid, 3 = highlight
SPRITE_TEST_TUBE: list[list[int]] = [
    [0, 1, 1, 1, 0],
    [0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0],
    [0, 1, 2, 1, 0],
    [0, 1, 2, 1, 0],
    [0, 1, 2, 1, 0],
    [0, 0, 3, 0, 0],
]

TEST_TUBE_COLORS: dict[int, RGB] = {
    1: (200, 200, 255),  # Glass outline
    2: (0, 180, 255),  # Liquid
    3: (255, 255, 255),  # Highlight
}


@register_card
class ChemicalAgentCard(Card):
    """Scrolling celebration message for Chemical Agent.

    This card shows a fixed celebratory message with a test tube icon
    before and after the text:

        "Chemical Agent won the Copilot Innovation Challenge!!"

    Config options:
        text: Override the default message text (optional)
        color: RGB tuple for text color (default: yellowish white)
        bgcolor: RGB tuple for background color (default: black)
        scroll_speed: Pixels per second for scrolling (default: 30)
        repeats: Number of scroll loops (default: 1)
    """

    card_type = "chemical_agent"

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the Chemical Agent card."""
        super().__init__(config)
        default_text = "Chemical Agent won the Copilot Innovation Challenge!!"
        self.text: str = self.config.get("text", default_text)
        default_color: RGB = (255, 255, 0)
        self.color: RGB = tuple(self.config.get("color", default_color))  # type: ignore
        self.bgcolor: RGB = tuple(self.config.get("bgcolor", BLACK))  # type: ignore
        self.scroll_speed: float = float(self.config.get("scroll_speed", 30.0))
        self.repeats: int = int(self.config.get("repeats", 1))

    def _draw_sprite(
        self,
        canvas: Canvas,
        x: int,
        sprite: list[list[int]],
        colors: dict[int, RGB],
    ) -> int:
        """Draw a sprite on the canvas and return its width."""
        sprite_height = len(sprite)
        sprite_width = len(sprite[0]) if sprite else 0
        y_offset = (HEIGHT - sprite_height) // 2

        for row_idx, row in enumerate(sprite):
            for col_idx, pixel in enumerate(row):
                if pixel == 0:
                    continue
                color = colors.get(pixel, WHITE)
                px = x + col_idx
                py = y_offset + row_idx
                if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                    canvas.set_pixel(px, py, color)

        return sprite_width

    def _render_frame(self, offset: int, content_width: int) -> Frame:
        """Render a single frame of the scrolling celebration."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(self.bgcolor)

        x = WIDTH - offset

        # Leading test tube
        sprite_width = self._draw_sprite(canvas, x, SPRITE_TEST_TUBE, TEST_TUBE_COLORS)
        x += sprite_width + 2  # sprite + spacing

        # Text
        y = 1
        draw_text(canvas, x, y, self.text, self.color)
        x += text_width(self.text) + 2

        # Trailing test tube
        self._draw_sprite(canvas, x, SPRITE_TEST_TUBE, TEST_TUBE_COLORS)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate scrolling frames for the Chemical Agent celebration."""
        # Compute total content width (sprite + spacing + text + spacing + sprite)
        text_w = text_width(self.text)
        sprite_w = len(SPRITE_TEST_TUBE[0])
        content_width = sprite_w + 2 + text_w + 2 + sprite_w
        total_scroll = content_width + WIDTH + 1

        pixels_per_frame = self.scroll_speed / 30.0
        frame_delay = 1.0 / 30.0

        scrolls_done = 0
        while scrolls_done < self.repeats:
            offset = 0.0
            while offset < total_scroll:
                frame = self._render_frame(int(offset), content_width)
                yield frame, frame_delay
                offset += pixels_per_frame

            scrolls_done += 1
