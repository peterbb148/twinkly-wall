"""Tests for the CLI module."""

from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from twinkly_wall import __version__, cli
from twinkly_wall.cli import app, main, parse_color, render_text_centered


class TestParseColor:
    """Tests for color parsing."""

    def test_named_colors(self):
        """Should parse named colors."""
        assert parse_color("red") == (255, 0, 0)
        assert parse_color("green") == (0, 255, 0)
        assert parse_color("blue") == (0, 0, 255)
        assert parse_color("white") == (255, 255, 255)
        assert parse_color("black") == (0, 0, 0)

    def test_named_colors_case_insensitive(self):
        """Named colors should be case insensitive."""
        assert parse_color("RED") == (255, 0, 0)
        assert parse_color("Red") == (255, 0, 0)

    def test_hex_with_hash(self):
        """Should parse hex colors with # prefix."""
        assert parse_color("#FF0000") == (255, 0, 0)
        assert parse_color("#00ff00") == (0, 255, 0)
        assert parse_color("#0000FF") == (0, 0, 255)

    def test_hex_without_hash(self):
        """Should parse hex colors without # prefix."""
        assert parse_color("FF0000") == (255, 0, 0)
        assert parse_color("00ff00") == (0, 255, 0)

    def test_rgb_format(self):
        """Should parse R,G,B format."""
        assert parse_color("255,0,0") == (255, 0, 0)
        assert parse_color("0,255,0") == (0, 255, 0)
        assert parse_color("128,128,128") == (128, 128, 128)

    def test_invalid_color(self):
        """Should raise ValueError for invalid colors."""
        with pytest.raises(ValueError):
            parse_color("notacolor")
        with pytest.raises(ValueError):
            parse_color("GGGGGG")  # Invalid hex


class TestRenderTextCentered:
    """Tests for text rendering."""

    def test_renders_frame(self):
        """Should return a valid frame."""
        frame = render_text_centered("Hi")
        assert len(frame) == 10  # HEIGHT
        assert len(frame[0]) == 50  # WIDTH

    def test_renders_with_color(self):
        """Should render text with specified color."""
        red = (255, 0, 0)
        frame = render_text_centered("A", red)

        # Should have at least one red pixel
        has_red = any(frame[y][x] == red for y in range(len(frame)) for x in range(len(frame[0])))
        assert has_red


runner = CliRunner()


