"""Dispatch the unified command to its wall and on-demand modes."""

import argparse
import sys

from . import __version__, cli, daemon, watch


def main(argv: list[str] | None = None) -> int:
    """Run the requested mode with its own arguments and exit status."""
    args = sys.argv[1:] if argv is None else argv
    commands = {
        "wall": (daemon.main, "Run the configured playlist on the LED wall."),
        "say": (cli.main, "Play a card on demand or preview it in the terminal."),
        "watch": (watch.main, "Replay the active wall card in the terminal."),
    }
    if args and args[0] in commands:
        handler, _ = commands[args[0]]
        return handler(args[1:])

    parser = argparse.ArgumentParser(prog="twinkly-cli", description="Control a Twinkly LED wall.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(title="commands", metavar="{wall,say,watch}")
    for name, (_, help_text) in commands.items():
        subparsers.add_parser(name, help=help_text)
    if args:
        parser.parse_args(args)
    else:
        parser.print_help()
    return 0
