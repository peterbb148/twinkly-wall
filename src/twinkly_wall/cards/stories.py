"""Stories-style card that cycles short messages."""

from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..fonts import draw_text, text_width
from ..types import BLACK, HEIGHT, RGB, WHITE, WIDTH, Frame, blend_color
from .base import Card, CardContext, register_card


@register_card
class StoriesCard(Card):
    """Cycle through short text stories with fades.

    This card is inspired by "stories" UI patterns: it shows a sequence of
    short messages, fading between them.

    Config options:
        stories: List of text strings to show (required)
        color: RGB tuple for text color (default: white)
        bgcolor: RGB tuple for background color (default: black)
        story_duration: Seconds each story stays fully visible (default: 2.0)
        fade_duration: Seconds for fade in/out (default: 0.6)
        repeats: How many times to loop the list (default: 1)
    """

    card_type = "stories"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.stories: list[str] = list(self.config.get("stories", []))
        self.color: RGB = tuple(self.config.get("color", WHITE))  # type: ignore
        self.bgcolor: RGB = tuple(self.config.get("bgcolor", BLACK))  # type: ignore
        self.story_duration: float = float(self.config.get("story_duration", 2.0))
        self.fade_duration: float = float(self.config.get("fade_duration", 0.6))
        self.repeats: int = int(self.config.get("repeats", 1))

    def _render_story(self, text: str, color: RGB) -> Frame:
        """Render a single story centered on the canvas."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(self.bgcolor)

        tw = text_width(text)
        x = max(0, (WIDTH - tw) // 2)
        y = 1
        draw_text(canvas, x, y, text, color)
        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate story frames with fade transitions."""
        if not self.stories:
            canvas = Canvas(WIDTH, HEIGHT)
            canvas.clear(self.bgcolor)
            yield canvas.copy(), self.duration
            return

        frame_delay = 1.0 / 30.0
        fade_frames = max(1, int(self.fade_duration / frame_delay))
        hold_frames = max(1, int(self.story_duration / frame_delay))

        loop_count = max(1, self.repeats)

        for _ in range(loop_count):
            for text in self.stories:
                # Fade in
                for i in range(fade_frames):
                    alpha = (i + 1) / fade_frames
                    color = blend_color(self.bgcolor, self.color, alpha)
                    frame = self._render_story(text, color)
                    yield frame, frame_delay

                # Hold
                base_frame = self._render_story(text, self.color)
                for _ in range(hold_frames):
                    yield base_frame, frame_delay

                # Fade out
                for i in range(fade_frames):
                    alpha = 1.0 - ((i + 1) / fade_frames)
                    color = blend_color(self.bgcolor, self.color, alpha)
                    frame = self._render_story(text, color)
                    yield frame, frame_delay
