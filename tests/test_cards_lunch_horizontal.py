"""Check the dated horizontal lunch playlist and the pixels it renders."""

from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from twinkly_wall.canvas import Canvas
from twinkly_wall.cards import CardContext, create_card
from twinkly_wall.cards.base import CardLayout
from twinkly_wall.config import load_playlist
from twinkly_wall.fonts import CHAR_SPACING, CHAR_WIDTH, draw_text, text_width
from twinkly_wall.types import BLACK, HEIGHT, WIDTH

_PLAYLIST = Path(__file__).resolve().parents[1] / "config/lunch-horizontal.yaml"
_BROWN = (180, 116, 62)
_GREEN = (0, 128, 0)


@pytest.mark.parametrize(
    ("day", "meal"),
    [
        ("2026-11-30", "Green Thai Curry with Veggies and Rice"),
        ("2026-12-01", "Gyros with Pork and Pita"),
        ("2026-12-02", "Pork Meatloaf with Sauce & Potatoes"),
        ("2026-12-03", "Tortellini with Ricotta, Spinach, Creamy Sauce and Chicken"),
        ("2026-12-04", "Turkey Meatballs in Curry with Rice & Chutney"),
    ],
)
def test_dated_playlist_scrolls_the_exact_meal(day, meal):
    [entry] = load_playlist(_PLAYLIST).cards
    card = create_card(entry.type, entry.config)
    assert card is not None
    assert card.layout is CardLayout.landscape

    # In this week, 00:30 in Copenhagen is still the previous UTC date.
    instant = datetime.fromisoformat(f"{day}T00:30+01:00").astimezone(UTC)
    assert instant.date() < date.fromisoformat(day)
    with patch("twinkly_wall.cards.lunch_horizontal.datetime") as clock:
        clock.now.side_effect = instant.astimezone
        frames = list(card.frames(CardContext()))
        clock.now.assert_called_once_with(ZoneInfo("Europe/Copenhagen"))

    width = text_width(meal)
    expected = Canvas(width + WIDTH * 2, HEIGHT)
    draw_text(expected, WIDTH, 1, meal, _BROWN)
    if day == "2026-11-30":
        draw_text(expected, WIDTH, 1, "Green", _GREEN)

    assert len(frames) == WIDTH + width + 1
    for offset, (frame, delay) in enumerate(frames):
        assert frame == [row[offset : offset + WIDTH] for row in expected.frame]
        assert delay == 1 / 25


def test_color_names_are_case_insensitive_and_match_whole_words():
    card = create_card("lunch_horizontal", {"menu": {date(2026, 11, 30): "bLuE, Greenhouse & Red"}})
    assert card is not None
    with patch("twinkly_wall.cards.lunch_horizontal.datetime") as clock:
        clock.now.return_value = datetime(2026, 11, 30, 12)
        frames = [frame for frame, _ in card.frames(CardContext())]

    text = "bLuE, Greenhouse & Red"
    stride = CHAR_WIDTH + CHAR_SPACING
    expected = Canvas(text_width(text), HEIGHT)
    draw_text(expected, 0, 1, text, _BROWN)
    draw_text(expected, 0, 1, "bLuE", (0, 0, 255))
    draw_text(expected, text.index("Red") * stride, 1, "Red", (255, 0, 0))
    actual = [[frames[WIDTH + x][y][0] for x in range(expected.width)] for y in range(HEIGHT)]
    assert actual == expected.frame
    assert {pixel for row in actual for pixel in row} == {BLACK, _BROWN, (0, 0, 255), (255, 0, 0)}


def test_same_card_skips_unlisted_dates_and_rechecks_the_date_on_each_play():
    card = create_card("lunch_horizontal", {"menu": {"2026-12-04": "Friday"}})
    assert card is not None
    with patch("twinkly_wall.cards.lunch_horizontal.datetime") as clock:
        clock.now.return_value = datetime(2026, 12, 3, 12)
        assert list(card.frames(CardContext())) == []
        clock.now.return_value = datetime(2026, 12, 4, 12)
        assert list(card.frames(CardContext()))
        clock.now.return_value = datetime(2026, 12, 5, 12)
        assert list(card.frames(CardContext())) == []


@pytest.mark.parametrize(
    ("config", "error"),
    [
        ({}, "requires a 'menu' mapping"),
        ({"menu": {"2026-02-30": "Lunch"}}, "Invalid lunch menu date"),
        ({"menu": {"20261130": "Lunch"}}, "use YYYY-MM-DD"),
        ({"menu": {"2026-11-30": " "}}, "must be a nonempty string"),
        ({"menu": {"2026-11-30": 42}}, "must be a nonempty string"),
    ],
)
def test_invalid_menu_config_is_reported(config, error):
    with pytest.raises(ValueError, match=error):
        create_card("lunch_horizontal", config)
