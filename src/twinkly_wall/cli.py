"""Command-line interface for Twinkly Wall."""

import argparse
import sys

from .canvas import Canvas
from .cards import (
    BeerCard,
    CardContext,
    CarlsbergLabCard,
    ClockCard,
    PacmanCard,
    RainbowCard,
    SnowCard,
    TestPatternCard,
    TextCard,
    TwinklysayCard,
)
from .fonts import draw_text, text_width
from .outputs.terminal import animate_frames, print_frame
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


def cmd_preview(args: argparse.Namespace) -> int:
    """Handle the 'preview' subcommand - preview a card animation."""
    card_type = args.card
    duration = args.duration

    # Create the appropriate card
    if card_type == "clock":
        try:
            color = parse_color(args.color) if args.color else WHITE
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        card = ClockCard(
            {
                "duration": duration,
                "color": list(color),
                "format_24h": not args.twelve_hour,
                "blink_colon": not args.no_blink,
            }
        )
    elif card_type == "text":
        if not args.text:
            print("Error: --text is required for text card", file=sys.stderr)
            return 1
        try:
            color = parse_color(args.color) if args.color else WHITE
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        card = TextCard(
            {
                "duration": duration,
                "text": args.text,
                "color": list(color),
                "scroll": args.scroll,
            }
        )
    elif card_type == "pacman":
        card = PacmanCard(
            {
                "duration": duration,
                "speed": args.speed,
                "theme": args.theme,
            }
        )
    elif card_type == "beer":
        card = BeerCard(
            {
                "duration": duration,
            }
        )
    elif card_type == "snow":
        card = SnowCard(
            {
                "duration": duration,
                "wind": args.wind,
                "accumulate": args.accumulate,
            }
        )
    elif card_type == "rainbow":
        card = RainbowCard(
            {
                "duration": duration,
                "mode": args.mode,
                "speed": args.speed,
            }
        )
    elif card_type == "test_pattern":
        card = TestPatternCard(
            {
                "duration": duration,
                "mode": args.pattern_mode,
            }
        )
    elif card_type == "carlsberg_lab":
        card = CarlsbergLabCard(
            {
                "duration": duration,
                "scroll_speed": args.speed,
            }
        )
    elif card_type == "twinklysay":
        if not args.text:
            print("Error: --text is required for twinklysay card", file=sys.stderr)
            return 1
        try:
            color = parse_color(args.color) if args.color else WHITE
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        card = TwinklysayCard(
            {
                "text": args.text,
                "color": list(color),
            }
        )
    else:
        print(f"Error: Unknown card type '{card_type}'", file=sys.stderr)
        print("Available cards: clock, text, pacman, beer, snow, rainbow, test_pattern, carlsberg_lab, twinklysay", file=sys.stderr)
        return 1

    # Create context and run
    ctx = CardContext()

    print(f"Previewing '{card_type}' card for {duration}s (Ctrl+C to stop)...")
    print()

    # Use animate_frames for smooth animation
    animate_frames(
        card.frames(ctx),
        color_mode=not args.no_color,
        use_half_blocks=True,
        clear_between=False,
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

    # 'preview' subcommand
    preview_parser = subparsers.add_parser(
        "preview",
        help="Preview a card animation",
        description="Preview a card animation in the terminal",
    )
    preview_parser.add_argument(
        "card",
        choices=["clock", "text", "pacman", "beer", "snow", "rainbow", "test_pattern", "carlsberg_lab", "twinklysay"],
        help="Card type to preview",
    )
    preview_parser.add_argument(
        "-d",
        "--duration",
        type=float,
        default=10.0,
        help="Duration in seconds (default: 10)",
    )
    preview_parser.add_argument(
        "-c",
        "--color",
        help="Text color (name, hex #RRGGBB, or R,G,B)",
    )
    preview_parser.add_argument(
        "--no-color",
        action="store_true",
        help="Use grayscale output",
    )
    # Clock-specific options
    preview_parser.add_argument(
        "--twelve-hour",
        action="store_true",
        help="Use 12-hour format (clock only)",
    )
    preview_parser.add_argument(
        "--no-blink",
        action="store_true",
        help="Disable colon blinking (clock only)",
    )
    # Text-specific options
    preview_parser.add_argument(
        "-t",
        "--text",
        help="Text message (required for text card)",
    )
    preview_parser.add_argument(
        "--scroll",
        action="store_true",
        help="Force scrolling (text card)",
    )
    # Pacman-specific options
    preview_parser.add_argument(
        "--speed",
        type=float,
        default=15.0,
        help="Animation speed in pixels/sec (pacman card, default: 15)",
    )
    preview_parser.add_argument(
        "--theme",
        choices=["trees", "beer", "hearts", "snow", "ghosts", "dots", "snowman", "hops"],
        default="trees",
        help="What Pac-Man eats (pacman card, default: trees)",
    )
    # Snow-specific options
    preview_parser.add_argument(
        "--wind",
        type=float,
        default=0.0,
        help="Wind direction -1 to 1 (snow card, default: 0)",
    )
    preview_parser.add_argument(
        "--accumulate",
        action="store_true",
        help="Accumulate snow at bottom (snow card)",
    )
    # Rainbow-specific options
    preview_parser.add_argument(
        "--mode",
        choices=["rainbow", "plasma", "wave", "gradient"],
        default="rainbow",
        help="Rainbow animation mode (rainbow card, default: rainbow)",
    )
    # Test pattern options
    preview_parser.add_argument(
        "--pattern-mode",
        choices=["rows", "all_rows", "cols", "corners", "gradient", "numbers"],
        default="rows",
        help="Test pattern mode (test_pattern card, default: rows)",
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
    elif args.command == "preview":
        return cmd_preview(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
