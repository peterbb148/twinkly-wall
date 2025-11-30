"""Weather display card with animated icons."""

import math
import random
import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..datasources.weather import WeatherData, WeatherError
from ..fonts import draw_text, text_width
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card

# Weather condition colors
CONDITION_COLORS: dict[str, RGB] = {
    "clear": (255, 200, 50),  # Sunny yellow
    "mainly_clear": (255, 200, 100),
    "partly_cloudy": (200, 200, 200),
    "overcast": (150, 150, 150),
    "fog": (180, 180, 200),
    "drizzle": (100, 150, 255),
    "rain": (50, 100, 255),
    "rain_showers": (80, 130, 255),
    "freezing_drizzle": (150, 200, 255),
    "freezing_rain": (150, 180, 255),
    "snow": (255, 255, 255),
    "snow_grains": (240, 240, 255),
    "snow_showers": (230, 230, 255),
    "thunderstorm": (255, 100, 255),
    "unknown": (200, 200, 200),
}

# Sun sprite (7x7)
SUN_SPRITE: list[list[int]] = [
    [0, 0, 1, 1, 1, 0, 0],
    [0, 1, 1, 1, 1, 1, 0],
    [1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1],
    [0, 1, 1, 1, 1, 1, 0],
    [0, 0, 1, 1, 1, 0, 0],
]

# Cloud sprite (9x5)
CLOUD_SPRITE: list[list[int]] = [
    [0, 0, 1, 1, 1, 0, 0, 0, 0],
    [0, 1, 1, 1, 1, 1, 1, 0, 0],
    [1, 1, 1, 1, 1, 1, 1, 1, 0],
    [1, 1, 1, 1, 1, 1, 1, 1, 1],
    [0, 1, 1, 1, 1, 1, 1, 1, 0],
]

# Snowflake sprite (5x5)
SNOWFLAKE_SPRITE: list[list[int]] = [
    [0, 0, 1, 0, 0],
    [1, 0, 1, 0, 1],
    [0, 1, 1, 1, 0],
    [1, 0, 1, 0, 1],
    [0, 0, 1, 0, 0],
]


def draw_sprite(canvas: Canvas, sprite: list[list[int]], x: int, y: int, color: RGB) -> None:
    """Draw a sprite on the canvas."""
    for sy, row in enumerate(sprite):
        for sx, pixel in enumerate(row):
            if pixel:
                px, py = x + sx, y + sy
                if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                    canvas.set_pixel(px, py, color)


