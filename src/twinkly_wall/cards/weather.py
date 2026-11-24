"""Weather display card - scrolling forecast text."""

import logging
import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..datasources.weather import WeatherData, WeatherError
from ..fonts import (
    CHAR_WIDTH,
    draw_text,
    draw_text_vertical_stacked,
    text_width,
    vertical_text_height,
)
from ..types import BLACK, HEIGHT, PORTRAIT_HEIGHT, PORTRAIT_WIDTH, RGB, WIDTH, Frame
from .base import Card, CardContext, CardLayout, register_card

logger = logging.getLogger(__name__)

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
    """Display current weather as scrolling text.

    Config options:
        show_feels_like: Show feels-like temperature instead of actual (default: false)
        color: Override text color (default: based on condition)
        scroll_speed: Scroll speed in pixels per second (default: 30)
    """

    card_type = "weather"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.show_feels_like: bool = self.config.get("show_feels_like", False)
        self.scroll_speed: float = self.config.get("scroll_speed", 30.0)
        self.color: RGB | None = None
        if "color" in self.config:
            self.color = tuple(self.config["color"])  # type: ignore

    def _get_color(self, weather: WeatherData) -> RGB:
        """Get display color based on weather condition."""
        if self.color:
            return self.color
        return CONDITION_COLORS.get(weather.condition, (200, 200, 200))

    def _render_frame(self, text: str, color: RGB, offset: int) -> Frame:
        """Render a frame of scrolling weather text."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        x = WIDTH - offset
        y = 1  # Vertically centered

        draw_text(canvas, x, y, text, color)
        return canvas.copy()

    def _scroll_length(self, text: str) -> int:
        return text_width(text) + WIDTH + 1

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate scrolling weather text frames."""
        # Get weather datasource from context
        weather_ds = ctx.datasources.get("weather")
        if not weather_ds:
            logger.warning("Weather card skipped: no weather datasource configured")
            return

        # Fetch weather data
        try:
            weather = weather_ds.get_weather()
        except WeatherError as e:
            logger.warning(f"Weather card skipped: {e}")
            return

        # Build weather text
        temp = weather.feels_like if self.show_feels_like else weather.temperature
        condition = weather.condition.replace("_", " ").title()
        text = f"{temp:.0f}C {condition}"

        color = self._get_color(weather)
        total_scroll = self._scroll_length(text)

        # Animation
        frame_delay = 1.0 / 30.0
        pixels_per_frame = self.scroll_speed / 30.0

        start_time = time.time()
        offset = 0.0
        scroll_completed = False

        while True:
            frame = self._render_frame(text, color, int(offset))
            yield frame, frame_delay

            offset += pixels_per_frame

            if offset >= total_scroll:
                scroll_completed = True
                offset = 0.0

            elapsed = time.time() - start_time
            if scroll_completed and elapsed >= self.duration:
                break


@register_card
class WeatherVerticalCard(WeatherCard):
    """Scroll the current temperature and condition in upright portrait text."""

    card_type = "weather_vertical"
    layout = CardLayout.portrait

    def _render_frame(self, text: str, color: RGB, offset: int) -> Frame:
        canvas = Canvas(PORTRAIT_WIDTH, PORTRAIT_HEIGHT)
        x = (canvas.width - CHAR_WIDTH) // 2
        draw_text_vertical_stacked(canvas, x, canvas.height - offset, text, color)
        return canvas.copy()

    def _scroll_length(self, text: str) -> int:
        return vertical_text_height(text) + PORTRAIT_HEIGHT + 1
