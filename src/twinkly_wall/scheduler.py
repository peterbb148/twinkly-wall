"""Card scheduler for rotating through playlist cards."""

import logging
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from .cards import Card, CardContext, create_card
from .config import CardConfig, OperatingHoursConfig, PlaylistConfig, is_within_operating_hours
from .effects import crossfade
from .types import HEIGHT, WIDTH, Frame

if TYPE_CHECKING:
    from .mcp_client import MCPClient

logger = logging.getLogger(__name__)


class Output(Protocol):
    """Protocol for frame output targets."""

    def send_frame(self, frame: Frame) -> None:
        """Send a frame to the output device."""
        ...


@dataclass
class SchedulerState:
    """Current state of the scheduler."""

    current_card_index: int = 0
    cards_played: int = 0
    last_frame: Frame | None = None
    running: bool = False
    mcp_interrupt: bool = False  # Flag to interrupt current card for MCP


class Scheduler:
    """Card scheduler that rotates through a playlist.

    The scheduler loads cards from the playlist config and plays them
    in sequence, handling transitions between cards.

    Attributes:
        playlist: The playlist configuration
        context: Shared context passed to cards
        state: Current scheduler state
    """

    def __init__(
        self,
        playlist: PlaylistConfig,
        context: CardContext | None = None,
        outputs: list[Output] | None = None,
        mcp_client: "MCPClient | None" = None,
        operating_hours: OperatingHoursConfig | None = None,
    ):
        """Initialize the scheduler.

        Args:
            playlist: Playlist configuration with cards
            context: Optional shared context for cards
            outputs: Optional list of output targets
            mcp_client: Optional MCP client for remote control
            operating_hours: Optional operating hours configuration
        """
        self.playlist = playlist
        self.context = context or CardContext()
        self.outputs = outputs or []
        self.mcp_client = mcp_client
        self.operating_hours = operating_hours or OperatingHoursConfig()
        self.state = SchedulerState()
        self._transition_steps = 15  # Steps for crossfade transitions
        self._last_mcp_poll = 0.0  # Track last MCP poll time
        self._mcp_poll_interval = 2.0  # Seconds between MCP polls
        self._blank_frame: Frame = [[(0, 0, 0) for _ in range(WIDTH)] for _ in range(HEIGHT)]
        self._outside_hours_logged = False  # Avoid log spam

    def _create_card_from_config(self, card_config: CardConfig) -> Any:
        """Create a card instance from configuration.

        Args:
            card_config: Card configuration

        Returns:
            Card instance or None if creation failed
        """
        config = {
            "duration": card_config.duration,
            **card_config.config,
        }
        card = create_card(card_config.type, config)
        if card is None:
            logger.warning(f"Unknown card type: {card_config.type}")
        return card

    def _send_frame(self, frame: Frame) -> None:
        """Send a frame to all outputs."""
        for output in self.outputs:
            try:
                output.send_frame(frame)
            except Exception as e:
                logger.error(f"Error sending frame to output: {e}")
        self.state.last_frame = frame

    def _apply_transition(
        self,
        from_frame: Frame | None,
        to_frame: Frame,
        transition: str,
    ) -> Iterator[Frame]:
        """Apply a transition effect between frames.

        Args:
            from_frame: Previous frame (or None for first)
            to_frame: Next frame
            transition: Transition type name

        Yields:
            Transition frames
        """
        if from_frame is None or transition == "none":
            yield to_frame
            return

        if transition == "crossfade":
            yield from crossfade(from_frame, to_frame, self._transition_steps)
        else:
            # Unknown transition, just switch
            yield to_frame

    def _check_mcp_commands(self) -> bool:
        """Check for MCP commands if client is configured.

        Returns:
            True if there are pending MCP commands to execute
        """
        if not self.mcp_client:
            return False

        now = time.time()
        if now - self._last_mcp_poll < self._mcp_poll_interval:
            return self.mcp_client.has_pending_commands()

        self._last_mcp_poll = now
        self.mcp_client.check_for_commands()
        return self.mcp_client.has_pending_commands()

    def _play_mcp_cards(self) -> None:
        """Play all pending MCP cards."""
        if not self.mcp_client:
            return

        while self.mcp_client.has_pending_commands() and self.state.running:
            card = self.mcp_client.get_next_card()
            if card is None:
                continue

            logger.info(f"Playing MCP card: {card.card_type}")
            self._play_card_instance(card)

    def _play_card_instance(self, card: Card) -> None:
        """Play a card instance directly.

        Args:
            card: Card instance to play
        """
        try:
            first_frame = True
            for frame, delay in card.frames(self.context):
                if not self.state.running:
                    break

                # Apply transition for first frame
                if first_frame:
                    for t_frame in self._apply_transition(
                        self.state.last_frame, frame, "crossfade"
                    ):
                        self._send_frame(t_frame)
                        time.sleep(0.03)  # ~30fps for transitions
                    first_frame = False
                else:
                    self._send_frame(frame)

                if delay > 0:
                    time.sleep(delay)

        except Exception as e:
            logger.error(f"Error playing card: {e}")

    def run_once(self) -> None:
        """Run through the playlist once."""
        if not self.playlist.cards:
            logger.warning("No cards in playlist")
            return

        self.state.running = True
        self.state.current_card_index = 0

        for i, card_config in enumerate(self.playlist.cards):
            if not self.state.running:
                break

            self.state.current_card_index = i
            self._play_card(card_config)
            self.state.cards_played += 1

        self.state.running = False

    def run_loop(self) -> None:
        """Run the playlist in an infinite loop."""
        if not self.playlist.cards:
            logger.warning("No cards in playlist")
            return

        self.state.running = True

        while self.state.running:
            # Check operating hours
            if not is_within_operating_hours(self.operating_hours):
                if not self._outside_hours_logged:
                    logger.info("Outside operating hours - display off")
                    self._outside_hours_logged = True
                    # Clear any pending MCP commands when going outside hours
                    if self.mcp_client:
                        self.mcp_client._pending_commands.clear()
                    # Turn off Twinkly devices properly (not just blank frame)
                    for output in self.outputs:
                        if hasattr(output, "turn_off"):
                            output.turn_off()
                # Sleep until next check
                time.sleep(60)  # Check every minute
                continue

            # We're within operating hours
            if self._outside_hours_logged:
                logger.info("Within operating hours - resuming display")
                self._outside_hours_logged = False
                # Turn Twinkly devices back on (realtime mode)
                for output in self.outputs:
                    if hasattr(output, "turn_on"):
                        output.turn_on()

            for i, card_config in enumerate(self.playlist.cards):
                if not self.state.running:
                    break

                # Re-check operating hours before each card
                if not is_within_operating_hours(self.operating_hours):
                    break  # Exit inner loop, will be caught by outer loop

                self.state.current_card_index = i
                self._play_card(card_config)
                self.state.cards_played += 1

    def _play_card(self, card_config: CardConfig) -> None:
        """Play a single card.

        Args:
            card_config: Card configuration
        """
        card = self._create_card_from_config(card_config)
        if card is None:
            logger.warning(f"Skipping unknown card type: {card_config.type}")
            return

        logger.info(f"Playing card: {card_config.type} for {card_config.duration}s")
        self.state.mcp_interrupt = False

        try:
            first_frame = True
            for frame, delay in card.frames(self.context):
                if not self.state.running:
                    break

                # Check for MCP commands - interrupt current card if any
                if self._check_mcp_commands():
                    logger.info(f"MCP command received, interrupting {card_config.type}")
                    self.state.mcp_interrupt = True
                    self._play_mcp_cards()
                    # After MCP cards, break out to resume playlist
                    break

                # Apply transition for first frame
                if first_frame:
                    transition_type = card_config.transition
                    for t_frame in self._apply_transition(
                        self.state.last_frame, frame, transition_type
                    ):
                        self._send_frame(t_frame)
                        if transition_type != "none":
                            time.sleep(0.03)  # ~30fps for transitions
                    first_frame = False
                else:
                    self._send_frame(frame)

                if delay > 0:
                    time.sleep(delay)

        except Exception as e:
            logger.error(f"Error playing card {card_config.type}: {e}")
            # Continue to next card

    def stop(self) -> None:
        """Stop the scheduler."""
        self.state.running = False

    def frames(self) -> Iterator[tuple[Frame, float]]:
        """Generate frames from the playlist without outputs.

        This is useful for testing or when you want to handle
        frame output yourself.

        Yields:
            Tuples of (frame, delay)
        """
        if not self.playlist.cards:
            return

        for card_config in self.playlist.cards:
            card = self._create_card_from_config(card_config)
            if card is None:
                continue

            try:
                first_frame = True
                for frame, delay in card.frames(self.context):
                    if first_frame and self.state.last_frame is not None:
                        # Yield transition frames
                        transition_type = card_config.transition
                        if transition_type == "crossfade":
                            for t_frame in crossfade(
                                self.state.last_frame, frame, self._transition_steps
                            ):
                                yield t_frame, 0.03
                        first_frame = False

                    self.state.last_frame = frame
                    yield frame, delay

            except Exception as e:
                logger.error(f"Error generating frames for {card_config.type}: {e}")
