"""Snake game animation card."""

import random
import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card

SNAKE_COLOR: RGB = (0, 255, 0)
SNAKE_HEAD_COLOR: RGB = (0, 200, 0)
FOOD_COLOR: RGB = (255, 0, 0)


@register_card
class SnakeCard(Card):
    """Classic Snake game animation.

    Config options:
        speed: Game speed multiplier (default: 1.0)
        initial_length: Starting snake length (default: 5)
    """

    card_type = "snake"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.speed: float = self.config.get("speed", 1.0)
        self.initial_length: int = self.config.get("initial_length", 5)

    def _spawn_food(self, snake: list[tuple[int, int]]) -> tuple[int, int]:
        """Spawn food at a random location not on the snake."""
        while True:
            x = random.randint(0, WIDTH - 1)
            y = random.randint(0, HEIGHT - 1)
            if (x, y) not in snake:
                return (x, y)

    def _render_frame(
        self, snake: list[tuple[int, int]], food: tuple[int, int]
    ) -> Frame:
        """Render the current game state."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        # Draw food
        canvas.set_pixel(food[0], food[1], FOOD_COLOR)

        # Draw snake
        for i, (x, y) in enumerate(snake):
            if 0 <= x < WIDTH and 0 <= y < HEIGHT:
                if i == 0:
                    canvas.set_pixel(x, y, SNAKE_HEAD_COLOR)
                else:
                    # Gradient from head to tail
                    brightness = int(255 * (1 - i / len(snake) * 0.5))
                    canvas.set_pixel(x, y, (0, brightness, 0))

        return canvas.copy()

    def _get_ai_direction(
        self,
        head: tuple[int, int],
        food: tuple[int, int],
        snake: list[tuple[int, int]],
        current_dir: tuple[int, int],
    ) -> tuple[int, int]:
        """Simple AI to move snake towards food."""
        hx, hy = head
        fx, fy = food
        dx, dy = current_dir

        # Possible directions (excluding reverse)
        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        # Remove reverse direction
        reverse = (-dx, -dy)
        if reverse in directions:
            directions.remove(reverse)

        # Score each direction
        best_dir = current_dir
        best_score = -1000

        for d in directions:
            new_x = hx + d[0]
            new_y = hy + d[1]

            # Skip if would hit wall
            if new_x < 0 or new_x >= WIDTH or new_y < 0 or new_y >= HEIGHT:
                continue

            # Skip if would hit self
            if (new_x, new_y) in snake[:-1]:
                continue

            # Score based on distance to food
            dist = abs(new_x - fx) + abs(new_y - fy)
            score = -dist

            if score > best_score:
                best_score = score
                best_dir = d

        return best_dir

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate Snake animation frames."""
        # Initialize snake in the middle
        start_x = WIDTH // 2
        start_y = HEIGHT // 2
        snake: list[tuple[int, int]] = [
            (start_x - i, start_y) for i in range(self.initial_length)
        ]
        direction = (1, 0)  # Moving right

        food = self._spawn_food(snake)

        start_time = time.time()
        frame_delay = 1.0 / (10 * self.speed)  # Snake moves slower than 30fps
        move_timer = 0.0

        while time.time() - start_time < self.duration:
            # Get AI direction
            direction = self._get_ai_direction(snake[0], food, snake, direction)

            # Move snake
            head_x, head_y = snake[0]
            new_head = (head_x + direction[0], head_y + direction[1])

            # Wrap around walls
            new_head = (new_head[0] % WIDTH, new_head[1] % HEIGHT)

            # Check self collision - reset if hit
            if new_head in snake:
                # Reset snake
                snake = [(start_x - i, start_y) for i in range(self.initial_length)]
                direction = (1, 0)
                food = self._spawn_food(snake)
            else:
                snake.insert(0, new_head)

                # Check food collision
                if new_head == food:
                    # Grow - don't remove tail
                    food = self._spawn_food(snake)
                else:
                    # Remove tail
                    snake.pop()

            frame = self._render_frame(snake, food)
            yield frame, frame_delay
