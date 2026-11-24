"""Vertical torch with flickering flame tips and rising embers."""

import math
import random
import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..types import BLACK, PORTRAIT_HEIGHT, PORTRAIT_WIDTH, RGB, Frame, blend_color
from .base import Card, CardContext, CardLayout, register_card

FLAME_CYCLE_SECONDS = 4.16
HEAT_COLORS: tuple[tuple[float, RGB], ...] = (
    (0.0, (25, 2, 0)),
    (0.20, (132, 13, 0)),
    (0.39, (244, 49, 0)),
    (0.59, (255, 114, 5)),
    (0.76, (255, 188, 25)),
    (0.92, (255, 231, 102)),
    (1.0, (255, 248, 192)),
)


def _flame_color(heat: float) -> RGB:
    """Interpolate from the cool red edges to the yellow-white core."""
    for (low, cool), (high, hot) in zip(HEAT_COLORS, HEAT_COLORS[1:], strict=False):
        if heat <= high:
            return blend_color(cool, hot, (heat - low) / (high - low))
    return HEAT_COLORS[-1][1]


@register_card
class TorchVerticalCard(Card):
    """Vertical torch with a bright core at the bottom and uneven flame tips.

    Config options:
        intensity: Flicker speed multiplier (default: 1.0).
        ember_density: Number of drifting embers (default: 10).
    """

    card_type = "torch_vertical"
    layout = CardLayout.portrait

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.intensity: float = float(self.config.get("intensity", 1.0))
        self.ember_density: int = int(self.config.get("ember_density", 10))

    def _draw_flame(self, canvas: Canvas, phase: float) -> None:
        """Merge three tapered flame tongues into one bright base."""
        tongues = (
            (4.55, 30 + 4.2 * math.sin(3 * phase), 3.9, 0.1),
            (2.45, 17 + 3.1 * math.sin(5 * phase + 1.2), 2.15, 1.7),
            (6.55, 21 + 4 * math.sin(4 * phase + 2.3), 2.15, 3.1),
        )
        for y in range(PORTRAIT_HEIGHT):
            height = PORTRAIT_HEIGHT - 1 - y
            row_heat = [0.0] * PORTRAIT_WIDTH
            for center, reach, radius, offset in tongues:
                rise = height / reach
                if rise >= 1:
                    continue
                bend = 0.8 * math.sin(3 * phase - 6 * rise + offset) + 0.65 * math.sin(
                    2 * phase - 3 * rise + offset
                )
                center_at_height = center + rise * bend
                width = (
                    radius
                    * (1 - rise) ** 0.7
                    * (0.94 + 0.16 * math.sin(4 * phase + 7 * rise + offset))
                )
                tip_fade = min(1.0, 3.5 * (1 - rise) + 0.14)
                for x, previous_heat in enumerate(row_heat):
                    edge = 1 - abs(x - center_at_height) / width
                    if edge > 0:
                        heat = (0.22 + 0.78 * edge**0.55 - 0.42 * rise) * tip_fade
                        row_heat[x] = max(previous_heat, heat)

            for x, heat in enumerate(row_heat):
                if heat > 0.07:
                    canvas.set_pixel(x, y, _flame_color(heat))

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Yield portrait frames with embers that fade as they rise."""
        frame_delay = 1.0 / 30.0
        embers = [
            (random.uniform(2.5, 7), random.random(), random.uniform(0.2, 0.75))
            for _ in range(self.ember_density)
        ]
        start = time.monotonic()
        while (elapsed := time.monotonic() - start) < self.duration:
            cycles = elapsed / FLAME_CYCLE_SECONDS
            phase = math.tau * cycles * self.intensity
            canvas = Canvas(PORTRAIT_WIDTH, PORTRAIT_HEIGHT)
            self._draw_flame(canvas, phase)

            for center, offset, speed in embers:
                progress = (offset + cycles * speed) % 1
                x = int(center + math.sin(phase * 2 + offset * 9) * progress)
                y = PORTRAIT_HEIGHT - 1 - int(14 + progress * 31)
                if canvas.get_pixel(x, y) == BLACK:
                    brightness = (1 - progress) ** 0.8
                    canvas.set_pixel(x, y, (round(230 * brightness), round(95 * brightness), 5))

            yield canvas.copy(), frame_delay
