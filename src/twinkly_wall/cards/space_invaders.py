"""Space Invaders animation card."""

import random
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from ..canvas import Canvas
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card

# Invader sprite (5x4)
INVADER_SPRITE: list[list[int]] = [
    [0, 1, 0, 1, 0],
    [1, 1, 1, 1, 1],
    [1, 0, 1, 0, 1],
    [0, 1, 0, 1, 0],
]

# Ship sprite (5x2)
SHIP_SPRITE: list[list[int]] = [
    [0, 0, 1, 0, 0],
    [1, 1, 1, 1, 1],
]

INVADER_COLORS: list[RGB] = [
    (0, 255, 0),    # Green
    (0, 200, 255),  # Cyan
    (255, 100, 0),  # Orange
]

SHIP_COLOR: RGB = (0, 255, 100)
BULLET_COLOR: RGB = (255, 255, 0)
EXPLOSION_COLOR: RGB = (255, 100, 0)


@dataclass
class Invader:
    """An invader alien."""

    x: int
    y: int
    color: RGB
    alive: bool = True


@dataclass
class Bullet:
    """A bullet fired by the ship."""

    x: int
    y: float


@dataclass
class Explosion:
    """An explosion effect."""

    x: int
    y: int
    life: int = 5


@register_card
class SpaceInvadersCard(Card):
    """Space Invaders game animation.

    Config options:
        rows: Number of invader rows (default: 2)
        cols: Number of invader columns (default: 6)
        speed: Game speed multiplier (default: 1.0)
    """

    card_type = "space_invaders"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.rows: int = self.config.get("rows", 2)
        self.cols: int = self.config.get("cols", 6)
        self.speed: float = self.config.get("speed", 1.0)

    def _create_invaders(self) -> list[Invader]:
        """Create the invader grid."""
        invaders = []
        start_x = 2
        start_y = 0
        spacing_x = 7
        spacing_y = 5

        for row in range(self.rows):
            color = INVADER_COLORS[row % len(INVADER_COLORS)]
            for col in range(self.cols):
                invaders.append(
                    Invader(
                        x=start_x + col * spacing_x,
                        y=start_y + row * spacing_y,
                        color=color,
                    )
                )
        return invaders

    def _draw_sprite(
        self, canvas: Canvas, sprite: list[list[int]], x: int, y: int, color: RGB
    ) -> None:
        """Draw a sprite on the canvas."""
        for sy, row in enumerate(sprite):
            for sx, pixel in enumerate(row):
                if pixel:
                    px, py = x + sx, y + sy
                    if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                        canvas.set_pixel(px, py, color)

    def _render_frame(
        self,
        invaders: list[Invader],
        ship_x: int,
        bullets: list[Bullet],
        explosions: list[Explosion],
    ) -> Frame:
        """Render the current game state."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        # Draw invaders
        for inv in invaders:
            if inv.alive:
                self._draw_sprite(canvas, INVADER_SPRITE, inv.x, inv.y, inv.color)

        # Draw ship
        self._draw_sprite(canvas, SHIP_SPRITE, ship_x, HEIGHT - 2, SHIP_COLOR)

        # Draw bullets
        for bullet in bullets:
            if 0 <= int(bullet.y) < HEIGHT:
                canvas.set_pixel(bullet.x, int(bullet.y), BULLET_COLOR)

        # Draw explosions
        for exp in explosions:
            brightness = int(255 * (exp.life / 5))
            color = (brightness, brightness // 3, 0)
            canvas.set_pixel(exp.x, exp.y, color)
            # Expand explosion
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                px, py = exp.x + dx, exp.y + dy
                if 0 <= px < WIDTH and 0 <= py < HEIGHT and exp.life > 2:
                    canvas.set_pixel(px, py, (brightness // 2, brightness // 6, 0))

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate Space Invaders animation frames."""
        invaders = self._create_invaders()
        ship_x = WIDTH // 2 - 2
        ship_dir = 1
        bullets: list[Bullet] = []
        explosions: list[Explosion] = []

        invader_dir = 1
        invader_move_timer = 0
        invader_move_interval = 15

        shoot_timer = 0
        shoot_interval = 20

        start_time = time.time()
        frame_delay = 1.0 / 30.0

        while time.time() - start_time < self.duration:
            # Move ship
            ship_x += ship_dir
            if ship_x <= 0 or ship_x >= WIDTH - 5:
                ship_dir = -ship_dir

            # Move invaders
            invader_move_timer += 1
            if invader_move_timer >= invader_move_interval / self.speed:
                invader_move_timer = 0
                # Check if any invader hits edge
                hit_edge = False
                for inv in invaders:
                    if inv.alive:
                        if inv.x + invader_dir < 0 or inv.x + invader_dir > WIDTH - 5:
                            hit_edge = True
                            break

                if hit_edge:
                    invader_dir = -invader_dir
                    for inv in invaders:
                        inv.y += 1
                else:
                    for inv in invaders:
                        inv.x += invader_dir

            # Shoot
            shoot_timer += 1
            if shoot_timer >= shoot_interval / self.speed:
                shoot_timer = 0
                bullets.append(Bullet(x=ship_x + 2, y=HEIGHT - 3))

            # Move bullets
            for bullet in bullets:
                bullet.y -= 0.5 * self.speed

            # Check collisions
            for bullet in bullets[:]:
                for inv in invaders:
                    if inv.alive:
                        if (
                            inv.x <= bullet.x < inv.x + 5
                            and inv.y <= bullet.y < inv.y + 4
                        ):
                            inv.alive = False
                            bullets.remove(bullet)
                            explosions.append(Explosion(x=bullet.x, y=int(bullet.y)))
                            break

            # Remove off-screen bullets
            bullets = [b for b in bullets if b.y >= 0]

            # Update explosions
            for exp in explosions:
                exp.life -= 1
            explosions = [e for e in explosions if e.life > 0]

            # Respawn invaders if all dead
            if not any(inv.alive for inv in invaders):
                invaders = self._create_invaders()

            frame = self._render_frame(invaders, ship_x, bullets, explosions)
            yield frame, frame_delay
