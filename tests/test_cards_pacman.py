"""Exercise portrait Pac-Man cards through the registry."""

import pytest

from twinkly_wall.cards import CardContext, create_card
from twinkly_wall.cards.pacman import THEMES
from twinkly_wall.types import GOLD, YELLOW, Frame


def _color_rows(frame: Frame, color: tuple[int, int, int]) -> set[int]:
    return {y for y, row in enumerate(frame) if color in row}


@pytest.mark.parametrize("name,first,last", [("pacman_up", 49, 0), ("pacman_down", 0, 49)])
def test_portrait_pacman_eats_upright_christmas_trees(name, first, last):
    card = create_card(name, {"speed": 30, "num_items": 2, "repeats": 2})
    assert card is not None
    frames = [frame for frame, _ in card.frames(CardContext())]
    middle = len(frames) // 2
    assert all(len(frame) == 50 and all(len(row) == 10 for row in frame) for frame in frames)
    for cycle in (frames[:middle], frames[middle:]):
        assert cycle[0] == frames[0]
        stars = _color_rows(cycle[0], GOLD)
        assert len(stars) == 2
        trunk = THEMES["trees"].color_map[2]
        assert _color_rows(cycle[0], trunk) == {y + offset for y in stars for offset in (7, 8)}
        for frame in cycle:
            assert _color_rows(frame, GOLD) <= stars
        assert not _color_rows(cycle[-1], GOLD)
        pacman = [rows for frame in cycle if (rows := _color_rows(frame, YELLOW))]
        assert pacman[0] == {first}
        assert pacman[-1] == {last}


@pytest.mark.parametrize("name", ["pacman_up", "pacman_down"])
def test_default_portrait_christmas_trees_do_not_overlap(name):
    card = create_card(name)
    assert card is not None
    frame, _ = next(card.frames(CardContext()))
    stars = _color_rows(frame, GOLD)
    trunk = THEMES["trees"].color_map[2]
    assert len(stars) == 4
    assert _color_rows(frame, trunk) == {y + offset for y in stars for offset in (7, 8)}
    assert len(_color_rows(frame, trunk)) == 8


def test_reverse_chase_catches_moving_ghosts_before_they_exit():
    card = create_card("pacman_chase_eat_ghosts", {"speed": 30})
    assert card is not None
    frames = [frame for frame, _ in card.frames(CardContext())]
    blue = THEMES["ghosts"].color_map[1]
    first_ghost_rows = _color_rows(frames[0], blue)
    assert len(first_ghost_rows) == 21
    assert _color_rows(frames[4], blue) == {y - 1 for y in first_ghost_rows}
    catches = []
    for start in (33, 23, 13):
        # Track the top of each ghost so partial overlap with Pac-Man does not count.
        catch = next(
            index for index, frame in enumerate(frames) if frame[start - index // 4][4] != blue
        )
        ghost_top = start - catch // 4
        assert ghost_top > 0
        assert ghost_top < min(_color_rows(frames[catch], YELLOW)) <= ghost_top + 7
        catches.append(catch)
    assert catches[0] < catches[1] < catches[2]
    assert not _color_rows(frames[-1], blue)
