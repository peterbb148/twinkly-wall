"""Core types for Twinkly Wall."""

from typing import TypeAlias

# Display dimensions (Twinkly Matrix 500: 50 columns × 10 rows for horizontal display)
WIDTH: int = 50
HEIGHT: int = 10

# RGB color tuple (0-255 per channel)
RGB: TypeAlias = tuple[int, int, int]

# A frame is a 2D array of RGB values: Frame[y][x] = (r, g, b)
Frame: TypeAlias = list[list[RGB]]

# Common colors
BLACK: RGB = (0, 0, 0)
WHITE: RGB = (255, 255, 255)
RED: RGB = (255, 0, 0)
GREEN: RGB = (0, 255, 0)
BLUE: RGB = (0, 0, 255)
YELLOW: RGB = (255, 255, 0)
CYAN: RGB = (0, 255, 255)
MAGENTA: RGB = (255, 0, 255)
ORANGE: RGB = (255, 165, 0)

# Christmas colors
CHRISTMAS_RED: RGB = (255, 0, 0)
CHRISTMAS_GREEN: RGB = (0, 128, 0)
GOLD: RGB = (255, 215, 0)
SNOW_WHITE: RGB = (255, 250, 250)

# Beer colors (Carlsberg!)
BEER_GOLD: RGB = (255, 198, 41)
BEER_FOAM: RGB = (255, 248, 220)
CARLSBERG_GREEN: RGB = (0, 66, 37)


def create_empty_frame(color: RGB = BLACK) -> Frame:
    """Create a new frame filled with a solid color."""
    return [[color for _ in range(WIDTH)] for _ in range(HEIGHT)]


def copy_frame(frame: Frame) -> Frame:
    """Create a deep copy of a frame."""
    return [row[:] for row in frame]


def blend_color(c1: RGB, c2: RGB, alpha: float) -> RGB:
    """Blend two colors. alpha=0 gives c1, alpha=1 gives c2."""
    alpha = max(0.0, min(1.0, alpha))
    return (
        int(c1[0] * (1 - alpha) + c2[0] * alpha),
        int(c1[1] * (1 - alpha) + c2[1] * alpha),
        int(c1[2] * (1 - alpha) + c2[2] * alpha),
    )


def scale_color(color: RGB, factor: float) -> RGB:
    """Scale a color's brightness by a factor."""
    return (
        min(255, max(0, int(color[0] * factor))),
        min(255, max(0, int(color[1] * factor))),
        min(255, max(0, int(color[2] * factor))),
    )
