"""Core types and helpers for Twinkly Wall."""

from enum import StrEnum
from typing import TypeAlias

# Display dimensions (Twinkly Matrix 500: 50 columns × 10 rows for horizontal display)
WIDTH: int = 50
HEIGHT: int = 10
PORTRAIT_WIDTH: int = HEIGHT
PORTRAIT_HEIGHT: int = WIDTH

# RGB color tuple (0-255 per channel)
RGB: TypeAlias = tuple[int, int, int]

# A frame is a 2D array of RGB values: Frame[y][x] = (r, g, b)
Frame: TypeAlias = list[list[RGB]]


class Orientation(StrEnum):
    """Display mount specified by the wire edge or a legacy mount name."""

    top = "top"
    bottom = "bottom"
    left = "left"
    right = "right"
    horizontal = "horizontal"
    vertical_left = "vertical_left"
    vertical_right = "vertical_right"


def mount_rotation(orientation: Orientation) -> int:
    """Return the clockwise rotation from the native landscape mount in degrees."""
    # The native strand map puts the wire edge (bottom of the strands)
    # at the right of the landscape frame.
    return {
        Orientation.top: -90,
        Orientation.bottom: 90,
        Orientation.left: 180,
        Orientation.right: 0,
        Orientation.horizontal: 0,
        Orientation.vertical_left: -90,
        Orientation.vertical_right: 90,
    }[orientation]


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


def rotate_frame_cw(frame: Frame) -> Frame:
    """Rotate a frame 90 degrees clockwise."""
    if not frame or not frame[0]:
        return []

    height = len(frame)
    width = len(frame[0])
    # New frame has dimensions width × height
    return [[frame[height - 1 - x][y] for x in range(height)] for y in range(width)]


def rotate_frame_ccw(frame: Frame) -> Frame:
    """Rotate a frame 90 degrees counter-clockwise."""
    if not frame or not frame[0]:
        return []

    height = len(frame)
    width = len(frame[0])
    # New frame has dimensions width × height
    return [[frame[x][width - 1 - y] for x in range(height)] for y in range(width)]


def rotate_frame_180(frame: Frame) -> Frame:
    """Rotate a frame 180 degrees."""
    if not frame or not frame[0]:
        return []

    height = len(frame)
    width = len(frame[0])
    return [[frame[height - 1 - y][width - 1 - x] for x in range(width)] for y in range(height)]


def rotate_frame(frame: Frame, degrees: int) -> Frame:
    """Rotate a frame clockwise by a multiple of 90 degrees."""
    return {
        0: copy_frame,
        90: rotate_frame_cw,
        180: rotate_frame_180,
        270: rotate_frame_ccw,
    }[degrees % 360](frame)


def apply_orientation(
    frame: Frame,
    orientation: Orientation,
    *,
    mirror_h: bool = False,
    mirror_v: bool = False,
) -> Frame:
    """Orient a card frame for the viewer and flip it along the requested axes.

    Args:
        frame: Card pixels in their logical portrait or landscape layout.
        orientation: Physical display mount.
        mirror_h: Flip left to right as viewed on the display.
        mirror_v: Flip top to bottom as viewed on the display.

    Returns:
        Pixels laid out as seen by the viewer.
    """
    if not frame or not frame[0]:
        return copy_frame(frame)

    rotation = mount_rotation(orientation)
    portrait_frame = len(frame) > len(frame[0])
    portrait_display = rotation % 180 != 0
    if portrait_frame == portrait_display:
        oriented = copy_frame(frame)
    else:
        # Opposite mounts use opposite quarter-turns for sideways cards.
        oriented = rotate_frame(frame, -90 if rotation in (-90, 180) else 90)

    if mirror_v:
        oriented.reverse()
    if mirror_h:
        for row in oriented:
            row.reverse()
    return oriented
