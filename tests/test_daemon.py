"""Verify the daemon's public command name and version."""

import runpy
from pathlib import Path
from unittest.mock import Mock

import pytest

from twinkly_wall import __version__, daemon
from twinkly_wall.daemon import main
from twinkly_wall.outputs import twinkly


@pytest.mark.parametrize(
    ("flag", "expected"),
    [("--help", "usage: twinkly-cli wall "), ("--version", f"twinkly-cli {__version__}\n")],
)
def test_daemon_command_metadata(flag, expected, capsys):
    with pytest.raises(SystemExit) as result:
        main([flag])
    assert result.value.code == 0
    assert capsys.readouterr().out.startswith(expected)


def test_packaged_entrypoint_runs_the_daemon(monkeypatch, capsys):
    entrypoint = Path(__file__).resolve().parents[1] / "packaging/entrypoint.py"
    monkeypatch.setattr("sys.argv", ["twinkly-cli", "wall", "--version"])
    with pytest.raises(SystemExit) as result:
        runpy.run_path(str(entrypoint), run_name="__main__")
    assert result.value.code == 0
    assert capsys.readouterr().out == f"twinkly-cli {__version__}\n"


def test_mcp_only_wall_skips_playlist_and_starts_with_leds_off(tmp_path, monkeypatch):
    settings = tmp_path / "settings.yaml"
    settings.write_text("twinkly: {host: localhost, orientation: top, mirror_h: true}\n")
    load_playlist = Mock(side_effect=AssertionError("MCP-only mode loaded the playlist"))
    client = Mock()
    create_client = Mock(return_value=client)
    output = Mock()
    create_output = Mock(return_value=output)
    scheduler = Mock(wraps=daemon.Scheduler)
    monkeypatch.setattr(daemon, "load_playlist", load_playlist)
    monkeypatch.setattr(daemon, "MCPClient", create_client)
    monkeypatch.setattr(twinkly, "TwinklyOutput", create_output)
    monkeypatch.setattr(daemon.TwinklyDaemon, "_setup_signals", Mock())
    monkeypatch.setattr(daemon.Scheduler, "run_loop", Mock())
    monkeypatch.setattr(daemon, "Scheduler", scheduler)
    monkeypatch.setenv("TWINKLY_MCP_URL", "https://mcp.example")
    monkeypatch.delenv("TWINKLY_API_KEY", raising=False)

    assert main(["--mcp-only", "--settings", str(settings)]) == 0
    load_playlist.assert_not_called()
    create_client.assert_called_once_with(server_url="https://mcp.example", api_key=None)
    client.register_cards.assert_called_once_with()
    create_output.assert_called_once_with(host="localhost", port=80, mirror_h=True, mirror_v=False)
    assert output.orientation == "top"
    assert scheduler.call_args.kwargs["playlist"].cards == []
    assert scheduler.call_args.kwargs["mcp_client"] is client
    assert [call[0] for call in output.method_calls] == ["start", "turn_off", "stop"]


def test_mcp_only_wall_reports_failed_registration(monkeypatch, caplog):
    client = Mock()
    client.register_cards.return_value = False
    setup_outputs = Mock(return_value=[])
    monkeypatch.setattr(daemon, "MCPClient", Mock(return_value=client))
    monkeypatch.setattr(daemon.TwinklyDaemon, "_setup_signals", Mock())
    monkeypatch.setattr(daemon.TwinklyDaemon, "_create_outputs", setup_outputs)

    assert main(["--mcp-only", "--terminal"]) == 1
    assert "Could not register cards with the MCP server" in caplog.text


def test_wall_startup_logs_weather_status_without_coordinates(tmp_path, monkeypatch, caplog):
    latitude, longitude = 12.345678, -98.765432
    settings = tmp_path / "settings.yaml"
    settings.write_text(f"weather: {{latitude: {latitude}, longitude: {longitude}}}\n")
    cards = tmp_path / "cards.yaml"
    cards.write_text("cards: [{type: clock}]\n")
    scheduler = Mock(wraps=daemon.Scheduler)
    monkeypatch.setattr(daemon.TwinklyDaemon, "_setup_signals", Mock())
    monkeypatch.setattr(daemon.TwinklyDaemon, "_create_outputs", Mock(return_value=[]))
    monkeypatch.setattr(daemon.Scheduler, "run_loop", Mock())
    monkeypatch.setattr(daemon, "Scheduler", scheduler)
    caplog.set_level("INFO", logger=daemon.__name__)

    assert main(["--terminal", "--settings", str(settings), "--cards", str(cards)]) == 0

    weather = scheduler.call_args.kwargs["context"].datasources["weather"]
    assert (weather.latitude, weather.longitude) == (latitude, longitude)
    assert "Weather datasource configured" in caplog.messages
    assert str(latitude) not in caplog.text
    assert str(longitude) not in caplog.text
