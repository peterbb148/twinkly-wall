"""Tests for core types."""

from twinkly_wall.types import (
    BLACK,
    HEIGHT,
    WHITE,
    WIDTH,
    blend_color,
    copy_frame,
    create_empty_frame,
    scale_color,
)


def test_create_empty_frame_dimensions():
    """Empty frame should have correct dimensions."""
    frame = create_empty_frame()
    assert len(frame) == HEIGHT
    assert all(len(row) == WIDTH for row in frame)


def test_create_empty_frame_default_color():
    """Empty frame should be filled with black by default."""
    frame = create_empty_frame()
    assert all(pixel == BLACK for row in frame for pixel in row)


def test_create_empty_frame_custom_color():
    """Empty frame can be filled with a custom color."""
    frame = create_empty_frame(WHITE)
    assert all(pixel == WHITE for row in frame for pixel in row)


def test_copy_frame_creates_independent_copy():
    """Copy should be independent of original."""
    original = create_empty_frame(BLACK)
    original[0][0] = WHITE

    copied = copy_frame(original)
    copied[0][0] = (128, 128, 128)

    assert original[0][0] == WHITE
    assert copied[0][0] == (128, 128, 128)


def test_blend_color_extremes():
    """Blend at extremes should return original colors."""
    assert blend_color(BLACK, WHITE, 0.0) == BLACK
    assert blend_color(BLACK, WHITE, 1.0) == WHITE


def test_blend_color_midpoint():
    """Blend at midpoint should average colors."""
    result = blend_color(BLACK, WHITE, 0.5)
    assert result == (127, 127, 127)


def test_scale_color():
    """Scale should multiply color values."""
    result = scale_color((100, 100, 100), 0.5)
    assert result == (50, 50, 50)


def test_scale_color_clamps():
    """Scale should clamp values to 0-255."""
    result = scale_color((200, 200, 200), 2.0)
    assert result == (255, 255, 255)

    result = scale_color((100, 100, 100), -1.0)
    assert result == (0, 0, 0)
