"""Command-line interface for Twinkly Wall."""

import argparse
import sys

from .canvas import Canvas
from .fonts import draw_text, text_width
from .outputs.terminal import print_frame
from .types import HEIGHT, RGB, WHITE, WIDTH


def parse_color(color_str: str) -> RGB:
    """
    Parse a color string into an RGB tuple.

    Supports formats:
    - Hex: #FF0000 or FF0000
    - RGB: 255,0,0
    - Named colors: red, green, blue, white, yellow, cyan, magenta, orange
    """
    color_str = color_str.strip().lower()

    # Named colors
    named_colors = {
        "black": (0, 0, 0),
        "white": (255, 255, 255),
        "red": (255, 0, 0),
        "green": (0, 255, 0),
        "blue": (0, 0, 255),
        "yellow": (255, 255, 0),
        "cyan": (0, 255, 255),
        "magenta": (255, 0, 255),
        "orange": (255, 165, 0),
        "gold": (255, 215, 0),
    }

    if color_str in named_colors:
        return named_colors[color_str]

    # Hex format
    if color_str.startswith("#"):
        color_str = color_str[1:]

    if len(color_str) == 6:
        try:
            r = int(color_str[0:2], 16)
            g = int(color_str[2:4], 16)
            b = int(color_str[4:6], 16)
            return (r, g, b)
        except ValueError:
            pass

    # RGB format: 255,0,0
    if "," in color_str:
        try:
            parts = color_str.split(",")
            if len(parts) == 3:
                return (int(parts[0]), int(parts[1]), int(parts[2]))
        except ValueError:
            pass

    raise ValueError(f"Invalid color format: {color_str}")


def render_text_centered(text: str, color: RGB = WHITE) -> list[list[RGB]]:
    """Render text centered vertically on a standard display frame."""
    canvas = Canvas(WIDTH, HEIGHT)

    # Calculate text dimensions
    tw = text_width(text)

    # Center horizontally (or start at 0 if text is wider than display)
    x = max(0, (WIDTH - tw) // 2)

    # Center vertically (font height is 7, display height is 10)
    y = 1  # This puts the 7-pixel-high text roughly centered

    draw_text(canvas, x, y, text, color)
    return canvas.copy()


def cmd_say(args: argparse.Namespace) -> int:
    """Handle the 'say' subcommand - render text to terminal."""
    try:
        color = parse_color(args.color)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    text = args.text
    frame = render_text_centered(text, color)

    print_frame(
        frame,
        color_mode=not args.no_color,
        use_half_blocks=not args.no_half_blocks,
    )

    return 0


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for twinklysay."""
    parser = argparse.ArgumentParser(
        prog="twinklysay",
        description="Render text and animations for Twinkly LED displays",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # 'say' subcommand
    say_parser = subparsers.add_parser(
        "say",
        help="Render text message",
        description="Render a text message to the terminal (or LED display)",
    )
    say_parser.add_argument(
        "text",
        help="Text to display",
    )
    say_parser.add_argument(
        "-c",
        "--color",
        default="white",
        help="Text color (name, hex #RRGGBB, or R,G,B). Default: white",
    )
    say_parser.add_argument(
        "--no-color",
        action="store_true",
        help="Use grayscale output instead of colors",
    )
    say_parser.add_argument(
        "--no-half-blocks",
        action="store_true",
        help="Use full blocks instead of half-blocks (lower resolution)",
    )

    # Version
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point for twinklysay CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "say":
        return cmd_say(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
