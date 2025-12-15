"""Science Magazine paper announcement card."""

from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..fonts import draw_text, text_width
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card

# Science Magazine colors
SCIENCE_RED: RGB = (187, 0, 0)  # Science Magazine red
WHITE: RGB = (255, 255, 255)


@register_card
class SciencePaperCard(Card):
    """Science Magazine paper announcement with logo-style text.

    Displays "Science" in a red box with white text (like the magazine logo),
    followed by the paper title in white text.

    Config options:
        title: Paper title (required)
        prefix_text: Text before title (default: "Science")
        scroll_speed: Pixels per second (default: 25)
        box_padding: Padding around Science text (default: 1)
    """

    card_type = "science_paper"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.title: str = self.config.get("title", "Paper Title Goes Here")
        self.prefix_text: str = self.config.get("prefix_text", "Science")
        self.scroll_speed: float = self.config.get("scroll_speed", 40.0)
        self.box_padding: int = self.config.get("box_padding", 1)
        self.repeats: int = self.config.get("repeats", 1)

    def _get_content_width(self) -> int:
        """Get total width of all content."""
        # Width of "Science" box
        prefix_w = text_width(self.prefix_text)
        box_width = prefix_w + self.box_padding * 2

        # Gap between box and title
        gap = 4

        # Width of title
        title_w = text_width(self.title)

        return box_width + gap + title_w

    def _render_frame(self, offset: int) -> Frame:
        """Render a single frame."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        x = WIDTH - offset

        # Draw "Science" in red box
        prefix_w = text_width(self.prefix_text)
        box_width = prefix_w + self.box_padding * 2
        box_height = 9  # Font height + padding

        # Draw red background box
        for bx in range(box_width):
            for by in range(box_height):
                px = x + bx
                py = by
                if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                    canvas.set_pixel(px, py, SCIENCE_RED)

        # Draw "Science" text in white on the red box
        draw_text(canvas, x + self.box_padding, 1, self.prefix_text, WHITE)

        # Draw title after the box with a gap
        title_x = x + box_width + 4
        draw_text(canvas, title_x, 1, self.title, WHITE)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate animation frames."""
        content_width = self._get_content_width()
        total_scroll = content_width + WIDTH + 1

        frame_delay = 1.0 / 30.0
        pixels_per_frame = self.scroll_speed / 30.0

        offset = 0.0
        scrolls_done = 0

        while scrolls_done < self.repeats:
            frame = self._render_frame(int(offset))
            yield frame, frame_delay

            offset += pixels_per_frame

            if offset >= total_scroll:
                scrolls_done += 1
                offset = 0.0
