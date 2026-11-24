"""Command-line interface for Twinkly Wall."""

import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import requests
import typer
import yaml

from . import __version__
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
from .cards.base import load_card_definitions
from .config import _process_env_vars, load_playlist, load_settings
from .fonts import draw_text, text_width
from .outputs.terminal import animate_frames, print_frame
from .outputs.twinkly import TwinklyOutput
from .types import HEIGHT, RGB, WHITE, WIDTH, Orientation


@dataclass
class CLIOptions:
    """Validated command options passed to the existing rendering handlers."""

    card: str | None = None
    id: int | None = None
    playlist: Path | None = None
    settings: Path | None = None
    duration: float = 10.0
    color: str | None = None
    no_color: bool = False
    no_half_blocks: bool = False
    orientation: Orientation | None = None
    twelve_hour: bool = False
    no_blink: bool = False
    text: str | None = None
    scroll: bool = False
    scroll_direction: str = "horizontal"
    speed: float = 15.0
    theme: str = "trees"
    wind: float = 0.0
    accumulate: bool = False
    mode: str = "rainbow"
    pattern_mode: str = "rows"
    server: str | None = None
    interval: float = 2.0
    api_key: str | None = None


def create_context_with_datasources(settings_path: Path | None = None) -> CardContext:
    """Create a CardContext with datasources from settings."""
    settings = load_settings(settings_path)
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


def _build_card(card_type: str, args: CLIOptions, duration: float):
    """Create a card instance from CLI arguments or playlist selection."""
    if args.id is not None:
        return _card_from_playlist(args.id, getattr(args, "playlist", None))

    # Create the appropriate card
    if card_type == "clock":
        try:
            color = parse_color(args.color) if args.color else WHITE
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return None, ""
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


def cmd_say(args: CLIOptions) -> int:
    """Handle the 'say' subcommand - render text to terminal."""
    try:
        color = parse_color(args.color or "white")
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    text = args.text
    frame = render_text_centered(text or "", color)

    print_frame(
        frame,
        color_mode=not args.no_color,
        use_half_blocks=not args.no_half_blocks,
    )

    return 0


def cmd_card(args: CLIOptions) -> int:
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
    if not settings.twinkly.host:
        raise ValueError("Configure twinkly.host in --settings before sending to a device")
    output = TwinklyOutput(
        host=settings.twinkly.host,
        port=settings.twinkly.port,
        mirror_h=settings.twinkly.mirror_h,
        mirror_v=settings.twinkly.mirror_v,
    )
    output.orientation = args.orientation or settings.twinkly.orientation

    ctx = create_context_with_datasources(args.settings)

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


def cmd_list(args: CLIOptions) -> int:
    """List available registered cards and optional playlist entries."""
    definitions = load_card_definitions()
    print("Registered cards:")
    for name in sorted(list_card_types(definitions)):
        definition = definitions.get(name)
        if definition is None:
            print(f" - {name}")
        else:
            print(f" - {name} ({definition.source})")

    if args.playlist:
        playlist = load_playlist(args.playlist)
        if playlist.cards:
            print(f"\nPlaylist ({args.playlist}):")
            for idx, cfg in enumerate(playlist.cards, start=1):
                print(f" [{idx}] {cfg.type}")
        else:
            print(f"\nPlaylist {args.playlist} is empty.")
    return 0


def cmd_mcp(args: CLIOptions) -> int:
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
        if not client.register_cards():
            raise ConnectionError(f"Could not register cards with MCP server at {server_url}")
        client.run(use_terminal=True, register=False)
    except KeyboardInterrupt:
        print("\nStopped.")

    return 0


def cmd_preview(args: CLIOptions) -> int:
    """Handle the 'preview' subcommand - preview a card animation."""
    card_type = args.card
    duration = args.duration

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
    ctx = create_context_with_datasources(args.settings)

    name = label or card_type
    print(f"Previewing '{name}' card for {duration}s (Ctrl+C to stop)...")
    print()

    display = load_settings(args.settings).twinkly
    animate_frames(
        card.frames(ctx),
        color_mode=not args.no_color,
        use_half_blocks=True,
        clear_between=False,
        orientation=args.orientation or display.orientation,
        mirror_h=display.mirror_h,
        mirror_v=display.mirror_v,
    )

    return 0


def _preview_playlist(args: CLIOptions) -> int:
    """Preview an entire playlist in the terminal."""
    playlist = load_playlist(args.playlist)
    if not playlist.cards:
        print(f"No cards found in playlist: {args.playlist}", file=sys.stderr)
        return 1

    ctx = create_context_with_datasources(args.settings)
    display = load_settings(args.settings).twinkly
    total_cards = len(playlist.cards)

    print(f"Previewing playlist: {args.playlist} ({total_cards} cards)")
    print("Press Ctrl+C to stop")
    print()

    try:
        while True:  # Loop playlist
            for idx, cfg in enumerate(playlist.cards, start=1):
                card = create_card(cfg.type, {**cfg.config, "duration": cfg.duration})
                if card is None:
                    raise ValueError(f"Unknown card type in playlist: {cfg.type}")

                print(f"[{idx}/{total_cards}] {cfg.type} ({cfg.duration}s)")

                animate_frames(
                    card.frames(ctx),
                    color_mode=not args.no_color,
                    use_half_blocks=True,
                    clear_between=False,
                    orientation=args.orientation or display.orientation,
                    mirror_h=display.mirror_h,
                    mirror_v=display.mirror_v,
                )
    except KeyboardInterrupt:
        print("\nStopped.")

    return 0


