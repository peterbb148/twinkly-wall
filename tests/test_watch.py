"""Test local replay, transport failures, and wall playback publication."""

import json
from itertools import islice
from queue import Queue
from threading import Event
from unittest.mock import MagicMock, Mock, call

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


def test_replay_cannot_outrun_an_acknowledged_position(monkeypatch):
    tick = [100.0]
    monkeypatch.setattr(watch, "monotonic", lambda: tick[0])
    output = Mock()
    viewer = watch._Viewer(output)
    replay = {"renderer": "lunch_horizontal/v1", "meal": "Red Cabbage"}
    viewer.show(observation(replay, elapsed_ms=800))
    first = output.send_frame.call_args
    tick[0] = 120.0
    viewer.show(observation(replay, elapsed_ms=800))
    assert viewer.elapsed == 0.8
    assert output.send_frame.call_args == first
    assert not viewer.finished
    tick[0] += 0.04
    viewer.show(observation(replay, elapsed_ms=1600))
    assert 0.8 < viewer.elapsed < 0.85
    assert output.send_frame.call_count == 2


def test_midpoint_catch_up_is_bounded_and_interruptible(monkeypatch):
    monkeypatch.setattr(watch, "monotonic", lambda: 100)
    output = Mock()
    viewer = watch._Viewer(output)
    steps = 0

    def slow_card(inputs, ctx):
        nonlocal steps
        while True:
            steps += 1
            yield [[(0, 0, 0)]], 1 / 30

    monkeypatch.setattr(watch, "_replay_frames", slow_card)
    replay = {"renderer": "pacman_up/v1"}
    viewer.show(observation(replay, elapsed_ms=3_600_000))
    assert steps == watch._CATCH_UP_BATCH
    output.send_frame.assert_not_called()
    viewer.show(observation(None, state="off"))
    assert viewer.status == "Wall is off"
    assert steps == watch._CATCH_UP_BATCH


def test_replay_holds_last_frame_until_wall_reports_state_change(monkeypatch):
    monkeypatch.setattr(watch, "monotonic", lambda: 100)
    frame = [[(0, 0, 0)]]
    monkeypatch.setattr(watch, "_replay_frames", lambda inputs, ctx: iter([(frame, 0.04)]))
    output = Mock()
    viewer = watch._Viewer(output)
    viewer.show(observation({"renderer": "lunch_horizontal/v1"}, elapsed_ms=60))
    output.send_frame.assert_called_once_with(frame)
    assert viewer.finished
    assert viewer.status == "Playing card-id"


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
        assert kwargs["headers"] == {
            "Content-Type": "application/json",
            "Authorization": "Bearer test",
        }
        assert isinstance(kwargs["data"], bytes)
        sample = json.loads(kwargs["data"])
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
    monkeypatch.setattr(now_playing, "PROGRESS_SECONDS", 0.1)
    publisher = now_playing.NowPlayingPublisher(
        "http://example.test", "test", Orientation.top, True, False
    )
    publisher.start("off")
    try:
        initial = published.get(timeout=2)
        assert initial["state"] == "off"
        publisher.set_state("idle")
        card = create_card("pacman_up", {"theme": "unknown"})
        publisher.playing(card, 0.2)
        release_first.set()
        current = published.get(timeout=2)
        publisher.progress(0.5)
        heartbeat = published.get(timeout=2)
        assert current["state"] == "playing" and current["orientation"] == "top"
        assert current["playback"]["elapsed_ms"] == 200
        assert current["playback"]["replay"]["theme"] == "trees"
        assert heartbeat["sequence"] > current["sequence"] > initial["sequence"]
        assert heartbeat["playback"]["instance"] == current["playback"]["instance"]
        assert heartbeat["playback"]["elapsed_ms"] == 500
    finally:
        release_first.set()
        publisher.close()
    assert attempts[-1]["state"] == "off" and attempts[-1]["playback"] is None


def test_scheduler_requires_controller_ack_and_tracks_remote_interruption(monkeypatch):
    from twinkly_wall import scheduler as scheduler_module

    config = CardConfig(type="pacman_up")
    publisher = Mock()
    device = Mock()
    device.send_frame.side_effect = [False] + [True] * 20
    scheduler = Scheduler(PlaylistConfig(cards=[config]), outputs=[device], now_playing=publisher)
    monkeypatch.setattr(scheduler_module, "time", Mock())
    remote = create_card("pacman_up", {"theme": "dots"})
    frame = next(remote.frames(CardContext()))[0]
    playlist = create_card("pacman_up", {"theme": "trees"})
    monkeypatch.setattr(playlist, "frames", lambda ctx: iter([(frame, 0.04)] * 4))
    monkeypatch.setattr(remote, "frames", lambda ctx: iter([(frame, 0.04)] * 2))
    monkeypatch.setattr(scheduler, "_create_card_from_config", lambda _: playlist)
    monkeypatch.setattr(
        scheduler, "_check_mcp_commands", Mock(side_effect=[False, False, False, True])
    )
    monkeypatch.setattr(scheduler, "_play_mcp_cards", lambda: scheduler._play_card_instance(remote))
    scheduler.run_once()
    assert [args.args[0] for args in publisher.playing.call_args_list] == [playlist, remote]
    assert [args.args[1] for args in publisher.playing.call_args_list] == [0.04, 0]
    assert publisher.progress.call_args_list == [call(0.08), call(0.04)]
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


@pytest.mark.parametrize(("characters", "includes_replay"), [(250, True), (1000, False)])
def test_snapshot_uses_utf8_and_preserves_metadata_within_wire_limit(characters, includes_replay):
    meal = "🍅" * characters
    playback = {
        "instance": 1,
        "card_id": "lunch_horizontal",
        "elapsed_ms": 0,
        "replay": {"renderer": "lunch_horizontal/v1", "meal": meal},
    }
    original = {"state": "playing", "playback": playback}
    body = now_playing._snapshot_bytes(original)
    assert len(body) <= now_playing.MAX_SNAPSHOT_BYTES
    sent = json.loads(body)
    expected_replay = playback["replay"] if includes_replay else None
    assert sent == {"state": "playing", "playback": {**playback, "replay": expected_replay}}
    assert ("🍅".encode() in body) is includes_replay


@pytest.mark.parametrize(
    "config",
    [
        {"repeats": 2.0},
        {"num_items": True},
        {"speed": True},
        {"pacman_color": [1.0, 2, 3]},
        {"pacman_color": [1, 2]},
    ],
)
def test_incompatible_pacman_config_only_publishes_card_metadata(config):
    card = create_card("pacman_up", config)
    assert card.replay_inputs() is None


def test_shutdown_wait_budget_covers_an_inflight_post_and_the_off_post():
    publisher = now_playing.NowPlayingPublisher(
        "http://example.test", None, Orientation.top, False, False
    )
    publisher._worker = Mock()
    publisher.close()
    publisher._worker.join.assert_called_once_with(timeout=4 * now_playing.REQUEST_TIMEOUT)
    assert publisher._state == "off"
