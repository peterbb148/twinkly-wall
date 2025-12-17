# How We Built the Twinkly Wall

## The Idea

We wanted to create a fun, interactive LED display for our office at Carlsberg Research Laboratory. The goal was a programmable "billboard" that could show animations, messages, weather, and celebrate events - all controlled remotely.

## Hardware Setup

**Components:**
- **Twinkly Matrix 500** - A consumer LED panel with 500 LEDs arranged in a 10×50 pixel grid
- **Raspberry Pi 4** - The brains running our Python software
- **Wi-Fi Access Point** - The Pi creates a dedicated network for the Twinkly

**Network Architecture:**
```
[Raspberry Pi] ─── Wi-Fi AP ───> [Twinkly Matrix 500]
      │                              10 × 50 LEDs
   Ethernet
      │
  [Office Network/Internet]
```

The Raspberry Pi connects to the office network via Ethernet (for internet access) while simultaneously hosting a Wi-Fi access point that the Twinkly connects to. This isolated network ensures reliable, low-latency communication with the LED panel.

## Software Architecture

We built a Python application (`twinkly-wall`) with these core components:

| Component | Purpose |
|-----------|---------|
| **Canvas** | 10×50 pixel drawing primitives (set_pixel, clear, copy) |
| **Fonts** | Custom 7-pixel bitmap font for text rendering |
| **Cards** | Self-contained display modules (clock, weather, animations) |
| **Scheduler** | Rotates through a playlist of cards |
| **Outputs** | Renders to terminal (preview) or Twinkly hardware |

## The Card System

Each "card" is a Python class that generates animation frames. Cards are configured via YAML:

```yaml
cards:
  - type: weather
    duration: 8

  - type: text
    text: "Merry Christmas!"
    color: [255, 0, 0]
    scroll: true

  - type: pacman
    theme: trees
```

**Available cards include:** clock, weather, text, Pac-Man animations, beer bubbles, snowfall, rainbow effects, DNA helix, Science Magazine announcements, barley field, and many more.

## Remote Control via Claude

The most innovative feature is MCP (Model Context Protocol) integration, allowing Claude Desktop to send messages to the display:

```
Claude Desktop ──► MCP Server (Render.com) ◄── Polling ── Raspberry Pi
```

When someone asks Claude to display a message, it sends the command to our MCP server, which the Raspberry Pi polls every 2 seconds. Messages appear instantly on the wall.

## Key Technical Decisions

1. **Python + UV** - Modern Python packaging with `uv` for fast, reproducible builds
2. **Frame-based rendering** - Each card yields (frame, delay) tuples for smooth animations
3. **YAML configuration** - Easy playlist editing without code changes
4. **Operating hours** - Automatic on/off scheduling (8:00-18:00 weekdays)
5. **Graceful degradation** - Cards skip gracefully if data sources (weather API) fail

## Development Workflow

```bash
# Preview in terminal
uv run twinklysay preview pacman

# Preview from playlist
uv run twinklysay preview --playlist config/online.yaml

# Run on actual hardware
twinkly-wall --playlist config/online.yaml
```

## Results

The Twinkly Wall has become a beloved feature of our office - displaying weather forecasts, countdown to Christmas, celebrating Science Magazine publications, and spreading holiday cheer with animated Pac-Man eating Christmas trees.

---

*Built at Carlsberg Research Laboratory, December 2024*
