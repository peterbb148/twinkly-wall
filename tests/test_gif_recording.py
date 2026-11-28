"""Tests for recording terminal previews as GIFs."""

import pytest
from PIL import Image
from typer.testing import CliRunner

from twinkly_wall import cli
from twinkly_wall.outputs import gif as gif_output
from twinkly_wall.types import Orientation


@pytest.fixture(autouse=True)
def isolate_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))


def test_record_card_matches_display_mapping_and_timing(tmp_path, monkeypatch):
    class Card:
        def frames(self, context):
            yield [[(255, 0, 0), (0, 0, 255)]], 0.04
            yield [[(0, 255, 0), (0, 0, 255)]], 0.06

    monkeypatch.setattr(cli, "_build_card", lambda *args: (Card(), "example"))
    monkeypatch.setattr("time.sleep", lambda _: None)
    settings = tmp_path / "settings.yaml"
    settings.write_text("twinkly:\n  mirror_h: true\n")
    output = tmp_path / "card.gif"
    result = CliRunner().invoke(
        cli.app,
        ["preview", "clock", "--gif", str(output), "--settings", str(settings), "--scale", "2"],
    )
    assert result.exit_code == 0, result.output
    with Image.open(output) as gif:
        assert gif.size == (4, 2)
        assert gif.n_frames == 2
        assert gif.info["duration"] == 40
        assert gif.convert("RGB").getpixel((0, 0)) == (0, 0, 255)
        gif.seek(1)
        assert gif.info["duration"] == 60
        assert gif.convert("RGB").getpixel((3, 0)) == (0, 255, 0)


def test_record_playlist_loops_until_duration(tmp_path, monkeypatch):
    class Card:
        def __init__(self, color):
            self.color = color

        def frames(self, context):
            yield [[self.color]], 0.04

    monkeypatch.setattr(
        cli,
        "create_card",
        lambda name, config: Card((255, 0, 0) if name == "clock" else (0, 0, 255)),
    )
    monkeypatch.setattr("time.sleep", lambda _: None)
    playlist = tmp_path / "cards.yaml"
    playlist.write_text("cards:\n  - type: clock\n  - type: rainbow\n")
    output = tmp_path / "playlist.gif"
    result = CliRunner().invoke(
        cli.app,
        [
            "preview",
            "--playlist",
            str(playlist),
            "--gif",
            str(output),
            "--record-duration",
            "0.1",
            "--scale",
            "1",
        ],
    )
    assert result.exit_code == 0, result.output
    with Image.open(output) as gif:
        assert gif.n_frames == 3
        assert [gif.seek(i) or gif.info["duration"] for i in range(3)] == [40, 40, 20]


def test_recording_loop_requires_duration(tmp_path):
    playlist = tmp_path / "cards.yaml"
    playlist.write_text("cards:\n  - type: clock\n")
    result = CliRunner().invoke(
        cli.app, ["preview", "--playlist", str(playlist), "--gif", str(tmp_path / "out.gif")]
    )
    assert result.exit_code != 0
    assert "record-duration" in result.output


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["--record-duration", "1"], "require --gif"),
        (["--gif", "out.gif", "--no-color"], "only supported for terminal"),
        (["--gif", "out.gif"], "provide a card"),
    ],
)
def test_recording_options_report_errors(args, message):
    result = CliRunner().invoke(cli.app, ["preview", *args])
    assert result.exit_code == 1
    assert message in result.output


def test_recording_honors_portrait_orientation(tmp_path, monkeypatch):
    class Card:
        def frames(self, context):
            yield [[(255, 0, 0), (0, 0, 255)]], 0.01

    monkeypatch.setattr(cli, "_build_card", lambda *args: (Card(), "example"))
    monkeypatch.setattr("time.sleep", lambda _: None)
    output = tmp_path / "portrait.gif"
    result = CliRunner().invoke(
        cli.app,
        ["preview", "clock", "--gif", str(output), "--orientation", "top", "--scale", "1"],
    )
    assert result.exit_code == 0, result.output
    with Image.open(output) as image:
        assert image.size == (1, 2)
        rgb = image.convert("RGB")
        assert rgb.getpixel((0, 0)) == (0, 0, 255)
        assert rgb.getpixel((0, 1)) == (255, 0, 0)


