"""Exercise the Christmas batch through card registration and playlist loading."""

import json
import random
from itertools import islice
from pathlib import Path

import pytest

from twinkly_wall.cards import CardContext, create_card
from twinkly_wall.cards.base import CardLayout, get_card_layout
from twinkly_wall.cards.christmas_vertical import _ICE, _SNOW, TuborgSnowVerticalCard
from twinkly_wall.cards.lunch_vertical import _menu_frame
from twinkly_wall.config import load_playlist
from twinkly_wall.fonts import FONT_5X7
from twinkly_wall.types import GOLD, PORTRAIT_HEIGHT, PORTRAIT_WIDTH, WHITE

_EXAMPLE = Path(__file__).resolve().parents[1] / "config/christmas-vertical.example.yaml"


def test_all_christmas_playlist_cards_render_in_portrait_from_the_example_playlist(
    monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)
    playlist = load_playlist(_EXAMPLE)
    assert [entry.type for entry in playlist.cards] == [
        "christmas_tree_vertical",
        "pacman_up",
        "santa_rocket_vertical",
        "aurora",
        "lunch_vertical",
        "tuborg_snow_vertical",
        "sparkle_curtain",
        "tuborg_julebryg_vertical",
        "beer_vertical",
        "santa_chimney_vertical",
        "meteor_shower",
        "gift_stack_vertical",
        "lava_column",
        "nisse_lab_vertical",
        "reindeer_weather_vane_vertical",
    ]
    existing_animations = {
        "pacman_up",
        "aurora",
        "sparkle_curtain",
        "beer_vertical",
        "meteor_shower",
        "lava_column",
    }
    for entry in playlist.cards:
        assert get_card_layout(entry.type, {}) is CardLayout.portrait
        card = create_card(entry.type, {**entry.config, "duration": entry.duration})
        assert card is not None
        sequence = card.frames(CardContext())
        is_existing = entry.type in existing_animations
        frames = list(islice(sequence, 4) if is_existing else sequence)
        assert frames
        assert all(len(frame) == PORTRAIT_HEIGHT for frame, _ in frames)
        assert all(len(row) == PORTRAIT_WIDTH for frame, _ in frames for row in frame)
        assert all(delay > 0 for _, delay in frames)
        if not is_existing:
            assert sum(delay for _, delay in frames) >= entry.duration - 1e-9
            assert frames[0][0] != frames[-1][0]


def test_tree_star_lights_late_and_flashes():
    card = create_card("christmas_tree_vertical")
    assert card is not None
    frames = [frame for frame, _ in card.frames(CardContext())]
    assert frames[0][6][4] == (0, 0, 0)
    assert frames[-1][6][4] == WHITE
    assert len({frame[4][2] for frame in frames[75:]}) > 1


def test_rocket_clears_the_top_of_the_display():
    card = create_card("santa_rocket_vertical")
    assert card is not None
    frames = [frame for frame, _ in card.frames(CardContext())]
    assert all(pixel == WHITE for pixel in frames[0][38][3:7])
    assert sum(pixel == WHITE for row in frames[-1] for pixel in row) < 8


def test_snowbank_grows_and_resets_between_plays(monkeypatch):
    rng = random.Random
    monkeypatch.setattr("twinkly_wall.cards.christmas_vertical.random.Random", lambda: rng(72))
    card = TuborgSnowVerticalCard({"duration": 14})
    frames = [frame for frame, _ in card.frames(CardContext())]
    initial_base = sum(pixel != _ICE for pixel in frames[0][-1])
    assert initial_base < 4
    assert frames[-1][-1].count(_SNOW) >= initial_base + 6
    assert any(pixel == _SNOW for pixel in frames[-1][-4])
    assert next(card.frames(CardContext()))[0] == frames[0]


def test_lunch_reads_named_json_each_play_and_finishes_scrolling(monkeypatch, tmp_path):
    monkeypatch.setenv("TWINKLY_CARD_DIR", str(tmp_path))
    (tmp_path / "canteen.yaml").write_text(
        "type: lunch_vertical\nmenu_path: menu.json\n", encoding="utf-8"
    )
    menu_path = tmp_path / "menu.json"
    menu = {"date": "2026-11-25", "name": " Æg  og\n flæsk ", "description": "Rødkål på siden"}
    menu_path.write_text(json.dumps(menu), encoding="utf-8")
    card = create_card("canteen", {"duration": 1})
    assert card is not None
    frames = list(card.frames(CardContext()))
    assert frames[-1][0] == _menu_frame("RØDKÅL PÅ SIDEN", 39, WHITE)
    assert sum(delay for _, delay in frames) > 1

    menu.update(date="2026-11-26", name="Æg", description="Rødkål")
    menu_path.write_text(json.dumps(menu), encoding="utf-8")
    updated = list(card.frames(CardContext()))
    assert len(updated) == 4
    assert updated[1][0] != frames[1][0]
    assert updated[2][0] == _menu_frame("ÆG", -20, GOLD)
    assert all(letter in FONT_5X7 for letter in "ÆØÅ")


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        (None, "Could not read lunch menu"),
        (b"\xff", "Could not read lunch menu"),
        (b"{", "Could not read lunch menu"),
        (b"[]", "expected a lunch menu JSON object"),
        (b'{"date":"2026-11-25","name":true,"description":"test"}', "'name'"),
        (b'{"date":"2026-11-25","name":"test","description":" "}', "'description'"),
        (b'{"date":"2026-02-30","name":"test","description":"test"}', "YYYY-MM-DD"),
        (b'{"date":"20261125","name":"test","description":"test"}', "YYYY-MM-DD"),
    ],
)
def test_lunch_reports_file_and_schema_errors(tmp_path, contents, message):
    path = tmp_path / "menu.json"
    if contents is not None:
        path.write_bytes(contents)
    card = create_card("lunch_vertical", {"menu_path": str(path)})
    assert card is not None
    with pytest.raises(ValueError, match=message):
        next(card.frames(CardContext()))


def test_lunch_requires_a_menu_path():
    card = create_card("lunch_vertical")
    assert card is not None
    with pytest.raises(ValueError, match="requires a 'menu_path'"):
        next(card.frames(CardContext()))
