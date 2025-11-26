"""Base classes for the card system."""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from ..types import Frame


@dataclass
class CardContext:
    """Context passed to cards containing shared resources.

    Attributes:
        datasources: Dict of data source instances (weather, leaderboard, etc.)
        config: Card-specific configuration from cards.yaml
    """

    datasources: dict[str, Any] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)


class Card(ABC):
    """Abstract base class for display cards.

    Cards generate sequences of frames to be displayed on the LED matrix.
    Each card can produce static content or animations.
    """

    # Card type name used in configuration
    card_type: str = "base"

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the card with optional configuration.

        Args:
            config: Card-specific configuration dict
        """
        self.config = config or {}

    @abstractmethod
    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate frames for this card.

        Args:
            ctx: Card context with datasources and config

        Yields:
            Tuples of (frame, delay) where delay is seconds until next frame.
            A delay of 0 means show immediately and continue.
        """
        pass

    @property
    def duration(self) -> float:
        """Total duration this card should be displayed (seconds)."""
        return self.config.get("duration", 10.0)


# Card registry for dynamic card loading
_card_registry: dict[str, type[Card]] = {}


def register_card(card_class: type[Card]) -> type[Card]:
    """Decorator to register a card class in the registry.

    Usage:
        @register_card
        class MyCard(Card):
            card_type = "my_card"
            ...
    """
    _card_registry[card_class.card_type] = card_class
    return card_class


def get_card_class(card_type: str) -> type[Card] | None:
    """Look up a card class by its type name."""
    return _card_registry.get(card_type)


def list_card_types() -> list[str]:
    """Return list of all registered card type names."""
    return list(_card_registry.keys())


def create_card(card_type: str, config: dict[str, Any] | None = None) -> Card | None:
    """Create a card instance by type name.

    Args:
        card_type: The card type name (e.g., "clock", "text")
        config: Optional configuration dict for the card

    Returns:
        Card instance or None if type not found
    """
    card_class = get_card_class(card_type)
    if card_class is None:
        return None
    return card_class(config)
