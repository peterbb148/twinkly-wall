"""Smoke-test a packaged CLI outside the checkout with no Python or UV on PATH."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> None:
    """Verify bundled runtime, rendering, YAML, and expected input failures."""
    binary = Path(sys.argv[1]).resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="twinklysay-smoke-") as directory:
        root = Path(directory)
        # The child receives no Python, UV, source checkout, or developer configuration.
        env = {
            "PATH": str(root),
            "HOME": str(root),
            "LANG": "en_US.UTF-8",
            "TERM": "dumb",
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

        assert "Usage:" in run("--help")
        assert "twinklysay " in run("--version")
        assert "clock" in run("list")
        assert run("say", "Hello", "--no-color").strip()
        assert "Previewing" in run("preview", "clock", "--duration", "0.03", "--no-color")
        settings = root / "settings.yaml"
        settings.write_text("twinkly: {orientation: vertical_left}\n")
        playlist = root / "cards.yaml"
        playlist.write_text("cards:\n  - type: clock\n    duration: 0.03\n")
        assert "[1] clock" in run("list", "--playlist", str(playlist))
        assert "1:clock" in run(
            "preview",
            "--id",
            "1",
            "--playlist",
            str(playlist),
            "--settings",
            str(settings),
            "--no-color",
        )
        image = root / "sample.png"
        image.write_bytes(
            (Path(__file__).resolve().parents[1] / "assets/carlsberg.png").read_bytes()
        )
        playlist.write_text(f"cards:\n  - type: image\n    path: {image}\n    duration: 0.03\n")
        output = run("preview", "--id", "1", "--playlist", str(playlist), "--no-color")
        assert "Failed to load image" not in output
        assert any(block in output for block in "░▒▓█")
        playlist.write_text("[")
        run("list", "--playlist", str(playlist), code=2)
        assert "Error" in run("say", "Hello", "--color", "invalid", code=1)
        run("list", "--playlist", str(root / "missing.yaml"), code=2)
        run("card", "clock", code=1)
    print("Packaged CLI smoke tests passed (isolated directory, empty executable PATH).")


if __name__ == "__main__":
    main()
