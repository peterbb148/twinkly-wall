"""Animated Christmas scenes for the native portrait canvas."""

import math
import random
from abc import abstractmethod
from collections.abc import Iterator

from ..canvas import Canvas
from ..fonts import draw_char, draw_text_vertical_stacked, vertical_text_height
from ..types import GOLD, PORTRAIT_HEIGHT, PORTRAIT_WIDTH, RGB, WHITE, Frame
from .base import Card, CardContext, CardLayout, register_card
from .tuborg_sleigh import SKY_BLUE

_RED: RGB = (225, 27, 35)
_GREEN: RGB = (18, 130, 64)
_BLUE: RGB = (65, 151, 235)
_SNOW: RGB = (238, 249, 255)
_ICE: RGB = (125, 192, 232)


class _PortraitScene(Card):
    """Render one complete scene in the configured duration."""

    layout = CardLayout.portrait

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Yield portrait frames at up to twelve frames per second."""
        steps = math.ceil(self.duration * 12)
        canvas = Canvas(PORTRAIT_WIDTH, PORTRAIT_HEIGHT)
        for step in range(steps):
            canvas.clear()
            self.draw(canvas, step / max(1, steps - 1))
            yield canvas.copy(), self.duration / steps

    @abstractmethod
    def draw(self, canvas: Canvas, progress: float) -> None:
        """Draw the scene at a normalized point in its animation."""


@register_card
class ChristmasTreeVerticalCard(_PortraitScene):
    """Light the ornaments in groups, then shine the tree-top star."""

    card_type = "christmas_tree_vertical"

    def draw(self, canvas: Canvas, progress: float) -> None:
        canvas.fill_rect(4, 40, 2, 7, (119, 70, 32))
        canvas.draw_line(1, 47, 8, 47, _ICE)
        for top, height in ((10, 13), (18, 15), (27, 16)):
            for row in range(height):
                spread = row * 4 // (height - 1)
                canvas.fill_rect(4 - spread, top + row, 2 * spread + 2, 1, _GREEN)
                canvas.set_pixel(4 - spread, top + row, (45, 177, 83))

        ornaments = (
            (4, 15, _RED),
            (6, 21, GOLD),
            (2, 25, _BLUE),
            (5, 29, _RED),
            (7, 34, GOLD),
            (3, 37, _BLUE),
            (7, 41, _RED),
        )
        for index, (x, y, color) in enumerate(ornaments):
            if progress >= 0.07 * (index + 1):
                canvas.set_pixel(x, y, color)

        if progress >= 0.52:
            canvas.draw_line(2, 6, 7, 6, GOLD)
            canvas.fill_rect(4, 3, 2, 7, GOLD)
            canvas.fill_rect(4, 6, 2, 1, WHITE)
            if int(progress * 20) % 3 != 0:
                for x, y in ((2, 4), (7, 4), (2, 8), (7, 8)):
                    canvas.set_pixel(x, y, (255, 171, 41))


@register_card
class SantaRocketVerticalCard(_PortraitScene):
    """Count down before a Santa-hat rocket launches upward."""

    card_type = "santa_rocket_vertical"

    def draw(self, canvas: Canvas, progress: float) -> None:
        canvas.clear(SKY_BLUE)
        for x, y in ((2, 3), (7, 6), (4, 12), (0, 17), (9, 24), (2, 29), (8, 35)):
            canvas.set_pixel(x, y, _ICE if (x + int(progress * 16)) % 3 else WHITE)

        if progress < 0.3:
            draw_char(canvas, 2, 12, str(3 - int(progress * 10)), GOLD)
            canvas.draw_line(0, 47, 9, 47, _ICE)

        launch = min(1.0, max(0.0, (progress - 0.3) / 0.55))
        y = 32 - round(51 * launch**1.6)
        canvas.fill_rect(3, y + 5, 4, 8, WHITE)
        canvas.fill_rect(2, y + 11, 6, 3, _RED)
        canvas.fill_rect(3, y + 2, 4, 3, _RED)
        canvas.fill_rect(4, y + 1, 3, 2, _RED)
        canvas.set_pixel(6, y, WHITE)
        canvas.fill_rect(4, y + 7, 2, 2, _BLUE)
        if 0.3 <= progress < 0.85:
            canvas.fill_rect(4, y + 14, 2, 3 + int(progress * 24) % 4, GOLD)
        if progress >= 0.3:
            for index in range(8):
                spark_y = y + 16 + index * 4 + int(progress * 19) % 4
                canvas.set_pixel(3 + (index * 3) % 4, spark_y, _ICE if index > 3 else GOLD)


@register_card
class TuborgSnowVerticalCard(Card):
    """Drift downward against pale blue and build an uneven bank on contact."""

    card_type = "tuborg_snow_vertical"
    layout = CardLayout.portrait

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Start a fresh snowbank on each play."""
        steps = math.ceil(self.duration * 12)
        rng = random.Random()
        flakes = [
            (rng.randrange(PORTRAIT_WIDTH), rng.uniform(-16, 48), rng.uniform(0.6, 1.5))
            for _ in range(17)
        ]
        bank = [0] * PORTRAIT_WIDTH
        canvas = Canvas(PORTRAIT_WIDTH, PORTRAIT_HEIGHT)
        for step in range(steps):
            canvas.clear(_ICE)
            for index, (x, y, speed) in enumerate(flakes):
                if (step + index * 3) % 19 == 0:
                    x = (x + rng.choice((-1, 1))) % PORTRAIT_WIDTH
                y += speed
                if y >= PORTRAIT_HEIGHT - bank[x]:
                    bank[x] = min(bank[x] + 1, 4 + x % 4)
                    x, y = rng.randrange(PORTRAIT_WIDTH), rng.uniform(-19, -1)
                flakes[index] = (x, y, speed)
                if y >= 0:
                    canvas.set_pixel(x, int(y), WHITE if index % 2 else _SNOW)
            for x, height in enumerate(bank):
                canvas.fill_rect(x, PORTRAIT_HEIGHT - height, 1, height, _SNOW)
            yield canvas.copy(), self.duration / steps


