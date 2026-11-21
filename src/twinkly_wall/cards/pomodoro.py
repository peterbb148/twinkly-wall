"""Pomodoro timer card."""

import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..fonts import draw_text, text_width
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card

WORK_COLOR: RGB = (255, 50, 50)  # Red for work
BREAK_COLOR: RGB = (50, 255, 50)  # Green for break
BG_DARK: RGB = (30, 30, 30)


@register_card
class PomodoroCard(Card):
    """Pomodoro timer with work/break phases.

    Config options:
        work_minutes: Work phase duration (default: 25)
        break_minutes: Break phase duration (default: 5)
        show_progress: Show progress bar (default: true)
    """

    card_type = "pomodoro"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.work_minutes: int = self.config.get("work_minutes", 25)
        self.break_minutes: int = self.config.get("break_minutes", 5)
        self.show_progress: bool = self.config.get("show_progress", True)

    def _render_frame(self, phase: str, remaining_seconds: int, progress: float) -> Frame:
        """Render the pomodoro display."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        # Choose color based on phase
        color = WORK_COLOR if phase == "WORK" else BREAK_COLOR

        # Format time
        minutes = remaining_seconds // 60
        seconds = remaining_seconds % 60
        time_str = f"{minutes:02d}:{seconds:02d}"

        # Draw phase label (top)
        label_w = text_width(phase)
        label_x = (WIDTH - label_w) // 2
        draw_text(canvas, label_x, 0, phase, color)

        # Draw time (bottom)
        time_w = text_width(time_str)
        time_x = (WIDTH - time_w) // 2
        draw_text(canvas, time_x, 5, time_str, (255, 255, 255))

        # Draw progress bar at very bottom
        if self.show_progress:
            bar_y = HEIGHT - 1
            bar_width = int(WIDTH * progress)
            for x in range(WIDTH):
                if x < bar_width:
                    canvas.set_pixel(x, bar_y, color)
                else:
                    canvas.set_pixel(x, bar_y, BG_DARK)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate pomodoro timer frames."""
        # Calculate total cycle time
        work_seconds = self.work_minutes * 60
        break_seconds = self.break_minutes * 60
        cycle_seconds = work_seconds + break_seconds

        start_time = time.time()
        frame_delay = 0.5

        while time.time() - start_time < self.duration:
            # Calculate position in cycle
            elapsed = time.time() - start_time
            cycle_pos = elapsed % cycle_seconds

            if cycle_pos < work_seconds:
                # Work phase
                phase = "WORK"
                remaining = int(work_seconds - cycle_pos)
                progress = cycle_pos / work_seconds
            else:
                # Break phase
                phase = "BREAK"
                break_pos = cycle_pos - work_seconds
                remaining = int(break_seconds - break_pos)
                progress = break_pos / break_seconds

            frame = self._render_frame(phase, remaining, progress)
            yield frame, frame_delay
