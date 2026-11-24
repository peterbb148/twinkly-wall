"""Exercise the output path with asymmetric Matrix 500 frames."""

from unittest.mock import Mock

import pytest

from twinkly_wall.cards import CardContext, create_card
from twinkly_wall.config import CardConfig, PlaylistConfig
from twinkly_wall.outputs.terminal import TerminalOutput
from twinkly_wall.outputs.twinkly import TwinklyOutput
from twinkly_wall.scheduler import Scheduler


@pytest.mark.parametrize("layout,width,height", [("landscape", 50, 10), ("portrait", 10, 50)])
@pytest.mark.parametrize(
    "mount", ["top", "bottom", "left", "right", "horizontal", "vertical_left", "vertical_right"]
)
@pytest.mark.parametrize("mirror_h", [False, True])
@pytest.mark.parametrize("mirror_v", [False, True])
def test_send_frame_maps_every_pixel(monkeypatch, layout, width, height, mount, mirror_h, mirror_v):
    frame = [[(x, y, (3 * x + y) % 256) for x in range(width)] for y in range(height)]
    device = TwinklyOutput("unused", mirror_h=mirror_h, mirror_v=mirror_v)
    device.orientation = mount
    device.client = Mock()
    device.send_frame(frame)
    request = device.client._request
    assert request.call_args.args == ("POST", "/led/rt/frame")
    payload = request.call_args.kwargs["data"]
    assert len(payload) == 1500

    terminal = TerminalOutput(orientation=mount, mirror_h=mirror_h, mirror_v=mirror_v)
    display = Mock()
    monkeypatch.setattr("twinkly_wall.outputs.terminal.print_frame", display)
    terminal.send_frame(frame)
    preview = display.call_args.args[0]

    landscape = mount in ("horizontal", "left", "right")
    view_width, view_height = (50, 10) if landscape else (10, 50)
    assert len(preview) == view_height
    assert all(len(row) == view_width for row in preview)
    row_order = [5, 6, 7, 8, 9, 4, 3, 2, 1, 0]
    for strand, native_y in enumerate(row_order):
        for led in range(50):
            native_x = led if strand % 5 % 2 else 49 - led
            if mount in ("top", "vertical_left"):
                view_x, view_y = native_y, 49 - native_x
            elif mount in ("bottom", "vertical_right"):
                view_x, view_y = 9 - native_y, native_x
            elif mount == "left":
                view_x, view_y = 49 - native_x, 9 - native_y
            else:
                view_x, view_y = native_x, native_y

            x = view_width - 1 - view_x if mirror_h else view_x
            y = view_height - 1 - view_y if mirror_v else view_y
            if landscape and layout == "portrait":
                x, y = (9 - y, x) if mount == "left" else (y, 49 - x)
            elif mount in ("top", "vertical_left") and layout == "landscape":
                x, y = 49 - y, x
            elif mount in ("bottom", "vertical_right") and layout == "landscape":
                x, y = y, 9 - x

            index = 3 * (50 * strand + led)
            assert payload[index : index + 3] == bytes(frame[y][x])
            assert preview[view_y][view_x] == frame[y][x]


@pytest.mark.parametrize(
    "name,width,height",
    [
        ("clock", 50, 10),
        ("torch_vertical", 10, 50),
        ("candle_vertical", 10, 50),
        ("beer_vertical", 10, 50),
        ("score_tower", 10, 50),
        ("countdown_ruler", 10, 50),
        ("vertical_bars", 10, 50),
        ("rain", 10, 50),
        ("aurora", 10, 50),
        ("meteor_shower", 10, 50),
        ("vines", 10, 50),
        ("lava_column", 10, 50),
        ("sparkle_curtain", 10, 50),
    ],
)
def test_card_logical_dimensions(name, width, height):
    card = create_card(name)
    assert card is not None
    frame, _ = next(card.frames(CardContext()))
    assert len(frame) == height
    assert all(len(row) == width for row in frame)


@pytest.mark.parametrize(
    "mount,width,height", [("left", 50, 10), ("right", 50, 10), ("top", 10, 50), ("bottom", 10, 50)]
)
def test_mixed_playlist_crossfades(mount, width, height):
    playlist = PlaylistConfig(
        cards=[
            CardConfig(type="clock", duration=0.01),
            CardConfig(type="torch_vertical", duration=0.01, transition="crossfade"),
            CardConfig(type="clock", duration=0.01, transition="crossfade"),
        ]
    )
    scheduler = Scheduler(playlist, orientation=mount)
    transitions = [frame for frame, delay in scheduler.frames() if delay == 0.03]
    assert len(transitions) == 32
    assert all(len(frame) == height for frame in transitions)
    assert all(len(row) == width for frame in transitions for row in frame)
