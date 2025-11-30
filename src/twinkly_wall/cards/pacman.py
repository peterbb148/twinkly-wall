"""Pac-Man eating things animation card."""

import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from ..canvas import Canvas
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card

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
            1: (33, 33, 255),  # Blue ghost body (vulnerable/scared)
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
        theme: What to eat - trees, beer, hearts, snow, ghosts, dots (default: trees)
        pacman_color: RGB tuple for Pac-Man (default: yellow)
        speed: Pixels per second (default: 15)
        num_items: Number of items to place (default: 4)
        animation_complete: Wait for animation to complete before ending (default: true)
    """

    card_type = "pacman"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.theme_name: str = self.config.get("theme", "trees")
        self.theme: EdibleTheme = THEMES.get(self.theme_name, THEMES["trees"])
        self.pacman_color: RGB = tuple(self.config.get("pacman_color", PACMAN_COLOR))  # type: ignore
        self.speed: float = self.config.get("speed", 15.0)
        self.num_items: int = self.config.get("num_items", 4)
        self.animation_complete: bool = self.config.get("animation_complete", True)

    def _render_frame(
        self,
        pacman_x: float,
        mouth_open: bool,
        item_positions: list[int],
        eaten: set[int],
    ) -> Frame:
        """Render a single frame of the animation."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        # Draw items that haven't been eaten
        for i, ix in enumerate(item_positions):
            if i not in eaten:
                draw_sprite(
                    canvas,
                    self.theme.sprite,
                    ix,
                    self.theme.y_offset,
                    self.theme.color_map,
                )

        # Draw Pac-Man
        pacman_sprite = PACMAN_OPEN if mouth_open else PACMAN_CLOSED
        pacman_color_map = {1: self.pacman_color}
        draw_sprite(canvas, pacman_sprite, int(pacman_x), 1, pacman_color_map)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate Pac-Man animation frames."""
        # Calculate sprite width for spacing
        sprite_width = len(self.theme.sprite[0]) if self.theme.sprite else 7

        # Place items evenly across the display
        item_spacing = (WIDTH - sprite_width) // (self.num_items + 1)
        item_positions = [item_spacing * (i + 1) for i in range(self.num_items)]

        # Animation state
        pacman_x = -8.0  # Start off-screen left
        eaten: set[int] = set()
        mouth_open = True
        mouth_timer = 0.0
        animation_completed = False

        start_time = time.time()
        frame_delay = 1.0 / 30.0  # 30 FPS

        while True:
            # Check for eating items
            pacman_front = int(pacman_x) + 7  # Front of Pac-Man
            for i, ix in enumerate(item_positions):
                item_center = ix + sprite_width // 2
                if i not in eaten and pacman_front >= item_center:
                    eaten.add(i)

            # Render frame
            frame = self._render_frame(pacman_x, mouth_open, item_positions, eaten)
            yield frame, frame_delay

            # Update position
            pacman_x += self.speed * frame_delay

            # Loop when off-screen right
            if pacman_x > WIDTH:
                animation_completed = True
                pacman_x = -8.0
                eaten.clear()

            # Check exit conditions
            elapsed = time.time() - start_time
            if self.animation_complete:
                if animation_completed and elapsed >= self.duration:
                    break
            else:
                if elapsed >= self.duration:
                    break

            # Animate mouth (toggle every 0.15s)
            mouth_timer += frame_delay
            if mouth_timer >= 0.15:
                mouth_open = not mouth_open
                mouth_timer = 0.0
