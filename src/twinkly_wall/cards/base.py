"""Base classes for the card system."""

import os
import re
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml

from ..types import Frame, Orientation


@dataclass
class CardContext:
    """Context passed to cards containing shared resources.

    Attributes:
        datasources: Dict of data source instances (weather, leaderboard, etc.)
        config: Card-specific configuration from cards.yaml
        orientation: Effective display mount for cards that adapt to the wall
    """

    datasources: dict[str, Any] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)
    orientation: Orientation = Orientation.horizontal


class CardLayout(StrEnum):
    """Native canvas layout of a registered card."""

    landscape = "landscape"
    portrait = "portrait"
    adaptive = "adaptive"


class Card(ABC):
    """Abstract base class for display cards.

    Cards generate sequences of frames to be displayed on the LED matrix.
    Each card can produce static content or animations.
    """

    # Card type name used in configuration
    card_type: str = "base"
    layout = CardLayout.landscape

    @classmethod
    def get_layout(cls, config: dict[str, Any] | None = None) -> CardLayout:
        """Return the card's layout without initializing its renderer."""
        return cls.layout

    @classmethod
    def get_layout_source(cls, config: dict[str, Any] | None) -> dict[str, Any] | None:
        """Return the configured child card when it determines this card's layout."""
        return None

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the card with optional configuration.

        Args:
            config: Card-specific configuration dict
        """
        self.config = config or {}
        self.registered_name = self.card_type

    def replay_inputs(self) -> dict[str, Any] | None:
        """Return versioned inputs for replaying this instance after its first frame."""
        return None

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


@dataclass(frozen=True)
class CardDefinition:
    """A named configuration for an existing renderer."""

    renderer: str
    config: dict[str, Any]
    source: Path


def load_card_definitions() -> dict[str, CardDefinition]:
    """Discover cards in repository and user directories or an explicit override."""
    override = os.environ.get("TWINKLY_CARD_DIR")
    directories = (
        [Path(override).expanduser()]
        if override is not None
        else [
            Path.cwd() / "config" / "cards.d",
            Path.home() / ".config" / "twinkly-wall" / "cards.d",
        ]
    )
    sources = []
    for directory in dict.fromkeys(path.resolve() for path in directories):
        if override is None and not directory.exists():
            continue
        if not directory.is_dir():
            raise ValueError(
                f"Card definition directory does not exist or is not a directory: {directory}"
            )
        sources.extend(sorted(directory.iterdir()))

    definitions = {}
    for source in sources:
        if source.suffix not in {".yaml", ".yml"} or not source.is_file():
            continue
        name = source.stem
        if not re.fullmatch(r"[a-z][a-z0-9_-]*", name):
            raise ValueError(f"{source}: card name must use lowercase letters, digits, _, or -")
        if name in _card_registry:
            raise ValueError(f"{source}: card name '{name}' is already in use by a built-in card")
        if name in definitions:
            raise ValueError(
                f"{source}: card name '{name}' is already in use by {definitions[name].source}"
            )
        try:
            data = yaml.safe_load(source.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as error:
            raise ValueError(f"{source}: could not read card definition: {error}") from error
        if not isinstance(data, dict) or not all(isinstance(key, str) for key in data):
            raise ValueError(f"{source}: expected a YAML mapping with string keys")
        renderer = data.pop("type", None)
        if not isinstance(renderer, str) or renderer not in _card_registry:
            raise ValueError(f"{source}: 'type' must name a built-in card renderer")
        if renderer == "image":
            asset_path = data.get("path")
            if not isinstance(asset_path, str) or not asset_path:
                raise ValueError(f"{source}: image cards require an asset path")
            asset = (source.parent / asset_path).resolve()
            if not asset.is_file():
                raise ValueError(f"{source}: image does not exist: {asset}")
            data["path"] = str(asset)
        menu_path = data.get("menu_path")
        if renderer == "lunch_vertical" and isinstance(menu_path, str) and menu_path.strip():
            data["menu_path"] = str((source.parent / Path(menu_path).expanduser()).resolve())
        definitions[name] = CardDefinition(renderer, data, source.resolve())
    return definitions


def list_card_types(definitions: dict[str, CardDefinition] | None = None) -> list[str]:
    """Return the names of built-in renderers and external cards."""
    if definitions is None:
        definitions = load_card_definitions()
    return [*_card_registry, *definitions]


def get_card_layout(
    name: str, definitions: dict[str, CardDefinition], config: dict[str, Any] | None = None
) -> CardLayout:
    """Resolve a registered name's layout, including external and playlist options."""
    visited_sources: set[int] = set()
    while True:
        definition = definitions.get(name)
        if definition is not None:
            name = definition.renderer
            config = {**definition.config, **(config or {})}
        card_class = _card_registry[name]
        source = card_class.get_layout_source(config)
        if source is None:
            return card_class.get_layout(config)

        source_type = source.get("type")
        if not isinstance(source_type, str) or (
            source_type not in _card_registry and source_type not in definitions
        ):
            return card_class.get_layout(config)
        # Nested uses of the same renderer can still have distinct background configurations.
        if id(source) in visited_sources:
            raise ValueError(f"Circular card layout reference to '{source_type}'")
        visited_sources.add(id(source))
        name = source_type
        config = {key: value for key, value in source.items() if key != "type"}


def create_card(card_type: str, config: dict[str, Any] | None = None) -> Card | None:
    """Create a card instance by type name.

    Args:
        card_type: The card type name (e.g., "clock", "text")
        config: Optional configuration dict for the card

    Returns:
        Card instance or None if type not found
    """
    card_class = get_card_class(card_type)
    if card_class is not None:
        return card_class(config)
    definition = load_card_definitions().get(card_type)
    if definition is None:
        return None
    card = _card_registry[definition.renderer]({**definition.config, **(config or {})})
    card.registered_name = card_type
    return card
