"""Tests for the card scheduler."""

import pytest

from twinkly_wall.cards import CardContext
from twinkly_wall.config import CardConfig, PlaylistConfig
from twinkly_wall.scheduler import Scheduler, SchedulerState
from twinkly_wall.types import Frame


class MockOutput:
    """Mock output for testing."""

    def __init__(self):
        self.frames: list[Frame] = []

    def send_frame(self, frame: Frame) -> None:
        self.frames.append(frame)


class TestSchedulerState:
    """Tests for SchedulerState dataclass."""

    def test_default_state(self):
        """Test default scheduler state."""
        state = SchedulerState()
        assert state.current_card_index == 0
        assert state.cards_played == 0
        assert state.last_frame is None
        assert state.running is False


class TestScheduler:
    """Tests for the Scheduler class."""

    def test_scheduler_init(self):
        """Test scheduler initialization."""
        playlist = PlaylistConfig(cards=[CardConfig(type="clock")])
        scheduler = Scheduler(playlist)

        assert scheduler.playlist == playlist
        assert isinstance(scheduler.context, CardContext)
        assert scheduler.outputs == []
        assert scheduler.state.running is False

    def test_scheduler_with_outputs(self):
        """Test scheduler with output targets."""
        playlist = PlaylistConfig(cards=[CardConfig(type="clock")])
        output = MockOutput()
        scheduler = Scheduler(playlist, outputs=[output])

        assert len(scheduler.outputs) == 1

    def test_scheduler_empty_playlist(self):
        """Test scheduler with empty playlist doesn't crash."""
        playlist = PlaylistConfig()
        scheduler = Scheduler(playlist)

        # Should just return without error
        scheduler.run_once()
        assert scheduler.state.cards_played == 0

    def test_scheduler_frames_generator(self):
        """Test scheduler frames generator produces frames."""
        playlist = PlaylistConfig(
            cards=[CardConfig(type="clock", duration=0.1)]
        )
        scheduler = Scheduler(playlist)

        # Get some frames
        frames = list(scheduler.frames())
        assert len(frames) > 0

        # Each frame should be a tuple of (Frame, float)
        for frame, delay in frames:
            assert isinstance(frame, list)
            assert isinstance(delay, float)
            assert delay >= 0

    def test_scheduler_unknown_card_type_skipped(self):
        """Test that unknown card types are skipped."""
        playlist = PlaylistConfig(
            cards=[
                CardConfig(type="unknown_type"),
                CardConfig(type="clock", duration=0.1),
            ]
        )
        scheduler = Scheduler(playlist)

        # Should still produce frames from the clock card
        frames = list(scheduler.frames())
        assert len(frames) > 0

    def test_scheduler_stop(self):
        """Test scheduler stop method."""
        playlist = PlaylistConfig()
        scheduler = Scheduler(playlist)
        scheduler.state.running = True

        scheduler.stop()
        assert scheduler.state.running is False

    def test_scheduler_sends_to_outputs(self):
        """Test that scheduler sends frames to outputs."""
        playlist = PlaylistConfig(
            cards=[CardConfig(type="clock", duration=0.1)]
        )
        output = MockOutput()
        scheduler = Scheduler(playlist, outputs=[output])

        # Run once with a very short duration
        scheduler.run_once()

        # Should have sent frames to the output
        assert len(output.frames) > 0

    def test_scheduler_with_transition(self):
        """Test scheduler with crossfade transition."""
        playlist = PlaylistConfig(
            default_transition="crossfade",
            cards=[
                CardConfig(type="clock", duration=0.1),
                CardConfig(type="clock", duration=0.1),
            ],
        )
        scheduler = Scheduler(playlist)

        frames = list(scheduler.frames())
        # Should have transition frames between cards
        assert len(frames) > 0

    def test_scheduler_multiple_cards(self):
        """Test scheduler plays multiple cards in sequence."""
        playlist = PlaylistConfig(
            cards=[
                CardConfig(type="clock", duration=0.1),
                CardConfig(type="text", duration=0.1, config={"text": "Hi"}),
            ]
        )
        scheduler = Scheduler(playlist)

        # Run once through the playlist
        scheduler.run_once()
        assert scheduler.state.cards_played == 2
