"""Command-line interface for Twinkly Wall."""

import argparse
import sys
import time

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
    create_card,
    list_card_types,
)
from .config import load_playlist, load_settings
from .fonts import draw_text, text_width
from .outputs.terminal import animate_frames, print_frame
from .outputs.twinkly import TwinklyOutput
from .types import HEIGHT, RGB, WHITE, WIDTH, Orientation


def create_context_with_datasources() -> CardContext:
    """Create a CardContext with datasources from settings."""
    settings = load_settings()
    datasources: dict = {}

    # Add weather datasource if configured
    if settings.weather.latitude and settings.weather.longitude:
        from .datasources.weather import WeatherDataSource

        datasources["weather"] = WeatherDataSource(
            latitude=settings.weather.latitude,
            longitude=settings.weather.longitude,
            cache_duration=settings.weather.cache_duration,
        )

    return CardContext(datasources=datasources)


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


def _card_from_playlist(index: int, playlist_path: str | None):
    """Load a card from a playlist by index (1-based)."""
    playlist = load_playlist(playlist_path)
    if not playlist.cards:
        print("No cards found in playlist", file=sys.stderr)
        return None, ""
    if index < 1 or index > len(playlist.cards):
        print(f"Card id {index} out of range (1-{len(playlist.cards)})", file=sys.stderr)
        return None, ""
    cfg = playlist.cards[index - 1]
    card = create_card(cfg.type, {**cfg.config, "duration": cfg.duration})
    if card is None:
        print(f"Unknown card type '{cfg.type}' in playlist", file=sys.stderr)
        return None, ""
    label = f"{index}:{cfg.type}"
    return card, label


def _build_card(card_type: str, args: argparse.Namespace, duration: float):
    """Create a card instance from CLI arguments or playlist selection."""
    if getattr(args, "id", None):
        return _card_from_playlist(args.id, getattr(args, "playlist", None))

    # Create the appropriate card
    if card_type == "clock":
        try:
            color = parse_color(args.color) if args.color else WHITE
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return None
        card = ClockCard(
            {
                "duration": duration,
                "color": list(color),
                "format_24h": not args.twelve_hour,
                "blink_colon": not args.no_blink,
            }
        )
        return card, "clock"
    if card_type == "text":
        if not args.text:
            print("Error: --text is required for text card", file=sys.stderr)
            return None, ""
        try:
            color = parse_color(args.color) if args.color else WHITE
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return None, ""
        card = TextCard(
            {
                "duration": duration,
                "text": args.text,
                "color": list(color),
                "scroll": args.scroll,
                "scroll_direction": getattr(args, "scroll_direction", "horizontal"),
            }
        )
        return card, "text"
    if card_type == "pacman":
        return PacmanCard(
            {
                "duration": duration,
                "speed": args.speed,
                "theme": args.theme,
            }
        ), "pacman"
    if card_type == "beer":
        return BeerCard(
            {
                "duration": duration,
            }
        ), "beer"
    if card_type == "snow":
        return SnowCard(
            {
                "duration": duration,
                "wind": args.wind,
                "accumulate": args.accumulate,
            }
        ), "snow"
    if card_type == "rainbow":
        return RainbowCard(
            {
                "duration": duration,
                "mode": args.mode,
                "speed": args.speed,
            }
        ), "rainbow"
    if card_type == "test_pattern":
        return TestPatternCard(
            {
                "duration": duration,
                "mode": args.pattern_mode,
            }
        ), "test_pattern"
    if card_type == "carlsberg_lab":
        return CarlsbergLabCard(
            {
                "duration": duration,
                "scroll_speed": args.speed,
            }
        ), "carlsberg_lab"
    if card_type == "twinklysay":
        if not args.text:
            print("Error: --text is required for twinklysay card", file=sys.stderr)
            return None, ""
        try:
            color = parse_color(args.color) if args.color else WHITE
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return None, ""
        return TwinklysayCard(
            {
                "text": args.text,
                "color": list(color),
                "scroll_direction": getattr(args, "scroll_direction", "horizontal"),
            }
        ), "twinklysay"

    # Fallback: instantiate any registered card with default config
    generic = create_card(card_type, {"duration": duration})
    if generic:
        return generic, card_type

    print(f"Error: Unknown card type '{card_type}'", file=sys.stderr)
    available = ", ".join(sorted(list_card_types()))
    print(f"Available cards: {available}", file=sys.stderr)
    return None, ""


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


