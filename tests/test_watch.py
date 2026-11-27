"""Test local replay, transport failures, and wall playback publication."""

from itertools import islice
from queue import Queue
from threading import Event
from time import monotonic
from unittest.mock import MagicMock, Mock

import pytest
import requests

from twinkly_wall import command, now_playing, watch
from twinkly_wall.cards import CardContext, create_card
from twinkly_wall.cards.lunch_horizontal import meal_frames
from twinkly_wall.config import CardConfig, PlaylistConfig
from twinkly_wall.outputs.twinkly import TwinklyOutput
from twinkly_wall.scheduler import Scheduler
from twinkly_wall.types import Orientation


def observation(replay, *, elapsed_ms=200, instance=1, state="playing", age_ms=0):
    return watch.Observation(
        snapshot={
            "publisher": 10,
            "state": state,
            "orientation": "bottom",
            "mirror_h": True,
            "mirror_v": False,
            "playback": {
                "instance": instance,
                "card_id": "card-id",
                "elapsed_ms": elapsed_ms,
                "replay": replay,
            },
        },
        age_ms=age_ms,
        received=100,
    )


@pytest.mark.parametrize("renderer", ["pacman_up", "lunch_horizontal"])
def test_watch_replays_a_midpoint_and_switches_repeated_card(renderer, monkeypatch):
    monkeypatch.setattr(watch, "monotonic", lambda: 100)
    if renderer == "pacman_up":
        card = create_card(renderer, {"speed": 15.5, "theme": "dots", "num_items": 5})
        expected = list(islice(card.frames(CardContext()), 15))
        replay = card.replay_inputs()
    else:
        meal = "Green Beans"
        replay = {"renderer": "lunch_horizontal/v1", "meal": meal}
        expected = list(islice(meal_frames(meal), 15))

    output = Mock()
    viewer = watch._Viewer(output)
    viewer.show(observation(replay, elapsed_ms=205))
    viewer.show(observation(replay, elapsed_ms=205))
    assert output.orientation is Orientation.bottom
    assert output.mirror_h is True and output.mirror_v is False
    index = 6 if renderer == "pacman_up" else 5
    output.send_frame.assert_called_once_with(expected[index][0])
    viewer.show(observation(replay, elapsed_ms=2, instance=2))
    assert output.send_frame.call_args.args[0] == expected[0][0]
    viewer.show(observation(replay, elapsed_ms=1_000_000, instance=2))
    assert "Waiting for the next card" in viewer.status


def test_unsupported_and_stale_wall_states_clear_the_preview(capsys, monkeypatch):
    monkeypatch.setattr(watch, "monotonic", lambda: 100)
    output = Mock()
    viewer = watch._Viewer(output)
    for sample in [
        watch.Observation(),
        observation(None),
        observation({"renderer": "other/v1"}, instance=2),
        observation(None, age_ms=31000),
        observation(None, state="idle"),
        observation(None, state="off"),
    ]:
        viewer.show(sample)
    screen = capsys.readouterr().out
    for status in ("Waiting for the wall", "Local replay unavailable", "stale", "idle", "off"):
        assert status in screen
    output.send_frame.assert_not_called()


@pytest.mark.parametrize("status", [200, 401, 404, 503])
def test_watch_http_status_and_consistent_auth(status):
    session = Mock()
    response = session.get.return_value
    response.status_code = status
    response.json.return_value = {"snapshot": {"version": 1}, "age_ms": 1200}
    if status == 503:
        response.raise_for_status.side_effect = requests.HTTPError()
    value = watch.read_now_playing(session, "http://example.test/api/now-playing", "test")
    assert value.fatal is (status in {401, 404})
    assert (value.snapshot is not None) is (status == 200)
    session.get.assert_called_once_with(
        "http://example.test/api/now-playing", headers={"Authorization": "Bearer test"}, timeout=2
    )


@pytest.mark.parametrize(
    ("data", "status", "fatal"),
    [
        ({"snapshot": None}, "Waiting for the wall", False),
        ({"snapshot": {"version": 2}}, "Incompatible now-playing version", True),
        ({}, "Invalid now-playing response", True),
    ],
)
def test_watch_none_incompatible_and_invalid_responses(data, status, fatal):
    session = Mock()
    session.get.return_value.json.return_value = data
    result = watch.read_now_playing(session, "http://example.test/api/now-playing", None)
    assert result.status == status and result.fatal is fatal


