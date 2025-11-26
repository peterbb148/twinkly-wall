"""Tests for the card base classes and registry."""

from collections.abc import Iterator

from twinkly_wall.cards.base import (
    Card,
    CardContext,
    create_card,
    get_card_class,
    list_card_types,
    register_card,
)
from twinkly_wall.types import BLACK, Frame


class TestCardContext:
    """Tests for CardContext."""

    def test_default_empty(self):
        """CardContext should have empty defaults."""
        ctx = CardContext()
        assert ctx.datasources == {}
        assert ctx.config == {}

    def test_with_datasources(self):
        """CardContext should accept datasources."""
        ctx = CardContext(datasources={"weather": "mock_weather"})
        assert ctx.datasources["weather"] == "mock_weather"

    def test_with_config(self):
        """CardContext should accept config."""
        ctx = CardContext(config={"brightness": 100})
        assert ctx.config["brightness"] == 100


class TestCardRegistry:
    """Tests for card registry functions."""

    def test_register_and_get_card(self):
        """Should register and retrieve card classes."""

        @register_card
        class TestCard(Card):
            card_type = "test_card_unique_1"

            def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
                yield [[(0, 0, 0)]], 0.0

        assert get_card_class("test_card_unique_1") is TestCard

    def test_get_unknown_card(self):
        """Should return None for unknown card types."""
        assert get_card_class("nonexistent_card_type") is None

    def test_list_card_types(self):
        """Should list registered card types."""

        @register_card
        class AnotherTestCard(Card):
            card_type = "test_card_unique_2"

            def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
                yield [[(0, 0, 0)]], 0.0

        types = list_card_types()
        assert "test_card_unique_2" in types

    def test_create_card(self):
        """Should create card instances by type."""

        @register_card
        class CreateTestCard(Card):
            card_type = "test_card_unique_3"

            def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
                yield [[(0, 0, 0)]], 0.0

        card = create_card("test_card_unique_3")
        assert card is not None
        assert isinstance(card, CreateTestCard)

    def test_create_card_with_config(self):
        """Should pass config to created card."""

        @register_card
        class ConfigTestCard(Card):
            card_type = "test_card_unique_4"

            def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
                yield [[(0, 0, 0)]], 0.0

        card = create_card("test_card_unique_4", {"duration": 20})
        assert card is not None
        assert card.config["duration"] == 20

    def test_create_unknown_card(self):
        """Should return None for unknown card types."""
        card = create_card("totally_unknown_card")
        assert card is None


class TestCard:
    """Tests for Card base class."""

    def test_default_duration(self):
        """Card should have default duration of 10 seconds."""

        @register_card
        class DurationTestCard(Card):
            card_type = "test_card_unique_5"

            def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
                yield [[(0, 0, 0)]], 0.0

        card = DurationTestCard()
        assert card.duration == 10.0

    def test_custom_duration(self):
        """Card should respect duration from config."""

        @register_card
        class CustomDurationCard(Card):
            card_type = "test_card_unique_6"

            def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
                yield [[(0, 0, 0)]], 0.0

        card = CustomDurationCard({"duration": 30})
        assert card.duration == 30

    def test_frames_generator(self):
        """Card frames() should yield frame tuples."""

        @register_card
        class FramesTestCard(Card):
            card_type = "test_card_unique_7"

            def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
                frame: Frame = [[BLACK for _ in range(5)] for _ in range(3)]
                yield frame, 0.1
                yield frame, 0.2

        card = FramesTestCard()
        ctx = CardContext()
        frame_list = list(card.frames(ctx))

        assert len(frame_list) == 2
        assert frame_list[0][1] == 0.1
        assert frame_list[1][1] == 0.2
