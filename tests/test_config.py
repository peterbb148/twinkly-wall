"""Tests for configuration loading."""

import os
import tempfile

from twinkly_wall.config import (
    CardConfig,
    PlaylistConfig,
    Settings,
    TwinklyConfig,
    WeatherConfig,
    load_playlist,
    load_settings,
)


class TestSettings:
    """Tests for Settings dataclass."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()
        assert settings.twinkly.host == ""
        assert settings.twinkly.port == 80
        assert settings.weather.api_key == ""
        assert settings.extra == {}

    def test_custom_settings(self):
        """Test settings with custom values."""
        settings = Settings(
            twinkly=TwinklyConfig(host="192.168.1.100", port=8080),
            weather=WeatherConfig(api_key="test", city_id="123"),
        )
        assert settings.twinkly.host == "192.168.1.100"
        assert settings.twinkly.port == 8080
        assert settings.weather.api_key == "test"


class TestLoadSettings:
    """Tests for load_settings function."""

    def test_load_settings_no_file_returns_defaults(self):
        """Test loading settings when no file exists."""
        settings = load_settings("/nonexistent/path.yaml")
        assert isinstance(settings, Settings)
        assert settings.twinkly.host == ""

    def test_load_settings_none_path_returns_defaults(self):
        """Test loading settings with None path returns defaults."""
        settings = load_settings(None)
        assert isinstance(settings, Settings)

    def test_load_settings_from_file(self):
        """Test loading settings from a YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
twinkly:
  host: "192.168.1.50"
  port: 8080
weather:
  api_key: "my-api-key"
  city_id: "2618425"
  units: "imperial"
""")
            f.flush()

            try:
                settings = load_settings(f.name)
                assert settings.twinkly.host == "192.168.1.50"
                assert settings.twinkly.port == 8080
                assert settings.weather.api_key == "my-api-key"
                assert settings.weather.city_id == "2618425"
                assert settings.weather.units == "imperial"
            finally:
                os.unlink(f.name)

    def test_load_settings_env_var_substitution(self):
        """Test environment variable substitution in settings."""
        os.environ["TEST_API_KEY"] = "secret-key-123"
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                f.write("""
weather:
  api_key: "${TEST_API_KEY}"
""")
                f.flush()

                try:
                    settings = load_settings(f.name)
                    assert settings.weather.api_key == "secret-key-123"
                finally:
                    os.unlink(f.name)
        finally:
            del os.environ["TEST_API_KEY"]

    def test_load_settings_extra_keys(self):
        """Test that extra keys are stored in extra dict."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
custom_setting: "value"
another_key:
  nested: true
""")
            f.flush()

            try:
                settings = load_settings(f.name)
                assert settings.extra["custom_setting"] == "value"
                assert settings.extra["another_key"]["nested"] is True
            finally:
                os.unlink(f.name)


class TestPlaylistConfig:
    """Tests for PlaylistConfig dataclass."""

    def test_default_playlist(self):
        """Test default playlist values."""
        playlist = PlaylistConfig()
        assert playlist.cards == []
        assert playlist.default_duration == 10.0
        assert playlist.default_transition == "none"

    def test_playlist_with_cards(self):
        """Test playlist with card configs."""
        cards = [
            CardConfig(type="clock", duration=5.0),
            CardConfig(type="text", config={"text": "Hello"}),
        ]
        playlist = PlaylistConfig(cards=cards)
        assert len(playlist.cards) == 2
        assert playlist.cards[0].type == "clock"
        assert playlist.cards[1].config["text"] == "Hello"


class TestLoadPlaylist:
    """Tests for load_playlist function."""

    def test_load_playlist_no_file_returns_empty(self):
        """Test loading playlist when no file exists."""
        playlist = load_playlist("/nonexistent/path.yaml")
        assert isinstance(playlist, PlaylistConfig)
        assert playlist.cards == []

    def test_load_playlist_from_file(self):
        """Test loading playlist from a YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
default_duration: 15
default_transition: crossfade

cards:
  - type: clock
    duration: 10
    color: [255, 0, 0]

  - type: text
    text: "Hello World"
    duration: 5
    transition: none
""")
            f.flush()

            try:
                playlist = load_playlist(f.name)
                assert playlist.default_duration == 15
                assert playlist.default_transition == "crossfade"
                assert len(playlist.cards) == 2

                clock_card = playlist.cards[0]
                assert clock_card.type == "clock"
                assert clock_card.duration == 10
                assert clock_card.config["color"] == [255, 0, 0]

                text_card = playlist.cards[1]
                assert text_card.type == "text"
                assert text_card.duration == 5
                assert text_card.transition == "none"
                assert text_card.config["text"] == "Hello World"
            finally:
                os.unlink(f.name)

    def test_load_playlist_uses_defaults(self):
        """Test that cards use default duration/transition when not specified."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
default_duration: 20
default_transition: crossfade

cards:
  - type: clock
""")
            f.flush()

            try:
                playlist = load_playlist(f.name)
                assert len(playlist.cards) == 1
                assert playlist.cards[0].duration == 20
                assert playlist.cards[0].transition == "crossfade"
            finally:
                os.unlink(f.name)

    def test_load_playlist_skips_invalid_cards(self):
        """Test that cards without type are skipped."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("""
cards:
  - type: clock
  - duration: 10
  - type: text
    text: "valid"
""")
            f.flush()

            try:
                playlist = load_playlist(f.name)
                # Only 2 valid cards (clock and text)
                assert len(playlist.cards) == 2
                assert playlist.cards[0].type == "clock"
                assert playlist.cards[1].type == "text"
            finally:
                os.unlink(f.name)
