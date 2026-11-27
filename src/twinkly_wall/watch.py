"""Read now-playing state and render compatible cards locally."""

import argparse
import os
from collections.abc import Iterator
from dataclasses import dataclass
from threading import Event, Thread
from time import monotonic, sleep
from typing import Any

import requests

from .cards import CardContext
from .cards.lunch_horizontal import meal_frames
from .cards.pacman import PacmanUpCard
from .mcp_client import DEFAULT_SERVER_URL
from .now_playing import NOW_PLAYING_PATH, REQUEST_TIMEOUT, STALE_SECONDS
from .outputs.terminal import TerminalOutput
from .types import Frame, Orientation

_POLL_SECONDS = 1.0
_DISPLAY_STEP = 1 / 30


@dataclass(frozen=True)
class Observation:
    """One server sample or an explicit connection status."""

    snapshot: dict[str, Any] | None = None
    age_ms: int = 0
    received: float = 0.0
    status: str = "Waiting for the wall"
    fatal: bool = False


def read_now_playing(session: requests.Session, url: str, api_key: str | None) -> Observation:
    """Read the latest sample without touching the wall command queue."""
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        response = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        if response.status_code in (401, 403):
            return Observation(status="Now-playing authentication failed", fatal=True)
        if response.status_code in (404, 405):
            return Observation(status="MCP server does not support now-playing", fatal=True)
        response.raise_for_status()
        data = response.json()
        snapshot = data["snapshot"]
        if snapshot is None:
            return Observation()
        if snapshot["version"] != 1:
            return Observation(status="Incompatible now-playing version", fatal=True)
        return Observation(snapshot, int(data["age_ms"]), monotonic())
    except requests.RequestException:
        return Observation(status="Now-playing connection unavailable")
    except (KeyError, TypeError, ValueError):
        return Observation(status="Invalid now-playing response", fatal=True)


class _Receiver:
    def __init__(self, url: str, key: str | None):
        self.observation = Observation()
        self.stop = Event()
        self.thread = Thread(target=self._poll, args=(url, key), daemon=True)

    def _poll(self, url: str, key: str | None) -> None:
        with requests.Session() as session:
            while not self.stop.is_set():
                self.observation = read_now_playing(session, url, key)
                if self.observation.fatal or self.stop.wait(_POLL_SECONDS):
                    return


def _replay_frames(inputs: dict[str, Any], ctx: CardContext) -> Iterator[tuple[Frame, float]]:
    """Use the wall's renderer and resolved inputs."""
    if inputs["renderer"] == "lunch_horizontal/v1":
        return meal_frames(inputs["meal"])
    if inputs["renderer"] == "pacman_up/v1":
        return PacmanUpCard(
            {
                "theme": inputs["theme"],
                "speed": inputs["speed"],
                "num_items": inputs["num_items"],
                "repeats": inputs["repeats"],
                "pacman_color": inputs["color"],
            }
        ).frames(ctx)
    raise ValueError("Unsupported renderer")


class _Viewer:
    def __init__(self, output: TerminalOutput):
        self.output = output
        self.status = ""
        self.instance: tuple[int, int] | None = None
        self.frames: Iterator[tuple[Frame, float]] = iter(())
        self.frame_end = 0.0
        self.elapsed = 0.0
        self.last_tick = 0.0
        self.finished = False

    def _show_status(self, status: str) -> None:
        if status != self.status:
            self.output.start()
            print(status, flush=True)
            self.status = status

    def show(self, observation: Observation) -> None:
        """Advance the local renderer to the best known wall playback position."""
        snapshot = observation.snapshot
        if snapshot is None:
            self.instance = None
            self._show_status(observation.status)
            return
        now = monotonic()
        age = observation.age_ms / 1000 + max(0.0, now - observation.received)
        if age > STALE_SECONDS:
            self.instance = None
            self._show_status("Wall state is stale")
            return
        if snapshot["state"] != "playing":
            self.instance = None
            self._show_status("Wall is off" if snapshot["state"] == "off" else "Wall is idle")
            return

        playback = snapshot["playback"]
        instance = (snapshot["publisher"], playback["instance"])
        acknowledged = playback["elapsed_ms"] / 1000
        if self.instance != instance:
            self.instance = instance
            self.frame_end = 0.0
            self.elapsed = acknowledged
            self.last_tick = now
            self.finished = False
            self.status = ""
            self.output.orientation = Orientation(snapshot["orientation"])
            self.output.mirror_h = snapshot["mirror_h"]
            self.output.mirror_v = snapshot["mirror_v"]
            inputs = playback["replay"]
            try:
                self.frames = _replay_frames(
                    inputs, CardContext(orientation=self.output.orientation)
                )
            except (KeyError, TypeError, ValueError):
                self.finished = True
                self._show_status(f"Local replay unavailable for {playback['card_id']}")
                return
            self._show_status(f"Playing {playback['card_id']}")

        if self.finished:
            return
        self.elapsed = min(acknowledged, self.elapsed + max(0.0, now - self.last_tick))
        self.last_tick = now
        frame = None
        while self.frame_end <= self.elapsed:
            step = next(self.frames, None)
            if step is None:
                self.finished = True
                break
            frame, delay = step
            self.frame_end += delay
        if frame is not None:
            self.output.send_frame(frame)


def main(argv: list[str] | None = None) -> int:
    """Watch the wall in a terminal using local card replay."""
    parser = argparse.ArgumentParser(prog="twinkly-cli watch", description=__doc__)
    parser.add_argument("--mcp-server", help="MCP server URL (default: $TWINKLY_MCP_URL)")
    parser.add_argument("--no-color", action="store_true", help="Render frames without ANSI colors")
    args = parser.parse_args(argv)
    base = args.mcp_server or os.environ.get("TWINKLY_MCP_URL") or DEFAULT_SERVER_URL
    receiver = _Receiver(base.rstrip("/") + NOW_PLAYING_PATH, os.environ.get("TWINKLY_API_KEY"))
    output = TerminalOutput(color_mode=not args.no_color)
    viewer = _Viewer(output)
    receiver.thread.start()
    try:
        while True:
            observation = receiver.observation
            try:
                viewer.show(observation)
            except (KeyError, TypeError, ValueError):
                viewer._show_status("Invalid now-playing response")
                return 1
            if observation.fatal:
                return 1
            sleep(_DISPLAY_STEP)
    except KeyboardInterrupt:
        return 0
    finally:
        receiver.stop.set()
        receiver.thread.join(timeout=REQUEST_TIMEOUT)
        output.stop()
