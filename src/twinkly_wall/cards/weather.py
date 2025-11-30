"""Weather display card."""

import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..datasources.weather import WeatherData, WeatherError
from ..fonts import draw_text, text_width
from ..types import HEIGHT, RGB, WIDTH, Frame
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


@register_card
class WeatherCard(Card):
    """Display current weather information.

    Config options:
        show_condition: Show weather condition icon/animation (default: true)
        show_feels_like: Show feels-like temperature (default: false)
        color: Override text color (default: based on condition)
    """

    card_type = "weather"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.show_condition: bool = self.config.get("show_condition", True)
        self.show_feels_like: bool = self.config.get("show_feels_like", False)
        self.color: RGB | None = None
        if "color" in self.config:
            self.color = tuple(self.config["color"])  # type: ignore

    def _get_color(self, weather: WeatherData) -> RGB:
        """Get display color based on weather condition."""
        if self.color:
            return self.color
        return CONDITION_COLORS.get(weather.condition, (200, 200, 200))

    def _render_temperature(self, weather: WeatherData) -> Frame:
        """Render temperature display."""
        canvas = Canvas(WIDTH, HEIGHT)

        color = self._get_color(weather)

        # Format temperature
        temp = weather.feels_like if self.show_feels_like else weather.temperature
        temp_str = f"{temp:.0f}C"

        # Center the text
        tw = text_width(temp_str)
        x = max(0, (WIDTH - tw) // 2)
        y = 1

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

        # Build display text
        temp = weather.temperature
        condition = weather.condition.replace("_", " ").title()
        text = f"{temp:.0f}C {condition}"
        content_width = text_width(text)

        # If text fits, show static; otherwise scroll
        if content_width <= WIDTH:
            frame = self._render_temperature(weather)
            start_time = time.time()
            while time.time() - start_time < self.duration:
                yield frame, 0.5
        else:
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
