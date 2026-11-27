"""Pac-Man eating things animation card."""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Literal

from ..canvas import Canvas
from ..types import PORTRAIT_HEIGHT, PORTRAIT_WIDTH, RGB, WIDTH, Frame
from .base import Card, CardContext, CardLayout, register_card

# Pac-Man sprites (7x7) - mouth open and closed
PACMAN_OPEN: list[list[int]] = [
    [0, 0, 1, 1, 1, 0, 0],
    [0, 1, 1, 1, 1, 1, 0],
    [1, 1, 1, 1, 0, 0, 0],
    [1, 1, 1, 0, 0, 0, 0],
    [1, 1, 1, 1, 0, 0, 0],
    [0, 1, 1, 1, 1, 1, 0],
    [0, 0, 1, 1, 1, 0, 0],
]

PACMAN_OPEN_UP = [list(row) for row in zip(*(row[::-1] for row in PACMAN_OPEN), strict=True)]
PACMAN_OPEN_DOWN = [list(row) for row in zip(*reversed(PACMAN_OPEN), strict=True)]

PACMAN_CLOSED: list[list[int]] = [
    [0, 0, 1, 1, 1, 0, 0],
    [0, 1, 1, 1, 1, 1, 0],
    [1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1],
    [0, 1, 1, 1, 1, 1, 0],
    [0, 0, 1, 1, 1, 0, 0],
]

# Christmas tree sprite (7x9 with star)
SPRITE_TREE: list[list[int]] = [
    [0, 0, 0, 3, 0, 0, 0],  # 3 = star
    [0, 0, 0, 1, 0, 0, 0],
    [0, 0, 1, 1, 1, 0, 0],
    [0, 0, 1, 1, 1, 0, 0],
    [0, 1, 1, 1, 1, 1, 0],
    [0, 1, 1, 1, 1, 1, 0],
    [1, 1, 1, 1, 1, 1, 1],
    [0, 0, 0, 2, 0, 0, 0],  # 2 = trunk
    [0, 0, 0, 2, 0, 0, 0],
]

# Beer mug sprite (7x9)
SPRITE_BEER: list[list[int]] = [
    [0, 1, 0, 1, 0, 1, 0],  # Foam bubbles
    [1, 1, 1, 1, 1, 1, 1],  # Foam top
    [1, 2, 2, 2, 2, 2, 1],  # Beer
    [1, 2, 2, 2, 2, 2, 1],
    [1, 2, 2, 2, 2, 2, 3],  # 3 = handle
    [1, 2, 2, 2, 2, 2, 3],
    [1, 2, 2, 2, 2, 2, 3],
    [1, 2, 2, 2, 2, 2, 1],
    [1, 1, 1, 1, 1, 1, 1],  # Bottom
]

# Heart sprite (7x7)
SPRITE_HEART: list[list[int]] = [
    [0, 1, 1, 0, 1, 1, 0],
    [1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1],
    [0, 1, 1, 1, 1, 1, 0],
    [0, 0, 1, 1, 1, 0, 0],
    [0, 0, 0, 1, 0, 0, 0],
]

# Snowflake sprite (7x7)
SPRITE_SNOWFLAKE: list[list[int]] = [
    [0, 0, 1, 0, 1, 0, 0],
    [0, 0, 0, 1, 0, 0, 0],
    [1, 0, 1, 1, 1, 0, 1],
    [0, 1, 1, 1, 1, 1, 0],
    [1, 0, 1, 1, 1, 0, 1],
    [0, 0, 0, 1, 0, 0, 0],
    [0, 0, 1, 0, 1, 0, 0],
]

# Ghost sprite (7x7) - classic arcade ghost
SPRITE_GHOST: list[list[int]] = [
    [0, 0, 1, 1, 1, 0, 0],
    [0, 1, 1, 1, 1, 1, 0],
    [1, 2, 2, 1, 2, 2, 1],  # 2 = eyes
    [1, 2, 2, 1, 2, 2, 1],
    [1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1],
    [1, 0, 1, 0, 1, 0, 1],  # Wavy bottom
]

# Dot/pellet sprite (3x3)
SPRITE_DOT: list[list[int]] = [
    [0, 1, 0],
    [1, 1, 1],
    [0, 1, 0],
]

# Snowman sprite (7x9)
SPRITE_SNOWMAN: list[list[int]] = [
    [0, 0, 0, 2, 0, 0, 0],  # 2 = hat
    [0, 0, 2, 2, 2, 0, 0],  # hat brim
    [0, 0, 1, 1, 1, 0, 0],  # head
    [0, 0, 3, 1, 3, 0, 0],  # 3 = eyes
    [0, 0, 1, 4, 1, 0, 0],  # 4 = carrot nose
    [0, 1, 1, 1, 1, 1, 0],  # body top
    [0, 1, 5, 1, 5, 1, 0],  # 5 = buttons
    [1, 1, 1, 5, 1, 1, 1],  # body bottom
    [0, 1, 1, 1, 1, 1, 0],  # base
]

