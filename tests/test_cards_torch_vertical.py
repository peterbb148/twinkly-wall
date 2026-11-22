"""Regression tests for the vertical flame and its rising embers."""

from types import SimpleNamespace

import pytest

from twinkly_wall.cards import CardContext, torch_vertical
from twinkly_wall.types import BLACK, PORTRAIT_HEIGHT, PORTRAIT_WIDTH, Frame


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    time = SimpleNamespace(now=0.0)
    monkeypatch.setattr(torch_vertical, "time", SimpleNamespace(monotonic=lambda: time.now))
    return time


def test_flame_has_a_hot_base_and_narrow_flickering_tips(clock: SimpleNamespace) -> None:
    card = torch_vertical.TorchVerticalCard({"duration": 1, "ember_density": 0})
    frames = card.frames(CardContext())
    initial, delay = next(frames)

    assert len(initial) == PORTRAIT_HEIGHT
    assert all(len(row) == PORTRAIT_WIDTH for row in initial)
    assert delay == pytest.approx(1 / 30)
    assert initial[0] == [BLACK] * PORTRAIT_WIDTH
    assert initial[-1][5][1] > 210

    first_lit_row = next(row for row in initial if any(pixel != BLACK for pixel in row))
    tip_width = sum(pixel != BLACK for pixel in first_lit_row)
    base_width = sum(pixel != BLACK for pixel in initial[-1])
    assert 0 < tip_width < base_width

    clock.now = 0.25
    flicker, _ = next(frames)
    assert flicker != initial
    clock.now = 1.0
    assert next(frames, None) is None


def test_ember_moves_up_and_dims(clock: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        torch_vertical,
        "random",
        SimpleNamespace(uniform=lambda low, high: (low + high) / 2, random=lambda: 0.8),
    )
    card = torch_vertical.TorchVerticalCard({"duration": 1, "ember_density": 1})
    frames = card.frames(CardContext())
    initial, _ = next(frames)
    clock.now = 0.5
    later, _ = next(frames)

    def ember(frame: Frame) -> tuple[int, int]:
        """Find the spark above the flame body."""
        (point,) = [
            (y, red)
            for y, row in enumerate(frame[:15])
            for red, green, blue in row
            if (red, green, blue) != BLACK
        ]
        return point

    first_y, first_red = ember(initial)
    later_y, later_red = ember(later)
    assert later_y < first_y
    assert 0 < later_red < first_red
