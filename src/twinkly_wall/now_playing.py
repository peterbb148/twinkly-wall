"""Wall-initiated publishing of playback state and replay inputs."""

from threading import Condition, Thread
from time import monotonic, time_ns
from typing import Any, Literal

import requests

from .cards import Card
from .types import Orientation

NOW_PLAYING_PATH = "/api/now-playing"
HEARTBEAT_SECONDS = 10.0
STALE_SECONDS = 30.0
REQUEST_TIMEOUT = 2.0


class NowPlayingPublisher:
    """Send the latest wall state on a worker independent of LED playback."""

    def __init__(
        self,
        server_url: str,
        api_key: str | None,
        orientation: Orientation,
        mirror_h: bool,
        mirror_v: bool,
    ) -> None:
        self._url = server_url.rstrip("/") + NOW_PLAYING_PATH
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._display = {
            "version": 1,
            "publisher": time_ns(),
            "orientation": orientation.value,
            "mirror_h": mirror_h,
            "mirror_v": mirror_v,
        }
        self._condition = Condition()
        self._sequence = 0
        self._state = "idle"
        self._playback: dict[str, Any] | None = None
        self._started = 0.0
        self._closed = False
        self._worker = Thread(target=self._publish, name="now-playing", daemon=True)

    def start(self, initial: Literal["idle", "off"]) -> None:
        """Start publishing after the output is initialized."""
        self.set_state(initial)
        self._worker.start()

    def set_state(self, state: Literal["idle", "off"]) -> None:
        """Publish a lifecycle change without doing any network I/O."""
        with self._condition:
            if self._state != state or self._sequence == 0:
                self._state = state
                self._playback = None
                self._sequence += 1
                self._condition.notify()

    def playing(self, card: Card, started: float) -> None:
        """Record successful playback with a new instance for every activation."""
        replay = card.replay_inputs()
        with self._condition:
            self._sequence += 1
            self._state = "playing"
            self._playback = {
                "instance": self._sequence,
                "card_id": card.registered_name,
                "replay": replay,
            }
            self._started = started
            self._condition.notify()

    def close(self) -> None:
        """Give the worker a bounded opportunity to deliver the final off state."""
        self.set_state("off")
        with self._condition:
            self._closed = True
            self._condition.notify()
        self._worker.join(timeout=REQUEST_TIMEOUT)

    def _publish(self) -> None:
        last_sequence = 0
        with requests.Session() as session:
            while True:
                with self._condition:
                    self._condition.wait_for(
                        lambda: self._sequence != last_sequence or self._closed,
                        timeout=HEARTBEAT_SECONDS,
                    )
                    if self._closed and self._sequence == last_sequence:
                        return
                    self._sequence += 1
                    last_sequence = self._sequence
                    playback = self._playback
                    if playback is not None:
                        playback = {
                            **playback,
                            "elapsed_ms": max(0, round((monotonic() - self._started) * 1000)),
                        }
                    snapshot = {
                        **self._display,
                        "sequence": last_sequence,
                        "state": self._state,
                        "playback": playback,
                    }
                try:
                    session.post(
                        self._url, headers=self._headers, json=snapshot, timeout=REQUEST_TIMEOUT
                    ).raise_for_status()
                except requests.RequestException:
                    # A failed post is retried by the next state update or heartbeat.
                    continue
