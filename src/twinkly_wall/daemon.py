"""Main daemon entry point for Twinkly Wall."""

import argparse
import logging
import signal
import sys
from pathlib import Path

from .cards import CardContext
from .config import load_playlist, load_settings
from .scheduler import Scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class TwinklyDaemon:
    """Main daemon for running the Twinkly Wall display.

    The daemon loads configuration, sets up the scheduler, and runs
    the card playlist in a loop.
    """

    def __init__(
        self,
        settings_path: Path | None = None,
        cards_path: Path | None = None,
        terminal_output: bool = False,
    ):
        """Initialize the daemon.

        Args:
            settings_path: Path to settings.yaml
            cards_path: Path to cards.yaml
            terminal_output: If True, output to terminal instead of Twinkly device
        """
        self.settings = load_settings(settings_path)
        self.playlist = load_playlist(cards_path)
        from .outputs.terminal import TerminalOutput
        from .outputs.twinkly import TwinklyOutput

        self.terminal_output = terminal_output
        self.scheduler: Scheduler | None = None
        self._terminal: TerminalOutput | None = None
        self._twinkly: TwinklyOutput | None = None
        self._setup_signals()

    def _setup_signals(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum: int, frame: object) -> None:
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()

    def _create_outputs(self) -> list:
        """Create output targets based on settings.

        Returns:
            List of output instances
        """
        outputs = []

        # Add terminal output if requested
        if self.terminal_output:
            from .outputs.terminal import TerminalOutput

            self._terminal = TerminalOutput()
            outputs.append(self._terminal)
            logger.info("Terminal output enabled")

        # Add Twinkly output if configured
        if self.settings.twinkly.host:
            from .outputs.twinkly import TwinklyOutput

            self._twinkly = TwinklyOutput(
                host=self.settings.twinkly.host,
                port=self.settings.twinkly.port,
                mirror_h=self.settings.twinkly.mirror_h,
                mirror_v=self.settings.twinkly.mirror_v,
            )
            outputs.append(self._twinkly)
            logger.info(f"Twinkly output configured: {self.settings.twinkly.host}")

        return outputs

    def _create_context(self) -> CardContext:
        """Create the card context with datasources.

        Returns:
            CardContext instance
        """
        datasources: dict = {}

        # Add weather datasource if configured
        if self.settings.weather.latitude and self.settings.weather.longitude:
            from .datasources.weather import WeatherDataSource

            datasources["weather"] = WeatherDataSource(
                latitude=self.settings.weather.latitude,
                longitude=self.settings.weather.longitude,
                cache_duration=self.settings.weather.cache_duration,
            )
            logger.info(
                f"Weather datasource configured: {self.settings.weather.latitude}, "
                f"{self.settings.weather.longitude}"
            )

        return CardContext(datasources=datasources)

    def run(self) -> None:
        """Run the daemon."""
        if not self.playlist.cards:
            logger.error("No cards configured in playlist")
            sys.exit(1)

        logger.info(f"Starting Twinkly Wall daemon with {len(self.playlist.cards)} cards")

        outputs = self._create_outputs()
        context = self._create_context()

        self.scheduler = Scheduler(
            playlist=self.playlist,
            context=context,
            outputs=outputs,
        )

        # Start outputs
        if self._terminal:
            self._terminal.start()
        if self._twinkly:
            self._twinkly.start()

        try:
            logger.info("Starting playlist loop...")
            self.scheduler.run_loop()
        finally:
            # Clean up outputs
            if self._terminal:
                self._terminal.stop()
            if self._twinkly:
                self._twinkly.stop()

        logger.info("Daemon stopped")

    def stop(self) -> None:
        """Stop the daemon."""
        if self.scheduler:
            self.scheduler.stop()


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for the daemon."""
    parser = argparse.ArgumentParser(
        prog="twinkly-wall",
        description="Run the Twinkly Wall LED display daemon",
    )
    parser.add_argument(
        "-s",
        "--settings",
        type=Path,
        help="Path to settings.yaml",
    )
    parser.add_argument(
        "-c",
        "--cards",
        type=Path,
        help="Path to cards.yaml",
    )
    parser.add_argument(
        "-t",
        "--terminal",
        action="store_true",
        help="Output to terminal instead of Twinkly device",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the daemon."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    daemon = TwinklyDaemon(
        settings_path=args.settings,
        cards_path=args.cards,
        terminal_output=args.terminal,
    )

    try:
        daemon.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Daemon error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
