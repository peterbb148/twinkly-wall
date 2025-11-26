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
    ):
        """Initialize the daemon.

        Args:
            settings_path: Path to settings.yaml
            cards_path: Path to cards.yaml
        """
        self.settings = load_settings(settings_path)
        self.playlist = load_playlist(cards_path)
        self.scheduler: Scheduler | None = None
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

        # Add Twinkly output if configured
        if self.settings.twinkly.host:
            logger.info(f"Twinkly output configured: {self.settings.twinkly.host}")
            # TODO: Add TwinklyOutput when implemented
            # from .outputs.twinkly import TwinklyOutput
            # outputs.append(TwinklyOutput(
            #     host=self.settings.twinkly.host,
            #     port=self.settings.twinkly.port,
            # ))

        return outputs

    def _create_context(self) -> CardContext:
        """Create the card context with datasources.

        Returns:
            CardContext instance
        """
        datasources: dict = {}

        # Add weather datasource if configured
        if self.settings.weather.api_key:
            logger.info("Weather datasource configured")
            # TODO: Add weather datasource when implemented
            # from .datasources.weather import WeatherDataSource
            # datasources["weather"] = WeatherDataSource(
            #     api_key=self.settings.weather.api_key,
            #     city_id=self.settings.weather.city_id,
            #     units=self.settings.weather.units,
            # )

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

        logger.info("Starting playlist loop...")
        self.scheduler.run_loop()

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
