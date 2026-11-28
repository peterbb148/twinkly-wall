"""Record preview frames as an animated GIF."""

import math
import struct
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path

from PIL import Image

from ..types import Frame, Orientation, apply_orientation

MAX_FRAMES = 10_000
MAX_PIXELS = 25_000_000


def record_gif(
    frames: Iterator[tuple[Frame, float]],
    path: Path,
    orientation: Orientation,
    *,
    mirror_h: bool = False,
    mirror_v: bool = False,
    scale: int = 8,
    duration: float | None = None,
) -> None:
    """Capture frames in real time, then write a bounded, scaled GIF."""
    if not isinstance(scale, int) or scale < 1:
        raise ValueError("GIF scale must be a positive integer")
    if duration is not None and (not math.isfinite(duration) or duration <= 0):
        raise ValueError("GIF duration must be finite and greater than zero")
    images: list[Image.Image] = []
    timestamps: list[float] = []
    started = time.monotonic()
    deadline = started + duration if duration is not None else math.inf
    size: tuple[int, int] | None = None

    while time.monotonic() < deadline:
        item = next(frames, None)
        if item is None or time.monotonic() >= deadline:
            break
        frame, delay = item
        if not math.isfinite(delay) or delay < 0:
            raise ValueError("GIF frame delays must be finite and nonnegative")
        delay = min(delay, max(0.0, deadline - time.monotonic()))
        if delay > 655.35:
            raise ValueError("A GIF frame delay cannot exceed 655.35 seconds")
        if len(images) >= MAX_FRAMES:
            raise ValueError(f"Recording exceeds the {MAX_FRAMES} frame memory limit")

        if not frame or not frame[0] or any(len(row) != len(frame[0]) for row in frame):
            raise ValueError("Cannot record an empty or irregular frame")
        oriented = apply_orientation(frame, orientation, mirror_h=mirror_h, mirror_v=mirror_v)
        width, height = len(oriented[0]), len(oriented)
        scaled_size = (width * scale, height * scale)
        if max(scaled_size) > 65535:
            raise ValueError("GIF dimensions cannot exceed 65535 pixels per axis")
        if size is not None and size != scaled_size:
            raise ValueError("All GIF frames must have the same dimensions")
        size = scaled_size
        if scaled_size[0] * scaled_size[1] * (len(images) + 1) > MAX_PIXELS:
            raise ValueError(f"Recording exceeds the {MAX_PIXELS} pixel memory limit")

        image = Image.new("RGB", (width, height))
        image.putdata([pixel for row in oriented for pixel in row])
        image = image.quantize(colors=256).resize(scaled_size, Image.Resampling.NEAREST)
        ready = time.monotonic()
        if ready >= deadline:
            break
        # Keep the previous frame visible while the next frame is prepared.
        timestamps.append(ready - started if images else 0.0)
        images.append(image)
        time.sleep(min(delay, max(0.0, deadline - ready)))

    if not images:
        raise ValueError("No frames to record")
    timestamps.append(min(time.monotonic(), deadline) - started)
    ticks = [round(timestamp * 100) for timestamp in timestamps]
    durations = [max(1, end - start) * 10 for start, end in zip(ticks, ticks[1:])]
    if max(durations) > 655350:
        raise ValueError("A GIF frame delay cannot exceed 655.35 seconds")
    temporary_path: Path | None = None
    try:
        # Encode beside the destination so failure never truncates an existing GIF.
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".gif", delete=False) as file:
            temporary_path = Path(file.name)
        images[0].save(
            temporary_path,
            format="GIF",
            save_all=True,
            append_images=images[1:],
            duration=durations,
            loop=0,
            optimize=False,
        )
        temporary_path.replace(path)
    except (struct.error, OverflowError) as error:
        raise ValueError(
            "GIF delay exceeds 655.35 seconds after identical frames were merged"
        ) from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
