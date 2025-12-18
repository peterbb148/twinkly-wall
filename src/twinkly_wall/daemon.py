"""Main daemon entry point for Twinkly Wall."""

import argparse
import logging
import os
import signal
import sys
from pathlib import Path

from .cards import CardContext
from .config import load_playlist, load_settings
from .mcp_client import DEFAULT_SERVER_URL, MCPClient
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
        mcp_enabled: bool = False,
        mcp_server: str | None = None,
        mcp_api_key: str | None = None,
    ):
        """Initialize the daemon.

        Args:
            settings_path: Path to settings.yaml
            cards_path: Path to cards.yaml
            terminal_output: If True, output to terminal instead of Twinkly device
            mcp_enabled: If True, enable MCP remote control
            mcp_server: MCP server URL (default from env or hardcoded)
            mcp_api_key: MCP API key (default from env)
        """
        self.settings = load_settings(settings_path)
        self.playlist = load_playlist(cards_path)
        from .outputs.terminal import TerminalOutput
        from .outputs.twinkly import TwinklyOutput

        self.terminal_output = terminal_output
        self.mcp_enabled = mcp_enabled
        self.mcp_server = mcp_server
        self.mcp_api_key = mcp_api_key
        self.scheduler: Scheduler | None = None
        self._terminal: TerminalOutput | None = None
        self._twinkly: TwinklyOutput | None = None
        self._mcp_client: MCPClient | None = None
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

            self._terminal = TerminalOutput(
                orientation=self.settings.twinkly.orientation,
            )
            outputs.append(self._terminal)
            logger.info("Terminal output enabled")

        # Add Twinkly output if configured (skip if terminal-only mode)
        if self.settings.twinkly.host and not self.terminal_output:
            from .outputs.twinkly import TwinklyOutput

            self._twinkly = TwinklyOutput(
                host=self.settings.twinkly.host,
                port=self.settings.twinkly.port,
                mirror_h=self.settings.twinkly.mirror_h,
                mirror_v=self.settings.twinkly.mirror_v,
            )
            self._twinkly.orientation = self.settings.twinkly.orientation
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

    def _create_mcp_client(self) -> MCPClient | None:
        """Create MCP client if enabled.

        Returns:
            MCPClient instance or None if MCP is disabled
        """
        if not self.mcp_enabled:
            return None

        server_url = (
            self.mcp_server
            or os.environ.get("TWINKLY_MCP_URL")
            or DEFAULT_SERVER_URL
        )
        api_key = self.mcp_api_key or os.environ.get("TWINKLY_API_KEY")

        client = MCPClient(
            server_url=server_url,
            api_key=api_key,
        )

        # Register cards with the server
        client.register_cards()

        logger.info(f"MCP client enabled, polling {server_url}")
        return client

    def run(self) -> None:
        """Run the daemon."""
        if not self.playlist.cards:
            logger.error("No cards configured in playlist")
            sys.exit(1)

        logger.info(f"Starting Twinkly Wall daemon with {len(self.playlist.cards)} cards")

        outputs = self._create_outputs()
        context = self._create_context()
        self._mcp_client = self._create_mcp_client()

        self.scheduler = Scheduler(
            playlist=self.playlist,
            context=context,
            outputs=outputs,
            mcp_client=self._mcp_client,
            operating_hours=self.settings.operating_hours,
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
        "--mcp",
        action="store_true",
        help="Enable MCP remote control (polls MCP server for commands)",
    )
    parser.add_argument(
        "--mcp-server",
        type=str,
        help="MCP server URL (default: $TWINKLY_MCP_URL or https://twinkly-mcp.onrender.com)",
    )
    parser.add_argument(
        "--mcp-api-key",
        type=str,
        help="MCP API key (default: $TWINKLY_API_KEY)",
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
        mcp_enabled=args.mcp,
        mcp_server=args.mcp_server,
        mcp_api_key=args.mcp_api_key,
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