@register_card
class TuborgJulebrygVerticalCard(_PortraitScene):
    """Show AFB above the upright bottle, then 0% and XMAS in turn."""

    card_type = "tuborg_julebryg_vertical"

    def draw(self, canvas: Canvas, progress: float) -> None:
        if progress < 0.55:
            glass = (50, 66, 33)
            canvas.fill_rect(2, 35, 6, 12, glass)
            canvas.fill_rect(3, 33, 4, 3, glass)
            canvas.fill_rect(4, 27, 2, 7, glass)
            canvas.fill_rect(3, 27, 4, 2, GOLD)
            canvas.fill_rect(2, 39, 6, 5, SKY_BLUE)
            canvas.set_pixel(5, 40, WHITE)
            canvas.set_pixel(6, 42, WHITE)
            canvas.draw_line(3, 35, 3, 37, (115, 136, 64))
            canvas.set_pixel(3, 35 + int(progress * 32) % 4, _ICE)
            draw_text_vertical_stacked(canvas, 2, 1, "AFB", GOLD)
        else:
            text = "0%" if progress < 0.75 else "XMAS"
            draw_text_vertical_stacked(
                canvas, 2, (PORTRAIT_HEIGHT - vertical_text_height(text)) // 2, text, WHITE
            )


@register_card
class SantaChimneyVerticalCard(_PortraitScene):
    """Wiggle Santa's boots above the bricks, then send up soot."""

    card_type = "santa_chimney_vertical"

    def draw(self, canvas: Canvas, progress: float) -> None:
        canvas.clear(SKY_BLUE)
        brick = (147, 48, 39)
        for y in range(30, 50, 4):
            canvas.fill_rect(2, y, 6, 3, brick)
            canvas.draw_line(4 + y % 3, y, 4 + y % 3, y + 2, (88, 32, 37))
        canvas.fill_rect(1, 27, 8, 3, (176, 67, 50))
        canvas.draw_line(1, 26, 8, 26, _SNOW)
        if progress < 0.68:
            drop = round(55 * max(0.0, progress - 0.48))
            kick = int(progress * 19) % 2
            for x, lift in ((3, kick), (6, 1 - kick)):
                toe = x - 1 if x == 3 else x
                boot_y = 19 + drop - 4 * lift
                for y in range(boot_y, min(27, boot_y + 8)):
                    if y < boot_y + 3:
                        canvas.fill_rect(toe, y, 2, 1, (33, 26, 32))
                    else:
                        canvas.set_pixel(x, y, WHITE if y == boot_y + 3 else _RED)
        else:
            rise = int((progress - 0.68) * 64)
            for x, offset in ((3, 0), (5, 3), (6, 5), (4, 8), (2, 2)):
                canvas.set_pixel(x, 26 - rise - offset, (127, 134, 147))


