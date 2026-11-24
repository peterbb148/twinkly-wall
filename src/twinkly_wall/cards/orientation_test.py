"""Asymmetric markers for verifying a mounted wall's orientation and mirrors."""

from collections.abc import Iterator

from ..canvas import Canvas
from ..types import (
    BLUE,
    GREEN,
    PORTRAIT_HEIGHT,
    PORTRAIT_WIDTH,
    RED,
    WHITE,
    YELLOW,
    Frame,
    mount_rotation,
)
from .base import Card, CardContext, CardLayout, register_card


@register_card
class OrientationTestCard(Card):
    """Show an up arrow and distinct corner markers in the wall's aspect ratio."""

    card_type = "orientation_test"
    layout = CardLayout.adaptive

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Repeat the pattern so the controller stays in realtime mode."""
        if mount_rotation(ctx.orientation) % 180:
            canvas = Canvas(PORTRAIT_WIDTH, PORTRAIT_HEIGHT)
        else:
            canvas = Canvas()

        # Dice pips distinguish the corners even when colors are unavailable.
        right = canvas.width - 3
        bottom = canvas.height - 3
        for x, y, color, pips in (
            (0, 0, RED, ((1, 1),)),
            (right, 0, GREEN, ((0, 0), (2, 2))),
            (0, bottom, BLUE, ((0, 0), (1, 1), (2, 2))),
            (right, bottom, YELLOW, ((0, 0), (2, 0), (0, 2), (2, 2))),
        ):
            for dx, dy in pips:
                canvas.set_pixel(x + dx, y + dy, color)

        center = canvas.width // 2
        top = (canvas.height - 6) // 2
        canvas.draw_line(center - 1, top, center - 4, top + 3, WHITE)
        canvas.draw_line(center, top, center + 3, top + 3, WHITE)
        canvas.fill_rect(center - 1, top, 2, 6, WHITE)

        frame = canvas.copy()
        remaining = self.duration
        while remaining > 0:
            delay = min(remaining, 0.25)
            yield frame, delay
            remaining -= delay
