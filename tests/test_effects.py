"""Tests for visual effects."""

from twinkly_wall.effects import (
    crossfade,
    fade_in,
    fade_out,
    scroll_left,
    scroll_right,
    slide_in_left,
    slide_in_right,
    wipe_left,
    wipe_right,
)
from twinkly_wall.types import BLACK, WHITE


def make_frame(width: int, height: int, color: tuple[int, int, int] = WHITE):
    """Helper to create a solid-color frame."""
    return [[color for _ in range(width)] for _ in range(height)]


class TestFadeIn:
    """Tests for fade_in effect."""

    def test_fade_in_starts_black(self):
        """First frame should be black."""
        frame = make_frame(5, 3, WHITE)
        frames = list(fade_in(frame, steps=5))

        first = frames[0]
        assert all(first[y][x] == BLACK for y in range(3) for x in range(5))

    def test_fade_in_ends_at_target(self):
        """Last frame should be the target."""
        frame = make_frame(5, 3, WHITE)
        frames = list(fade_in(frame, steps=5))

        last = frames[-1]
        assert all(last[y][x] == WHITE for y in range(3) for x in range(5))

    def test_fade_in_step_count(self):
        """Should produce steps+1 frames."""
        frame = make_frame(5, 3)
        frames = list(fade_in(frame, steps=10))
        assert len(frames) == 11

    def test_fade_in_brightness_increases(self):
        """Brightness should increase with each step."""
        frame = make_frame(2, 2, (100, 100, 100))
        frames = list(fade_in(frame, steps=5))

        # Get brightness of first pixel in each frame
        brightnesses = [f[0][0][0] for f in frames]

        # Should be monotonically increasing
        for i in range(1, len(brightnesses)):
            assert brightnesses[i] >= brightnesses[i - 1]


class TestFadeOut:
    """Tests for fade_out effect."""

    def test_fade_out_starts_at_source(self):
        """First frame should be the source."""
        frame = make_frame(5, 3, WHITE)
        frames = list(fade_out(frame, steps=5))

        first = frames[0]
        assert all(first[y][x] == WHITE for y in range(3) for x in range(5))

    def test_fade_out_ends_black(self):
        """Last frame should be black."""
        frame = make_frame(5, 3, WHITE)
        frames = list(fade_out(frame, steps=5))

        last = frames[-1]
        assert all(last[y][x] == BLACK for y in range(3) for x in range(5))

    def test_fade_out_brightness_decreases(self):
        """Brightness should decrease with each step."""
        frame = make_frame(2, 2, (100, 100, 100))
        frames = list(fade_out(frame, steps=5))

        brightnesses = [f[0][0][0] for f in frames]

        # Should be monotonically decreasing
        for i in range(1, len(brightnesses)):
            assert brightnesses[i] <= brightnesses[i - 1]


class TestCrossfade:
    """Tests for crossfade effect."""

    def test_crossfade_starts_at_from(self):
        """First frame should be the from_frame."""
        from_frame = make_frame(5, 3, (255, 0, 0))
        to_frame = make_frame(5, 3, (0, 255, 0))
        frames = list(crossfade(from_frame, to_frame, steps=5))

        first = frames[0]
        assert all(first[y][x] == (255, 0, 0) for y in range(3) for x in range(5))

    def test_crossfade_ends_at_to(self):
        """Last frame should be the to_frame."""
        from_frame = make_frame(5, 3, (255, 0, 0))
        to_frame = make_frame(5, 3, (0, 255, 0))
        frames = list(crossfade(from_frame, to_frame, steps=5))

        last = frames[-1]
        assert all(last[y][x] == (0, 255, 0) for y in range(3) for x in range(5))

    def test_crossfade_midpoint(self):
        """Midpoint should be blended."""
        from_frame = make_frame(2, 2, (0, 0, 0))
        to_frame = make_frame(2, 2, (100, 100, 100))
        frames = list(crossfade(from_frame, to_frame, steps=2))

        # Middle frame (step 1 of 2) should be ~50% blend
        mid = frames[1]
        assert mid[0][0] == (50, 50, 50)


