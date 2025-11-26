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

# Preview text in terminal
twinklysay "Hello World"

# Preview with color
twinklysay "Merry Christmas" --color 255,0,0

# Preview animation
twinklysay --animation snow
```

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