# Typed values shared by the Typer commands.
class ScrollDirection(StrEnum):
    """Text scrolling directions."""

    horizontal = "horizontal"
    vertical_up = "vertical_up"
    vertical_down = "vertical_down"
    vertical_rotated_up = "vertical_rotated_up"
    vertical_rotated_down = "vertical_rotated_down"


class PacmanTheme(StrEnum):
    """Supported Pac-Man themes."""

    trees = "trees"
    beer = "beer"
    hearts = "hearts"
    snow = "snow"
    ghosts = "ghosts"
    dots = "dots"
    snowman = "snowman"
    hops = "hops"


class RainbowMode(StrEnum):
    """Rainbow rendering modes."""

    rainbow = "rainbow"
    plasma = "plasma"
    wave = "wave"
    gradient = "gradient"


class PatternMode(StrEnum):
    """Device test patterns."""

    rows = "rows"
    all_rows = "all_rows"
    cols = "cols"
    corners = "corners"
    gradient = "gradient"
    numbers = "numbers"


def _validate_card(value: str | None) -> str | None:
    """Reject unknown card names before starting rendering or contacting hardware."""
    if value is not None and value not in _registered_card_names():
        raise typer.BadParameter(
            f"Unknown card '{value}'. Use 'twinklysay list' for available cards."
        )
    return value


def _registered_card_names() -> set[str]:
    """Resolve card names for Typer validation and report catalog errors."""
    try:
        return set(list_card_types())
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error


def _validate_config_path(value: Path | None, *, playlist: bool) -> Path | None:
    """Validate explicit YAML input before the existing loaders consume it."""
    if value is None:
        return None
    try:
        data = yaml.safe_load(value.read_text())
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise typer.BadParameter(f"Cannot read YAML: {error}") from error
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise typer.BadParameter("Configuration must be a YAML mapping")
    data = _process_env_vars(data)
    if playlist:
        cards = data.get("cards", [])
        if not isinstance(cards, list):
            raise typer.BadParameter("Playlist cards must be a list")
        names = _registered_card_names()
        for item in cards:
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("type"), str)
                or item["type"] not in names
            ):
                raise typer.BadParameter("Each playlist card must have a registered type")
    else:
        for section in ("twinkly", "weather", "operating_hours"):
            if section in data and not isinstance(data[section], dict):
                raise typer.BadParameter(f"Settings section '{section}' must be a mapping")
        orientation = data.get("twinkly", {}).get("orientation", "horizontal")
        if not isinstance(orientation, str) or orientation not in {
            item.value for item in Orientation
        }:
            raise typer.BadParameter(f"Invalid display orientation: {orientation}")
    return value


def _validate_playlist(value: Path | None) -> Path | None:
    """Validate an explicitly selected playlist."""
    return _validate_config_path(value, playlist=True)


def _validate_settings(value: Path | None) -> Path | None:
    """Validate an explicitly selected settings file."""
    return _validate_config_path(value, playlist=False)


ConfigPath = Annotated[
    Path | None,
    typer.Option(
        exists=True, file_okay=True, dir_okay=False, readable=True, callback=_validate_playlist
    ),
]
CardName = Annotated[
    str | None, typer.Argument(callback=_validate_card, help="Registered card type")
]
PlaylistID = Annotated[int | None, typer.Option("--id", min=1, help="Playlist card ID (1-based)")]
Duration = Annotated[float, typer.Option("--duration", "-d", min=0.001, help="Duration in seconds")]
Color = Annotated[str | None, typer.Option("--color", "-c", help="Color name, hex, or R,G,B")]
Text = Annotated[str | None, typer.Option("--text", "-t", help="Text for text/twinklysay cards")]
Speed = Annotated[float, typer.Option(min=0.001, help="Animation speed in pixels/sec")]
Wind = Annotated[float, typer.Option(min=-1, max=1, help="Snow wind direction")]
NoColor = Annotated[bool, typer.Option("--no-color", help="Render grayscale terminal output")]
Mount = Annotated[
    Orientation | None, typer.Option("--orientation", help="Wire edge as seen from the front")
]
SettingsPath = Annotated[
    Path | None,
    typer.Option(
        "--settings", "-s", exists=True, dir_okay=False, readable=True, callback=_validate_settings
    ),
]

app = typer.Typer(
    name="say",
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Render text and animations for Twinkly LED displays.",
    add_completion=False,
    pretty_exceptions_enable=False,
)


