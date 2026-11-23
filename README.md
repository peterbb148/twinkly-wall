# Twinkly Wall

A Raspberry Pi-controlled LED billboard using Twinkly Matrix 500 (10×50 pixel display) for office Christmas fun.

## Features

- **Wall Daemon** (`twinkly-cli wall`) - Run the configured playlist on the LED wall
- **On-demand CLI** (`twinkly-cli say`) - Send a card to the wall or preview it in your terminal
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

Twinkly CLI release targets include **64-bit Raspberry Pi OS (Trixie)**,
**Ubuntu ARM64**, and **macOS Apple Silicon**. See [CLI installation and
releases](docs/CLI.md) for installers, supported versions, and setup.

```bash
# Install with UV
uv sync --locked --no-dev

# Run the CLI
uv run --locked --no-dev twinkly-cli --help
```

## CLI Usage (`twinkly-cli say`)

Use `twinkly-cli say` to list or preview cards, or send a card directly to the wall.

- List registered cards (and optionally the playlist with ids):

```bash
uv run twinkly-cli say list --playlist config/cards.yaml
```

### Display Text (`text`)

Render a static text message in your terminal:

```bash
# Basic text (white)
uv run twinkly-cli say text "Hello World"

# Colored text (by name)
uv run twinkly-cli say text "Merry Christmas" --color red

# Colored text (hex)
uv run twinkly-cli say text "Happy New Year" --color "#FFD700"

# Colored text (RGB)
uv run twinkly-cli say text "Cheers!" --color 255,165,0
```

**Supported color names:** black, white, red, green, blue, yellow, cyan, magenta, orange, gold

### Preview Animations (`preview`)

Preview card animations in your terminal:

```bash
# Clock (24-hour format, blinking colon)
uv run twinkly-cli say preview clock

# Clock (12-hour format)
uv run twinkly-cli say preview clock --twelve-hour

# Scrolling text
uv run twinkly-cli say preview text --text "Hello from the Twinkly Wall!"

# Pac-Man eating Christmas trees
uv run twinkly-cli say preview pacman --theme trees

# Pac-Man eating beer mugs
uv run twinkly-cli say preview pacman --theme beer

# Snowfall
uv run twinkly-cli say preview snow

# Snowfall with wind and accumulation
uv run twinkly-cli say preview snow --wind 0.5 --accumulate

# Beer bubbles
uv run twinkly-cli say preview beer

# Rainbow effects
uv run twinkly-cli say preview rainbow --mode plasma

# Vertical-friendly cards
uv run twinkly-cli say preview rain
uv run twinkly-cli say preview vertical_bars
uv run twinkly-cli say preview stories --duration 8
uv run twinkly-cli say preview score_tower --playlist config/leaderboard.yaml

# Twinklysay (scrolling message, used for remote messages)
uv run twinkly-cli say preview twinklysay --text "Remote message!" --color gold

# Send a card to the LED device (one-shot)
uv run twinkly-cli say card twinklysay --text "Hello LED!" --color gold

# Send a playlist card by id (uses cards.yaml)
uv run twinkly-cli say card --id 3 --playlist config/cards.yaml
```

**Available cards:** clock, text, pacman, beer, beer_vertical, snow, rainbow, test_pattern, carlsberg_lab, candle_vertical, twinklysay, rain, vertical_bars, stories, score_tower

### Common Options

| Option | Description |
|--------|-------------|
| `-d, --duration` | Animation duration in seconds (default: 10) |
| `-c, --color` | Text color (name, hex, or R,G,B) |
| `--no-color` | Grayscale output |
| `--orientation` | Preview orientation: horizontal, vertical_left, vertical_right (matches `twinkly.orientation`) |

Configure the physical mount and mirror axes in settings. See [display orientation and mirroring](docs/CLI.md#display-orientation-and-mirroring).

## Remote Control (MCP Integration)

The daemon supports remote control via the [twinkly-mcp](https://github.com/peterbb148/twinkly-mcp) server. When enabled, Claude Desktop can send commands to display messages or run cards on the LED wall.

### Architecture

```
┌─────────────────┐     MCP Protocol      ┌──────────────────┐
│  Claude Desktop │ ◄──────────────────► │  Twinkly MCP     │
│  (MCP Client)   │                       │  Server (Render) │
└─────────────────┘                       └────────┬─────────┘
                                                   │
                                          HTTP Polling
                                                   │
                                                   ▼
                                          ┌──────────────────┐
                                          │  Raspberry Pi    │
                                          │  (twinkly-cli wall)   │
                                          └──────────────────┘
```

### Running with MCP

```bash
# Run daemon with MCP enabled (on Raspberry Pi)
twinkly-cli wall --mcp

# Run in terminal mode for testing (no LED hardware)
twinkly-cli wall -t --mcp

# Custom MCP server
twinkly-cli wall --mcp --mcp-server https://your-server.com

# With API key authentication
twinkly-cli wall --mcp --mcp-api-key YOUR_KEY
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `TWINKLY_MCP_URL` | MCP server URL (default: https://twinkly-mcp.onrender.com) |
| `TWINKLY_API_KEY` | API key for MCP server authentication |

### How It Works

1. The daemon polls the MCP server every 2 seconds
2. When a command arrives (e.g., `twinklysay` or `run_card`):
   - Current card is interrupted
   - MCP command is executed immediately
   - Playlist resumes from the next card
3. Available cards are registered with the server on startup

### Standalone MCP Client

For testing without the full daemon:

```bash
# Start MCP polling client (terminal output only)
uv run twinkly-cli say mcp

# Custom poll interval
uv run twinkly-cli say mcp -i 5
```

## Development

CI uses Python 3.11 and uv 0.12.5. Use that uv version to reproduce these checks.

```bash
# Install dev dependencies
uv sync --locked --python 3.11

# Run tests
uv run --locked pytest

# Check lint and formatting
uv run --locked ruff check src/ tests/
uv run --locked ruff format --check src/ tests/

# Audit the committed lockfile as CI does
uv audit --locked --python-version 3.11
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
│   ├── cli.py          # On-demand commands (twinkly-cli say)
│   ├── daemon.py       # Main daemon (twinkly-cli wall)
│   ├── scheduler.py    # Card playlist scheduler
│   └── mcp_client.py   # MCP server polling client
├── config/
│   ├── cards.yaml      # Card playlist configuration
│   └── settings.yaml   # Device and API settings
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
