"""Tests for Canvas."""

from twinkly_wall.canvas import Canvas
from twinkly_wall.types import BLACK, RED, WHITE


def test_canvas_default_dimensions():
    """Canvas should have correct default dimensions."""
    canvas = Canvas()
    assert canvas.width == 50
    assert canvas.height == 10


def test_canvas_custom_dimensions():
    """Canvas can have custom dimensions."""
    canvas = Canvas(width=20, height=5)
    assert canvas.width == 20
    assert canvas.height == 5


def test_canvas_starts_black():
    """New canvas should be all black."""
    canvas = Canvas()
    for y in range(canvas.height):
        for x in range(canvas.width):
            assert canvas.get_pixel(x, y) == BLACK


def test_set_and_get_pixel():
    """Setting a pixel should be retrievable."""
    canvas = Canvas()
    canvas.set_pixel(5, 3, RED)
    assert canvas.get_pixel(5, 3) == RED


def test_set_pixel_out_of_bounds_ignored():
    """Setting pixels outside bounds should be silently ignored."""
    canvas = Canvas()
    canvas.set_pixel(-1, 0, RED)
    canvas.set_pixel(0, -1, RED)
    canvas.set_pixel(100, 0, RED)
    canvas.set_pixel(0, 100, RED)
    # Should not raise, canvas unchanged
    assert canvas.get_pixel(0, 0) == BLACK


def test_get_pixel_out_of_bounds_returns_black():
    """Getting pixels outside bounds should return black."""
    canvas = Canvas()
    assert canvas.get_pixel(-1, 0) == BLACK
    assert canvas.get_pixel(100, 100) == BLACK


def test_clear():
    """Clear should fill entire canvas with color."""
    canvas = Canvas()
    canvas.set_pixel(5, 5, RED)
    canvas.clear(WHITE)

    for y in range(canvas.height):
        for x in range(canvas.width):
            assert canvas.get_pixel(x, y) == WHITE


def test_fill_rect():
    """Fill rect should fill a rectangular area."""
    canvas = Canvas()
    canvas.fill_rect(2, 2, 3, 3, RED)

    # Check filled area
    for y in range(2, 5):
        for x in range(2, 5):
            assert canvas.get_pixel(x, y) == RED

    # Check outside area
    assert canvas.get_pixel(1, 1) == BLACK
    assert canvas.get_pixel(5, 5) == BLACK


def test_draw_rect():
    """Draw rect should draw just the outline."""
    canvas = Canvas()
    canvas.draw_rect(2, 2, 4, 4, RED)

    # Corners should be filled
    assert canvas.get_pixel(2, 2) == RED
    assert canvas.get_pixel(5, 2) == RED
    assert canvas.get_pixel(2, 5) == RED
    assert canvas.get_pixel(5, 5) == RED

    # Center should be empty
    assert canvas.get_pixel(3, 3) == BLACK
    assert canvas.get_pixel(4, 4) == BLACK


def test_copy_returns_independent_frame():
    """Copy should return an independent frame."""
    canvas = Canvas()
    canvas.set_pixel(0, 0, RED)

    frame = canvas.copy()
    canvas.set_pixel(0, 0, WHITE)

    assert frame[0][0] == RED
    assert canvas.get_pixel(0, 0) == WHITE


def test_blit_simple():
    """Blit should copy source frame onto canvas."""
    canvas = Canvas(width=10, height=10)
    source = [[RED for _ in range(3)] for _ in range(3)]

    canvas.blit(source, dest_x=2, dest_y=2)

    assert canvas.get_pixel(2, 2) == RED
    assert canvas.get_pixel(4, 4) == RED
    assert canvas.get_pixel(1, 1) == BLACK


def test_blit_with_transparency():
    """Blit with transparency should skip transparent pixels."""
    canvas = Canvas(width=10, height=10)
    canvas.fill_rect(0, 0, 10, 10, WHITE)

    source = [[BLACK, RED], [RED, BLACK]]
    canvas.blit(source, dest_x=0, dest_y=0, transparent=BLACK)

    assert canvas.get_pixel(0, 0) == WHITE  # Transparent, not overwritten
    assert canvas.get_pixel(1, 0) == RED
    assert canvas.get_pixel(0, 1) == RED
    assert canvas.get_pixel(1, 1) == WHITE  # Transparent, not overwritten


def test_gradient_horizontal():
    """Horizontal gradient should interpolate colors."""
    canvas = Canvas(width=10, height=1)
    canvas.gradient_horizontal(BLACK, WHITE)

    # First pixel should be black
    assert canvas.get_pixel(0, 0) == BLACK
    # Last pixel should be white
    assert canvas.get_pixel(9, 0) == WHITE
    # Middle should be gray-ish
    mid = canvas.get_pixel(5, 0)
    assert 100 < mid[0] < 200
