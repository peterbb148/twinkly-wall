"""Tests for the card scheduler."""

from datetime import datetime
from unittest.mock import Mock, call

import pytest

from twinkly_wall import scheduler as scheduler_module
from twinkly_wall.cards import CardContext
from twinkly_wall.config import CardConfig, OperatingHoursConfig, PlaylistConfig
from twinkly_wall.mcp_client import MCPClient
from twinkly_wall.scheduler import Scheduler, SchedulerState
from twinkly_wall.types import BLACK, HEIGHT, WHITE, WIDTH, Frame


class MockOutput:
    """Mock output for testing."""

    def __init__(self):
        self.frames: list[Frame] = []

    def send_frame(self, frame: Frame) -> None:
        self.frames.append(frame)


def test_mcp_only_loop_waits_for_hours_and_plays_remote_frames(monkeypatch):
    output = Mock()
    frame_only_output = MockOutput()
    client = MCPClient()
    poll = Mock(side_effect=[[], [{"type": "twinklysay", "payload": {"text": "Hi"}}]])
    monkeypatch.setattr(client, "poll_commands", poll)
    scheduler = Scheduler(PlaylistConfig(), outputs=[output, frame_only_output], mcp_client=client)
    clock = Mock()
    clock.time.side_effect = [100.0, 102.0]
    monkeypatch.setattr(scheduler_module, "is_within_operating_hours", lambda _: clock.sleep.called)

    def sleep(delay):
        if delay == 2.0 and poll.call_count == 2:
            scheduler.stop()

    clock.sleep.side_effect = sleep
    monkeypatch.setattr(scheduler_module, "time", clock)

    scheduler.run_loop()

    assert poll.call_count == 2
    assert clock.sleep.call_args_list[:2] == [call(60), call(2.0)]
    assert scheduler.state.cards_played == 0
    assert scheduler.state.last_frame is None
    methods = [event[0] for event in output.method_calls]
    assert methods[:2] == ["turn_off", "turn_on"]
    assert methods[2:-1] == ["send_frame"] * output.send_frame.call_count
    assert output.send_frame.call_count > 0
    assert methods[-1] == "turn_off"
    assert len(frame_only_output.frames) == output.send_frame.call_count


def test_unlisted_lunch_playlist_polls_remote_commands_and_waits(monkeypatch):
    card = CardConfig(type="lunch_horizontal", config={"menu": {"2026-11-30": "Curry"}})
    output = MockOutput()
    client = MCPClient()
    remote_frame = [[WHITE] * WIDTH for _ in range(HEIGHT)]
    remote_card = Mock()
    remote_card.frames.return_value = iter([(remote_frame, 0)])
    poll = Mock(return_value=[{"type": "run_card"}])
    monkeypatch.setattr(client, "poll_commands", poll)
    monkeypatch.setattr(client, "create_card_from_command", Mock(return_value=remote_card))
    scheduler = Scheduler(PlaylistConfig(cards=[card]), outputs=[output], mcp_client=client)

    lunch_clock = Mock()
    lunch_clock.now.return_value = datetime(2026, 11, 29, 12)
    monkeypatch.setattr("twinkly_wall.cards.lunch_horizontal.datetime", lunch_clock)
    clock = Mock()
    clock.time.return_value = 100.0
    clock.sleep.side_effect = lambda delay: scheduler.stop() if delay == 2.0 else None
    monkeypatch.setattr(scheduler_module, "time", clock)

    scheduler.run_loop()

    poll.assert_called_once()
    assert output.frames == [remote_frame]
    assert clock.sleep.call_args_list == [call(0.03), call(2.0)]


def test_mcp_only_loop_stays_off_when_stopped_during_poll(monkeypatch):
    output = Mock()
    client = MCPClient()
    scheduler = Scheduler(PlaylistConfig(), outputs=[output], mcp_client=client)

    def poll():
        scheduler.stop()
        return [{"type": "twinklysay", "payload": {"text": "Hi"}}]

    monkeypatch.setattr(client, "poll_commands", poll)
    clock = Mock()
    clock.time.return_value = 100.0
    monkeypatch.setattr(scheduler_module, "time", clock)
    scheduler.run_loop()

    assert output.method_calls == []
    clock.sleep.assert_not_called()


