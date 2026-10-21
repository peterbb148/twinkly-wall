"""Weather datasource using Open-Meteo API."""

import logging
import time
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)

# WMO Weather interpretation codes
# https://open-meteo.com/en/docs
WMO_CODES = {
    0: "clear",
    1: "mainly_clear",
    2: "partly_cloudy",
    3: "overcast",
    45: "fog",
    48: "fog",
    51: "drizzle",
    53: "drizzle",
    55: "drizzle",
    56: "freezing_drizzle",
    57: "freezing_drizzle",
    61: "rain",
    63: "rain",
    65: "rain",
    66: "freezing_rain",
    67: "freezing_rain",
    71: "snow",
    73: "snow",
    75: "snow",
    77: "snow_grains",
    80: "rain_showers",
    81: "rain_showers",
    82: "rain_showers",
    85: "snow_showers",
    86: "snow_showers",
    95: "thunderstorm",
    96: "thunderstorm",
    99: "thunderstorm",
}


@dataclass
class WeatherData:
    """Current weather data."""

    temperature: float  # Celsius
    feels_like: float  # Celsius
    humidity: int  # Percentage
    wind_speed: float  # km/h
    weather_code: int  # WMO code
    condition: str  # Human-readable condition
    is_day: bool
    timestamp: float  # Unix timestamp when fetched


class WeatherError(Exception):
    """Error fetching weather data."""

    pass


class WeatherDataSource:
    """Fetch weather data from Open-Meteo API.

    Open-Meteo is free and doesn't require an API key.
    """

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(
        self,
        latitude: float,
        longitude: float,
        cache_duration: int = 600,  # 10 minutes
        timeout: float = 10.0,
    ):
        """Initialize weather datasource.

        Args:
            latitude: Location latitude
            longitude: Location longitude
            cache_duration: How long to cache results in seconds
            timeout: Request timeout in seconds
        """
        self.latitude = latitude
        self.longitude = longitude
        self.cache_duration = cache_duration
        self.timeout = timeout
        self._cache: WeatherData | None = None
        self._cache_time: float = 0

    def _fetch(self) -> WeatherData:
        """Fetch current weather from API."""
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "current": [
                "temperature_2m",
                "apparent_temperature",
                "relative_humidity_2m",
                "wind_speed_10m",
                "weather_code",
                "is_day",
            ],
            "timezone": "auto",
        }

        try:
            response = requests.get(
                self.BASE_URL,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            raise WeatherError(f"Failed to fetch weather: {e}") from e

        current = data.get("current", {})

        weather_code = current.get("weather_code", 0)
        condition = WMO_CODES.get(weather_code, "unknown")

        return WeatherData(
            temperature=current.get("temperature_2m", 0),
            feels_like=current.get("apparent_temperature", 0),
            humidity=current.get("relative_humidity_2m", 0),
            wind_speed=current.get("wind_speed_10m", 0),
            weather_code=weather_code,
            condition=condition,
            is_day=bool(current.get("is_day", 1)),
            timestamp=time.time(),
        )

    def get_weather(self) -> WeatherData:
        """Get current weather, using cache if available.

        Returns:
            WeatherData object with current conditions
        """
        now = time.time()

        # Return cached data if still valid
        if self._cache and (now - self._cache_time) < self.cache_duration:
            return self._cache

        # Fetch fresh data
        try:
            self._cache = self._fetch()
            self._cache_time = now
            logger.info(f"Weather updated: {self._cache.temperature}°C, {self._cache.condition}")
        except WeatherError as e:
            logger.warning(f"Weather fetch failed: {e}")
            # Return stale cache if available
            if self._cache:
                return self._cache
            raise

        return self._cache

    def get_temperature(self) -> float:
        """Get current temperature in Celsius."""
        return self.get_weather().temperature

    def get_condition(self) -> str:
        """Get current weather condition string."""
        return self.get_weather().condition

    def is_snowing(self) -> bool:
        """Check if it's currently snowing."""
        condition = self.get_condition()
        return condition in ("snow", "snow_grains", "snow_showers")

    def is_raining(self) -> bool:
        """Check if it's currently raining."""
        condition = self.get_condition()
        return condition in (
            "drizzle",
            "rain",
            "rain_showers",
            "freezing_rain",
            "freezing_drizzle",
        )
