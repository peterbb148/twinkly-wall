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


class CaptureClock:
    def __init__(self):
        self.now = 0.0

    def sleep(self, delay):
        self.now += delay

    def monotonic(self):
        return self.now


def _mock_capture_clock(monkeypatch):
    clock = CaptureClock()
    monkeypatch.setattr(gif_output, "time", clock)
    return clock


def test_record_card_matches_display_mapping_and_timing(tmp_path, monkeypatch):
    class Card:
        def frames(self, context):
            yield [[(255, 0, 0), (0, 0, 255)]], 0.04
            yield [[(0, 255, 0), (0, 0, 255)]], 0.06

    monkeypatch.setattr(cli, "_build_card", lambda *args: (Card(), "example"))
    _mock_capture_clock(monkeypatch)
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
    _mock_capture_clock(monkeypatch)
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
    _mock_capture_clock(monkeypatch)
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
    _mock_capture_clock(monkeypatch)
    result = CliRunner().invoke(
        cli.app, ["preview", "clock", "--gif", str(tmp_path / "missing" / "out.gif")]
    )
    assert result.exit_code != 0
    assert "Error:" in result.output


def test_real_card_records_over_time(tmp_path):
    output = tmp_path / "clock.gif"
    result = CliRunner().invoke(
        cli.app,
        ["preview", "clock", "--duration", "0.5", "--gif", str(output), "--scale", "1"],
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
    _mock_capture_clock(monkeypatch)
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
        ([([[(0, 0, 0)]], -0.01)], "delays"),
        ([([[(0, 0, 0)]], float("nan"))], "delays"),
        ([([[(0, 0, 0)]], 656)], "655.35"),
        ([([[(0, 0, 0)]], 0.1), ([[(0, 0, 0), (0, 0, 0)]], 0.1)], "same dimensions"),
    ],
)
def test_invalid_frames_fail_clearly(tmp_path, monkeypatch, frames, message):
    _mock_capture_clock(monkeypatch)
    with pytest.raises(ValueError, match=message):
        gif_output.record_gif(iter(frames), tmp_path / "out.gif", Orientation.right, scale=1)


def test_recording_limits_memory_and_dimensions(tmp_path, monkeypatch):
    _mock_capture_clock(monkeypatch)
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
    _mock_capture_clock(monkeypatch)
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


def test_text_gif_defaults_match_approved_settings(tmp_path, monkeypatch):
    _mock_capture_clock(monkeypatch)
    (tmp_path / "settings.yaml").write_text(
        "twinkly:\n  orientation: bottom\n  mirror_h: true\n  mirror_v: true\n"
    )
    approved = tmp_path / "approved.yaml"
    approved.write_text("twinkly:\n  orientation: left\n  mirror_h: false\n  mirror_v: false\n")
    default_output = tmp_path / "default.gif"
    explicit_output = tmp_path / "explicit.gif"
    for output, extra in [
        (default_output, []),
        (explicit_output, ["--scroll", "--settings", str(approved), "--orientation", "left"]),
    ]:
        result = CliRunner().invoke(
            cli.app,
            ["preview", "text", "--text", "Merry christmas", "--gif", str(output), *extra],
        )
        assert result.exit_code == 0, result.output
    assert default_output.read_bytes() == explicit_output.read_bytes()
    with Image.open(default_output) as image:
        assert image.size == (400, 80)
        assert image.n_frames > 100


@pytest.mark.parametrize("explicit_settings", [False, True])
@pytest.mark.parametrize("orientation", [None, "right"])
def test_text_gif_display_overrides(tmp_path, monkeypatch, explicit_settings, orientation):
    settings = tmp_path / "settings.yaml"
    settings.write_text("twinkly:\n  orientation: top\n  mirror_h: true\n  mirror_v: true\n")
    captured = {}

    def record(frames, path, mount, **options):
        captured.update(mount=mount, **options)

    monkeypatch.setattr(cli, "record_gif", record)
    extra = ["--settings", str(settings)] if explicit_settings else []
    if orientation:
        extra += ["--orientation", orientation]
    result = CliRunner().invoke(
        cli.app, ["preview", "text", "--text", "Hello", "--gif", "out.gif", *extra]
    )
    assert result.exit_code == 0, result.output
    assert captured["mount"] == (orientation or ("top" if explicit_settings else "left"))
    assert captured["mirror_h"] is explicit_settings
    assert captured["mirror_v"] is explicit_settings


def test_text_gif_can_disable_scrolling(tmp_path, monkeypatch):
    _mock_capture_clock(monkeypatch)
    output = tmp_path / "static.gif"
    result = CliRunner().invoke(
        cli.app,
        [
            "preview",
            "text",
            "--text",
            "Hello",
            "--gif",
            str(output),
            "--no-scroll",
            "--record-duration",
            "0.01",
        ],
    )
    assert result.exit_code == 0, result.output
    with Image.open(output) as image:
        assert image.n_frames == 1


