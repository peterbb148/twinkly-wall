"""DNA helix animation card."""

import math
import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..types import HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card

# DNA strand colors
STRAND_1_COLOR: RGB = (0, 150, 255)  # Blue
STRAND_2_COLOR: RGB = (255, 50, 100)  # Pink/Red
BASE_PAIR_COLORS: list[RGB] = [
    (255, 255, 0),  # Yellow (A-T)
    (0, 255, 150),  # Cyan/Green (G-C)
    (255, 150, 0),  # Orange (T-A)
    (150, 255, 0),  # Lime (C-G)
]
BACKGROUND_COLOR: RGB = (0, 0, 20)  # Dark blue


@register_card
class DNACard(Card):
    """DNA double helix animation.

    Config options:
        speed: Animation speed multiplier (default: 1.0)
        strand1_color: First strand color as [R, G, B] (default: blue)
        strand2_color: Second strand color as [R, G, B] (default: pink)
        background: Background color as [R, G, B] (default: dark blue)
    """

    card_type = "dna"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.speed: float = self.config.get("speed", 1.0)

        # Allow custom colors
        s1 = self.config.get("strand1_color")
        s2 = self.config.get("strand2_color")
        bg = self.config.get("background")

        self.strand1_color: RGB = tuple(s1) if s1 else STRAND_1_COLOR
        self.strand2_color: RGB = tuple(s2) if s2 else STRAND_2_COLOR
        self.background: RGB = tuple(bg) if bg else BACKGROUND_COLOR

    def _render_frame(self, t: float) -> Frame:
        """Render a single frame of the DNA helix."""
        canvas = Canvas(WIDTH, HEIGHT)

        # Fill background
        for y in range(HEIGHT):
            for x in range(WIDTH):
                canvas.set_pixel(x, y, self.background)

        # Animation parameters
        wave_speed = t * 2.0 * self.speed  # How fast the helix rotates
        wave_length = 12.0  # Pixels per full rotation
        amplitude = 3.5  # Max vertical offset from center
        center_y = HEIGHT / 2 - 0.5  # Center of the helix

        # Draw the double helix
        for x in range(WIDTH):
            # Phase for this x position
            phase = (x / wave_length) * 2 * math.pi - wave_speed

            # Calculate y positions for both strands (180 degrees apart)
            y1 = center_y + amplitude * math.sin(phase)
            y2 = center_y + amplitude * math.sin(phase + math.pi)

            # Determine which strand is in front based on cosine (z-depth)
            z1 = math.cos(phase)
            z2 = math.cos(phase + math.pi)

            # Draw base pair connection (rungs of the ladder)
            # Only draw when strands are roughly at same depth (crossing)
            rung_visibility = abs(z1 - z2) < 1.5
            if rung_visibility and x % 3 == 0:  # Draw rungs every 3 pixels
                y_min = int(min(y1, y2))
                y_max = int(max(y1, y2))
                base_color = BASE_PAIR_COLORS[(x // 3) % len(BASE_PAIR_COLORS)]

                # Dim the base pair based on depth
                depth_factor = 0.4 + 0.6 * (1 + min(z1, z2)) / 2
                dimmed_color = tuple(int(c * depth_factor) for c in base_color)

                for y in range(max(0, y_min), min(HEIGHT, y_max + 1)):
                    canvas.set_pixel(x, y, dimmed_color)

            # Draw strands with depth-based brightness
            # Back strand first, then front strand
            strands = [(y1, z1, self.strand1_color), (y2, z2, self.strand2_color)]
            strands.sort(key=lambda s: s[1])  # Sort by z (back to front)

            for y_pos, z_depth, color in strands:
                y_int = int(round(y_pos))
                if 0 <= y_int < HEIGHT:
                    # Brightness based on z-depth (-1 to 1 mapped to 0.3 to 1.0)
                    brightness = 0.3 + 0.7 * (z_depth + 1) / 2
                    lit_color = tuple(int(c * brightness) for c in color)
                    canvas.set_pixel(x, y_int, lit_color)

                    # Add slight glow above/below for thickness
                    if y_int > 0 and brightness > 0.6:
                        glow = tuple(int(c * brightness * 0.4) for c in color)
                        canvas.set_pixel(x, y_int - 1, glow)
                    if y_int < HEIGHT - 1 and brightness > 0.6:
                        glow = tuple(int(c * brightness * 0.4) for c in color)
                        canvas.set_pixel(x, y_int + 1, glow)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate DNA helix animation frames."""
        start_time = time.time()
        frame_delay = 1.0 / 30.0  # 30 FPS

        while time.time() - start_time < self.duration:
            t = time.time() - start_time
            frame = self._render_frame(t)
            yield frame, frame_delay
