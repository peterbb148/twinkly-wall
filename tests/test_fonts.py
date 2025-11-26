"""Tests for the bitmap font system."""

from twinkly_wall.canvas import Canvas
from twinkly_wall.fonts import (
    CHAR_HEIGHT,
    CHAR_SPACING,
    CHAR_WIDTH,
    draw_char,
    draw_text,
    get_char_bitmap,
    render_text_to_frame,
    text_width,
)
from twinkly_wall.types import BLACK, RED, WHITE


def test_get_char_bitmap_uppercase():
    """Should return bitmap for uppercase letters."""
    bitmap = get_char_bitmap("A")
    assert bitmap is not None
    assert len(bitmap) == CHAR_HEIGHT


def test_get_char_bitmap_lowercase():
    """Should return bitmap for lowercase letters."""
    bitmap = get_char_bitmap("a")
    assert bitmap is not None
    assert len(bitmap) == CHAR_HEIGHT


def test_get_char_bitmap_digits():
    """Should return bitmap for digits."""
    for digit in "0123456789":
        bitmap = get_char_bitmap(digit)
        assert bitmap is not None


def test_get_char_bitmap_space():
    """Should return empty bitmap for space."""
    bitmap = get_char_bitmap(" ")
    assert bitmap is not None
    assert all(row == 0 for row in bitmap)


def test_get_char_bitmap_unknown():
    """Should return None for unknown characters."""
    bitmap = get_char_bitmap("😀")
    assert bitmap is None


def test_text_width_empty():
    """Empty string should have width 0."""
    assert text_width("") == 0


def test_text_width_single_char():
    """Single character should have width of CHAR_WIDTH."""
    assert text_width("A") == CHAR_WIDTH


def test_text_width_multiple_chars():
    """Multiple characters should account for spacing."""
    # 3 chars of width 5, plus 2 spaces of width 1
    assert text_width("ABC") == 3 * CHAR_WIDTH + 2 * CHAR_SPACING


def test_draw_char():
    """Drawing a character should set pixels."""
    canvas = Canvas()
    draw_char(canvas, 0, 0, "A", WHITE)

    # The letter 'A' should have some pixels set
    has_pixels = any(
        canvas.get_pixel(x, y) != BLACK for y in range(CHAR_HEIGHT) for x in range(CHAR_WIDTH)
    )
    assert has_pixels


def test_draw_char_respects_color():
    """Drawing should use the specified color."""
    canvas = Canvas()
    draw_char(canvas, 0, 0, "A", RED)

    # At least one pixel should be RED
    has_red = any(
        canvas.get_pixel(x, y) == RED for y in range(CHAR_HEIGHT) for x in range(CHAR_WIDTH)
    )
    assert has_red


def test_draw_text():
    """Drawing text should place characters correctly."""
    canvas = Canvas()
    width = draw_text(canvas, 0, 0, "AB", WHITE)

    # Should return correct width
    assert width == 2 * CHAR_WIDTH + CHAR_SPACING

    # Both characters should have pixels
    # Check first char area
    first_has_pixels = any(
        canvas.get_pixel(x, y) != BLACK for y in range(CHAR_HEIGHT) for x in range(CHAR_WIDTH)
    )
    assert first_has_pixels

    # Check second char area (starts after first char + spacing)
    second_start = CHAR_WIDTH + CHAR_SPACING
    second_has_pixels = any(
        canvas.get_pixel(second_start + x, y) != BLACK
        for y in range(CHAR_HEIGHT)
        for x in range(CHAR_WIDTH)
    )
    assert second_has_pixels


def test_render_text_to_frame():
    """render_text_to_frame should create properly sized frame."""
    frame = render_text_to_frame("HI", WHITE)

    # Width should match text width
    expected_width = text_width("HI")
    assert len(frame[0]) == expected_width

    # Height should match display height (10)
    assert len(frame) == 10