def test_terminal_text_keeps_existing_defaults(monkeypatch):
    captured = {}

    def preview(options):
        captured.update(vars(options))
        return 0

    monkeypatch.setattr(cli, "cmd_preview", preview)
    result = CliRunner().invoke(cli.app, ["preview", "text", "--text", "Hello"])
    assert result.exit_code == 0, result.output
    assert captured["scroll"] is False
    assert captured["orientation"] is None


@pytest.mark.parametrize("short_delay", [0, 0.001])
def test_minimum_gif_delay_does_not_shorten_later_frames(tmp_path, monkeypatch, short_delay):
    _mock_capture_clock(monkeypatch)
    frames = [([[(i, 0, 0)]], short_delay) for i in range(10)]
    frames.append(([[(255, 0, 0)]], 0.1))
    output = tmp_path / "minimum-delay.gif"
    gif_output.record_gif(iter(frames), output, Orientation.right, scale=1)
    with Image.open(output) as image:
        durations = [image.seek(i) or image.info["duration"] for i in range(image.n_frames)]
        assert durations == [10] * 10 + [100]


@pytest.mark.parametrize("slow_stage", ["generation", "conversion"])
@pytest.mark.parametrize("limited", [False, True])
def test_processing_time_counts_toward_timestamps_and_deadline(
    tmp_path, monkeypatch, slow_stage, limited
):
    clock = _mock_capture_clock(monkeypatch)
    original_quantize = Image.Image.quantize
    produced = []

    def quantize(image, *args, **kwargs):
        clock.sleep(0.04)
        return original_quantize(image, *args, **kwargs)

    if slow_stage == "conversion":
        monkeypatch.setattr(Image.Image, "quantize", quantize)

    def frames():
        for i in range(10 if limited else 2):
            produced.append(i)
            if slow_stage == "generation":
                clock.sleep(0.04)
            yield [[(i * 20, 0, 0)]], 0.02

    output = tmp_path / "slow.gif"
    gif_output.record_gif(
        frames(), output, Orientation.right, scale=1, duration=0.15 if limited else None
    )
    with Image.open(output) as image:
        durations = [image.seek(i) or image.info["duration"] for i in range(image.n_frames)]
        assert durations == ([100, 50] if limited else [100, 20])
    assert len(produced) == (3 if limited else 2)
    assert clock.now == pytest.approx(0.16 if limited else 0.12)


def test_deadline_before_first_frame_fails_without_overwriting(tmp_path, monkeypatch):
    clock = _mock_capture_clock(monkeypatch)
    output = tmp_path / "existing.gif"
    output.write_bytes(b"existing")

    def frames():
        clock.sleep(1)
        yield [[(255, 0, 0)]], 0.1

    with pytest.raises(ValueError, match="No frames"):
        gif_output.record_gif(frames(), output, Orientation.right, duration=0.1)
    assert output.read_bytes() == b"existing"


def test_processing_time_cannot_exceed_gif_frame_delay(tmp_path, monkeypatch):
    clock = _mock_capture_clock(monkeypatch)

    def frames():
        yield [[(255, 0, 0)]], 0.1
        clock.sleep(656)
        yield [[(0, 255, 0)]], 0.1

    with pytest.raises(ValueError, match="655.35"):
        gif_output.record_gif(frames(), tmp_path / "out.gif", Orientation.right)


@pytest.mark.parametrize("playlist_entry", [False, True])
@pytest.mark.parametrize("record_duration,expected", [(None, 120), ("0.06", 60), ("1", 120)])
def test_scrolling_text_recording_respects_card_duration(
    tmp_path, monkeypatch, playlist_entry, record_duration, expected
):
    clock = _mock_capture_clock(monkeypatch)
    output = tmp_path / "bounded.gif"
    if playlist_entry:
        playlist = tmp_path / "cards.yaml"
        playlist.write_text(
            "cards:\n  - type: text\n    duration: 0.12\n"
            "    config:\n      text: Merry christmas\n      scroll: true\n"
        )
        options = ["--playlist", str(playlist), "--id", "1"]
    else:
        options = ["text", "--text", "Merry christmas", "--duration", "0.12"]
    if record_duration is not None:
        options += ["--record-duration", record_duration]
    result = CliRunner().invoke(cli.app, ["preview", *options, "--gif", str(output)])
    assert result.exit_code == 0, result.output
    with Image.open(output) as image:
        assert (
            sum(image.seek(i) or image.info["duration"] for i in range(image.n_frames)) == expected
        )
    assert clock.now == pytest.approx(expected / 1000)


def test_nonfinite_card_duration_is_rejected():
    result = CliRunner().invoke(
        cli.app, ["preview", "text", "--text", "Hello", "--duration", "inf", "--gif", "out.gif"]
    )
    assert result.exit_code == 1
    assert "Card duration must be finite" in result.output
