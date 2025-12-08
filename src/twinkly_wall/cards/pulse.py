"""Pulsating color effect card."""

import math
import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..fonts import draw_text, text_width
from ..types import HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card


@register_card
class PulseCard(Card):
    """Pulsating single-color effect with optional scrolling text.

    Config options:
        color: RGB color to pulse (default: [255, 0, 0] red)
        speed: Pulse speed multiplier (default: 1.0)
        mode: Pulse mode - breathing, heartbeat, strobe (default: breathing)
        min_brightness: Minimum brightness 0-1 (default: 0.1)
        max_brightness: Maximum brightness 0-1 (default: 1.0)
        text: Optional text to scroll across the pulsing background
        text_color: RGB color for text (default: [255, 255, 255] white)
        scroll_speed: Text scroll speed in pixels per second (default: 30)
    """

    card_type = "pulse"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        color = self.config.get("color", [255, 0, 0])
        self.color: RGB = tuple(color) if isinstance(color, list) else color
        self.speed: float = self.config.get("speed", 1.0)
        self.mode: str = self.config.get("mode", "breathing")
        self.min_brightness: float = self.config.get("min_brightness", 0.1)
        self.max_brightness: float = self.config.get("max_brightness", 1.0)
        # Text options
        self.text: str | None = self.config.get("text")
        text_color = self.config.get("text_color", [255, 255, 255])
        self.text_color: RGB = tuple(text_color) if isinstance(text_color, list) else text_color
        self.scroll_speed: float = self.config.get("scroll_speed", 30.0)

    def _apply_brightness(self, brightness: float) -> RGB:
        """Apply brightness to the base color."""
        r, g, b = self.color
        return (
            int(r * brightness),
            int(g * brightness),
            int(b * brightness),
        )

    def _breathing_brightness(self, t: float) -> float:
        """Smooth sine wave breathing pattern."""
        # Sine wave oscillates between min and max brightness
        wave = (math.sin(t * self.speed * 2) + 1) / 2  # 0 to 1
        return self.min_brightness + wave * (self.max_brightness - self.min_brightness)

    def _heartbeat_brightness(self, t: float) -> float:
        """Double-pulse heartbeat pattern."""
        # Heartbeat cycle is about 0.8 seconds
        cycle_time = 0.8 / self.speed
        cycle_pos = (t % cycle_time) / cycle_time  # 0 to 1 within cycle

        # Two quick pulses followed by a pause
        if cycle_pos < 0.15:
            # First beat up
            wave = cycle_pos / 0.15
        elif cycle_pos < 0.25:
            # First beat down
            wave = 1 - (cycle_pos - 0.15) / 0.10
        elif cycle_pos < 0.35:
            # Second beat up
            wave = (cycle_pos - 0.25) / 0.10
        elif cycle_pos < 0.50:
            # Second beat down
            wave = 1 - (cycle_pos - 0.35) / 0.15
        else:
            # Rest period
            wave = 0

        return self.min_brightness + wave * (self.max_brightness - self.min_brightness)

    def _strobe_brightness(self, t: float) -> float:
        """Sharp on/off strobe pattern."""
        # Strobe frequency based on speed
        frequency = 4 * self.speed  # flashes per second
        on = (t * frequency) % 1 < 0.5
        return self.max_brightness if on else self.min_brightness

    def _render_frame(self, brightness: float, text_offset: int = 0) -> Frame:
        """Render a frame with the given brightness and optional text."""
        canvas = Canvas(WIDTH, HEIGHT)
        color = self._apply_brightness(brightness)
        # Fill background with pulsing color
        for y in range(HEIGHT):
            for x in range(WIDTH):
                canvas.set_pixel(x, y, color)
        # Draw scrolling text if configured
        if self.text:
            x_pos = WIDTH - text_offset
            draw_text(canvas, x_pos, 1, self.text, self.text_color)
        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate pulsing animation frames."""
        brightness_fn = {
            "breathing": self._breathing_brightness,
            "heartbeat": self._heartbeat_brightness,
            "strobe": self._strobe_brightness,
        }.get(self.mode, self._breathing_brightness)

        # Calculate text scroll parameters
        if self.text:
            total_text_width = text_width(self.text)
            total_scroll = total_text_width + WIDTH
        else:
            total_scroll = 0

        start_time = time.time()
        frame_delay = 1.0 / 30.0  # 30 FPS
        text_offset = 0.0

        while time.time() - start_time < self.duration:
            t = time.time() - start_time
            brightness = brightness_fn(t)
            frame = self._render_frame(brightness, int(text_offset))
            yield frame, frame_delay
            # Update text scroll position
            if self.text:
                text_offset += self.scroll_speed * frame_delay
                if text_offset >= total_scroll:
                    text_offset = 0  # Loop
