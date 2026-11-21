"""Image and animated GIF display card."""

import logging
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from PIL import Image

from ..canvas import Canvas
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card

logger = logging.getLogger(__name__)


def load_image(path: str | Path) -> Image.Image:
    """Load an image file.

    Args:
        path: Path to image file (PNG, JPG, GIF, etc.)

    Returns:
        PIL Image object
    """
    return Image.open(path)


def resize_image(img: Image.Image, width: int, height: int, fit: str = "contain") -> Image.Image:
    """Resize image to fit display dimensions.

    Args:
        img: PIL Image
        width: Target width
        height: Target height
        fit: How to fit - "contain" (preserve aspect), "cover" (fill), "stretch"

    Returns:
        Resized PIL Image
    """
    if fit == "stretch":
        return img.resize((width, height), Image.Resampling.NEAREST)

    img_ratio = img.width / img.height
    target_ratio = width / height

    if fit == "contain":
        # Fit entire image within bounds
        if img_ratio > target_ratio:
            # Image is wider - fit to width
            new_width = width
            new_height = int(width / img_ratio)
        else:
            # Image is taller - fit to height
            new_height = height
            new_width = int(height * img_ratio)
    else:  # cover
        # Fill bounds, may crop
        if img_ratio > target_ratio:
            new_height = height
            new_width = int(height * img_ratio)
        else:
            new_width = width
            new_height = int(width / img_ratio)

    return img.resize((new_width, new_height), Image.Resampling.NEAREST)


def image_to_frame(img: Image.Image, offset_x: int = 0, offset_y: int = 0) -> Frame:
    """Convert PIL Image to Frame format.

    Args:
        img: PIL Image (should be RGB mode)
        offset_x: X offset to center image
        offset_y: Y offset to center image

    Returns:
        Frame (2D list of RGB tuples)
    """
    # Convert to RGB if needed
    if img.mode != "RGB":
        img = img.convert("RGB")

    frame: Frame = [[BLACK for _ in range(WIDTH)] for _ in range(HEIGHT)]

    for y in range(min(img.height, HEIGHT)):
        for x in range(min(img.width, WIDTH)):
            px = offset_x + x
            py = offset_y + y
            if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                r, g, b = img.getpixel((x, y))
                frame[py][px] = (r, g, b)

    return frame


def extract_gif_frames(img: Image.Image) -> list[tuple[Image.Image, float]]:
    """Extract frames and durations from animated GIF.

    Args:
        img: PIL Image (opened GIF)

    Returns:
        List of (frame_image, duration_seconds) tuples
    """
    frames = []

    try:
        while True:
            # Get frame duration (in milliseconds, default 100ms)
            duration_ms = img.info.get("duration", 100)
            duration_s = duration_ms / 1000.0

            # Convert frame to RGB
            frame_img = img.convert("RGB")
            frames.append((frame_img.copy(), duration_s))

            # Move to next frame
            img.seek(img.tell() + 1)
    except EOFError:
        pass  # End of frames

    return frames


