"""Visual effects for frame transitions and animations."""

from collections.abc import Iterator

from .types import Frame, blend_color, scale_color


def fade_in(frame: Frame, steps: int = 10) -> Iterator[Frame]:
    """Fade a frame in from black.

    Args:
        frame: The target frame to fade to
        steps: Number of steps in the fade (default: 10)

    Yields:
        Frames progressing from black to the target frame
    """
    height = len(frame)
    width = len(frame[0]) if height > 0 else 0

    for step in range(steps + 1):
        factor = step / steps
        result: Frame = []
        for y in range(height):
            row = []
            for x in range(width):
                row.append(scale_color(frame[y][x], factor))
            result.append(row)
        yield result


def fade_out(frame: Frame, steps: int = 10) -> Iterator[Frame]:
    """Fade a frame out to black.

    Args:
        frame: The source frame to fade from
        steps: Number of steps in the fade (default: 10)

    Yields:
        Frames progressing from the source frame to black
    """
    height = len(frame)
    width = len(frame[0]) if height > 0 else 0

    for step in range(steps + 1):
        factor = 1.0 - (step / steps)
        result: Frame = []
        for y in range(height):
            row = []
            for x in range(width):
                row.append(scale_color(frame[y][x], factor))
            result.append(row)
        yield result


def crossfade(from_frame: Frame, to_frame: Frame, steps: int = 10) -> Iterator[Frame]:
    """Crossfade between two frames.

    Args:
        from_frame: The starting frame
        to_frame: The ending frame
        steps: Number of steps in the crossfade (default: 10)

    Yields:
        Frames blending from from_frame to to_frame
    """
    height = len(from_frame)
    width = len(from_frame[0]) if height > 0 else 0

    for step in range(steps + 1):
        alpha = step / steps
        result: Frame = []
        for y in range(height):
            row = []
            for x in range(width):
                row.append(blend_color(from_frame[y][x], to_frame[y][x], alpha))
            result.append(row)
        yield result


def scroll_left(
    content: Frame,
    viewport_width: int,
    start_off_screen: bool = True,
) -> Iterator[Frame]:
    """Scroll content from right to left through a viewport.

    Args:
        content: The content frame (can be wider than viewport)
        viewport_width: Width of the visible viewport
        start_off_screen: If True, content starts off-screen to the right

    Yields:
        Frames showing the content scrolling left
    """
    height = len(content)
    content_width = len(content[0]) if height > 0 else 0

    # Calculate scroll range
    if start_off_screen:
        start_offset = -viewport_width
        end_offset = content_width
    else:
        start_offset = 0
        end_offset = max(0, content_width - viewport_width)

    for offset in range(start_offset, end_offset + 1):
        result: Frame = []
        for y in range(height):
            row = []
            for vx in range(viewport_width):
                cx = vx + offset  # Content x position
                if 0 <= cx < content_width:
                    row.append(content[y][cx])
                else:
                    row.append((0, 0, 0))  # Black for off-screen
            result.append(row)
        yield result


def scroll_right(
    content: Frame,
    viewport_width: int,
    start_off_screen: bool = True,
) -> Iterator[Frame]:
    """Scroll content from left to right through a viewport.

    Args:
        content: The content frame (can be wider than viewport)
        viewport_width: Width of the visible viewport
        start_off_screen: If True, content starts off-screen to the left

    Yields:
        Frames showing the content scrolling right
    """
    height = len(content)
    content_width = len(content[0]) if height > 0 else 0

    # Calculate scroll range (reverse of scroll_left)
    if start_off_screen:
        start_offset = content_width
        end_offset = -viewport_width
    else:
        start_offset = max(0, content_width - viewport_width)
        end_offset = 0

    for offset in range(start_offset, end_offset - 1, -1):
        result: Frame = []
        for y in range(height):
            row = []
            for vx in range(viewport_width):
                cx = vx + offset
                if 0 <= cx < content_width:
                    row.append(content[y][cx])
                else:
                    row.append((0, 0, 0))
            result.append(row)
        yield result


def slide_in_left(frame: Frame, steps: int | None = None) -> Iterator[Frame]:
    """Slide a frame in from the left edge.

    Args:
        frame: The frame to slide in
        steps: Number of steps (default: frame width)

    Yields:
        Frames showing the slide animation
    """
    height = len(frame)
    width = len(frame[0]) if height > 0 else 0

    if steps is None:
        steps = width

    for step in range(steps + 1):
        visible_width = int((step / steps) * width)
        result: Frame = []
        for y in range(height):
            row = []
            for x in range(width):
                if x < visible_width:
                    # Show pixel from the right side of the source
                    src_x = width - visible_width + x
                    row.append(frame[y][src_x])
                else:
                    row.append((0, 0, 0))
            result.append(row)
        yield result


def slide_in_right(frame: Frame, steps: int | None = None) -> Iterator[Frame]:
    """Slide a frame in from the right edge.

    Args:
        frame: The frame to slide in
        steps: Number of steps (default: frame width)

    Yields:
        Frames showing the slide animation
    """
    height = len(frame)
    width = len(frame[0]) if height > 0 else 0

    if steps is None:
        steps = width

    for step in range(steps + 1):
        visible_width = int((step / steps) * width)
        result: Frame = []
        for y in range(height):
            row = []
            for x in range(width):
                if x >= width - visible_width:
                    # Show pixel from the left side of the source
                    src_x = x - (width - visible_width)
                    row.append(frame[y][src_x])
                else:
                    row.append((0, 0, 0))
            result.append(row)
        yield result


def wipe_left(from_frame: Frame, to_frame: Frame, steps: int | None = None) -> Iterator[Frame]:
    """Wipe transition from right to left.

    Args:
        from_frame: The starting frame
        to_frame: The ending frame
        steps: Number of steps (default: frame width)

    Yields:
        Frames showing the wipe transition
    """
    height = len(from_frame)
    width = len(from_frame[0]) if height > 0 else 0

    if steps is None:
        steps = width

    for step in range(steps + 1):
        boundary = int((step / steps) * width)
        result: Frame = []
        for y in range(height):
            row = []
            for x in range(width):
                if x < boundary:
                    row.append(to_frame[y][x])
                else:
                    row.append(from_frame[y][x])
            result.append(row)
        yield result


def wipe_right(from_frame: Frame, to_frame: Frame, steps: int | None = None) -> Iterator[Frame]:
    """Wipe transition from left to right.

    Args:
        from_frame: The starting frame
        to_frame: The ending frame
        steps: Number of steps (default: frame width)

    Yields:
        Frames showing the wipe transition
    """
    height = len(from_frame)
    width = len(from_frame[0]) if height > 0 else 0

    if steps is None:
        steps = width

    for step in range(steps + 1):
        boundary = width - int((step / steps) * width)
        result: Frame = []
        for y in range(height):
            row = []
            for x in range(width):
                if x >= boundary:
                    row.append(to_frame[y][x])
                else:
                    row.append(from_frame[y][x])
            result.append(row)
        yield result