@pytest.mark.parametrize("closes_during", ["poll", "first_card"])
def test_mcp_only_loop_discards_commands_at_closing(monkeypatch, closes_during):
    output = Mock()
    client = MCPClient()
    scheduler = Scheduler(PlaylistConfig(), outputs=[output], mcp_client=client)
    during_hours = True
    played_text = []

    def poll():
        nonlocal during_hours
        during_hours = closes_during != "poll"
        return [
            {"type": "twinklysay", "payload": {"text": "First"}},
            {"type": "twinklysay", "payload": {"text": "Second"}},
        ]

    def play(card):
        nonlocal during_hours
        played_text.append(card.text)
        during_hours = False

    def sleep(delay):
        if delay == 60:
            scheduler.stop()

    clock = Mock()
    clock.time.return_value = 100.0
    clock.sleep.side_effect = sleep
    monkeypatch.setattr(client, "poll_commands", poll)
    monkeypatch.setattr(scheduler, "_play_card_instance", play)
    monkeypatch.setattr(scheduler_module, "is_within_operating_hours", lambda _: during_hours)
    monkeypatch.setattr(scheduler_module, "time", clock)

    scheduler.run_loop()

    assert not client.has_pending_commands()
    if closes_during == "poll":
        assert played_text == []
        assert output.method_calls == [call.turn_off()]
        clock.sleep.assert_called_once_with(60)
    else:
        assert played_text == ["First"]
        assert output.method_calls[:2] == [call.turn_on(), call.turn_off()]


@pytest.mark.parametrize(
    ("closes_during", "playback_sleeps", "sent_frames"),
    [("frame", [], 0), ("transition", [0.03], 1), ("hold", [0.03, 0.25, 0.25], 1)],
)
def test_mcp_only_interrupts_active_card_at_closing(
    monkeypatch, closes_during, playback_sleeps, sent_frames
):
    output = Mock()
    client = MCPClient()
    scheduler = Scheduler(
        PlaylistConfig(),
        outputs=[output],
        mcp_client=client,
        operating_hours=OperatingHoursConfig(enabled=True),
    )
    if closes_during == "transition":
        scheduler.state.last_frame = [[BLACK] * WIDTH for _ in range(HEIGHT)]
    during_hours = True
    frame = [[WHITE] * WIDTH for _ in range(HEIGHT)]

    def frames(_):
        nonlocal during_hours
        if closes_during == "frame":
            during_hours = False
        yield frame, 10.0
        pytest.fail("The card generated another frame after closing")

    card = Mock()
    card.frames.side_effect = frames
    monkeypatch.setattr(client, "create_card_from_command", Mock(return_value=card))
    monkeypatch.setattr(client, "poll_commands", Mock(return_value=[{}, {}]))
    monkeypatch.setattr(scheduler_module, "is_within_operating_hours", lambda _: during_hours)
    clock = Mock()
    clock.time.return_value = 100.0

    def sleep(delay):
        nonlocal during_hours
        if delay == 60:
            scheduler.stop()
        elif clock.sleep.call_count == len(playback_sleeps):
            during_hours = False

    clock.sleep.side_effect = sleep
    monkeypatch.setattr(scheduler_module, "time", clock)

    scheduler.run_loop()

    card.frames.assert_called_once_with(scheduler.context)
    assert not client.has_pending_commands()
    methods = [event[0] for event in output.method_calls]
    assert methods[: sent_frames + 2] == ["turn_on", *["send_frame"] * sent_frames, "turn_off"]
    assert output.send_frame.call_count == sent_frames
    if closes_during == "hold":
        output.send_frame.assert_called_once_with(frame)
    assert clock.sleep.call_args_list == [call(delay) for delay in [*playback_sleeps, 2, 60]]


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
        scheduler.run_loop()
        assert scheduler.state.cards_played == 0

    def test_playlist_loop_turns_display_back_on_when_hours_resume(self, monkeypatch):
        output = Mock()
        playlist = PlaylistConfig(cards=[CardConfig(type="clock")])
        scheduler = Scheduler(playlist, outputs=[output])
        hours = Mock(side_effect=[False, True, True])
        clock = Mock()
        play = Mock(side_effect=lambda _: scheduler.stop())
        monkeypatch.setattr(scheduler_module, "is_within_operating_hours", hours)
        monkeypatch.setattr(scheduler_module, "time", clock)
        monkeypatch.setattr(scheduler, "_play_card", play)

        scheduler.run_loop()

        clock.sleep.assert_called_once_with(60)
        assert output.method_calls == [call.turn_off(), call.turn_on()]
        play.assert_called_once_with(playlist.cards[0])

    def test_scheduler_frames_generator(self):
        """Test scheduler frames generator produces frames."""
        playlist = PlaylistConfig(cards=[CardConfig(type="clock", duration=0.1)])
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
        playlist = PlaylistConfig(cards=[CardConfig(type="clock", duration=0.1)])
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
