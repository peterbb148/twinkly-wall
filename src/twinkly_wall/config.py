"""Configuration loading from YAML files."""

import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .types import Orientation


@dataclass
class TwinklyConfig:
    """Twinkly device configuration."""

    host: str = ""
    port: int = 80
    mirror_h: bool = False
    mirror_v: bool = False
    orientation: Orientation = Orientation.horizontal


@dataclass
class WeatherConfig:
    """Weather configuration for Open-Meteo API."""

    latitude: float = 0.0
    longitude: float = 0.0
    cache_duration: int = 600  # 10 minutes


@dataclass
class OperatingHoursConfig:
    """Operating hours configuration.

    When enabled, the display only shows content during specified hours.
    Outside operating hours, the display is blank (or shows standby card).
    """

    enabled: bool = False
    start_hour: int = 8  # 08:00
    start_minute: int = 0
    end_hour: int = 18  # 18:00 (6 PM)
    end_minute: int = 0
    weekdays_only: bool = True  # Monday-Friday only
    timezone: str = "local"  # Use local timezone


@dataclass
class Settings:
    """Application settings loaded from settings.yaml."""

    twinkly: TwinklyConfig = field(default_factory=TwinklyConfig)
    weather: WeatherConfig = field(default_factory=WeatherConfig)
    operating_hours: OperatingHoursConfig = field(default_factory=OperatingHoursConfig)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class CardConfig:
    """Configuration for a single card in the playlist."""

    type: str
    duration: float = 10.0
    transition: str = "none"
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlaylistConfig:
    """Card playlist configuration loaded from cards.yaml."""

    cards: list[CardConfig] = field(default_factory=list)
    default_duration: float = 10.0
    default_transition: str = "none"


def _substitute_env_vars(value: str) -> str:
    """Substitute ${ENV_VAR} patterns with environment variables."""
    pattern = r"\$\{([^}]+)\}"

    def replacer(match: re.Match) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, "")

    return re.sub(pattern, replacer, value)


def _process_env_vars(obj: Any) -> Any:
    """Recursively process environment variables in config values."""
    if isinstance(obj, str):
        return _substitute_env_vars(obj)
    elif isinstance(obj, dict):
        return {k: _process_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_process_env_vars(item) for item in obj]
    return obj


def load_settings(path: Path | str | None = None) -> Settings:
    """Load settings from a YAML file.

    Args:
        path: Path to settings.yaml. If None, looks in default locations.

    Returns:
        Settings object with loaded configuration.
    """
    if path is None:
        # Try default locations
        candidates = [
            Path("config/settings.yaml"),
            Path("settings.yaml"),
            Path.home() / ".config" / "twinkly-wall" / "settings.yaml",
        ]
        for candidate in candidates:
            if candidate.exists():
                path = candidate
                break

    if path is None:
        return Settings()

    path = Path(path)
    if not path.exists():
        return Settings()

    with open(path) as f:
        data = yaml.safe_load(f) or {}

    # Process environment variables
    data = _process_env_vars(data)

    # Build settings object
    settings = Settings()

    if "twinkly" in data:
        tw = data["twinkly"]
        orientation = tw.get("orientation", Orientation.horizontal)
        try:
            orientation = Orientation(orientation)
        except ValueError as error:
            raise ValueError(f"Invalid display orientation: {orientation}") from error
        settings.twinkly = TwinklyConfig(
            host=tw.get("host", ""),
            port=tw.get("port", 80),
            mirror_h=tw.get("mirror_h", False),
            mirror_v=tw.get("mirror_v", False),
            orientation=orientation,
        )

    if "weather" in data:
        w = data["weather"]
        settings.weather = WeatherConfig(
            latitude=w.get("latitude", 0.0),
            longitude=w.get("longitude", 0.0),
            cache_duration=w.get("cache_duration", 600),
        )

    if "operating_hours" in data:
        oh = data["operating_hours"]
        settings.operating_hours = OperatingHoursConfig(
            enabled=oh.get("enabled", False),
            start_hour=oh.get("start_hour", 8),
            start_minute=oh.get("start_minute", 0),
            end_hour=oh.get("end_hour", 18),
            end_minute=oh.get("end_minute", 0),
            weekdays_only=oh.get("weekdays_only", True),
            timezone=oh.get("timezone", "local"),
        )

    # Store any extra config
    for key in data:
        if key not in ("twinkly", "weather", "operating_hours"):
            settings.extra[key] = data[key]

    return settings


def load_playlist(path: Path | str | None = None) -> PlaylistConfig:
    """Load card playlist from a YAML file.

    Args:
        path: Path to cards.yaml. If None, looks in default locations.

    Returns:
        PlaylistConfig object with loaded cards.
    """
    if path is None:
        # Try default locations
        candidates = [
            Path("config/cards.yaml"),
            Path("cards.yaml"),
            Path.home() / ".config" / "twinkly-wall" / "cards.yaml",
        ]
        for candidate in candidates:
            if candidate.exists():
                path = candidate
                break

    if path is None:
        return PlaylistConfig()

    path = Path(path)
    if not path.exists():
        return PlaylistConfig()

    with open(path) as f:
        data = yaml.safe_load(f) or {}

    # Process environment variables
    data = _process_env_vars(data)

    # Build playlist config
    playlist = PlaylistConfig(
        default_duration=data.get("default_duration", 10.0),
        default_transition=data.get("default_transition", "none"),
    )

    cards_data = data.get("cards", [])
    for card_data in cards_data:
        if isinstance(card_data, dict) and "type" in card_data:
            card_type = card_data.pop("type")
            duration = card_data.pop("duration", playlist.default_duration)
            transition = card_data.pop("transition", playlist.default_transition)

            playlist.cards.append(
                CardConfig(
                    type=card_type,
                    duration=duration,
                    transition=transition,
                    config=card_data,  # Remaining keys are card-specific config
                )
            )

    return playlist


def is_within_operating_hours(config: OperatingHoursConfig) -> bool:
    """Check if current time is within configured operating hours.

    Args:
        config: Operating hours configuration.

    Returns:
        True if operating hours are disabled OR current time is within hours.
        False if outside operating hours.
    """
    if not config.enabled:
        return True

    now = datetime.now()

    # Check weekday (Monday=0, Sunday=6)
    if config.weekdays_only and now.weekday() >= 5:  # Saturday or Sunday
        return False

    # Convert to minutes since midnight for easier comparison
    current_minutes = now.hour * 60 + now.minute
    start_minutes = config.start_hour * 60 + config.start_minute
    end_minutes = config.end_hour * 60 + config.end_minute

    if current_minutes < start_minutes or current_minutes >= end_minutes:
        return False

    return True
