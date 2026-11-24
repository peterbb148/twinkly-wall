"""Verify the chase variants through the card registry."""

import pytest

from twinkly_wall.cards import CardContext, create_card
from twinkly_wall.types import BLACK, CYAN, RED, WHITE, YELLOW, Frame


def _rows_with_color(frame: Frame, color: tuple[int, int, int]) -> list[int]:
    return [y for y, row in enumerate(frame) if color in row]


@pytest.mark.parametrize(
    "name,entry,exit_,step",
    [
        ("pacman_chase_up", 49, 0, -1),
        ("pacman_chase_down", 0, 49, 1),
    ],
)
def test_portrait_chase_sprites_and_direction(name, entry, exit_, step):
    card = create_card(name, {"speed": 30, "num_ghosts": 2, "ghost_colors": [RED, CYAN]})
    assert card is not None
    frames = [frame for frame, _ in card.frames(CardContext())]
    assert all(len(frame) == 50 and all(len(row) == 10 for row in frame) for frame in frames)

    pacman_frames = [
        (index, frame, rows)
        for index, frame in enumerate(frames)
        if (rows := _rows_with_color(frame, YELLOW))
    ]
    assert pacman_frames[0][2] == [entry]
    assert pacman_frames[-1][2] == [exit_]
    assert [_rows_with_color(frame, RED) for frame in frames if RED in frame[entry]][0] == [entry]

    open_mouth_frames = 0
    shared_frames = 0
    for index, frame, pacman_rows in pacman_frames:
        if 7 <= index <= 50:
            front = entry + step * (index - 1)
            back = front - step * 6
            assert frame[back][4] == YELLOW
            if frame[front][4] == BLACK:
                open_mouth_frames += 1

        ghost_rows = _rows_with_color(frame, RED)
        if len(ghost_rows) == 7:
            assert step * (pacman_rows[0] - ghost_rows[0]) > 0
            assert frame[ghost_rows[0] + 2][2] == WHITE
            assert frame[ghost_rows[-1]][2] == BLACK
            shared_frames += 1
    assert open_mouth_frames > 0
    assert shared_frames > 0
    assert any(_rows_with_color(frame, CYAN) == [exit_] for frame in frames)
    assert not any(RED in row or CYAN in row for row in frames[-1])


def test_existing_horizontal_chase_repeats():
    card = create_card("pacman_chase", {"speed": 30, "num_ghosts": 1, "repeats": 2})
    assert card is not None
    frames = [frame for frame, _ in card.frames(CardContext())]
    assert all(len(frame) == 10 and all(len(row) == 50 for row in frame) for frame in frames)
    cycle_length = len(frames) // 2
    for start in (0, cycle_length):
        assert any(row[-1] == YELLOW for row in frames[start + 3])
        assert any(row[0] == YELLOW for row in frames[start + 53])
