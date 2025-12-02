# Twinkly Wall

A Raspberry Pi-controlled LED billboard using Twinkly Matrix 500 (10×50 pixel display) for office Christmas fun.

## Features

- **CLI Preview Tool** (`twinklysay`) - Preview animations in your terminal
- **Display Cards** - Clock, weather, leaderboards, custom messages
- **Animations** - Pac-Man eating Christmas trees, beer bubbles, snowfall
- **Configurable Playlist** - YAML-based card rotation

## Architecture

```
[Raspberry Pi] ─── Wi-Fi AP ───> [Twinkly Matrix 500]
      │                              10 × 50 LEDs
      │
   Ethernet
      │
      v
  [Router/Internet]
      (for weather API, etc.)
```

## Quick Start

```bash
# Install with UV
uv pip install -e .

# Run the CLI
uv run twinklysay --help
```

## CLI Usage (`twinklysay`)

The `twinklysay` command provides two subcommands for terminal preview and testing.

- List registered cards (and optionally the playlist with ids):

```bash
uv run twinklysay list --playlist config/cards.yaml
```

### Display Text (`say`)

Render a static text message in your terminal:

```bash
# Basic text (white)
uv run twinklysay say "Hello World"

# Colored text (by name)
uv run twinklysay say "Merry Christmas" --color red

# Colored text (hex)
uv run twinklysay say "Happy New Year" --color "#FFD700"

# Colored text (RGB)
uv run twinklysay say "Cheers!" --color 255,165,0
```

**Supported color names:** black, white, red, green, blue, yellow, cyan, magenta, orange, gold

### Preview Animations (`preview`)

Preview card animations in your terminal:

```bash
# Clock (24-hour format, blinking colon)
uv run twinklysay preview clock

# Clock (12-hour format)
uv run twinklysay preview clock --twelve-hour

# Scrolling text
uv run twinklysay preview text --text "Hello from the Twinkly Wall!"

# Pac-Man eating Christmas trees
uv run twinklysay preview pacman --theme trees

# Pac-Man eating beer mugs
uv run twinklysay preview pacman --theme beer

# Snowfall
uv run twinklysay preview snow

# Snowfall with wind and accumulation
uv run twinklysay preview snow --wind 0.5 --accumulate

# Beer bubbles
uv run twinklysay preview beer

# Rainbow effects
uv run twinklysay preview rainbow --mode plasma

# Twinklysay (scrolling message, used for remote messages)
uv run twinklysay preview twinklysay --text "Remote message!" --color gold

# Send a card to the LED device (one-shot)
uv run twinklysay card twinklysay --text "Hello LED!" --color gold

# Send a playlist card by id (uses cards.yaml)
uv run twinklysay card --id 3 --playlist config/cards.yaml
```

**Available cards:** clock, text, pacman, beer, snow, rainbow, test_pattern, carlsberg_lab, twinklysay

### Common Options

| Option | Description |
|--------|-------------|
| `-d, --duration` | Animation duration in seconds (default: 10) |
| `-c, --color` | Text color (name, hex, or R,G,B) |
| `--no-color` | Grayscale output |

## Remote Messages (via MCP Server)

The `twinklysay` card is designed for remote messages sent via the [twinkly-mcp](https://github.com/peterbb148/twinkly-mcp) server. When a message is received:

1. The current card is interrupted
2. The message scrolls across the display once
3. The previous card resumes

This enables sending messages to the LED wall from Claude Desktop or other MCP clients.

## Development

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/
```

## Project Structure

```
twinkly-wall/
├── src/twinkly_wall/
│   ├── canvas.py       # 10×50 drawing primitives
│   ├── fonts.py        # Bitmap font rendering
│   ├── effects.py      # Scroll, fade, transitions
│   ├── cards/          # Display card implementations
│   ├── outputs/        # Terminal and Twinkly renderers
│   └── cli.py          # CLI entry point
├── config/
│   └── cards.yaml      # Card playlist configuration
└── tests/
```

## Configuration

Copy `config/settings.example.yaml` to `config/settings.yaml` and configure:

```yaml
twinkly:
  host: "192.168.50.10"

weather:
  api_key: "your-openweathermap-key"
  city_id: "2618425"  # Copenhagen
```

## License

MIT