# Carlsberg Hop logo sprite (9x9) - three overlapping leaf shapes
SPRITE_HOP: list[list[int]] = [
    [0, 0, 0, 0, 1, 0, 0, 0, 0],  # top leaf tip
    [0, 0, 0, 1, 1, 1, 0, 0, 0],  # top leaf
    [0, 0, 1, 1, 1, 1, 1, 0, 0],  # top leaf base
    [0, 1, 1, 0, 1, 0, 1, 1, 0],  # side leaves start
    [1, 1, 1, 0, 0, 0, 1, 1, 1],  # side leaves middle
    [1, 1, 0, 0, 0, 0, 0, 1, 1],  # side leaves
    [1, 1, 0, 0, 0, 0, 0, 1, 1],  # side leaves
    [0, 1, 1, 0, 0, 0, 1, 1, 0],  # side leaves taper
    [0, 0, 1, 0, 0, 0, 1, 0, 0],  # side leaf tips
]


@dataclass
class EdibleTheme:
    """Theme configuration for edible objects."""

    sprite: list[list[int]]
    color_map: dict[int, RGB]
    y_offset: int = 0  # Vertical offset for positioning


# Pre-defined themes
THEMES: dict[str, EdibleTheme] = {
    "trees": EdibleTheme(
        sprite=SPRITE_TREE,
        color_map={
            1: (0, 180, 0),  # Green tree
            2: (139, 69, 19),  # Brown trunk
            3: (255, 215, 0),  # Gold star
        },
        y_offset=0,
    ),
    "beer": EdibleTheme(
        sprite=SPRITE_BEER,
        color_map={
            1: (255, 248, 220),  # Foam/mug (cream)
            2: (255, 198, 41),  # Beer gold
            3: (200, 200, 200),  # Handle (gray)
        },
        y_offset=0,
    ),
    "hearts": EdibleTheme(
        sprite=SPRITE_HEART,
        color_map={
            1: (255, 0, 80),  # Pink-red heart
        },
        y_offset=1,
    ),
    "snow": EdibleTheme(
        sprite=SPRITE_SNOWFLAKE,
        color_map={
            1: (200, 220, 255),  # Light blue-white
        },
        y_offset=1,
    ),
    "ghosts": EdibleTheme(
        sprite=SPRITE_GHOST,
        color_map={
            1: (0, 0, 139),  # Dark blue ghost body (vulnerable/scared)
            2: (255, 255, 255),  # White eyes
        },
        y_offset=1,
    ),
    "dots": EdibleTheme(
        sprite=SPRITE_DOT,
        color_map={
            1: (255, 255, 255),  # White dot
        },
        y_offset=3,
    ),
    "snowman": EdibleTheme(
        sprite=SPRITE_SNOWMAN,
        color_map={
            1: (255, 255, 255),  # White snow body
            2: (40, 40, 40),  # Black hat
            3: (0, 0, 0),  # Black eyes
            4: (255, 140, 0),  # Orange carrot nose
            5: (60, 60, 60),  # Dark buttons
        },
        y_offset=0,
    ),
    "hops": EdibleTheme(
        sprite=SPRITE_HOP,
        color_map={
            1: (40, 74, 65),  # Carlsberg green (#284a41)
            2: (60, 100, 60),  # Stem green
        },
        y_offset=0,
    ),
}

PACMAN_COLOR: RGB = (255, 255, 0)  # Yellow


def draw_sprite(
    canvas: Canvas,
    sprite: list[list[int]],
    x: int,
    y: int,
    color_map: dict[int, RGB],
) -> None:
    """Draw a sprite onto the canvas."""
    for sy, row in enumerate(sprite):
        for sx, pixel in enumerate(row):
            if pixel > 0 and pixel in color_map:
                canvas.set_pixel(x + sx, y + sy, color_map[pixel])


