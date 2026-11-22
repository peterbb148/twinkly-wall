"""Exercise the unified command's help, validation, and mode dispatch."""

import pytest

from twinkly_wall import __version__, command


@pytest.mark.parametrize("args", [[], ["--help"]])
def test_root_help(args, capsys):
    try:
        assert command.main(args) == 0
    except SystemExit as error:
        assert error.code == 0
    usage = capsys.readouterr().out
    assert "Run the configured playlist" in usage
    assert "Play a card on demand" in usage


def test_root_version(capsys):
    with pytest.raises(SystemExit) as error:
        command.main(["--version"])
    assert error.value.code == 0
    assert capsys.readouterr().out == f"twinkly-cli {__version__}\n"


def test_unknown_mode(capsys):
    with pytest.raises(SystemExit) as error:
        command.main(["invalid"])
    assert error.value.code == 2
    assert "'invalid'" in capsys.readouterr().err


@pytest.mark.parametrize("mode", ["wall", "say"])
def test_dispatch_preserves_arguments_and_exit_code(mode, monkeypatch):
    def handle(args):
        assert args == ["--help", "--settings", "settings.yaml"]
        return 17

    monkeypatch.setattr(command.daemon if mode == "wall" else command.cli, "main", handle)
    assert command.main([mode, "--help", "--settings", "settings.yaml"]) == 17
