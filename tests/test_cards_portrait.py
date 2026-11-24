"""Check upright portrait variants and their inherited content."""

from itertools import islice
from unittest.mock import Mock

import pytest

from twinkly_wall.cards import CardContext, create_card
from twinkly_wall.cards.coffee import MUG_COLORS
from twinkly_wall.datasources.weather import WeatherData
from twinkly_wall.types import BLACK, GOLD, RED, WHITE, YELLOW, Frame


def _colors(frame: Frame) -> set[tuple[int, int, int]]:
    assert len(frame) == 50 and all(len(row) == 10 for row in frame)
    return {pixel for row in frame for pixel in row}


@pytest.mark.parametrize("show_hop", [True, False])
def test_portrait_lab_scrolls_lab_name_and_optional_hop(show_hop):
    card = create_card(
        "carlsberg_lab_vertical",
        {"scroll_speed": 300, "show_hop": show_hop, "hop_color": GOLD},
    )
    assert card is not None
    frames = [_colors(frame) for frame, _ in card.frames(CardContext())]
    assert frames[0] == {WHITE}
    assert any(BLACK in colors for colors in frames)
    assert any(GOLD in colors for colors in frames) is show_hop


def test_portrait_coffee_keeps_mug_above_scrolling_caption():
    card = create_card("coffee_vertical", {"message": "COFFEE BREAK", "color": GOLD})
    assert card is not None
    frames = [frame for frame, _ in islice(card.frames(CardContext()), 24)]
    assert MUG_COLORS[3] in _colors(frames[0])
    assert GOLD in _colors(frames[0])
    assert frames[0][:10] != frames[5][:10]
    assert frames[0][11:] != frames[-1][11:]
    assert all(GOLD not in row for row in frames[-1][:11])


def test_portrait_friday_can_celebrate_or_scroll_days(monkeypatch):
    card = create_card("friday_vertical", {"always_friday": True})
    assert card is not None
    celebration, _ = next(card.frames(CardContext()))
    assert RED in _colors(celebration)
    assert any(pixel != BLACK for row in celebration for pixel in row[:2] + row[7:])

    monkeypatch.setattr(card, "_is_friday", lambda: False)
    monkeypatch.setattr(card, "_days_until_friday", lambda: 1)
    countdown = [_colors(frame) for frame, _ in card.frames(CardContext())]
    assert countdown[0] == {BLACK}
    assert {BLACK, YELLOW} in countdown


def test_portrait_weather_uses_the_shared_datasource():
    source = Mock()
    source.get_weather.return_value = WeatherData(4, -3, 70, 15, 3, "overcast", True, 0)
    card = create_card(
        "weather_vertical",
        {"duration": 0, "show_feels_like": True, "color": GOLD, "scroll_speed": 300},
    )
    assert card is not None
    frames = [
        _colors(frame) for frame, _ in card.frames(CardContext(datasources={"weather": source}))
    ]
    assert frames[0] == {BLACK}
    assert {BLACK, GOLD} in frames
    source.get_weather.assert_called_once_with()


def test_portrait_countdown_can_show_missing_date():
    card = create_card("countdown_vertical")
    assert card is not None
    frame, _ = next(card.frames(CardContext()))
    assert _colors(frame) == {BLACK, RED}


@pytest.mark.parametrize("scroll", ["auto", True, False])
def test_portrait_countdown_supports_target_label_and_tree(scroll):
    card = create_card(
        "countdown_vertical",
        {
            "target": "2000-01-01",
            "label": "X",
            "prefix_sprite": "tree",
            "suffix_sprite": "tree",
            "scroll": scroll,
            "scroll_speed": 300,
        },
    )
    assert card is not None
    samples = islice(card.frames(CardContext()), 30 if scroll else 1)
    colors = set().union(*(_colors(frame) for frame, _ in samples))
    assert {BLACK, GOLD, WHITE, (150, 150, 150)} <= colors


def test_short_portrait_countdown_is_centered_by_default():
    card = create_card("countdown_vertical", {"target": "2000-01-01"})
    assert card is not None
    frame, delay = next(card.frames(CardContext()))
    assert delay == 0.5
    assert _colors(frame) == {BLACK, WHITE}
