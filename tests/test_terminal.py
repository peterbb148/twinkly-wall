"""Tests for the terminal output renderer."""

import io

from twinkly_wall.outputs.terminal import (
    frame_to_terminal,
    print_frame,
)
from twinkly_wall.types import BLACK, RED, WHITE


def test_frame_to_terminal_empty():
    """Empty frame should return empty string."""
    assert frame_to_terminal([]) == ""
    assert frame_to_terminal([[]]) == ""


def test_frame_to_terminal_color_mode():
    """Color mode should include ANSI escape codes."""
    frame = [[(255, 0, 0)]]  # Single red pixel
    result = frame_to_terminal(frame, color_mode=True, use_half_blocks=False)
    assert "\x1b[38;2;255;0;0m" in result  # Red foreground
    assert "█" in result


def test_frame_to_terminal_grayscale_mode():
    """Grayscale mode should use block characters without colors."""
    # Bright pixel
    frame = [[WHITE]]
    result = frame_to_terminal(frame, color_mode=False)
    assert "█" in result
    assert "\x1b[38;2" not in result  # No color codes

    # Dark pixel
    frame = [[BLACK]]
    result = frame_to_terminal(frame, color_mode=False)
    assert " " in result  # Space for black


def test_frame_to_terminal_grayscale_brightness_levels():
    """Grayscale mode should use different characters for different brightness."""
    # Test various brightness levels
    # Brightness < 32 -> space
    frame = [[(0, 0, 0)]]
    assert " " in frame_to_terminal(frame, color_mode=False)

    # Brightness 32-95 -> light shade
    frame = [[(50, 50, 50)]]
    assert "░" in frame_to_terminal(frame, color_mode=False)

    # Brightness 96-159 -> medium shade
    frame = [[(130, 130, 130)]]
    assert "▒" in frame_to_terminal(frame, color_mode=False)

    # Brightness 160-223 -> dark shade
    frame = [[(200, 200, 200)]]
    assert "▓" in frame_to_terminal(frame, color_mode=False)

    # Brightness >= 224 -> full block
    frame = [[(255, 255, 255)]]
    assert "█" in frame_to_terminal(frame, color_mode=False)


def test_frame_to_terminal_half_blocks():
    """Half block mode should combine two rows into one line."""
    # 2 rows should become 1 line with half blocks
    frame = [
        [(255, 0, 0)],  # Top row - red
        [(0, 255, 0)],  # Bottom row - green
    ]
    result = frame_to_terminal(frame, color_mode=True, use_half_blocks=True)
    lines = result.split("\n")
    assert len(lines) == 1  # Two rows combined into one

    # Should have half block character
    assert "▀" in result

    # Should have both colors (foreground for top, background for bottom)
    assert "\x1b[38;2;255;0;0m" in result  # Red foreground
    assert "\x1b[48;2;0;255;0m" in result  # Green background


def test_frame_to_terminal_half_blocks_odd_height():
    """Half block mode with odd height should handle last row correctly."""
    # 3 rows should become 2 lines
    frame = [
        [(255, 0, 0)],
        [(0, 255, 0)],
        [(0, 0, 255)],
    ]
    result = frame_to_terminal(frame, color_mode=True, use_half_blocks=True)
    lines = result.split("\n")
    assert len(lines) == 2  # 3 rows -> 2 lines

    # Last line should have blue top and black bottom
    assert "\x1b[38;2;0;0;255m" in result  # Blue foreground


def test_frame_to_terminal_multiple_columns():
    """Should handle multiple columns correctly."""
    frame = [
        [(255, 0, 0), (0, 255, 0), (0, 0, 255)],  # RGB row
    ]
    result = frame_to_terminal(frame, color_mode=True, use_half_blocks=False)

    # Should have all three colors
    assert "\x1b[38;2;255;0;0m" in result
    assert "\x1b[38;2;0;255;0m" in result
    assert "\x1b[38;2;0;0;255m" in result


def test_frame_to_terminal_reset_codes():
    """Output should end with reset code."""
    frame = [[RED]]
    result = frame_to_terminal(frame, color_mode=True)
    assert result.endswith("\x1b[0m")


def test_print_frame_writes_to_file():
    """print_frame should write to specified file object."""
    frame = [[WHITE]]
    output = io.StringIO()
    print_frame(frame, file=output)
    result = output.getvalue()
    assert len(result) > 0
    assert "\n" in result  # print adds newline


def test_print_frame_color_modes():
    """print_frame should respect color mode settings."""
    frame = [[WHITE]]

    # Color mode
    output = io.StringIO()
    print_frame(frame, color_mode=True, file=output)
    assert "\x1b[38;2" in output.getvalue()

    # Grayscale mode
    output = io.StringIO()
    print_frame(frame, color_mode=False, file=output)
    assert "\x1b[38;2" not in output.getvalue()
