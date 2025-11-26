"""Rainbow and ambient color animation card."""

import math
import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..types import HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card


def hsv_to_rgb(h: float, s: float, v: float) -> RGB:
    """Convert HSV to RGB. h is 0-360, s and v are 0-1."""
    h = h % 360
    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c

    if h < 60:
        r, g, b = c, x, 0
    elif h < 120:
        r, g, b = x, c, 0
    elif h < 180:
        r, g, b = 0, c, x
    elif h < 240:
        r, g, b = 0, x, c
    elif h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x

    return (int((r + m) * 255), int((g + m) * 255), int((b + m) * 255))


@register_card
class RainbowCard(Card):
    """Rainbow/ambient color animation.

    Config options:
        mode: Animation mode - rainbow, plasma, wave, gradient (default: rainbow)
        speed: Animation speed multiplier (default: 1.0)
        saturation: Color saturation 0-1 (default: 1.0)
        brightness: Color brightness 0-1 (default: 1.0)
    """

    card_type = "rainbow"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.mode: str = self.config.get("mode", "rainbow")
        self.speed: float = self.config.get("speed", 1.0)
        self.saturation: float = self.config.get("saturation", 1.0)
        self.brightness: float = self.config.get("brightness", 1.0)

    def _render_rainbow(self, t: float) -> Frame:
        """Horizontal rainbow that shifts over time."""
        canvas = Canvas(WIDTH, HEIGHT)
        for x in range(WIDTH):
            # Hue shifts across x and over time
            hue = (x * 7 + t * 50 * self.speed) % 360
            color = hsv_to_rgb(hue, self.saturation, self.brightness)
            for y in range(HEIGHT):
                canvas.set_pixel(x, y, color)
        return canvas.copy()

    def _render_plasma(self, t: float) -> Frame:
        """Plasma-style animated pattern."""
        canvas = Canvas(WIDTH, HEIGHT)
        t_scaled = t * self.speed

        for y in range(HEIGHT):
            for x in range(WIDTH):
                # Combine multiple sine waves for plasma effect
                v1 = math.sin(x * 0.3 + t_scaled)
                v2 = math.sin(y * 0.3 + t_scaled * 0.7)
                v3 = math.sin((x + y) * 0.2 + t_scaled * 0.5)
                v4 = math.sin(math.sqrt(x * x + y * y) * 0.3 + t_scaled * 0.8)

                # Combine and normalize to 0-360 for hue
                v = (v1 + v2 + v3 + v4) / 4
                hue = (v + 1) * 180  # Map -1..1 to 0..360

                color = hsv_to_rgb(hue, self.saturation, self.brightness)
                canvas.set_pixel(x, y, color)

        return canvas.copy()

    def _render_wave(self, t: float) -> Frame:
        """Vertical color wave moving horizontally."""
        canvas = Canvas(WIDTH, HEIGHT)
        t_scaled = t * self.speed * 30

        for x in range(WIDTH):
            # Single hue per column, shifting over time
            hue = (x * 5 - t_scaled) % 360

            # Add vertical brightness wave
            for y in range(HEIGHT):
                brightness_mod = 0.7 + 0.3 * math.sin(y * 0.5 + t * 2)
                color = hsv_to_rgb(hue, self.saturation, self.brightness * brightness_mod)
                canvas.set_pixel(x, y, color)

        return canvas.copy()

    def _render_gradient(self, t: float) -> Frame:
        """Slowly shifting gradient between two colors."""
        canvas = Canvas(WIDTH, HEIGHT)
        t_scaled = t * self.speed * 20

        # Two hues that slowly shift
        hue1 = t_scaled % 360
        hue2 = (t_scaled + 180) % 360  # Complementary

        for x in range(WIDTH):
            # Blend between the two hues across x
            blend = x / (WIDTH - 1)
            hue = hue1 + (hue2 - hue1) * blend
            if hue2 < hue1:
                hue = hue1 - (hue1 - hue2) * blend

            color = hsv_to_rgb(hue % 360, self.saturation, self.brightness)
            for y in range(HEIGHT):
                canvas.set_pixel(x, y, color)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate rainbow animation frames."""
        render_fn = {
            "rainbow": self._render_rainbow,
            "plasma": self._render_plasma,
            "wave": self._render_wave,
            "gradient": self._render_gradient,
        }.get(self.mode, self._render_rainbow)

        start_time = time.time()
        frame_delay = 1.0 / 30.0  # 30 FPS

        while time.time() - start_time < self.duration:
            t = time.time() - start_time
            frame = render_fn(t)
            yield frame, frame_delay
