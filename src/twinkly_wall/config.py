"""Configuration loading from YAML files."""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class TwinklyConfig:
    """Twinkly device configuration."""

    host: str = ""
    port: int = 80
    mirror_h: bool = False
    mirror_v: bool = False


@dataclass
class WeatherConfig:
    """Weather configuration for Open-Meteo API."""

    latitude: float = 0.0
    longitude: float = 0.0
    cache_duration: int = 600  # 10 minutes


@dataclass
class Settings:
    """Application settings loaded from settings.yaml."""

    twinkly: TwinklyConfig = field(default_factory=TwinklyConfig)
    weather: WeatherConfig = field(default_factory=WeatherConfig)
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
        settings.twinkly = TwinklyConfig(
            host=tw.get("host", ""),
            port=tw.get("port", 80),
            mirror_h=tw.get("mirror_h", False),
            mirror_v=tw.get("mirror_v", False),
        )

    if "weather" in data:
        w = data["weather"]
        settings.weather = WeatherConfig(
            latitude=w.get("latitude", 0.0),
            longitude=w.get("longitude", 0.0),
            cache_duration=w.get("cache_duration", 600),
        )

    # Store any extra config
    for key in data:
        if key not in ("twinkly", "weather"):
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
