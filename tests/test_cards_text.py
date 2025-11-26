"""Tests for the text card."""

from twinkly_wall.cards.base import CardContext, create_card, get_card_class
from twinkly_wall.cards.text import TextCard
from twinkly_wall.types import BLACK, WHITE


class TestTextCard:
    """Tests for TextCard."""

    def test_registered(self):
        """TextCard should be registered."""
        assert get_card_class("text") is TextCard

    def test_create_via_registry(self):
        """Should create TextCard via registry."""
        card = create_card("text", {"text": "Hello"})
        assert card is not None
        assert isinstance(card, TextCard)

    def test_default_config(self):
        """Should have sensible defaults."""
        card = TextCard({"text": "Test"})
        assert card.text == "Test"
        assert card.color == WHITE
        assert card.bgcolor == BLACK
        assert card.scroll == "auto"
        assert card.scroll_speed == 30.0
        assert card.align == "center"

    def test_custom_config(self):
        """Should accept custom config."""
        card = TextCard(
            {
                "text": "Custom",
                "color": [255, 0, 0],
                "bgcolor": [0, 0, 255],
                "scroll": True,
                "scroll_speed": 50.0,
                "align": "left",
            }
        )
        assert card.text == "Custom"
        assert card.color == (255, 0, 0)
        assert card.bgcolor == (0, 0, 255)
        assert card.scroll is True
        assert card.scroll_speed == 50.0
        assert card.align == "left"

    def test_should_scroll_auto_short_text(self):
        """Auto scroll should be False for short text."""
        card = TextCard({"text": "Hi", "scroll": "auto"})
        assert card._should_scroll() is False

    def test_should_scroll_auto_long_text(self):
        """Auto scroll should be True for long text."""
        card = TextCard({"text": "This is a very long text message!", "scroll": "auto"})
        assert card._should_scroll() is True

    def test_should_scroll_forced(self):
        """Forced scroll should override auto."""
        card = TextCard({"text": "Hi", "scroll": True})
        assert card._should_scroll() is True

        card = TextCard({"text": "This is a very long text!", "scroll": False})
        assert card._should_scroll() is False

    def test_render_static_creates_frame(self):
        """Should render static text to a frame."""
        card = TextCard({"text": "Hi"})
        frame = card._render_static()

        # Should be full display size
        assert len(frame) == 10
        assert len(frame[0]) == 50

        # Should have some non-black pixels
        has_content = any(
            frame[y][x] != BLACK for y in range(len(frame)) for x in range(len(frame[0]))
        )
        assert has_content

    def test_render_static_with_bgcolor(self):
        """Should render with background color."""
        card = TextCard({"text": "A", "bgcolor": [0, 0, 255]})
        frame = card._render_static()

        # Background pixels should be blue
        # Check a corner that won't have text
        assert frame[0][0] == (0, 0, 255)

    def test_render_static_alignment_left(self):
        """Left alignment should place text at x=0."""
        card = TextCard({"text": "A", "align": "left", "color": [255, 0, 0]})
        frame = card._render_static()

        # First column area should have the text (red pixels)
        has_red_left = any(frame[y][x] == (255, 0, 0) for y in range(10) for x in range(5))
        assert has_red_left

    def test_render_static_alignment_right(self):
        """Right alignment should place text at right edge."""
        card = TextCard({"text": "A", "align": "right", "color": [255, 0, 0]})
        frame = card._render_static()

        # Right side should have the text (red pixels)
        has_red_right = any(frame[y][x] == (255, 0, 0) for y in range(10) for x in range(45, 50))
        assert has_red_right

    def test_render_scrolling_frame(self):
        """Should render scrolling frame at offset."""
        card = TextCard({"text": "Test"})
        content_width = 23  # "Test" width

        # At offset 0, text should be at right edge (x=50)
        frame = card._render_scrolling_frame(0, content_width)
        assert len(frame) == 10
        assert len(frame[0]) == 50

        # At offset 50, text should start at x=0
        frame = card._render_scrolling_frame(50, content_width)
        assert len(frame) == 10

    def test_frames_static(self):
        """Should generate static frames for short text."""
        card = TextCard({"text": "Hi", "duration": 0.5, "scroll": False})
        ctx = CardContext()

        frames = list(card.frames(ctx))
        assert len(frames) > 0

        # All frames should be the same for static
        first_frame = frames[0][0]
        for frame, delay in frames:
            assert frame == first_frame
            assert delay == 0.5

    def test_frames_scrolling(self):
        """Should generate scrolling frames for long text."""
        card = TextCard(
            {
                "text": "This is a long scrolling message!",
                "duration": 0.5,
                "scroll": True,
            }
        )
        ctx = CardContext()

        frames = list(card.frames(ctx))
        assert len(frames) > 0

        # Scrolling frames should have shorter delay
        for frame, delay in frames:
            assert len(frame) == 10
            assert len(frame[0]) == 50
            assert delay < 0.1  # ~30 FPS