def test_recording_reports_output_errors(tmp_path, monkeypatch):
    class Card:
        def frames(self, context):
            yield [[(255, 0, 0)]], 0.01

    monkeypatch.setattr(cli, "_build_card", lambda *args: (Card(), "example"))
    monkeypatch.setattr("time.sleep", lambda _: None)
    result = CliRunner().invoke(
        cli.app, ["preview", "clock", "--gif", str(tmp_path / "missing" / "out.gif")]
    )
    assert result.exit_code != 0
    assert "Error:" in result.output


def test_real_card_records_over_time(tmp_path):
    output = tmp_path / "clock.gif"
    result = CliRunner().invoke(
        cli.app,
        ["preview", "clock", "--duration", "0.12", "--gif", str(output), "--scale", "1"],
    )
    assert result.exit_code == 0, result.output
    with Image.open(output) as image:
        assert image.size == (50, 10)
        assert image.info["duration"] >= 100


def test_real_playlist_records_at_native_resolution(tmp_path):
    playlist = tmp_path / "cards.yaml"
    playlist.write_text(
        "cards:\n  - type: orientation_test\n    duration: 0.04\n"
        "  - type: test_pattern\n    duration: 0.04\n"
    )
    output = tmp_path / "playlist.gif"
    result = CliRunner().invoke(
        cli.app,
        [
            "preview",
            "--playlist",
            str(playlist),
            "--gif",
            str(output),
            "--record-duration",
            "0.12",
            "--scale",
            "1",
        ],
    )
    assert result.exit_code == 0, result.output
    with Image.open(output) as image:
        assert image.size == (50, 10)
        assert image.n_frames >= 2
        assert sum(image.seek(i) or image.info["duration"] for i in range(image.n_frames)) == 120


def test_delays_are_rounded_without_accumulating_30fps_drift(tmp_path, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)
    frames = [([[(i, 0, 0)]], 1 / 30) for i in range(6)]
    output = tmp_path / "timing.gif"
    gif_output.record_gif(iter(frames), output, Orientation.right, scale=1)
    with Image.open(output) as image:
        durations = []
        for i in range(image.n_frames):
            image.seek(i)
            durations.append(image.info["duration"])
        assert durations == [30, 40, 30, 30, 40, 30]


@pytest.mark.parametrize(
    ("frames", "message"),
    [
        ([], "No frames"),
        ([([], 0.1)], "empty or irregular"),
        ([([[(0, 0, 0)], []], 0.1)], "empty or irregular"),
        ([([[(0, 0, 0)]], 0)], "delays"),
        ([([[(0, 0, 0)]], float("nan"))], "delays"),
        ([([[(0, 0, 0)]], 656)], "655.35"),
        ([([[(0, 0, 0)]], 0.1), ([[(0, 0, 0), (0, 0, 0)]], 0.1)], "same dimensions"),
    ],
)
def test_invalid_frames_fail_clearly(tmp_path, monkeypatch, frames, message):
    monkeypatch.setattr("time.sleep", lambda _: None)
    with pytest.raises(ValueError, match=message):
        gif_output.record_gif(iter(frames), tmp_path / "out.gif", Orientation.right, scale=1)


def test_recording_limits_memory_and_dimensions(tmp_path, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)
    frame = [[(255, 0, 0)]]
    monkeypatch.setattr(gif_output, "MAX_FRAMES", 1)
    with pytest.raises(ValueError, match="frame memory limit"):
        gif_output.record_gif(iter([(frame, 0.01)] * 2), tmp_path / "out.gif", Orientation.right)
    monkeypatch.setattr(gif_output, "MAX_PIXELS", 3)
    with pytest.raises(ValueError, match="pixel memory limit"):
        gif_output.record_gif(iter([(frame, 0.01)]), tmp_path / "out.gif", Orientation.right)
    with pytest.raises(ValueError, match="65535"):
        gif_output.record_gif(
            iter([(frame, 0.01)]), tmp_path / "out.gif", Orientation.right, scale=65536
        )


