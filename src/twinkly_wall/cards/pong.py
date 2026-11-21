"""Pong game animation card."""

import random
import time
from collections.abc import Iterator
from typing import Any

from ..canvas import Canvas
from ..types import BLACK, HEIGHT, RGB, WIDTH, Frame
from .base import Card, CardContext, register_card

PADDLE_COLOR: RGB = (255, 255, 255)
BALL_COLOR: RGB = (255, 255, 0)
SCORE_COLOR: RGB = (100, 100, 100)


@register_card
class PongCard(Card):
    """Classic Pong game animation.

    Config options:
        ball_speed: Ball speed multiplier (default: 1.0)
        paddle_height: Height of paddles (default: 4)
        ai_skill: AI reaction speed 0-1 (default: 0.8)
    """

    card_type = "pong"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.ball_speed: float = self.config.get("ball_speed", 1.0)
        self.paddle_height: int = self.config.get("paddle_height", 4)
        self.ai_skill: float = self.config.get("ai_skill", 0.8)

    def _render_frame(
        self,
        ball_x: float,
        ball_y: float,
        paddle1_y: int,
        paddle2_y: int,
        score1: int,
        score2: int,
    ) -> Frame:
        """Render the current game state."""
        canvas = Canvas(WIDTH, HEIGHT)
        canvas.clear(BLACK)

        # Draw center line (dashed)
        for y in range(0, HEIGHT, 2):
            canvas.set_pixel(WIDTH // 2, y, (50, 50, 50))

        # Draw paddles
        for y in range(self.paddle_height):
            # Left paddle
            py = paddle1_y + y
            if 0 <= py < HEIGHT:
                canvas.set_pixel(1, py, PADDLE_COLOR)
            # Right paddle
            py = paddle2_y + y
            if 0 <= py < HEIGHT:
                canvas.set_pixel(WIDTH - 2, py, PADDLE_COLOR)

        # Draw ball
        bx, by = int(ball_x), int(ball_y)
        if 0 <= bx < WIDTH and 0 <= by < HEIGHT:
            canvas.set_pixel(bx, by, BALL_COLOR)

        return canvas.copy()

    def frames(self, ctx: CardContext) -> Iterator[tuple[Frame, float]]:
        """Generate Pong animation frames."""
        # Game state
        ball_x = WIDTH / 2.0
        ball_y = HEIGHT / 2.0
        ball_vx = random.choice([-1, 1]) * 0.5 * self.ball_speed
        ball_vy = random.uniform(-0.3, 0.3) * self.ball_speed

        paddle1_y = HEIGHT // 2 - self.paddle_height // 2
        paddle2_y = HEIGHT // 2 - self.paddle_height // 2

        score1 = 0
        score2 = 0

        start_time = time.time()
        frame_delay = 1.0 / 30.0

        while time.time() - start_time < self.duration:
            # Move ball
            ball_x += ball_vx
            ball_y += ball_vy

            # Ball collision with top/bottom
            if ball_y <= 0 or ball_y >= HEIGHT - 1:
                ball_vy = -ball_vy
                ball_y = max(0, min(HEIGHT - 1, ball_y))

            # Ball collision with paddles
            # Left paddle
            if ball_x <= 2 and paddle1_y <= ball_y < paddle1_y + self.paddle_height:
                ball_vx = abs(ball_vx)  # Bounce right
                # Add spin based on where ball hit paddle
                hit_pos = (ball_y - paddle1_y) / self.paddle_height
                ball_vy = (hit_pos - 0.5) * 0.5

            # Right paddle
            if ball_x >= WIDTH - 3 and paddle2_y <= ball_y < paddle2_y + self.paddle_height:
                ball_vx = -abs(ball_vx)  # Bounce left
                hit_pos = (ball_y - paddle2_y) / self.paddle_height
                ball_vy = (hit_pos - 0.5) * 0.5

            # Score and reset
            if ball_x < 0:
                score2 += 1
                ball_x = WIDTH / 2.0
                ball_y = HEIGHT / 2.0
                ball_vx = 0.5 * self.ball_speed
                ball_vy = random.uniform(-0.3, 0.3) * self.ball_speed
            elif ball_x >= WIDTH:
                score1 += 1
                ball_x = WIDTH / 2.0
                ball_y = HEIGHT / 2.0
                ball_vx = -0.5 * self.ball_speed
                ball_vy = random.uniform(-0.3, 0.3) * self.ball_speed

            # AI paddle movement (both paddles are AI)
            # Left paddle
            target_y = ball_y - self.paddle_height // 2
            if random.random() < self.ai_skill:
                if paddle1_y < target_y:
                    paddle1_y = min(HEIGHT - self.paddle_height, paddle1_y + 1)
                elif paddle1_y > target_y:
                    paddle1_y = max(0, paddle1_y - 1)

            # Right paddle
            if random.random() < self.ai_skill:
                if paddle2_y < target_y:
                    paddle2_y = min(HEIGHT - self.paddle_height, paddle2_y + 1)
                elif paddle2_y > target_y:
                    paddle2_y = max(0, paddle2_y - 1)

            frame = self._render_frame(ball_x, ball_y, paddle1_y, paddle2_y, score1, score2)
            yield frame, frame_delay