def test_dispatch_watch_and_exit_cleanly_on_interrupt(monkeypatch):
    receiver = Mock(observation=watch.Observation())
    output = Mock()
    connect = Mock(return_value=receiver)
    monkeypatch.setattr(watch, "_Receiver", connect)
    monkeypatch.setattr(watch, "TerminalOutput", lambda **kwargs: output)
    monkeypatch.setattr(watch, "sleep", Mock(side_effect=KeyboardInterrupt))
    monkeypatch.setenv("TWINKLY_API_KEY", "test")
    assert command.main(["watch", "--mcp-server", "http://example.test/", "--no-color"]) == 0
    connect.assert_called_once_with("http://example.test/api/now-playing", "test")
    receiver.stop.set.assert_called_once()
    output.stop.assert_called_once()


def test_publisher_keeps_latest_retries_and_shuts_down_off(monkeypatch):
    published = Queue()
    release_first = Event()
    attempts = []

    def post(url, **kwargs):
        assert url.endswith("/api/now-playing")
        assert kwargs["headers"] == {"Authorization": "Bearer test"}
        sample = kwargs["json"]
        attempts.append(sample)
        published.put(sample)
        if len(attempts) == 1:
            assert release_first.wait(2)
            raise requests.ConnectionError()
        return Mock()

    session = Mock(post=post)
    manager = MagicMock()
    manager.__enter__.return_value = session
    monkeypatch.setattr(now_playing.requests, "Session", lambda: manager)
    monkeypatch.setattr(now_playing, "HEARTBEAT_SECONDS", 0.05)
    publisher = now_playing.NowPlayingPublisher(
        "http://example.test", "test", Orientation.top, True, False
    )
    publisher.start("off")
    try:
        initial = published.get(timeout=2)
        assert initial["state"] == "off"
        publisher.set_state("idle")
        card = create_card("pacman_up", {"theme": "unknown"})
        publisher.playing(card, monotonic() - 0.2)
        release_first.set()
        current = published.get(timeout=2)
        heartbeat = published.get(timeout=2)
        assert current["state"] == "playing" and current["orientation"] == "top"
        assert current["playback"]["elapsed_ms"] >= 200
        assert current["playback"]["replay"]["theme"] == "trees"
        assert heartbeat["sequence"] > current["sequence"] > initial["sequence"]
        assert heartbeat["playback"]["instance"] == current["playback"]["instance"]
        assert heartbeat["playback"]["elapsed_ms"] > current["playback"]["elapsed_ms"]
    finally:
        release_first.set()
        publisher.close()
    assert attempts[-1]["state"] == "off" and attempts[-1]["playback"] is None


def test_scheduler_requires_controller_ack_and_tracks_remote_interruption(monkeypatch):
    from twinkly_wall import scheduler as scheduler_module

    config = CardConfig(type="pacman_up")
    publisher = Mock()
    device = Mock()
    device.send_frame.side_effect = [False] + [True] * 17
    scheduler = Scheduler(PlaylistConfig(cards=[config]), outputs=[device], now_playing=publisher)
    monkeypatch.setattr(scheduler_module, "time", Mock())
    remote = create_card("pacman_up", {"theme": "dots"})
    frame = next(remote.frames(CardContext()))[0]
    playlist = create_card("pacman_up", {"theme": "trees"})
    monkeypatch.setattr(playlist, "frames", lambda ctx: iter([(frame, 0.04)] * 3))
    monkeypatch.setattr(remote, "frames", lambda ctx: iter([(frame, 0)]))
    monkeypatch.setattr(scheduler, "_create_card_from_config", lambda _: playlist)
    monkeypatch.setattr(scheduler, "_check_mcp_commands", Mock(side_effect=[False, False, True]))
    monkeypatch.setattr(scheduler, "_play_mcp_cards", lambda: scheduler._play_card_instance(remote))
    scheduler.run_once()
    assert [args.args[0] for args in publisher.playing.call_args_list] == [playlist, remote]
    assert publisher.set_state.call_args.args == ("idle",)
    scheduler._set_output_power(False)
    publisher.set_state.assert_called_with("off")


def test_controller_ack_distinguishes_device_rejection(monkeypatch):
    output = TwinklyOutput("example.test")
    monkeypatch.setattr(output.client, "ensure_auth", Mock())
    request = Mock(side_effect=[{"code": 1000}, {"code": 1001}, {"code": 1000}])
    monkeypatch.setattr(output.client, "_request", request)
    monkeypatch.setattr(output.client, "login", Mock())
    frame = [[(0, 0, 0)] * 50 for _ in range(10)]
    assert output.send_frame(frame) is True
    assert output.send_frame(frame) is False
