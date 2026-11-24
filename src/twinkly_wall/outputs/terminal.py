"""Terminal output renderer for previewing frames in the console."""

import sys
import time
from collections.abc import Iterator

from ..types import BLACK, RGB, Frame, Orientation, apply_orientation


def _brightness(color: RGB) -> int:
    """Calculate perceived brightness of a color (0-255)."""
    r, g, b = color
    # Using standard luminance formula
    return int(0.299 * r + 0.587 * g + 0.114 * b)


def frame_to_terminal(
    frame: Frame,
    color_mode: bool = True,
    use_half_blocks: bool = True,
) -> str:
    """
    Convert a frame to a string for terminal display.

    Args:
        frame: The frame to render
        color_mode: If True, use ANSI 24-bit colors. If False, use grayscale blocks.
        use_half_blocks: If True, use half-block characters to double vertical resolution.

    Returns:
        A string that can be printed to the terminal.
    """
    if not frame or not frame[0]:
        return ""

    lines: list[str] = []
    height = len(frame)
    width = len(frame[0])

    if use_half_blocks and color_mode:
        # Use upper half block (▀) with foreground for top pixel and background for bottom
        # This doubles vertical resolution
        for y in range(0, height, 2):
            line = ""
            for x in range(width):
                top = frame[y][x]
                # Bottom pixel (if exists)
                bottom = frame[y + 1][x] if y + 1 < height else BLACK

                # Set foreground (top) and background (bottom) colors
                line += f"\x1b[38;2;{top[0]};{top[1]};{top[2]}m"
                line += f"\x1b[48;2;{bottom[0]};{bottom[1]};{bottom[2]}m"
                line += "▀"

            line += "\x1b[0m"  # Reset colors
            lines.append(line)
    elif color_mode:
        # Full color, one character per pixel
        for y in range(height):
            line = ""
            for x in range(width):
                r, g, b = frame[y][x]
                line += f"\x1b[38;2;{r};{g};{b}m█"
            line += "\x1b[0m"
            lines.append(line)
    else:
        # Grayscale mode using block characters
        for y in range(height):
            line = ""
            for x in range(width):
                brightness = _brightness(frame[y][x])
                if brightness < 32:
                    line += " "
                elif brightness < 96:
                    line += "░"
                elif brightness < 160:
                    line += "▒"
                elif brightness < 224:
                    line += "▓"
                else:
                    line += "█"
            lines.append(line)

    return "\n".join(lines)


def print_frame(
    frame: Frame,
    color_mode: bool = True,
    use_half_blocks: bool = True,
    file=None,
) -> None:
    """Print a frame to the terminal."""
    if file is None:
        file = sys.stdout
    output = frame_to_terminal(frame, color_mode, use_half_blocks)
    print(output, file=file)


def clear_screen() -> None:
    """Clear the terminal screen and move cursor to top-left."""
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.flush()


def move_cursor_up(lines: int) -> None:
    """Move cursor up by N lines (for overwriting previous frame)."""
    sys.stdout.write(f"\x1b[{lines}A")
    sys.stdout.flush()


def hide_cursor() -> None:
    """Hide the terminal cursor."""
    sys.stdout.write("\x1b[?25l")
    sys.stdout.flush()


def show_cursor() -> None:
    """Show the terminal cursor."""
    sys.stdout.write("\x1b[?25h")
    sys.stdout.flush()


def animate_frames(
    frames: Iterator[tuple[Frame, float]],
    color_mode: bool = True,
    use_half_blocks: bool = True,
    clear_between: bool = True,
    orientation: Orientation = Orientation.horizontal,
    *,
    mirror_h: bool = False,
    mirror_v: bool = False,
) -> None:
    """
    Animate a sequence of frames in the terminal.

    Args:
        frames: Iterator of (frame, delay) tuples
        color_mode: Use ANSI colors
        use_half_blocks: Use half-block characters for double resolution
        clear_between: If True, clear between frames. If False, overwrite in place.
    """
    try:
        hide_cursor()
        first_frame = True

        for frame, delay in frames:
            oriented = apply_orientation(frame, orientation, mirror_h=mirror_h, mirror_v=mirror_v)

            if clear_between:
                clear_screen()
            elif not first_frame:
                # Move cursor up to overwrite previous frame
                height = len(oriented)
                lines_to_move = height // 2 if use_half_blocks else height
                move_cursor_up(lines_to_move)

            print_frame(oriented, color_mode, use_half_blocks)
            first_frame = False

            if delay > 0:
                time.sleep(delay)

    finally:
        show_cursor()
        print()  # Newline after animation


def preview_text(text: str, color: RGB = (255, 255, 255)) -> None:
    """Quick helper to preview text in the terminal."""
    from ..canvas import Canvas
    from ..fonts import draw_text
    from ..types import HEIGHT, WIDTH

    canvas = Canvas(WIDTH, HEIGHT)
    draw_text(canvas, 0, 1, text, color)
    print_frame(canvas.copy())


class TerminalOutput:
    """Terminal output target for the scheduler.

    This class implements the Output protocol and renders frames
    to the terminal in real-time.
    """

    def __init__(
        self,
        color_mode: bool = True,
        use_half_blocks: bool = True,
        orientation: Orientation = Orientation.horizontal,
        *,
        mirror_h: bool = False,
        mirror_v: bool = False,
    ):
        """Initialize terminal output.

        Args:
            color_mode: Use ANSI 24-bit colors
            use_half_blocks: Use half-block characters for double resolution
        """
        self.color_mode = color_mode
        self.use_half_blocks = use_half_blocks
        self.orientation = orientation
        self.mirror_h = mirror_h
        self.mirror_v = mirror_v
        self._first_frame = True
        self._last_height = 0

    def start(self) -> None:
        """Prepare terminal for output."""
        hide_cursor()
        clear_screen()
        self._first_frame = True

    def stop(self) -> None:
        """Restore terminal state."""
        show_cursor()
        print()

    def send_frame(self, frame: Frame) -> None:
        """Send a frame to the terminal."""
        oriented = apply_orientation(
            frame, self.orientation, mirror_h=self.mirror_h, mirror_v=self.mirror_v
        )

        if not self._first_frame and self._last_height > 0:
            move_cursor_up(self._last_height)

        print_frame(oriented, self.color_mode, self.use_half_blocks)

        height = len(oriented)
        self._last_height = height // 2 if self.use_half_blocks else height
        self._first_frame = False
