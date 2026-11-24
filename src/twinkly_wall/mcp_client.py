"""MCP server polling client for remote control.

This module provides a polling client that connects to the Twinkly MCP server
and executes commands received from Claude Desktop or other MCP clients.

The client is optional and can be disabled for offline operation.
"""

import logging
import time
from collections.abc import Callable
from typing import Any

import requests

from .cards import Card, CardContext, create_card, list_card_types
from .cards.twinklysay import TwinklysayCard
from .outputs.terminal import animate_frames

logger = logging.getLogger(__name__)

DEFAULT_SERVER_URL = "https://twinkly-mcp.onrender.com"
DEFAULT_POLL_INTERVAL = 2.0  # seconds


class MCPClient:
    """Polling client for the Twinkly MCP server.

    Polls the server for commands and can either execute them directly
    or return cards for the scheduler to play.
    """

    def __init__(
        self,
        server_url: str = DEFAULT_SERVER_URL,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        api_key: str | None = None,
        output_callback: Callable[[Any], None] | None = None,
    ):
        """Initialize the MCP client.

        Args:
            server_url: Base URL of the MCP server
            poll_interval: Seconds between polls
            api_key: Optional API key for authentication
            output_callback: Optional callback for frame output (default: terminal)
        """
        self.server_url = server_url.rstrip("/")
        self.poll_interval = poll_interval
        self.api_key = api_key
        self.output_callback = output_callback
        self.last_command_id: str | None = None
        self._running = False
        self._pending_commands: list[dict[str, Any]] = []

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers including auth if configured."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def sync_command_id(self) -> None:
        """Sync the last command ID without processing old commands.

        This should be called on startup to skip any commands that were
        sent before the client started. Only new commands after this
        point will be processed.
        """
        url = f"{self.server_url}/api/commands/poll"
        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            commands = data.get("commands", [])

            # Set last_command_id to the most recent command (if any)
            if commands:
                self.last_command_id = commands[-1]["id"]
                logger.info(
                    "Synced to command ID %s, skipping %d old commands",
                    self.last_command_id,
                    len(commands),
                )
            else:
                logger.info("No existing commands in queue")

        except requests.RequestException as e:
            logger.warning(f"Failed to sync command ID: {e}")

    def register_cards(self) -> bool:
        """Register available cards with the MCP server.

        Returns:
            True if registration succeeded
        """
        cards = list_card_types()
        try:
            response = requests.post(
                f"{self.server_url}/api/cards/register",
                json={"cards": cards},
                headers=self._get_headers(),
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Registered {data.get('count', len(cards))} cards with MCP server")

            # Sync command ID to skip old commands on startup
            self.sync_command_id()

            return True
        except requests.RequestException as e:
            logger.warning(f"Failed to register cards: {e}")
            return False

    def poll_commands(self) -> list[dict[str, Any]]:
        """Poll the server for new commands.

        Returns:
            List of new commands since last poll
        """
        url = f"{self.server_url}/api/commands/poll"
        if self.last_command_id:
            url += f"?after={self.last_command_id}"

        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            commands = data.get("commands", [])

            # Update last command ID
            if commands:
                self.last_command_id = commands[-1]["id"]

            return commands
        except requests.RequestException as e:
            logger.warning(f"Poll failed: {e}")
            return []

    def check_for_commands(self) -> bool:
        """Check for new commands without blocking.

        This is a non-blocking poll that stores commands in _pending_commands.

        Returns:
            True if new commands are available
        """
        commands = self.poll_commands()
        if commands:
            self._pending_commands.extend(commands)
            return True
        return False

    def get_next_card(self) -> Card | None:
        """Get the next card from pending commands.

        Returns:
            A Card instance to play, or None if no pending commands
        """
        if not self._pending_commands:
            return None

        cmd = self._pending_commands.pop(0)
        return self.create_card_from_command(cmd)

    def has_pending_commands(self) -> bool:
        """Check if there are pending commands to process."""
        return len(self._pending_commands) > 0

    def discard_pending_commands(self) -> None:
        """Discard commands that have been polled but have not started playback."""
        self._pending_commands.clear()

    def create_card_from_command(self, cmd: dict[str, Any]) -> Card | None:
        """Create a card instance from a command.

        Args:
            cmd: Command dict with type and payload

        Returns:
            Card instance or None if command is invalid
        """
        cmd_type = cmd.get("type")
        payload = cmd.get("payload", {})
        cmd_id = cmd.get("id", "unknown")

        logger.info(f"Creating card from command {cmd_id}: {cmd_type}")

        try:
            if cmd_type == "twinklysay":
                text = payload.get("text", "")
                if not text:
                    logger.warning("twinklysay: empty text")
                    return None
                return TwinklysayCard({"text": text})

            elif cmd_type == "run_card":
                card_id = payload.get("card_id", "")
                if not card_id:
                    logger.warning("run_card: empty card_id")
                    return None
                card = create_card(card_id, {"duration": 10})
                if card is None:
                    logger.warning(f"run_card: unknown card '{card_id}'")
                return card

            else:
                logger.warning(f"Unknown command type: {cmd_type}")
                return None

        except Exception as e:
            logger.error(f"Error creating card from command {cmd_id}: {e}")
            return None

    def execute_command(self, cmd: dict[str, Any], use_terminal: bool = True) -> bool:
        """Execute a single command.

        Args:
            cmd: Command dict with type and payload
            use_terminal: If True, render to terminal; if False, use output_callback

        Returns:
            True if command executed successfully
        """
        cmd_type = cmd.get("type")
        payload = cmd.get("payload", {})
        cmd_id = cmd.get("id", "unknown")

        logger.info(f"Executing command {cmd_id}: {cmd_type}")

        try:
            if cmd_type == "twinklysay":
                return self._execute_twinklysay(payload, use_terminal)
            elif cmd_type == "run_card":
                return self._execute_run_card(payload, use_terminal)
            else:
                logger.warning(f"Unknown command type: {cmd_type}")
                return False
        except Exception as e:
            logger.error(f"Error executing command {cmd_id}: {e}")
            return False

    def _execute_twinklysay(self, payload: dict[str, Any], use_terminal: bool) -> bool:
        """Execute a twinklysay command."""
        text = payload.get("text", "")
        if not text:
            logger.warning("twinklysay: empty text")
            return False

        card = TwinklysayCard({"text": text})
        ctx = CardContext()

        if use_terminal:
            print(f"\n[twinklysay] {text}")
            animate_frames(
                card.frames(ctx),
                color_mode=True,
                use_half_blocks=True,
                clear_between=False,
            )
        elif self.output_callback:
            for frame, delay in card.frames(ctx):
                self.output_callback(frame)
                time.sleep(delay)

        return True

    def _execute_run_card(self, payload: dict[str, Any], use_terminal: bool) -> bool:
        """Execute a run_card command."""
        card_id = payload.get("card_id", "")
        if not card_id:
            logger.warning("run_card: empty card_id")
            return False

        card = create_card(card_id, {"duration": 10})
        if card is None:
            logger.warning(f"run_card: unknown card '{card_id}'")
            return False

        ctx = CardContext()

        if use_terminal:
            print(f"\n[run_card] {card_id}")
            animate_frames(
                card.frames(ctx),
                color_mode=True,
                use_half_blocks=True,
                clear_between=False,
            )
        elif self.output_callback:
            for frame, delay in card.frames(ctx):
                self.output_callback(frame)
                time.sleep(delay)

        return True

    def run(self, use_terminal: bool = True, *, register: bool = True) -> None:
        """Run the polling loop.

        Args:
            use_terminal: If True, render commands to terminal
            register: Register cards before polling; False when registration already succeeded.
        """
        self._running = True
        logger.info(f"MCP client starting, polling {self.server_url}")

        # Register cards on startup unless the caller already did so.
        if register:
            self.register_cards()

        while self._running:
            try:
                commands = self.poll_commands()
                for cmd in commands:
                    self.execute_command(cmd, use_terminal)
            except KeyboardInterrupt:
                logger.info("MCP client stopped by user")
                break
            except Exception as e:
                logger.error(f"Polling error: {e}")

            time.sleep(self.poll_interval)

    def stop(self) -> None:
        """Stop the polling loop."""
        self._running = False


def run_mcp_client(
    server_url: str = DEFAULT_SERVER_URL,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    api_key: str | None = None,
    use_terminal: bool = True,
) -> None:
    """Convenience function to run the MCP client.

    Args:
        server_url: MCP server URL
        poll_interval: Seconds between polls
        api_key: Optional API key
        use_terminal: Render to terminal (vs LED output)
    """
    client = MCPClient(
        server_url=server_url,
        poll_interval=poll_interval,
        api_key=api_key,
    )
    client.run(use_terminal=use_terminal)
