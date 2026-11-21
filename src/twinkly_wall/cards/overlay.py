"""Overlay card - add scrolling text on top of any animation."""

from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..fonts import draw_text, text_width
from ..types import HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, create_card, register_card


@register_card
class OverlayCard(Card):
    """Overlay scrolling text on any background animation.

    Config options:
        background: Dict with background card config (type + options)
        text: Text to scroll across the animation
        text_color: RGB color for text (default: [255, 255, 255] white)
        scroll_speed: Pixels per second (default: 30)
        repeats: Number of times to scroll text (default: 1)
        y_position: Vertical position for text (default: 1)

    Example:
        - type: overlay
          background:
            type: ocean
            wave_speed: 1.0
          text: "Hello World"
          text_color: [255, 255, 255]
          scroll_speed: 30
          repeats: 1
    """

    card_type = "overlay"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.background_config: dict[str, Any] = self.config.get("background", {})
        self.text: str = self.config.get("text", "")
        text_color = self.config.get("text_color", [255, 255, 255])
        self.text_color: RGB = tuple(text_color) if isinstance(text_color, list) else text_color
        self.scroll_speed: float = self.config.get("scroll_speed", 30.0)
        self.repeats: int = self.config.get("repeats", 1)
        self.y_position: int = self.config.get("y_position", 1)

    def _create_background_card(self) -> Card | None:
        """Create the background card instance."""
        if not self.background_config:
            return None

        bg_type = self.background_config.get("type")
        if not bg_type:
            return None

        # Build config for background card - use very long duration
        # since we control timing via text scroll
        bg_config = {k: v for k, v in self.background_config.items() if k != "type"}
        bg_config["duration"] = 3600  # 1 hour max, we'll stop earlier

        return create_card(bg_type, bg_config)

    def _overlay_text(self, frame: Frame, text_offset: int) -> Frame:
        """Overlay scrolling text on a frame."""
        canvas = Canvas(WIDTH, HEIGHT)

        # Copy background frame to canvas
        for y in range(HEIGHT):
            for x in range(WIDTH):
                if y < len(frame) and x < len(frame[y]):
                    canvas.set_pixel(x, y, frame[y][x])

        # Draw text overlay
        x_pos = WIDTH - text_offset
        draw_text(canvas, x_pos, self.y_position, self.text, self.text_color)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate frames with text overlay."""
        if not self.text:
            # No text, just play background
            bg_card = self._create_background_card()
            if bg_card:
                yield from bg_card.frames(ctx)
            return

        # Calculate scroll parameters
        total_text_width = text_width(self.text)
        total_scroll = total_text_width + WIDTH + 1
        frame_delay = 1.0 / 30.0
        pixels_per_frame = self.scroll_speed * frame_delay

        # Create background card
        bg_card = self._create_background_card()

        # Track scrolls completed
        scrolls_done = 0
        text_offset = 0.0

        if bg_card:
            # Iterate through background frames while overlaying text
            bg_frames = bg_card.frames(ctx)

            while scrolls_done < self.repeats:
                try:
                    bg_frame, _ = next(bg_frames)
                except StopIteration:
                    # Background ended, restart it
                    bg_card = self._create_background_card()
                    if bg_card:
                        bg_frames = bg_card.frames(ctx)
                        try:
                            bg_frame, _ = next(bg_frames)
                        except StopIteration:
                            break
                    else:
                        break

                # Overlay text on background
                frame = self._overlay_text(bg_frame, int(text_offset))
                yield frame, frame_delay

                # Update scroll position
                text_offset += pixels_per_frame
                if text_offset >= total_scroll:
                    text_offset = 0
                    scrolls_done += 1
        else:
            # No background, just black with scrolling text
            while scrolls_done < self.repeats:
                black_frame: Frame = [[(0, 0, 0) for _ in range(WIDTH)] for _ in range(HEIGHT)]
                frame = self._overlay_text(black_frame, int(text_offset))
                yield frame, frame_delay

                text_offset += pixels_per_frame
                if text_offset >= total_scroll:
                    text_offset = 0
                    scrolls_done += 1