class WeatherIconRenderer:
    """Renders animated weather icons."""

    def __init__(self, condition: str):
        self.condition = condition
        self.raindrops: list[tuple[float, float]] = []
        self.snowflakes: list[tuple[float, float, float]] = []  # x, y, wobble
        self._init_particles()

    def _init_particles(self) -> None:
        """Initialize rain/snow particles."""
        if self.condition in ("rain", "rain_showers", "drizzle", "freezing_rain"):
            self.raindrops = [(random.uniform(0, 12), random.uniform(0, HEIGHT)) for _ in range(8)]
        elif self.condition in ("snow", "snow_showers", "snow_grains", "freezing_drizzle"):
            self.snowflakes = [
                (random.uniform(0, 12), random.uniform(0, HEIGHT), random.uniform(0, 6.28))
                for _ in range(6)
            ]

    def render(self, canvas: Canvas, x: int, y: int, frame_num: int) -> None:
        """Render the weather icon with animation."""
        if self.condition in ("clear", "mainly_clear"):
            self._draw_sun(canvas, x, y, frame_num)
        elif self.condition == "partly_cloudy":
            self._draw_sun(canvas, x + 2, y - 1, frame_num)
            self._draw_cloud(canvas, x - 1, y + 2, (200, 200, 200))
        elif self.condition in ("overcast", "fog"):
            self._draw_cloud(canvas, x, y, (150, 150, 150))
        elif self.condition in ("rain", "rain_showers", "drizzle"):
            self._draw_cloud(canvas, x, y - 1, (100, 100, 120))
            self._draw_rain(canvas, x, frame_num)
        elif self.condition in ("freezing_rain", "freezing_drizzle"):
            self._draw_cloud(canvas, x, y - 1, (150, 180, 200))
            self._draw_rain(canvas, x, frame_num, color=(150, 200, 255))
        elif self.condition in ("snow", "snow_showers", "snow_grains"):
            self._draw_cloud(canvas, x, y - 1, (180, 180, 200))
            self._draw_snow(canvas, x, frame_num)
        elif self.condition == "thunderstorm":
            self._draw_cloud(canvas, x, y - 1, (80, 80, 100))
            self._draw_lightning(canvas, x + 4, y + 4, frame_num)
            self._draw_rain(canvas, x, frame_num)
        else:
            # Unknown - just show cloud
            self._draw_cloud(canvas, x, y, (150, 150, 150))

    def _draw_sun(self, canvas: Canvas, x: int, y: int, frame_num: int) -> None:
        """Draw animated sun with pulsing rays."""
        # Pulsing brightness
        pulse = math.sin(frame_num * 0.2) * 0.15 + 0.85
        r = int(255 * pulse)
        g = int(200 * pulse)
        b = int(50 * pulse)
        draw_sprite(canvas, SUN_SPRITE, x, y, (r, g, b))

        # Animated rays (toggle on/off)
        if frame_num % 10 < 5:
            ray_color = (255, 220, 100)
            # Top ray
            if y - 1 >= 0:
                canvas.set_pixel(x + 3, y - 1, ray_color)
            # Bottom ray
            if y + 7 < HEIGHT:
                canvas.set_pixel(x + 3, y + 7, ray_color)
            # Left ray
            if x - 1 >= 0:
                canvas.set_pixel(x - 1, y + 3, ray_color)
            # Right ray
            if x + 7 < WIDTH:
                canvas.set_pixel(x + 7, y + 3, ray_color)

    def _draw_cloud(self, canvas: Canvas, x: int, y: int, color: RGB) -> None:
        """Draw a cloud."""
        draw_sprite(canvas, CLOUD_SPRITE, x, y, color)

    def _draw_rain(self, canvas: Canvas, x: int, frame_num: int, color: RGB = (100, 150, 255)) -> None:
        """Draw animated rain."""
        for i, (rx, ry) in enumerate(self.raindrops):
            # Update position
            ry += 0.8
            if ry >= HEIGHT:
                ry = 0
                rx = random.uniform(0, 10)
            self.raindrops[i] = (rx, ry)

            # Draw raindrop
            px = int(x + rx)
            py = int(ry)
            if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                canvas.set_pixel(px, py, color)
            # Streak
            if 0 <= px < WIDTH and 0 <= py - 1 < HEIGHT:
                canvas.set_pixel(px, py - 1, (color[0] // 2, color[1] // 2, color[2] // 2))

    def _draw_snow(self, canvas: Canvas, x: int, frame_num: int) -> None:
        """Draw animated snow."""
        for i, (sx, sy, wobble) in enumerate(self.snowflakes):
            # Update position with wobble
            sy += 0.3
            wobble += 0.1
            sx += math.sin(wobble) * 0.2

            if sy >= HEIGHT:
                sy = 0
                sx = random.uniform(0, 10)

            self.snowflakes[i] = (sx, sy, wobble)

            # Draw snowflake
            px = int(x + sx)
            py = int(sy)
            if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                canvas.set_pixel(px, py, (255, 255, 255))

    def _draw_lightning(self, canvas: Canvas, x: int, y: int, frame_num: int) -> None:
        """Draw lightning flash."""
        # Flash every ~30 frames
        if frame_num % 45 < 3:
            color = (255, 255, 200)
            # Simple lightning bolt
            if 0 <= x < WIDTH and 0 <= y < HEIGHT:
                canvas.set_pixel(x, y, color)
            if 0 <= x + 1 < WIDTH and 0 <= y + 1 < HEIGHT:
                canvas.set_pixel(x + 1, y + 1, color)
            if 0 <= x < WIDTH and 0 <= y + 2 < HEIGHT:
                canvas.set_pixel(x, y + 2, color)
            if 0 <= x + 1 < WIDTH and 0 <= y + 3 < HEIGHT:
                canvas.set_pixel(x + 1, y + 3, color)


@register_card
class WeatherCard(Card):
    """Display current weather information with animated icons.

    Config options:
        show_icon: Show animated weather icon (default: true)
        show_condition: Show weather condition text (default: false)
        show_feels_like: Show feels-like temperature (default: false)
        color: Override text color (default: based on condition)
    """

    card_type = "weather"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.show_icon: bool = self.config.get("show_icon", True)
        self.show_condition: bool = self.config.get("show_condition", False)
        self.show_feels_like: bool = self.config.get("show_feels_like", False)
        self.color: RGB | None = None
        if "color" in self.config:
            self.color = tuple(self.config["color"])  # type: ignore

    def _get_color(self, weather: WeatherData) -> RGB:
        """Get display color based on weather condition."""
        if self.color:
            return self.color
        return CONDITION_COLORS.get(weather.condition, (200, 200, 200))

    def _render_with_icon(
        self, weather: WeatherData, icon_renderer: WeatherIconRenderer, frame_num: int
    ) -> Frame:
        """Render weather with animated icon."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        color = self._get_color(weather)

        # Draw icon on left side
        icon_renderer.render(canvas, 1, 1, frame_num)

        # Draw temperature on right side
        temp = weather.feels_like if self.show_feels_like else weather.temperature
        temp_str = f"{temp:.0f}C"
        tw = text_width(temp_str)
        x = WIDTH - tw - 1
        y = 2

        draw_text(canvas, x, y, temp_str, color)

        return canvas.copy()

    def _render_scrolling(self, weather: WeatherData, offset: int) -> Frame:
        """Render scrolling weather info."""
        canvas = Canvas(WIDTH, HEIGHT)

        color = self._get_color(weather)

        # Build weather string
        temp = weather.temperature
        condition = weather.condition.replace("_", " ").title()
        text = f"{temp:.0f}C {condition}"

        # Scroll position
        x = WIDTH - offset
        y = 1

        draw_text(canvas, x, y, text, color)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate weather display frames."""
        # Get weather datasource from context
        weather_ds = ctx.datasources.get("weather")
        if not weather_ds:
            # No weather configured, show error
            canvas = Canvas(WIDTH, HEIGHT)
            draw_text(canvas, 0, 1, "NO WX", (255, 0, 0))
            frame = canvas.copy()
            start_time = time.time()
            while time.time() - start_time < self.duration:
                yield frame, 1.0
            return

        # Fetch weather data
        try:
            weather = weather_ds.get_weather()
        except WeatherError:
            canvas = Canvas(WIDTH, HEIGHT)
            draw_text(canvas, 0, 1, "ERR", (255, 0, 0))
            frame = canvas.copy()
            start_time = time.time()
            while time.time() - start_time < self.duration:
                yield frame, 1.0
            return

        if self.show_icon and not self.show_condition:
            # Show animated icon with temperature
            icon_renderer = WeatherIconRenderer(weather.condition)
            start_time = time.time()
            frame_num = 0
            frame_delay = 1.0 / 15.0  # 15 FPS for smooth animation

            while time.time() - start_time < self.duration:
                frame = self._render_with_icon(weather, icon_renderer, frame_num)
                yield frame, frame_delay
                frame_num += 1
        else:
            # Build display text
            temp = weather.temperature
            condition = weather.condition.replace("_", " ").title()
            text = f"{temp:.0f}C {condition}"
            content_width = text_width(text)

            # Scrolling display
            total_scroll = content_width + WIDTH
            pixels_per_frame = 30.0 / 30.0  # 30 pixels/sec at 30 FPS
            frame_delay = 1.0 / 30.0

            start_time = time.time()
            offset = 0.0
            scroll_completed = False

            while True:
                frame = self._render_scrolling(weather, int(offset))
                yield frame, frame_delay

                offset += pixels_per_frame

                if offset >= total_scroll:
                    scroll_completed = True
                    offset = 0.0

                elapsed = time.time() - start_time
                if scroll_completed and elapsed >= self.duration:
                    break