@pytest.fixture(autouse=True)
def isolate_config(tmp_path, monkeypatch):
    """Keep developer settings and external providers out of CLI tests."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("TWINKLY_MCP_URL", raising=False)
    monkeypatch.delenv("TWINKLY_API_KEY", raising=False)


@pytest.mark.parametrize(
    "command",
    [
        [],
        ["--help"],
        ["say", "--help"],
        ["preview", "--help"],
        ["card", "--help"],
        ["mcp", "--help"],
        ["list", "--help"],
    ],
)
def test_help(command):
    result = runner.invoke(app, command)
    assert result.exit_code == 0
    assert "Usage:" in result.output


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == f"twinklysay {__version__}"


@pytest.mark.parametrize(
    "args",
    [["say", "Hi"], ["say", "Hi", "-c", "red"], ["say", "Hi", "--no-color", "--no-half-blocks"]],
)
def test_say(args):
    result = runner.invoke(app, args)
    assert result.exit_code == 0
    assert result.output.strip()


def test_list_cards():
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "clock" in result.output
    assert "twinklysay" in result.output


@pytest.mark.parametrize(
    "args",
    [
        ["say"],
        ["unknown"],
        ["preview", "unknown"],
        ["card", "unknown"],
        ["preview", "clock", "--duration", "0"],
        ["preview", "clock", "--duration", "abc"],
        ["preview", "--id", "0"],
        ["card", "--id", "-1"],
        ["preview", "clock", "--orientation", "diagonal"],
        ["preview", "text", "--scroll-direction", "diagonal"],
        ["preview", "pacman", "--theme", "unknown"],
        ["preview", "rainbow", "--mode", "unknown"],
        ["preview", "test_pattern", "--pattern-mode", "unknown"],
        ["preview", "snow", "--wind", "2"],
        ["mcp", "--interval", "0"],
        ["list", "--playlist", "missing.yaml"],
        ["card", "clock", "--settings", "missing.yaml"],
    ],
)
def test_invalid_arguments(args):
    result = runner.invoke(app, args)
    assert result.exit_code == 2
    assert "Traceback" not in result.output


@pytest.mark.parametrize(
    "args",
    [
        ["preview"],
        ["card"],
        ["preview", "text"],
        ["preview", "twinklysay"],
        ["card", "text"],
        ["card", "twinklysay"],
        ["say", "Hi", "-c", "invalid"],
        ["preview", "clock", "-c", "invalid"],
        ["preview", "text", "-t", "Hi", "-c", "invalid"],
        ["preview", "twinklysay", "-t", "Hi", "-c", "invalid"],
    ],
)
def test_command_validation(args):
    result = runner.invoke(app, args)
    assert result.exit_code == 1
    assert result.output.strip()
    assert "Traceback" not in result.output


@pytest.mark.parametrize(
    "card",
    [
        "clock",
        "text",
        "pacman",
        "beer",
        "snow",
        "rainbow",
        "test_pattern",
        "carlsberg_lab",
        "twinklysay",
        "rain",
    ],
)
def test_preview_dispatch(card, monkeypatch):
    animate = MagicMock()
    monkeypatch.setattr(cli, "animate_frames", animate)
    result = runner.invoke(
        app,
        [
            "preview",
            card,
            "-t",
            "Hello",
            "-d",
            "0.01",
            "--orientation",
            "vertical_right",
            "--no-color",
        ],
    )
    assert result.exit_code == 0, result.output
    animate.assert_called_once()
    assert animate.call_args.kwargs["orientation"] == "vertical_right"
    assert animate.call_args.kwargs["color_mode"] is False


def test_card_specific_options(monkeypatch):
    build = MagicMock(return_value=(MagicMock(), "pacman"))
    monkeypatch.setattr(cli, "_build_card", build)
    monkeypatch.setattr(cli, "animate_frames", MagicMock())
    result = runner.invoke(
        app,
        [
            "preview",
            "pacman",
            "--theme",
            "hops",
            "--speed",
            "20",
            "--wind",
            "-0.5",
            "--accumulate",
            "--twelve-hour",
            "--no-blink",
            "--scroll",
            "--scroll-direction",
            "vertical_up",
            "--mode",
            "plasma",
            "--pattern-mode",
            "corners",
        ],
    )
    assert result.exit_code == 0, result.output
    options = build.call_args.args[1]
    assert options.theme == "hops"
    assert options.speed == 20
    assert options.wind == -0.5
    assert options.accumulate and options.twelve_hour and options.no_blink and options.scroll
    assert options.scroll_direction == "vertical_up"
    assert options.mode == "plasma"
    assert options.pattern_mode == "corners"


@pytest.fixture
def playlist(tmp_path):
    path = tmp_path / "cards.yaml"
    path.write_text("cards:\n  - type: clock\n    duration: 0.01\n")
    return path


def test_explicit_playlist_listing(playlist):
    result = runner.invoke(app, ["list", "--playlist", str(playlist)])
    assert result.exit_code == 0
    assert "[1] clock" in result.output


@pytest.mark.parametrize("id", ["1", "2"])
def test_playlist_entry(playlist, monkeypatch, id):
    monkeypatch.setattr(cli, "animate_frames", MagicMock())
    result = runner.invoke(app, ["preview", "--playlist", str(playlist), "--id", id])
    assert result.exit_code == (0 if id == "1" else 1), result.output


def test_looping_playlist_stops_cleanly(playlist, monkeypatch):
    monkeypatch.setattr(cli, "animate_frames", MagicMock(side_effect=KeyboardInterrupt))
    result = runner.invoke(app, ["preview", "--playlist", str(playlist)])
    assert result.exit_code == 0
    assert "Stopped" in result.output


def test_empty_playlist(tmp_path):
    path = tmp_path / "empty.yaml"
    path.write_text("cards: []\n")
    assert runner.invoke(app, ["list", "--playlist", str(path)]).exit_code == 0
    assert runner.invoke(app, ["preview", "--playlist", str(path)]).exit_code == 1
    assert runner.invoke(app, ["preview", "--playlist", str(path), "--id", "1"]).exit_code == 1


@pytest.mark.parametrize(
    "content", ["[", "[]", "cards: clock", "cards: [clock]", "cards: [{type: unknown}]"]
)
def test_invalid_playlist_yaml(tmp_path, content):
    path = tmp_path / "invalid.yaml"
    path.write_text(content)
    result = runner.invoke(app, ["list", "--playlist", str(path)])
    assert result.exit_code == 2
    assert "Traceback" not in result.output


@pytest.mark.parametrize(
    "content", ["[", "[]", "twinkly: []", "weather: []", "twinkly: {orientation: diagonal}"]
)
def test_invalid_settings_yaml(tmp_path, content):
    path = tmp_path / "invalid.yaml"
    path.write_text(content)
    result = runner.invoke(app, ["preview", "clock", "--settings", str(path)])
    assert result.exit_code == 2
    assert "Traceback" not in result.output


def test_explicit_settings_used_for_preview(tmp_path, monkeypatch):
    path = tmp_path / "custom.yaml"
    path.write_text("twinkly: {orientation: vertical_left}\nweather: {latitude: 1, longitude: 2}\n")
    animate = MagicMock()
    monkeypatch.setattr(cli, "animate_frames", animate)
    result = runner.invoke(app, ["preview", "clock", "--settings", str(path)])
    assert result.exit_code == 0, result.output
    assert animate.call_args.kwargs["orientation"] == "vertical_left"
    ctx = cli.create_context_with_datasources(path)
    assert "weather" in ctx.datasources


def test_unconfigured_device_fails():
    result = runner.invoke(app, ["card", "clock"])
    assert result.exit_code == 1
    assert "twinkly.host" in result.output


@pytest.mark.parametrize("fails", [False, True])
def test_device_send_and_cleanup(tmp_path, monkeypatch, fails):
    path = tmp_path / "device.yaml"
    path.write_text("twinkly: {host: localhost, port: 8080, orientation: vertical_left}\n")
    output = MagicMock()
    if fails:
        output.start.side_effect = RuntimeError("device unreachable")
    factory = MagicMock(return_value=output)
    monkeypatch.setattr(cli, "TwinklyOutput", factory)
    monkeypatch.setattr(cli.time, "sleep", MagicMock())
    result = runner.invoke(app, ["card", "clock", "-d", "0.001", "--settings", str(path)])
    assert result.exit_code == (1 if fails else 0), result.output
    factory.assert_called_once_with(host="localhost", port=8080, mirror_h=False, mirror_v=False)
    output.stop.assert_called_once()
    if not fails:
        output.send_frame.assert_called()
    else:
        assert "device unreachable" in result.output


@pytest.mark.parametrize("registered", [False, True])
def test_mcp_registration_and_environment(monkeypatch, registered):
    from twinkly_wall import mcp_client

    client = MagicMock()
    client.register_cards.return_value = registered
    client.run.side_effect = KeyboardInterrupt
    factory = MagicMock(return_value=client)
    monkeypatch.setattr(mcp_client, "MCPClient", factory)
    monkeypatch.setenv("TWINKLY_MCP_URL", "http://localhost:8000")
    monkeypatch.setenv("TWINKLY_API_KEY", "test-secret")
    result = runner.invoke(app, ["mcp", "-i", "0.1"])
    assert result.exit_code == (0 if registered else 1), result.output
    factory.assert_called_once_with(
        server_url="http://localhost:8000", poll_interval=0.1, api_key="test-secret"
    )
    if registered:
        client.run.assert_called_once_with(use_terminal=True, register=False)
    else:
        client.run.assert_not_called()
        assert "Could not register" in result.output
    assert "test-secret" not in result.output


def test_interruption_restores_command_exit(monkeypatch):
    monkeypatch.setattr(cli, "animate_frames", MagicMock(side_effect=KeyboardInterrupt))
    result = runner.invoke(app, ["preview", "clock"])
    assert result.exit_code == 130
    assert "Stopped" in result.output


@pytest.mark.parametrize("loop_playlist", [False, True])
def test_real_renderer_restores_cursor_and_stops(playlist, monkeypatch, loop_playlist):
    from twinkly_wall.outputs import terminal

    show_cursor = MagicMock()
    monkeypatch.setattr(terminal, "show_cursor", show_cursor)
    monkeypatch.setattr(terminal.time, "sleep", MagicMock(side_effect=KeyboardInterrupt))
    args = ["preview", "--playlist", str(playlist)] if loop_playlist else ["preview", "clock"]
    result = runner.invoke(app, args)
    assert result.exit_code == (0 if loop_playlist else 130)
    show_cursor.assert_called_once()
    assert "Stopped" in result.output


def test_main_returns_exit_codes(capsys):
    assert main(["--version"]) == 0
    assert __version__ in capsys.readouterr().out
    assert main(["say", "Hi", "--color", "invalid"]) == 1
    assert main(["unknown"]) == 2
