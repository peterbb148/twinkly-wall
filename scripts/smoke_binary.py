"""Smoke-test a packaged CLI outside the checkout with no Python or UV on PATH."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> None:
    """Verify bundled runtime, rendering, YAML, and expected input failures."""
    binary = Path(sys.argv[1]).resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="twinkly-cli-smoke-") as directory:
        root = Path(directory)
        # The child receives no Python, UV, source checkout, or developer configuration.
        env = {
            "PATH": str(root),
            "HOME": str(root),
            "LANG": "en_US.UTF-8",
            "TERM": "dumb",
            "DISPLAY_ORIENTATION": "vertical_left",
            "CARD_TYPE": "clock",
        }
        # Keep the normal temporary directory available to PyInstaller's onefile loader.
        if "TMPDIR" in os.environ:
            env["TMPDIR"] = os.environ["TMPDIR"]

        def run(*args: str, code: int = 0) -> str:
            result = subprocess.run(
                [str(binary), *args],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != code:
                raise AssertionError(
                    f"{args}: exit {result.returncode}\n{result.stdout}\n{result.stderr}"
                )
            return result.stdout + result.stderr

        assert "{wall,say}" in run("--help")
        assert "{wall,say}" in run("-h")
        assert "usage: twinkly-cli wall" in run("wall", "--help")
        assert "Usage:" in run("say", "--help")
        assert "Usage:" in run("say", "preview", "-h")
        assert "twinkly-cli " in run("--version")
        assert "clock" in run("say", "list")
        assert run("say", "text", "Hello", "--no-color").strip()
        assert "Previewing" in run("say", "preview", "clock", "--duration", "0.03", "--no-color")
        settings = root / "settings.yaml"
        settings.write_text("twinkly: {orientation: '${DISPLAY_ORIENTATION}'}\n")
        playlist = root / "cards.yaml"
        playlist.write_text("cards:\n  - type: '${CARD_TYPE}'\n    duration: 0.03\n")
        assert "[1] clock" in run("say", "list", "--playlist", str(playlist))
        assert "1:clock" in run(
            "say",
            "preview",
            "--id",
            "1",
            "--playlist",
            str(playlist),
            "--settings",
            str(settings),
            "--no-color",
        )
        image = root / "sample.ppm"
        image.write_bytes(b"P6\n2 2\n255\n" + bytes([255]) * 12)
        playlist.write_text(f"cards:\n  - type: image\n    path: {image}\n    duration: 0.03\n")
        output = run("say", "preview", "--id", "1", "--playlist", str(playlist), "--no-color")
        assert "Failed to load image" not in output
        assert any(block in output for block in "░▒▓█")
        catalog = root / "config/cards.d"
        catalog.mkdir(parents=True)
        definition = catalog / "party-flame.yaml"
        definition.write_text("type: image\nlayout: portrait\npath: flame.ppm\nscroll: false\n")
        asset = catalog / "flame.ppm"
        asset.write_bytes(b"P6\n10 50\n255\n" + bytes(1500))
        assert f"party-flame ({definition.resolve()})" in run("say", "list")
        preview = (
            "say",
            "preview",
            "party-flame",
            "--settings",
            str(settings),
            "--duration",
            "0.03",
            "--no-color",
        )
        assert "█" not in run(*preview)
        asset.write_bytes(b"P6\n10 50\n255\n" + bytes([255]) * 1500)
        assert "█" * 10 in run(*preview)
        playlist.write_text("[")
        run("say", "list", "--playlist", str(playlist), code=2)
        assert "Error" in run("say", "text", "Hello", "--color", "invalid", code=1)
        run("say", "list", "--playlist", str(root / "missing.yaml"), code=2)
        run("say", "card", "clock", code=1)
    print("Packaged CLI smoke tests passed (isolated directory, empty executable PATH).")


if __name__ == "__main__":
    main()