@register_card
class PacmanCard(Card):
    """Pac-Man eating things animation.

    Config options:
        theme: Name from THEMES (default: trees)
        pacman_color: RGB tuple for Pac-Man (default: yellow)
        speed: Pixels per second (default: 15)
        num_items: Number of items to place (default: 4)
        repeats: Number of complete passes (default: 1)
    """

    card_type = "pacman"
    portrait_direction: Literal["up", "down"] | None = None
    open_sprite = PACMAN_OPEN
    target_speed_ratio = 0.0

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.theme_name: str = self.config.get("theme", "trees")
        self.theme: EdibleTheme = THEMES.get(self.theme_name, THEMES["trees"])
        self.pacman_color: RGB = tuple(self.config.get("pacman_color", PACMAN_COLOR))  # type: ignore
        self.speed: float = self.config.get("speed", 15.0)
        self.num_items: int = self.config.get("num_items", 4)
        self.repeats: int = self.config.get("repeats", 1)

    def _sprite_position(
        self, position: int, sprite: list[list[int]], landscape_y: int
    ) -> tuple[int, int]:
        """Place a sprite along the travel axis while keeping its own orientation."""
        if self.portrait_direction is None:
            return position, landscape_y
        x = (PORTRAIT_WIDTH - len(sprite[0])) // 2
        y = (
            PORTRAIT_HEIGHT - len(sprite) - position
            if self.portrait_direction == "up"
            else position
        )
        return x, y

    def _render_frame(
        self,
        pacman_position: int,
        mouth_open: bool,
        item_positions: list[int],
        eaten: set[int],
    ) -> Frame:
        """Render a single frame of the animation."""
        canvas = Canvas(PORTRAIT_WIDTH, PORTRAIT_HEIGHT) if self.portrait_direction else Canvas()

        # Draw items that haven't been eaten
        for i, position in enumerate(item_positions):
            if i not in eaten:
                x, y = self._sprite_position(position, self.theme.sprite, self.theme.y_offset)
                draw_sprite(canvas, self.theme.sprite, x, y, self.theme.color_map)

        # Draw Pac-Man
        pacman_sprite = self.open_sprite if mouth_open else PACMAN_CLOSED
        pacman_color_map = {1: self.pacman_color}
        x, y = self._sprite_position(pacman_position, pacman_sprite, 1)
        draw_sprite(canvas, pacman_sprite, x, y, pacman_color_map)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate Pac-Man animation frames."""
        track_length = PORTRAIT_HEIGHT if self.portrait_direction else WIDTH
        sprite = self.theme.sprite
        sprite_length = len(sprite) if self.portrait_direction else len(sprite[0])
        item_spacing = (track_length - sprite_length) // (self.num_items + 1)
        first_item = item_spacing
        if (
            self.portrait_direction
            and self.target_speed_ratio == 0
            and item_spacing < sprite_length
        ):
            item_spacing = sprite_length
            first_item = max(0, (track_length - self.num_items * sprite_length) // 2)
        item_starts = [first_item + item_spacing * i for i in range(self.num_items)]

        # Animation state
        start = -8.0
        pacman_position = start
        eaten: set[int] = set()
        mouth_open = True
        mouth_timer = 0.0
        cycles_done = 0

        frame_delay = 1.0 / 30.0  # 30 FPS

        while cycles_done < self.repeats:
            # Check for eating items
            target_offset = int((pacman_position - start) * self.target_speed_ratio)
            item_positions = [position + target_offset for position in item_starts]
            pacman_front = int(pacman_position) + len(self.open_sprite)
            for i, position in enumerate(item_positions):
                item_center = position + sprite_length // 2
                if i not in eaten and pacman_front >= item_center:
                    eaten.add(i)

            # Render frame
            frame = self._render_frame(int(pacman_position), mouth_open, item_positions, eaten)
            yield frame, frame_delay

            # Update position
            pacman_position += self.speed * frame_delay

            # Loop after Pac-Man exits.
            if pacman_position > track_length:
                cycles_done += 1
                pacman_position = start
                eaten.clear()

            # Animate mouth (toggle every 0.15s)
            mouth_timer += frame_delay
            if mouth_timer >= 0.15:
                mouth_open = not mouth_open
                mouth_timer = 0.0


@register_card
class PacmanUpCard(PacmanCard):
    """Eat themed objects from the bottom to the top of a portrait wall."""

    card_type = "pacman_up"
    layout = CardLayout.portrait
    portrait_direction = "up"
    open_sprite = PACMAN_OPEN_UP


@register_card
class PacmanDownCard(PacmanCard):
    """Eat themed objects from the top to the bottom of a portrait wall."""

    card_type = "pacman_down"
    layout = CardLayout.portrait
    portrait_direction = "down"
    open_sprite = PACMAN_OPEN_DOWN


@register_card
class PacmanChaseEatGhostsCard(PacmanUpCard):
    """Catch and eat moving ghosts while travelling up a portrait wall."""

    card_type = "pacman_chase_eat_ghosts"
    target_speed_ratio = 0.25

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__({"num_items": 3, **(config or {}), "theme": "ghosts"})
