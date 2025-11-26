"""Tests for the CLI module."""

import pytest

from twinkly_wall.cli import create_parser, main, parse_color, render_text_centered


class TestParseColor:
    """Tests for color parsing."""

    def test_named_colors(self):
        """Should parse named colors."""
        assert parse_color("red") == (255, 0, 0)
        assert parse_color("green") == (0, 255, 0)
        assert parse_color("blue") == (0, 0, 255)
        assert parse_color("white") == (255, 255, 255)
        assert parse_color("black") == (0, 0, 0)

    def test_named_colors_case_insensitive(self):
        """Named colors should be case insensitive."""
        assert parse_color("RED") == (255, 0, 0)
        assert parse_color("Red") == (255, 0, 0)

    def test_hex_with_hash(self):
        """Should parse hex colors with # prefix."""
        assert parse_color("#FF0000") == (255, 0, 0)
        assert parse_color("#00ff00") == (0, 255, 0)
        assert parse_color("#0000FF") == (0, 0, 255)

    def test_hex_without_hash(self):
        """Should parse hex colors without # prefix."""
        assert parse_color("FF0000") == (255, 0, 0)
        assert parse_color("00ff00") == (0, 255, 0)

    def test_rgb_format(self):
        """Should parse R,G,B format."""
        assert parse_color("255,0,0") == (255, 0, 0)
        assert parse_color("0,255,0") == (0, 255, 0)
        assert parse_color("128,128,128") == (128, 128, 128)

    def test_invalid_color(self):
        """Should raise ValueError for invalid colors."""
        with pytest.raises(ValueError):
            parse_color("notacolor")
        with pytest.raises(ValueError):
            parse_color("GGGGGG")  # Invalid hex


class TestRenderTextCentered:
    """Tests for text rendering."""

    def test_renders_frame(self):
        """Should return a valid frame."""
        frame = render_text_centered("Hi")
        assert len(frame) == 10  # HEIGHT
        assert len(frame[0]) == 50  # WIDTH

    def test_renders_with_color(self):
        """Should render text with specified color."""
        red = (255, 0, 0)
        frame = render_text_centered("A", red)

        # Should have at least one red pixel
        has_red = any(frame[y][x] == red for y in range(len(frame)) for x in range(len(frame[0])))
        assert has_red


class TestParser:
    """Tests for argument parser."""

    def test_say_command(self):
        """Should parse say command with text."""
        parser = create_parser()
        args = parser.parse_args(["say", "Hello"])
        assert args.command == "say"
        assert args.text == "Hello"

    def test_say_with_color(self):
        """Should parse say command with color option."""
        parser = create_parser()
        args = parser.parse_args(["say", "Hello", "-c", "red"])
        assert args.color == "red"

    def test_say_with_no_color(self):
        """Should parse no-color flag."""
        parser = create_parser()
        args = parser.parse_args(["say", "Hello", "--no-color"])
        assert args.no_color is True

    def test_say_default_color(self):
        """Default color should be white."""
        parser = create_parser()
        args = parser.parse_args(["say", "Hello"])
        assert args.color == "white"


class TestMain:
    """Tests for main entry point."""

    def test_no_command_shows_help(self, capsys):
        """No command should print help and return 0."""
        result = main([])
        assert result == 0
        captured = capsys.readouterr()
        assert "twinklysay" in captured.out

    def test_say_command_runs(self, capsys):
        """Say command should render and return 0."""
        result = main(["say", "Hi"])
        assert result == 0
        captured = capsys.readouterr()
        # Should have output with ANSI codes or block characters
        assert len(captured.out) > 0

    def test_say_invalid_color(self, capsys):
        """Invalid color should return error."""
        result = main(["say", "Hi", "-c", "notacolor"])
        assert result == 1
        captured = capsys.readouterr()
        assert "Error" in captured.err
