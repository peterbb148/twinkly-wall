"""Exercise external definitions through the CLI and playlist scheduler."""

from pathlib import Path
from unittest.mock import Mock

import pytest
from PIL import Image
from typer.testing import CliRunner

from twinkly_wall import cli
from twinkly_wall.cards import create_card
from twinkly_wall.config import load_playlist
from twinkly_wall.scheduler import Scheduler


@pytest.fixture
def catalog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tmp_path / "external"
    directory.mkdir()
    monkeypatch.setenv("TWINKLY_CARD_DIR", str(directory))
    return directory


def test_external_portrait_asset_updates_across_playbacks(
    catalog: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = catalog / "party-flame.yaml"
    source.write_text("type: image\nlayout: portrait\npath: flame.gif\nscroll: false\n")
    asset = catalog / "flame.gif"
    Image.new("RGB", (10, 50), (255, 100, 0)).save(asset)

    runner = CliRunner()
    listed = runner.invoke(cli.app, ["list"])
    assert listed.exit_code == 0, listed.output
    assert f"party-flame ({source})" in listed.output
    assert "torch_vertical" in listed.output

    output = Mock()
    monkeypatch.setattr(cli, "TwinklyOutput", Mock(return_value=output))
    settings = tmp_path / "settings.yaml"
    settings.write_text("twinkly: {host: localhost, orientation: vertical_left}\n")
    args = ["--settings", str(settings), "--duration", "0.03"]
    with monkeypatch.context() as renderer_patch:
        animate = Mock(side_effect=lambda frames, **_: next(frames))
        renderer_patch.setattr(cli, "animate_frames", animate)
        preview = runner.invoke(cli.app, ["preview", "party-flame", *args])
        assert preview.exit_code == 0, preview.output
        animate.assert_called_once()
    played = runner.invoke(cli.app, ["card", "party-flame", *args])
    assert played.exit_code == 0, played.output
    first = output.send_frame.call_args.args[0]
    assert len(first) == 50 and all(len(row) == 10 for row in first)
    assert first[0][0] == (255, 100, 0)

    Image.new("RGB", (10, 50), (0, 100, 255)).save(asset)
    playlist = tmp_path / "playlist.yaml"
    playlist.write_text("cards:\n  - type: party-flame\n    duration: 0.03\n")
    listed = runner.invoke(cli.app, ["list", "--playlist", str(playlist)])
    assert listed.exit_code == 0, listed.output
    assert "[1] party-flame" in listed.output
    later, _ = next(Scheduler(load_playlist(playlist)).frames())
    assert later[0][0] == (0, 100, 255)


@pytest.mark.parametrize(
    ("name", "contents", "message"),
    [
        ("clock.yaml", "type: image", "already in use"),
        ("a" * 101 + ".yaml", "type: clock", "at most 100 characters"),
        ("bad.yml", "type: missing", "built-in card renderer"),
        ("bad.yml", "type: image\npath: missing.gif", "image does not exist"),
        ("bad.yml", "[", "could not read card definition"),
    ],
)
def test_invalid_definition_reports_its_source(
    catalog: Path, name: str, contents: str, message: str
) -> None:
    source = catalog / name
    source.write_text(contents)
    result = CliRunner().invoke(cli.app, ["list"])
    assert result.exit_code == 1
    assert str(source) in result.output
    assert message in result.output


def test_create_card_uses_definition_options_with_playlist_overrides(catalog: Path) -> None:
    (catalog / "announcement.yaml").write_text("type: text\ntext: Hello\nscroll: false\n")
    card = create_card("announcement", {"duration": 4, "text": "Welcome"})
    assert card is not None
    assert card.config["scroll"] is False
    assert card.config["text"] == "Welcome"
    assert card.duration == 4


def test_overlay_layout_filter_uses_the_background_for_textless_overlays(
    catalog: Path, tmp_path: Path
) -> None:
    (catalog / "image.gif").touch()
    (catalog / "portrait-image.yaml").write_text("type: image\nlayout: portrait\npath: image.gif\n")
    (catalog / "portrait-overlay.yaml").write_text(
        "type: overlay\nbackground: {type: portrait-image}\n"
    )
    playlist = tmp_path / "playlist.yaml"
    playlist.write_text(
        "cards:\n"
        "  - type: overlay\n"
        "    background: {type: countdown_vertical}\n"
        "  - type: portrait-overlay\n"
        "    text: Hello\n"
        "  - type: overlay\n"
        "    background: {type: portrait-overlay}\n"
        "  - type: overlay\n"
        "    background: {type: orientation_test}\n"
        "  - type: portrait-overlay\n"
        "    background: {type: portrait-image, layout: landscape}\n"
        "  - type: overlay\n"
        "    background: {type: missing}\n"
    )

    runner = CliRunner()
    expected_entries = {
        "portrait": ["[1] overlay [portrait]", "[3] overlay [portrait]"],
        "adaptive": ["[4] overlay [adaptive]"],
        "landscape": [
            "[2] portrait-overlay [landscape]",
            "[5] portrait-overlay [landscape]",
            "[6] overlay [landscape]",
        ],
    }
    for layout, entries in expected_entries.items():
        result = runner.invoke(cli.app, ["list", "--layout", layout, "--playlist", str(playlist)])
        assert result.exit_code == 0, result.output
        assert ("portrait-overlay.yaml) [portrait]" in result.output) == (layout == "portrait")
        lines = result.output.splitlines()
        listed_entries = [line.strip() for line in lines if line.startswith(" [")]
        assert listed_entries == entries


def test_catalog_reports_circular_overlay_backgrounds(catalog: Path) -> None:
    (catalog / "overlay-a.yaml").write_text("type: overlay\nbackground: {type: overlay-b}\n")
    (catalog / "overlay-b.yaml").write_text("type: overlay\nbackground: {type: overlay-a}\n")
    result = CliRunner().invoke(cli.app, ["list"])
    assert result.exit_code == 1
    assert "Circular card layout reference" in result.output


def test_discovers_repository_and_user_catalogs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkout = tmp_path / "checkout"
    repo_cards = checkout / "config" / "cards.d"
    repo_cards.mkdir(parents=True)
    home = tmp_path / "home"
    user_cards = home / ".config" / "twinkly-wall" / "cards.d"
    user_cards.mkdir(parents=True)
    monkeypatch.chdir(checkout)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("TWINKLY_CARD_DIR", raising=False)

    definition = repo_cards / "repo-flame.yaml"
    definition.write_text("type: image\npath: flame.gif\nlayout: portrait\n")
    asset = repo_cards / "flame.gif"
    Image.new("RGB", (10, 50), (255, 100, 0)).save(asset)
    user_definition = user_cards / "user-clock.yaml"
    user_definition.write_text("type: clock\n")

    runner = CliRunner()
    listed = runner.invoke(cli.app, ["list"])
    assert listed.exit_code == 0, listed.output
    assert f"repo-flame ({definition.resolve()})" in listed.output
    assert f"user-clock ({user_definition.resolve()})" in listed.output
    card = create_card("repo-flame")
    assert card is not None and card.config["path"] == str(asset.resolve())

    duplicate = user_cards / definition.name
    duplicate.write_text("type: clock\n")
    conflict = runner.invoke(cli.app, ["list"])
    assert conflict.exit_code == 1
    assert str(duplicate.resolve()) in conflict.output
    assert str(definition.resolve()) in conflict.output

    monkeypatch.setenv("TWINKLY_CARD_DIR", str(repo_cards))
    overridden = runner.invoke(cli.app, ["list"])
    assert overridden.exit_code == 0, overridden.output
    assert "repo-flame" in overridden.output
    assert "user-clock" not in overridden.output