@register_card
class GiftStackVerticalCard(_PortraitScene):
    """Stack falling presents and topple them after the smallest one lands."""

    card_type = "gift_stack_vertical"

    def draw(self, canvas: Canvas, progress: float) -> None:
        canvas.draw_line(0, 48, 9, 48, _ICE)
        boxes = ((8, 9, _RED), (7, 8, _GREEN), (6, 7, _BLUE), (5, 6, _RED), (3, 3, GOLD))
        floor = 48
        for index, (width, height, color) in enumerate(boxes):
            drop = (progress - index * 0.14) / 0.23
            floor -= height
            if drop < 0:
                break
            y = round(-height + (floor + height) * min(1.0, drop) ** 2)
            x = (PORTRAIT_WIDTH - width) // 2
            if progress >= 0.8 and index:
                tumble = (progress - 0.8) * 5
                x += round(tumble * index * 2)
                y = min(48 - height, y + round(tumble * index * 6))
            elif progress >= 0.68 and index:
                x += int(progress * 43) % 2
            canvas.fill_rect(x, y, width, height - 1, color)
            ribbon = WHITE if color == GOLD else GOLD
            canvas.fill_rect(x + width // 2, y, 1, height - 1, ribbon)
            canvas.fill_rect(x, y + height // 2, width, 1, ribbon)


@register_card
class NisseLabVerticalCard(_PortraitScene):
    """Build pressure in a test tube while a nisse watches the foam spill."""

    card_type = "nisse_lab_vertical"

    def draw(self, canvas: Canvas, progress: float) -> None:
        canvas.draw_line(2, 22, 2, 44, _ICE)
        canvas.draw_line(7, 22, 7, 44, _ICE)
        canvas.draw_line(3, 45, 6, 45, _ICE)
        fluid_y = 34 - round(12 * progress)
        liquid = (round(215 * progress), round(170 * (1 - progress)), 38)
        canvas.fill_rect(3, fluid_y, 4, 45 - fluid_y, liquid)
        for index in range(6):
            bubble_y = 44 - (index * 4 + int(progress * 50)) % (45 - fluid_y)
            canvas.set_pixel(3 + index % 4, bubble_y, GOLD)
        if progress >= 0.55:
            canvas.fill_rect(6, 16, 4, 3, (248, 180, 119))
            canvas.fill_rect(6, 19, 4, 3, WHITE)
            canvas.fill_rect(5, 14, 5, 2, _RED)
            canvas.fill_rect(7, 11, 3, 3, _RED)
            canvas.set_pixel(9, 10, WHITE)
            canvas.set_pixel(7, 17, SKY_BLUE)
        if progress >= 0.78:
            lift = int(58 * (progress - 0.78))
            for x, offset in ((2, 2), (4, 4), (5, 2), (1, 0), (8, 0)):
                canvas.set_pixel(x, 22 - lift - offset, WHITE)
            canvas.set_pixel(1, 23 + lift, _SNOW)


@register_card
class ReindeerWeatherVaneVerticalCard(_PortraitScene):
    """Raise a red-nosed reindeer into a gust that sweeps it back under."""

    card_type = "reindeer_weather_vane_vertical"

    def draw(self, canvas: Canvas, progress: float) -> None:
        canvas.clear(SKY_BLUE)
        rise = min(1.0, progress * 4, max(0.0, (0.94 - progress) * 5))
        y = 52 - round(23 * rise)
        antler = (214, 164, 101)
        for x, tip in ((3, 1), (6, 8)):
            canvas.draw_line(x, y, x, y - 8, antler)
            canvas.draw_line(x, y - 3, tip, y - 6, antler)
            canvas.set_pixel(tip, y - 7, antler)
        canvas.fill_rect(2, y, 6, 6, (155, 91, 52))
        canvas.fill_rect(3, y + 4, 4, 4, antler)
        for x in (3, 6):
            canvas.set_pixel(x, y + 2, SKY_BLUE)
        pulse = int(6 * progress + 18 * progress**2) % 2
        canvas.fill_rect(4, y + 5, 2, 2, _RED if pulse else (255, 97, 60))
        for x in range(PORTRAIT_WIDTH):
            bank_y = 42 + (3 * x) % 4
            canvas.fill_rect(x, bank_y, 1, PORTRAIT_HEIGHT - bank_y, _SNOW)
        for index in range(7 + int(progress * 12)):
            x = (index * 3 + int(32 * progress**2)) % PORTRAIT_WIDTH
            y = (11 * index + int(10 * progress)) % 44
            canvas.set_pixel(x, y, _ICE)
