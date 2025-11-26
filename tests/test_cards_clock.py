"""Tests for the clock card."""

from datetime import datetime
from unittest.mock import patch

from twinkly_wall.cards.base import CardContext, create_card, get_card_class
from twinkly_wall.cards.clock import ClockCard
from twinkly_wall.types import BLACK, WHITE


class TestClockCard:
    """Tests for ClockCard."""

    def test_registered(self):
        """ClockCard should be registered."""
        assert get_card_class("clock") is ClockCard

    def test_create_via_registry(self):
        """Should create ClockCard via registry."""
        card = create_card("clock")
        assert card is not None
        assert isinstance(card, ClockCard)

    def test_default_config(self):
        """Should have sensible defaults."""
        card = ClockCard()
        assert card.color == WHITE
        assert card.format_24h is True
        assert card.show_seconds is False
        assert card.blink_colon is True

    def test_custom_config(self):
        """Should accept custom config."""
        card = ClockCard(
            {
                "color": [255, 0, 0],
                "format_24h": False,
                "show_seconds": True,
                "blink_colon": False,
            }
        )
        assert card.color == (255, 0, 0)
        assert card.format_24h is False
        assert card.show_seconds is True
        assert card.blink_colon is False

    def test_format_time_24h(self):
        """Should format time in 24h format."""
        card = ClockCard({"format_24h": True})
        dt = datetime(2024, 12, 25, 14, 30, 45)
        assert card._format_time(dt) == "14:30"

    def test_format_time_12h(self):
        """Should format time in 12h format."""
        card = ClockCard({"format_24h": False})

        # Afternoon
        dt = datetime(2024, 12, 25, 14, 30, 45)
        assert card._format_time(dt) == " 2:30"

        # Midnight
        dt = datetime(2024, 12, 25, 0, 5, 0)
        assert card._format_time(dt) == "12:05"

        # Noon
        dt = datetime(2024, 12, 25, 12, 0, 0)
        assert card._format_time(dt) == "12:00"

    def test_format_time_with_seconds(self):
        """Should include seconds when configured."""
        card = ClockCard({"show_seconds": True})
        dt = datetime(2024, 12, 25, 14, 30, 45)
        assert card._format_time(dt) == "14:30:45"

    def test_format_time_hidden_colon(self):
        """Should hide colon when show_colon=False."""
        card = ClockCard()
        dt = datetime(2024, 12, 25, 14, 30, 45)
        assert card._format_time(dt, show_colon=False) == "14 30"

    def test_render_time_creates_frame(self):
        """Should render time to a frame."""
        card = ClockCard()
        frame = card._render_time("12:34")

        # Should be full display size
        assert len(frame) == 10
        assert len(frame[0]) == 50

        # Should have some non-black pixels (the time text)
        has_content = any(
            frame[y][x] != BLACK for y in range(len(frame)) for x in range(len(frame[0]))
        )
        assert has_content

    def test_frames_generator(self):
        """Should generate frames."""
        card = ClockCard({"duration": 0.5})
        ctx = CardContext()

        frames = list(card.frames(ctx))

        # Should have generated some frames
        assert len(frames) > 0

        # Each frame should be a tuple of (Frame, delay)
        for frame, delay in frames:
            assert len(frame) == 10
            assert len(frame[0]) == 50
            assert delay == 0.1

    @patch("twinkly_wall.cards.clock.datetime")
    def test_frames_uses_current_time(self, mock_datetime):
        """Should use current time for display."""
        mock_now = datetime(2024, 12, 25, 9, 15, 0, 0)
        mock_datetime.now.return_value = mock_now

        card = ClockCard({"duration": 0.15, "blink_colon": False})
        ctx = CardContext()

        # Get first frame
        frame, _ = next(card.frames(ctx))

        # The time "9:15" should be rendered
        # We can't easily check the exact pixels, but we can verify the frame exists
        assert frame is not None
        assert len(frame) == 10
