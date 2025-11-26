"""Canvas for drawing on the 10×50 LED display."""

from .types import (
    BLACK,
    HEIGHT,
    RGB,
    WIDTH,
    Frame,
    blend_color,
    copy_frame,
    create_empty_frame,
)


class Canvas:
    """A drawable 10×50 pixel canvas that can be rendered to a Frame."""

    def __init__(self, width: int = WIDTH, height: int = HEIGHT):
        """Create a new canvas with the given dimensions."""
        self.width = width
        self.height = height
        self.frame: Frame = [[BLACK for _ in range(width)] for _ in range(height)]

    def clear(self, color: RGB = BLACK) -> None:
        """Clear the canvas to a solid color."""
        for y in range(self.height):
            for x in range(self.width):
                self.frame[y][x] = color

    def set_pixel(self, x: int, y: int, color: RGB) -> None:
        """Set a single pixel. Coordinates outside bounds are ignored."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.frame[y][x] = color

    def get_pixel(self, x: int, y: int) -> RGB:
        """Get a pixel color. Returns BLACK for coordinates outside bounds."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.frame[y][x]
        return BLACK

    def fill_rect(self, x: int, y: int, w: int, h: int, color: RGB) -> None:
        """Fill a rectangle with a solid color."""
        for dy in range(h):
            for dx in range(w):
                self.set_pixel(x + dx, y + dy, color)

    def draw_rect(self, x: int, y: int, w: int, h: int, color: RGB) -> None:
        """Draw a rectangle outline."""
        # Top and bottom edges
        for dx in range(w):
            self.set_pixel(x + dx, y, color)
            self.set_pixel(x + dx, y + h - 1, color)
        # Left and right edges
        for dy in range(h):
            self.set_pixel(x, y + dy, color)
            self.set_pixel(x + w - 1, y + dy, color)

    def draw_line(self, x0: int, y0: int, x1: int, y1: int, color: RGB) -> None:
        """Draw a line using Bresenham's algorithm."""
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy

        while True:
            self.set_pixel(x0, y0, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def blit(
        self,
        source: Frame,
        dest_x: int = 0,
        dest_y: int = 0,
        src_x: int = 0,
        src_y: int = 0,
        width: int | None = None,
        height: int | None = None,
        transparent: RGB | None = None,
    ) -> None:
        """
        Copy pixels from a source frame onto this canvas.

        Args:
            source: Source frame to copy from
            dest_x, dest_y: Destination position on this canvas
            src_x, src_y: Source position in the source frame
            width, height: Size of region to copy (None = entire source)
            transparent: Color to treat as transparent (skip copying)
        """
        src_height = len(source)
        src_width = len(source[0]) if src_height > 0 else 0

        if width is None:
            width = src_width - src_x
        if height is None:
            height = src_height - src_y

        for dy in range(height):
            for dx in range(width):
                sx = src_x + dx
                sy = src_y + dy
                if 0 <= sx < src_width and 0 <= sy < src_height:
                    color = source[sy][sx]
                    if transparent is None or color != transparent:
                        self.set_pixel(dest_x + dx, dest_y + dy, color)

    def blend_frame(self, other: Frame, alpha: float) -> None:
        """Blend another frame onto this canvas with given alpha."""
        for y in range(min(self.height, len(other))):
            for x in range(min(self.width, len(other[y]))):
                self.frame[y][x] = blend_color(self.frame[y][x], other[y][x], alpha)

    def copy(self) -> Frame:
        """Return a deep copy of the current frame."""
        return copy_frame(self.frame)

    def gradient_horizontal(self, color_left: RGB, color_right: RGB) -> None:
        """Fill the canvas with a horizontal gradient."""
        for x in range(self.width):
            alpha = x / (self.width - 1) if self.width > 1 else 0
            color = blend_color(color_left, color_right, alpha)
            for y in range(self.height):
                self.frame[y][x] = color

    def gradient_vertical(self, color_top: RGB, color_bottom: RGB) -> None:
        """Fill the canvas with a vertical gradient."""
        for y in range(self.height):
            alpha = y / (self.height - 1) if self.height > 1 else 0
            color = blend_color(color_top, color_bottom, alpha)
            for x in range(self.width):
                self.frame[y][x] = color
