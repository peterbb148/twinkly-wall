"""Bitmap font system for rendering text on the LED display."""

from .canvas import Canvas
from .types import RGB, WHITE

# 5×7 bitmap font data
# Each character is a list of 7 rows, each row is 5 bits (stored as int)
# Bit 0 = leftmost pixel, Bit 4 = rightmost pixel
FONT_5X7: dict[str, list[int]] = {
    # Uppercase letters
    "A": [0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
    "B": [0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110],
    "C": [0b01110, 0b10001, 0b10000, 0b10000, 0b10000, 0b10001, 0b01110],
    "D": [0b11110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b11110],
    "E": [0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111],
    "F": [0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000],
    "G": [0b01110, 0b10001, 0b10000, 0b10111, 0b10001, 0b10001, 0b01110],
    "H": [0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001],
    "I": [0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
    "J": [0b00111, 0b00010, 0b00010, 0b00010, 0b00010, 0b10010, 0b01100],
    "K": [0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001],
    "L": [0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111],
    "M": [0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001],
    "N": [0b10001, 0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001],
    "O": [0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
    "P": [0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000],
    "Q": [0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01101],
    "R": [0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001],
    "S": [0b01110, 0b10001, 0b10000, 0b01110, 0b00001, 0b10001, 0b01110],
    "T": [0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100],
    "U": [0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110],
    "V": [0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100],
    "W": [0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b10101, 0b01010],
    "X": [0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001],
    "Y": [0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100],
    "Z": [0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111],
    # Lowercase letters (simplified, same height)
    "a": [0b00000, 0b00000, 0b01110, 0b00001, 0b01111, 0b10001, 0b01111],
    "b": [0b10000, 0b10000, 0b10110, 0b11001, 0b10001, 0b10001, 0b11110],
    "c": [0b00000, 0b00000, 0b01110, 0b10000, 0b10000, 0b10001, 0b01110],
    "d": [0b00001, 0b00001, 0b01101, 0b10011, 0b10001, 0b10001, 0b01111],
    "e": [0b00000, 0b00000, 0b01110, 0b10001, 0b11111, 0b10000, 0b01110],
    "f": [0b00110, 0b01001, 0b01000, 0b11100, 0b01000, 0b01000, 0b01000],
    "g": [0b00000, 0b01111, 0b10001, 0b10001, 0b01111, 0b00001, 0b01110],
    "h": [0b10000, 0b10000, 0b10110, 0b11001, 0b10001, 0b10001, 0b10001],
    "i": [0b00100, 0b00000, 0b01100, 0b00100, 0b00100, 0b00100, 0b01110],
    "j": [0b00010, 0b00000, 0b00110, 0b00010, 0b00010, 0b10010, 0b01100],
    "k": [0b10000, 0b10000, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010],
    "l": [0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
    "m": [0b00000, 0b00000, 0b11010, 0b10101, 0b10101, 0b10001, 0b10001],
    "n": [0b00000, 0b00000, 0b10110, 0b11001, 0b10001, 0b10001, 0b10001],
    "o": [0b00000, 0b00000, 0b01110, 0b10001, 0b10001, 0b10001, 0b01110],
    "p": [0b00000, 0b00000, 0b11110, 0b10001, 0b11110, 0b10000, 0b10000],
    "q": [0b00000, 0b00000, 0b01101, 0b10011, 0b01111, 0b00001, 0b00001],
    "r": [0b00000, 0b00000, 0b10110, 0b11001, 0b10000, 0b10000, 0b10000],
    "s": [0b00000, 0b00000, 0b01110, 0b10000, 0b01110, 0b00001, 0b11110],
    "t": [0b01000, 0b01000, 0b11100, 0b01000, 0b01000, 0b01001, 0b00110],
    "u": [0b00000, 0b00000, 0b10001, 0b10001, 0b10001, 0b10011, 0b01101],
    "v": [0b00000, 0b00000, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100],
    "w": [0b00000, 0b00000, 0b10001, 0b10001, 0b10101, 0b10101, 0b01010],
    "x": [0b00000, 0b00000, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001],
    "y": [0b00000, 0b00000, 0b10001, 0b10001, 0b01111, 0b00001, 0b01110],
    "z": [0b00000, 0b00000, 0b11111, 0b00010, 0b00100, 0b01000, 0b11111],
    # Digits
    "0": [0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110],
    "1": [0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110],
    "2": [0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b01000, 0b11111],
    "3": [0b11111, 0b00010, 0b00100, 0b00010, 0b00001, 0b10001, 0b01110],
    "4": [0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010],
    "5": [0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110],
    "6": [0b00110, 0b01000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110],
    "7": [0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000],
    "8": [0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110],
    "9": [0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00010, 0b01100],
    # Punctuation and symbols
    " ": [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000],
    "!": [0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00000, 0b00100],
    '"': [0b01010, 0b01010, 0b01010, 0b00000, 0b00000, 0b00000, 0b00000],
    "#": [0b01010, 0b01010, 0b11111, 0b01010, 0b11111, 0b01010, 0b01010],
    "$": [0b00100, 0b01111, 0b10100, 0b01110, 0b00101, 0b11110, 0b00100],
    "%": [0b11000, 0b11001, 0b00010, 0b00100, 0b01000, 0b10011, 0b00011],
    "&": [0b01100, 0b10010, 0b10100, 0b01000, 0b10101, 0b10010, 0b01101],
    "'": [0b00100, 0b00100, 0b00100, 0b00000, 0b00000, 0b00000, 0b00000],
    "(": [0b00010, 0b00100, 0b01000, 0b01000, 0b01000, 0b00100, 0b00010],
    ")": [0b01000, 0b00100, 0b00010, 0b00010, 0b00010, 0b00100, 0b01000],
    "*": [0b00000, 0b00100, 0b10101, 0b01110, 0b10101, 0b00100, 0b00000],
    "+": [0b00000, 0b00100, 0b00100, 0b11111, 0b00100, 0b00100, 0b00000],
    ",": [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00100, 0b01000],
    "-": [0b00000, 0b00000, 0b00000, 0b11111, 0b00000, 0b00000, 0b00000],
    ".": [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00100],
    "/": [0b00000, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b00000],
    ":": [0b00000, 0b00000, 0b00100, 0b00000, 0b00000, 0b00100, 0b00000],
    ";": [0b00000, 0b00000, 0b00100, 0b00000, 0b00000, 0b00100, 0b01000],
    "<": [0b00010, 0b00100, 0b01000, 0b10000, 0b01000, 0b00100, 0b00010],
    "=": [0b00000, 0b00000, 0b11111, 0b00000, 0b11111, 0b00000, 0b00000],
    ">": [0b01000, 0b00100, 0b00010, 0b00001, 0b00010, 0b00100, 0b01000],
    "?": [0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b00000, 0b00100],
    "@": [0b01110, 0b10001, 0b00001, 0b01101, 0b10101, 0b10101, 0b01110],
    "[": [0b01110, 0b01000, 0b01000, 0b01000, 0b01000, 0b01000, 0b01110],
    "\\": [0b00000, 0b10000, 0b01000, 0b00100, 0b00010, 0b00001, 0b00000],
    "]": [0b01110, 0b00010, 0b00010, 0b00010, 0b00010, 0b00010, 0b01110],
    "^": [0b00100, 0b01010, 0b10001, 0b00000, 0b00000, 0b00000, 0b00000],
    "_": [0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b11111],
    "`": [0b01000, 0b00100, 0b00010, 0b00000, 0b00000, 0b00000, 0b00000],
    "{": [0b00010, 0b00100, 0b00100, 0b01000, 0b00100, 0b00100, 0b00010],
    "|": [0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100],
    "}": [0b01000, 0b00100, 0b00100, 0b00010, 0b00100, 0b00100, 0b01000],
    "~": [0b00000, 0b00000, 0b01000, 0b10101, 0b00010, 0b00000, 0b00000],
    # Special characters
    "°": [0b00110, 0b01001, 0b01001, 0b00110, 0b00000, 0b00000, 0b00000],
}

# Font metrics
CHAR_WIDTH = 5
CHAR_HEIGHT = 7
CHAR_SPACING = 1  # Space between characters
VERTICAL_CHAR_SPACING = 1  # Space between vertically stacked characters


def get_char_bitmap(char: str) -> list[int] | None:
    """Get the bitmap data for a character, or None if not available."""
    return FONT_5X7.get(char)


def text_width(text: str, spacing: int = CHAR_SPACING) -> int:
    """Calculate the pixel width of a text string."""
    if not text:
        return 0
    return len(text) * CHAR_WIDTH + (len(text) - 1) * spacing


def draw_char(canvas: Canvas, x: int, y: int, char: str, color: RGB = WHITE) -> int:
    """
    Draw a single character onto the canvas.

    Returns the width of the character drawn (for advancing cursor).
    """
    bitmap = get_char_bitmap(char)
    if bitmap is None:
        # Unknown character - draw a placeholder box
        canvas.draw_rect(x, y, CHAR_WIDTH, CHAR_HEIGHT, color)
        return CHAR_WIDTH

    for row_idx, row_bits in enumerate(bitmap):
        for col_idx in range(CHAR_WIDTH):
            if row_bits & (1 << (4 - col_idx)):  # Check bit from left to right
                canvas.set_pixel(x + col_idx, y + row_idx, color)

    return CHAR_WIDTH


def draw_char_rotated_cw(
    canvas: Canvas,
    x: int,
    y: int,
    char: str,
    color: RGB = WHITE,
) -> tuple[int, int]:
    """Draw a single character rotated 90 degrees clockwise.

    The standard 5x7 glyph becomes 7 pixels wide and 5 pixels tall.

    Args:
        canvas: Target canvas.
        x: Left coordinate of the rotated glyph.
        y: Top coordinate of the rotated glyph.
        char: Character to draw.
        color: Glyph color.

    Returns:
        Tuple of (width, height) of the drawn glyph.
    """
    bitmap = get_char_bitmap(char)
    width = CHAR_HEIGHT
    height = CHAR_WIDTH

    if bitmap is None:
        # Placeholder box for unknown characters
        canvas.draw_rect(x, y, width, height, color)
        return width, height

    # Original coordinates: (cx, cy) with cx in [0,4], cy in [0,6]
    # After 90° CW rotation:
    #   nx = cy
    #   ny = (CHAR_WIDTH - 1) - cx
    for cy, row_bits in enumerate(bitmap):
        for cx in range(CHAR_WIDTH):
            if row_bits & (1 << (4 - cx)):
                nx = x + cy
                ny = y + (CHAR_WIDTH - 1 - cx)
                canvas.set_pixel(nx, ny, color)

    return width, height


def draw_text(
    canvas: Canvas,
    x: int,
    y: int,
    text: str,
    color: RGB = WHITE,
    spacing: int = CHAR_SPACING,
) -> int:
    """
    Draw text onto the canvas starting at (x, y).

    Returns the total width of the text drawn.
    """
    cursor_x = x
    for i, char in enumerate(text):
        draw_char(canvas, cursor_x, y, char, color)
        cursor_x += CHAR_WIDTH
        if i < len(text) - 1:
            cursor_x += spacing
    return cursor_x - x


def draw_text_vertical_stacked(
    canvas: Canvas,
    x: int,
    y: int,
    text: str,
    color: RGB = WHITE,
    spacing: int = VERTICAL_CHAR_SPACING,
) -> int:
    """Draw text as a vertical stack of characters (no rotation).

    Each character is drawn using the normal 5x7 glyph, stacked along the Y axis:

        H
        e
        l
        l
        o

    Args:
        canvas: Target canvas.
        x: Left coordinate of the first glyph.
        y: Top coordinate of the first glyph.
        text: Text to draw.
        color: Glyph color.
        spacing: Vertical spacing between glyphs in pixels.

    Returns:
        Total height of the rendered text in pixels.
    """
    cursor_y = y
    total_height = 0

    for i, char in enumerate(text):
        draw_text(canvas, x, cursor_y, char, color)
        total_height += CHAR_HEIGHT
        cursor_y += CHAR_HEIGHT
        if i < len(text) - 1:
            cursor_y += spacing
            total_height += spacing

    return total_height


def draw_text_vertical_rotated(
    canvas: Canvas,
    x: int,
    y: int,
    text: str,
    color: RGB = WHITE,
    spacing: int = VERTICAL_CHAR_SPACING,
) -> int:
    """Draw text vertically using rotated glyphs (legacy helper).

    NOTE: Current vertical stacked text mode uses draw_text_vertical_stacked.
    This function is kept for backwards compatibility and may be removed later.
    """
    return draw_text_vertical_stacked(canvas, x, y, text, color, spacing)


def vertical_text_height(text: str, spacing: int = VERTICAL_CHAR_SPACING) -> int:
    """Calculate the pixel height of vertically stacked text."""
    if not text:
        return 0
    return len(text) * CHAR_HEIGHT + (len(text) - 1) * spacing


def render_text_to_frame(
    text: str,
    color: RGB = WHITE,
    spacing: int = CHAR_SPACING,
) -> list[list[RGB]]:
    """
    Render text to a minimal-width frame (useful for scrolling).

    Returns a frame just wide enough to contain the text.
    """
    from .types import HEIGHT

    width = text_width(text, spacing)
    if width <= 0:
        width = 1

    # Create a canvas with exact width needed
    canvas = Canvas(width=width, height=HEIGHT)
    draw_text(canvas, 0, 1, text, color, spacing)  # y=1 for top margin
    return canvas.copy()