@register_card
class ImageCard(Card):
    """Display static images or animated GIFs.

    Config options:
        path: Path to image file (required)
        fit: How to fit image - contain, cover, stretch (default: contain)
        scroll: Scroll wide images horizontally (default: auto)
        scroll_speed: Pixels per second for scrolling (default: 20)
        center: Center image on display (default: true)
        bgcolor: Background color RGB (default: black)
    """

    card_type = "image"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.path: str = self.config.get("path", "")
        self.fit: str = self.config.get("fit", "contain")
        self.scroll: bool | str = self.config.get("scroll", "auto")
        self.scroll_speed: float = self.config.get("scroll_speed", 20.0)
        self.center: bool = self.config.get("center", True)
        self.bgcolor: RGB = tuple(self.config.get("bgcolor", BLACK))  # type: ignore

    def _is_animated_gif(self, img: Image.Image) -> bool:
        """Check if image is an animated GIF."""
        try:
            img.seek(1)
            img.seek(0)
            return True
        except EOFError:
            return False

    def _should_scroll(self, img_width: int) -> bool:
        """Determine if image should scroll."""
        if self.scroll == "auto":
            return img_width > WIDTH
        return bool(self.scroll)

    def _render_static(self, img: Image.Image) -> Frame:
        """Render a static image frame."""
        # Resize to fit display
        resized = resize_image(img, WIDTH, HEIGHT, self.fit)

        # Calculate centering offset
        offset_x = 0
        offset_y = 0
        if self.center:
            offset_x = (WIDTH - resized.width) // 2
            offset_y = (HEIGHT - resized.height) // 2

        return image_to_frame(resized, offset_x, offset_y)

    def _render_scrolling(self, img: Image.Image, offset: int) -> Frame:
        """Render a scrolling image frame.

        Args:
            img: The full-width image
            offset: Current scroll offset (0 = start, increases as we scroll)
        """
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(self.bgcolor)

        # Convert image to RGB
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Resize height to fit display, keep width proportional
        if img.height != HEIGHT:
            ratio = HEIGHT / img.height
            new_width = int(img.width * ratio)
            img = img.resize((new_width, HEIGHT), Image.Resampling.NEAREST)

        # Draw visible portion
        for y in range(HEIGHT):
            for x in range(WIDTH):
                src_x = x + offset
                if 0 <= src_x < img.width:
                    r, g, b = img.getpixel((src_x, y))
                    canvas.set_pixel(x, y, (r, g, b))

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate image frames."""
        if not self.path:
            # No path, show error
            canvas = Canvas(WIDTH, HEIGHT)
            from ..fonts import draw_text

            draw_text(canvas, 0, 1, "NO IMG", (255, 0, 0))
            frame = canvas.copy()
            start_time = time.time()
            while time.time() - start_time < self.duration:
                yield frame, 1.0
            return

        # Resolve path
        path = Path(self.path)
        if not path.is_absolute():
            # Try relative to config directory
            path = Path("config") / path
        if not path.exists():
            # Try assets directory
            path = Path("assets") / self.path
        if not path.exists():
            path = Path(self.path)  # Use original

        try:
            img = load_image(path)
        except Exception as e:
            logger.error(f"Failed to load image {self.path}: {e}")
            canvas = Canvas(WIDTH, HEIGHT)
            from ..fonts import draw_text

            draw_text(canvas, 0, 1, "ERR", (255, 0, 0))
            frame = canvas.copy()
            start_time = time.time()
            while time.time() - start_time < self.duration:
                yield frame, 1.0
            return

        # Check if animated GIF
        if self._is_animated_gif(img):
            yield from self._animate_gif(img)
            return

        # Check if we should scroll
        # First resize to display height
        if img.height != HEIGHT:
            ratio = HEIGHT / img.height
            new_width = int(img.width * ratio)
            img_for_check = img.resize((new_width, HEIGHT), Image.Resampling.NEAREST)
        else:
            img_for_check = img

        if self._should_scroll(img_for_check.width):
            yield from self._scroll_image(img)
        else:
            # Static display
            frame = self._render_static(img)
            start_time = time.time()
            while time.time() - start_time < self.duration:
                yield frame, 0.1

    def _animate_gif(self, img: Image.Image) -> Iterator[tuple[Frame, float]]:
        """Animate a GIF."""
        gif_frames = extract_gif_frames(img)
        if not gif_frames:
            return

        start_time = time.time()
        frame_idx = 0

        while time.time() - start_time < self.duration:
            frame_img, frame_duration = gif_frames[frame_idx]

            # Resize and convert to frame
            resized = resize_image(frame_img, WIDTH, HEIGHT, self.fit)

            offset_x = 0
            offset_y = 0
            if self.center:
                offset_x = (WIDTH - resized.width) // 2
                offset_y = (HEIGHT - resized.height) // 2

            frame = image_to_frame(resized, offset_x, offset_y)
            yield frame, frame_duration

            # Next frame (loop)
            frame_idx = (frame_idx + 1) % len(gif_frames)

    def _scroll_image(self, img: Image.Image) -> Iterator[tuple[Frame, float]]:
        """Scroll a wide image."""
        # Resize height to fit display
        if img.height != HEIGHT:
            ratio = HEIGHT / img.height
            new_width = int(img.width * ratio)
            img = img.resize((new_width, HEIGHT), Image.Resampling.NEAREST)

        total_scroll = img.width  # Scroll until image is off screen
        pixels_per_frame = self.scroll_speed / 30.0
        frame_delay = 1.0 / 30.0

        start_time = time.time()
        offset = 0.0
        scroll_completed = False

        while True:
            frame = self._render_scrolling(img, int(offset))
            yield frame, frame_delay

            offset += pixels_per_frame

            if offset >= total_scroll:
                scroll_completed = True
                offset = 0.0

            elapsed = time.time() - start_time
            if scroll_completed and elapsed >= self.duration:
                break