class TestScrollLeft:
    """Tests for scroll_left effect."""

    def test_scroll_left_produces_frames(self):
        """Should produce frames for scrolling."""
        content = make_frame(10, 3, WHITE)
        frames = list(scroll_left(content, viewport_width=5, start_off_screen=False))

        assert len(frames) > 0

    def test_scroll_left_viewport_size(self):
        """Output frames should match viewport width."""
        content = make_frame(10, 3, WHITE)
        frames = list(scroll_left(content, viewport_width=5))

        for frame in frames:
            assert len(frame[0]) == 5
            assert len(frame) == 3

    def test_scroll_left_start_off_screen(self):
        """With start_off_screen, first frame should be black."""
        content = make_frame(10, 3, WHITE)
        frames = list(scroll_left(content, viewport_width=5, start_off_screen=True))

        first = frames[0]
        assert all(first[y][x] == BLACK for y in range(3) for x in range(5))


class TestScrollRight:
    """Tests for scroll_right effect."""

    def test_scroll_right_produces_frames(self):
        """Should produce frames for scrolling."""
        content = make_frame(10, 3, WHITE)
        frames = list(scroll_right(content, viewport_width=5, start_off_screen=False))

        assert len(frames) > 0

    def test_scroll_right_viewport_size(self):
        """Output frames should match viewport width."""
        content = make_frame(10, 3, WHITE)
        frames = list(scroll_right(content, viewport_width=5))

        for frame in frames:
            assert len(frame[0]) == 5
            assert len(frame) == 3


class TestSlideInLeft:
    """Tests for slide_in_left effect."""

    def test_slide_in_left_first_black(self):
        """First frame should be black."""
        frame = make_frame(10, 3, WHITE)
        frames = list(slide_in_left(frame))

        first = frames[0]
        assert all(first[y][x] == BLACK for y in range(3) for x in range(10))

    def test_slide_in_left_last_full(self):
        """Last frame should be the full source."""
        frame = make_frame(10, 3, WHITE)
        frames = list(slide_in_left(frame))

        last = frames[-1]
        assert all(last[y][x] == WHITE for y in range(3) for x in range(10))


class TestSlideInRight:
    """Tests for slide_in_right effect."""

    def test_slide_in_right_first_black(self):
        """First frame should be black."""
        frame = make_frame(10, 3, WHITE)
        frames = list(slide_in_right(frame))

        first = frames[0]
        assert all(first[y][x] == BLACK for y in range(3) for x in range(10))

    def test_slide_in_right_last_full(self):
        """Last frame should be the full source."""
        frame = make_frame(10, 3, WHITE)
        frames = list(slide_in_right(frame))

        last = frames[-1]
        assert all(last[y][x] == WHITE for y in range(3) for x in range(10))


class TestWipeLeft:
    """Tests for wipe_left effect."""

    def test_wipe_left_starts_with_from(self):
        """First frame should be from_frame."""
        from_frame = make_frame(10, 3, (255, 0, 0))
        to_frame = make_frame(10, 3, (0, 255, 0))
        frames = list(wipe_left(from_frame, to_frame))

        first = frames[0]
        assert all(first[y][x] == (255, 0, 0) for y in range(3) for x in range(10))

    def test_wipe_left_ends_with_to(self):
        """Last frame should be to_frame."""
        from_frame = make_frame(10, 3, (255, 0, 0))
        to_frame = make_frame(10, 3, (0, 255, 0))
        frames = list(wipe_left(from_frame, to_frame))

        last = frames[-1]
        assert all(last[y][x] == (0, 255, 0) for y in range(3) for x in range(10))


class TestWipeRight:
    """Tests for wipe_right effect."""

    def test_wipe_right_starts_with_from(self):
        """First frame should be from_frame."""
        from_frame = make_frame(10, 3, (255, 0, 0))
        to_frame = make_frame(10, 3, (0, 255, 0))
        frames = list(wipe_right(from_frame, to_frame))

        first = frames[0]
        assert all(first[y][x] == (255, 0, 0) for y in range(3) for x in range(10))

    def test_wipe_right_ends_with_to(self):
        """Last frame should be to_frame."""
        from_frame = make_frame(10, 3, (255, 0, 0))
        to_frame = make_frame(10, 3, (0, 255, 0))
        frames = list(wipe_right(from_frame, to_frame))

        last = frames[-1]
        assert all(last[y][x] == (0, 255, 0) for y in range(3) for x in range(10))
