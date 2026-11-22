"""Verify the daemon's public command name and version."""

import runpy
from pathlib import Path

import pytest

from twinkly_wall import __version__
from twinkly_wall.daemon import main


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