def _version_callback(value: bool) -> None:
    """Print the application version without requiring a subcommand."""
    if value:
        typer.echo(f"twinkly-cli {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def cli(
    ctx: typer.Context,
    version: Annotated[
        bool, typer.Option("--version", callback=_version_callback, is_eager=True)
    ] = False,
) -> None:
    """Show help when invoked without a command."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


def _execute(handler: Callable[[CLIOptions], int], options: CLIOptions) -> None:
    """Translate expected input and provider failures into a useful command exit code."""
    try:
        code = handler(options)
    except KeyboardInterrupt:
        typer.echo("\nStopped.", err=True)
        code = 130
    except (OSError, ValueError, yaml.YAMLError, requests.RequestException) as error:
        typer.echo(f"Error: {error}", err=True)
        code = 1
    raise typer.Exit(code)


@app.command("text")
def say(
    text: Annotated[str, typer.Argument(help="Text to display")],
    color: Annotated[str, typer.Option("--color", "-c")] = "white",
    no_color: NoColor = False,
    no_half_blocks: Annotated[bool, typer.Option("--no-half-blocks")] = False,
) -> None:
    """Render a text message in the terminal."""
    _execute(
        cmd_say,
        CLIOptions(text=text, color=color, no_color=no_color, no_half_blocks=no_half_blocks),
    )


@app.command("list")
def list_cards(playlist: ConfigPath = None) -> None:
    """List registered cards and optional numbered playlist entries."""
    _execute(cmd_list, CLIOptions(playlist=playlist))


@app.command("mcp")
def mcp(
    server: Annotated[str | None, typer.Option("--server", "-s", envvar="TWINKLY_MCP_URL")] = None,
    interval: Annotated[float, typer.Option("--interval", "-i", min=0.001)] = 2.0,
    api_key: Annotated[str | None, typer.Option(envvar="TWINKLY_API_KEY")] = None,
) -> None:
    """Poll the MCP server for remote commands and render them in the terminal."""
    _execute(cmd_mcp, CLIOptions(server=server, interval=interval, api_key=api_key))


@app.command("preview")
def preview(
    card: CardName = None,
    id: PlaylistID = None,
    playlist: ConfigPath = None,
    duration: Duration = 10.0,
    color: Color = None,
    no_color: NoColor = False,
    orientation: Mount = None,
    settings: SettingsPath = None,
    twelve_hour: bool = False,
    no_blink: bool = False,
    text: Text = None,
    scroll: bool = False,
    scroll_direction: ScrollDirection = ScrollDirection.horizontal,
    speed: Speed = 15.0,
    theme: PacmanTheme = PacmanTheme.trees,
    wind: Wind = 0.0,
    accumulate: bool = False,
    mode: RainbowMode = RainbowMode.rainbow,
    pattern_mode: PatternMode = PatternMode.rows,
) -> None:
    """Preview a card, a playlist entry, or a looping playlist in the terminal."""
    _execute(
        cmd_preview,
        CLIOptions(
            card=card,
            id=id,
            playlist=playlist,
            duration=duration,
            color=color,
            no_color=no_color,
            orientation=orientation,
            settings=settings,
            twelve_hour=twelve_hour,
            no_blink=no_blink,
            text=text,
            scroll=scroll,
            scroll_direction=scroll_direction,
            speed=speed,
            theme=theme,
            wind=wind,
            accumulate=accumulate,
            mode=mode,
            pattern_mode=pattern_mode,
        ),
    )


@app.command("card")
def card(
    card: CardName = None,
    id: PlaylistID = None,
    playlist: ConfigPath = None,
    settings: SettingsPath = None,
    duration: Duration = 10.0,
    color: Color = None,
    no_color: NoColor = False,
    orientation: Mount = None,
    twelve_hour: bool = False,
    no_blink: bool = False,
    text: Text = None,
    scroll: bool = False,
    scroll_direction: ScrollDirection = ScrollDirection.horizontal,
    speed: Speed = 15.0,
    theme: PacmanTheme = PacmanTheme.trees,
    wind: Wind = 0.0,
    accumulate: bool = False,
    mode: RainbowMode = RainbowMode.rainbow,
    pattern_mode: PatternMode = PatternMode.rows,
) -> None:
    """Send a card or numbered playlist entry directly to the Twinkly device."""
    _execute(
        cmd_card,
        CLIOptions(
            card=card,
            id=id,
            playlist=playlist,
            settings=settings,
            duration=duration,
            color=color,
            no_color=no_color,
            orientation=orientation,
            twelve_hour=twelve_hour,
            no_blink=no_blink,
            text=text,
            scroll=scroll,
            scroll_direction=scroll_direction,
            speed=speed,
            theme=theme,
            wind=wind,
            accumulate=accumulate,
            mode=mode,
            pattern_mode=pattern_mode,
        ),
    )


def main(argv: list[str] | None = None) -> int:
    """Run the Typer application and return its exit code for console entry points."""
    try:
        app(args=argv, prog_name="twinkly-cli say")
    except SystemExit as error:
        return int(error.code or 0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