def test_playlist_with_no_frames_fails_instead_of_looping(tmp_path, monkeypatch):
    class EmptyCard:
        def frames(self, context):
            return iter(())

    monkeypatch.setattr(cli, "create_card", lambda *args: EmptyCard())
    playlist = tmp_path / "cards.yaml"
    playlist.write_text("cards:\n  - type: clock\n")
    result = CliRunner().invoke(
        cli.app,
        [
            "preview",
            "--playlist",
            str(playlist),
            "--gif",
            str(tmp_path / "out.gif"),
            "--record-duration",
            "1",
        ],
    )
    assert result.exit_code == 1
    assert "No frames produced" in result.output


@pytest.mark.parametrize("duration", [0, -1, float("nan"), float("inf")])
def test_invalid_duration_rejected_before_consuming_frames(tmp_path, duration):
    with pytest.raises(ValueError, match="duration"):
        gif_output.record_gif(iter(()), tmp_path / "out.gif", Orientation.right, duration=duration)


@pytest.mark.parametrize("scale", [0, -1, 1.5])
def test_invalid_scale_rejected(tmp_path, scale):
    with pytest.raises(ValueError, match="scale"):
        gif_output.record_gif(iter(()), tmp_path / "out.gif", Orientation.right, scale=scale)


def test_merged_frame_delay_overflow_preserves_destination(tmp_path, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)
    output = tmp_path / "out.gif"
    output.write_bytes(b"existing file")
    frames = iter([([[(255, 0, 0)]], 400)] * 2)
    with pytest.raises(ValueError, match="merged"):
        gif_output.record_gif(frames, output, Orientation.right, scale=1)
    assert output.read_bytes() == b"existing file"
    assert list(tmp_path.iterdir()) == [output]


def test_interrupted_capture_preserves_destination(tmp_path, monkeypatch):
    def interrupt(delay):
        raise KeyboardInterrupt

    monkeypatch.setattr("time.sleep", interrupt)
    output = tmp_path / "out.gif"
    output.write_bytes(b"existing file")
    result = CliRunner().invoke(cli.app, ["preview", "clock", "--gif", str(output)])
    assert result.exit_code == 130
    assert "Recorded GIF" not in result.output
    assert output.read_bytes() == b"existing file"


@pytest.mark.parametrize(
    ("content", "message"),
    [("cards: []", "No cards found"), ("cards:\n  - type: nonexistent", "registered")],
)
def test_invalid_playlist_fails(tmp_path, content, message):
    playlist = tmp_path / "cards.yaml"
    playlist.write_text(content)
    result = CliRunner().invoke(
        cli.app,
        ["preview", "--playlist", str(playlist), "--gif", "out.gif", "--record-duration", "1"],
    )
    assert result.exit_code != 0
    assert message in result.output
    assert not (tmp_path / "out.gif").exists()


def test_record_playlist_entry_by_id(tmp_path):
    playlist = tmp_path / "cards.yaml"
    playlist.write_text("cards:\n  - type: clock\n    duration: 0.04\n")
    output = tmp_path / "entry.gif"
    result = CliRunner().invoke(
        cli.app, ["preview", "--playlist", str(playlist), "--id", "1", "--gif", str(output)]
    )
    assert result.exit_code == 0, result.output
    with Image.open(output) as image:
        assert image.size == (400, 80)


@pytest.mark.parametrize("duration", ["inf"])
def test_nonfinite_cli_duration_fails(duration):
    result = CliRunner().invoke(
        cli.app, ["preview", "clock", "--gif", "out.gif", "--record-duration", duration]
    )
    assert result.exit_code == 1
    assert "finite" in result.output