def cmd_card(args: argparse.Namespace) -> int:
    """Handle the 'card' subcommand - send a card to the Twinkly LED device."""
    card_type = args.card
    duration = args.duration

    if not args.id and not card_type:
        print("Please provide a card type or --id from playlist", file=sys.stderr)
        return 1

    card, label = _build_card(card_type, args, duration)
    if card is None:
        return 1

    settings = load_settings(args.settings)
    output = TwinklyOutput(
        host=settings.twinkly.host,
        port=settings.twinkly.port,
        mirror_h=settings.twinkly.mirror_h,
        mirror_v=settings.twinkly.mirror_v,
    )
    output.orientation = settings.twinkly.orientation

    ctx = create_context_with_datasources()

    name = label or card_type
    print(f"Sending '{name}' card to Twinkly at {settings.twinkly.host}...")

    try:
        output.start()
        for frame, delay in card.frames(ctx):
            output.send_frame(frame)
            time.sleep(delay)
    except Exception as e:
        print(f"Error sending card: {e}", file=sys.stderr)
        return 1
    finally:
        try:
            output.stop()
        except Exception:
            pass

    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List available registered cards and optional playlist entries."""
    types = sorted(list_card_types())
    print("Registered cards:")
    for name in types:
        print(f" - {name}")

    if args.playlist:
        playlist = load_playlist(args.playlist)
        if playlist.cards:
            print(f"\nPlaylist ({args.playlist}):")
            for idx, cfg in enumerate(playlist.cards, start=1):
                print(f" [{idx}] {cfg.type}")
        else:
            print(f"\nPlaylist {args.playlist} is empty or not found.")
    return 0


def cmd_mcp(args: argparse.Namespace) -> int:
    """Handle the 'mcp' subcommand - start MCP polling client."""
    import os

    from .mcp_client import MCPClient

    server_url = args.server or os.environ.get(
        "TWINKLY_MCP_URL", "https://twinkly-mcp.onrender.com"
    )
    api_key = args.api_key or os.environ.get("TWINKLY_API_KEY")
    poll_interval = args.interval

    print("Starting MCP client...")
    print(f"  Server: {server_url}")
    print(f"  Poll interval: {poll_interval}s")
    print("  Output: terminal")
    print()
    print("Waiting for commands from Claude... (Ctrl+C to stop)")
    print()

    client = MCPClient(
        server_url=server_url,
        poll_interval=poll_interval,
        api_key=api_key,
    )

    try:
        client.run(use_terminal=True)
    except KeyboardInterrupt:
        print("\nStopped.")

    return 0


def _resolve_orientation(arg_value: str | None) -> Orientation:
    """Resolve preview orientation, falling back to settings if not provided."""
    if arg_value:
        return arg_value  # type: ignore[return-value]

    # Load default settings (config/settings.yaml, settings.yaml, or ~/.config)
    settings = load_settings()
    return settings.twinkly.orientation


def cmd_preview(args: argparse.Namespace) -> int:
    """Handle the 'preview' subcommand - preview a card animation."""
    card_type = args.card
    duration = args.duration
    orientation: Orientation = _resolve_orientation(getattr(args, "orientation", None))

    # If playlist provided without --id or card type, play entire playlist
    if args.playlist and not args.id and not card_type:
        return _preview_playlist(args)

    if not args.id and not card_type:
        print("Please provide a card type or --id from playlist", file=sys.stderr)
        return 1

    card, label = _build_card(card_type, args, duration)
    if card is None:
        return 1

    # Create context and run
    ctx = create_context_with_datasources()

    name = label or card_type
    print(f"Previewing '{name}' card for {duration}s (Ctrl+C to stop)...")
    print()

    # Use animate_frames for smooth animation
    animate_frames(
        card.frames(ctx),
        color_mode=not args.no_color,
        use_half_blocks=True,
        clear_between=False,
        orientation=orientation,
    )

    return 0


def _preview_playlist(args: argparse.Namespace) -> int:
    """Preview an entire playlist in the terminal."""
    playlist = load_playlist(args.playlist)
    if not playlist.cards:
        print(f"No cards found in playlist: {args.playlist}", file=sys.stderr)
        return 1

    ctx = create_context_with_datasources()
    total_cards = len(playlist.cards)

    print(f"Previewing playlist: {args.playlist} ({total_cards} cards)")
    print("Press Ctrl+C to stop")
    print()

    try:
        while True:  # Loop playlist
            for idx, cfg in enumerate(playlist.cards, start=1):
                card = create_card(cfg.type, {**cfg.config, "duration": cfg.duration})
                if card is None:
                    print(f"Skipping unknown card type: {cfg.type}")
                    continue

                print(f"[{idx}/{total_cards}] {cfg.type} ({cfg.duration}s)")

                animate_frames(
                    card.frames(ctx),
                    color_mode=not args.no_color,
                    use_half_blocks=True,
                    clear_between=False,
                    orientation=_resolve_orientation(getattr(args, "orientation", None)),
                )
    except KeyboardInterrupt:
        print("\nStopped.")

    return 0


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for twinklysay."""
    parser = argparse.ArgumentParser(
        prog="twinklysay",
        description="Render text and animations for Twinkly LED displays",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # 'list' subcommand
    list_parser = subparsers.add_parser(
        "list",
        help="List available cards (and optional playlist entries)",
    )
    list_parser.add_argument(
        "--playlist",
        type=str,
        help="Path to cards.yaml to show indexed entries",
    )

    # 'mcp' subcommand - MCP polling client
    mcp_parser = subparsers.add_parser(
        "mcp",
        help="Start MCP polling client for remote control",
        description="Poll the MCP server for commands from Claude Desktop",
    )
    mcp_parser.add_argument(
        "-s",
        "--server",
        type=str,
        help="MCP server URL (default: $TWINKLY_MCP_URL or https://twinkly-mcp.onrender.com)",
    )
    mcp_parser.add_argument(
        "-i",
        "--interval",
        type=float,
        default=2.0,
        help="Poll interval in seconds (default: 2)",
    )
    mcp_parser.add_argument(
        "--api-key",
        type=str,
        help="API key for authentication (default: $TWINKLY_API_KEY)",
    )

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
        nargs="?",
        choices=sorted(list_card_types()),
        help="Card type to preview (required unless --id is used)",
    )
    preview_parser.add_argument(
        "--id",
        type=int,
        help="Preview a card by id from a playlist (1-based)",
    )
    preview_parser.add_argument(
        "--playlist",
        type=str,
        help=(
            "Path to playlist yaml. Use alone to preview entire playlist, "
            "or with --id for single card"
        ),
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
    preview_parser.add_argument(
        "--orientation",
        choices=["horizontal", "vertical_left", "vertical_right"],
        default=None,
        help=(
            "Display orientation for preview. "
            "Default: twinkly.orientation from settings.yaml (or horizontal)."
        ),
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
    preview_parser.add_argument(
        "--scroll-direction",
        choices=[
            "horizontal",
            "vertical_up",
            "vertical_down",
            "vertical_rotated_up",
            "vertical_rotated_down",
        ],
        default="horizontal",
        help="Scroll direction for text/twinklysay cards (default: horizontal)",
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

    # 'card' subcommand - send a card directly to the Twinkly device
    card_parser = subparsers.add_parser(
        "card",
        help="Send a single card to the Twinkly LED display",
        description="Render a specific card on the Twinkly device (uses settings.yaml)",
    )
    card_parser.add_argument(
        "card",
        nargs="?",
        choices=sorted(list_card_types()),
        help="Card type to display (required unless --id is used)",
    )
    card_parser.add_argument(
        "--id",
        type=int,
        help="Display a card by id from a playlist (1-based)",
    )
    card_parser.add_argument(
        "--playlist",
        type=str,
        help="Path to cards.yaml for --id (default: config/cards.yaml)",
    )
    card_parser.add_argument(
        "-s",
        "--settings",
        type=str,
        help="Path to settings.yaml (default: config/settings.yaml)",
    )
    card_parser.add_argument(
        "-d",
        "--duration",
        type=float,
        default=10.0,
        help="Duration in seconds (default: 10, some cards ignore)",
    )
    card_parser.add_argument(
        "-c",
        "--color",
        help="Text color (name, hex #RRGGBB, or R,G,B)",
    )
    card_parser.add_argument(
        "--no-color",
        action="store_true",
        help="Use grayscale output",
    )
    # Clock-specific options
    card_parser.add_argument(
        "--twelve-hour",
        action="store_true",
        help="Use 12-hour format (clock only)",
    )
    card_parser.add_argument(
        "--no-blink",
        action="store_true",
        help="Disable colon blinking (clock only)",
    )
    # Text-specific options
    card_parser.add_argument(
        "-t",
        "--text",
        help="Text message (required for text/twinklysay card)",
    )
    card_parser.add_argument(
        "--scroll",
        action="store_true",
        help="Force scrolling (text card)",
    )
    card_parser.add_argument(
        "--scroll-direction",
        choices=[
            "horizontal",
            "vertical_up",
            "vertical_down",
            "vertical_rotated_up",
            "vertical_rotated_down",
        ],
        default="horizontal",
        help="Scroll direction for text/twinklysay cards (default: horizontal)",
    )
    # Pacman-specific options
    card_parser.add_argument(
        "--speed",
        type=float,
        default=15.0,
        help="Animation speed in pixels/sec (pacman/carlsberg_lab card, default: 15)",
    )
    card_parser.add_argument(
        "--theme",
        choices=["trees", "beer", "hearts", "snow", "ghosts", "dots", "snowman", "hops"],
        default="trees",
        help="What Pac-Man eats (pacman card, default: trees)",
    )
    # Snow-specific options
    card_parser.add_argument(
        "--wind",
        type=float,
        default=0.0,
        help="Wind direction -1 to 1 (snow card, default: 0)",
    )
    card_parser.add_argument(
        "--accumulate",
        action="store_true",
        help="Accumulate snow at bottom (snow card)",
    )
    # Rainbow-specific options
    card_parser.add_argument(
        "--mode",
        choices=["rainbow", "plasma", "wave", "gradient"],
        default="rainbow",
        help="Rainbow animation mode (rainbow card, default: rainbow)",
    )
    # Test pattern options
    card_parser.add_argument(
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

    if args.command == "list":
        return cmd_list(args)
    elif args.command == "mcp":
        return cmd_mcp(args)
    elif args.command == "say":
        return cmd_say(args)
    elif args.command == "preview":
        return cmd_preview(args)
    elif args.command == "card":
        return cmd_card(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
