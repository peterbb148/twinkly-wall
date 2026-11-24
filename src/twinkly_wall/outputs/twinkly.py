"""Twinkly device API client and frame output."""

import base64
import logging
import os
import time
from dataclasses import dataclass

import requests

from ..types import (
    HEIGHT,
    WIDTH,
    Frame,
    Orientation,
    apply_orientation,
    mount_rotation,
    rotate_frame,
)

logger = logging.getLogger(__name__)


@dataclass
class DeviceInfo:
    """Twinkly device information."""

    product_name: str
    hardware_version: str
    firmware_version: str
    mac: str
    uuid: str
    number_of_led: int
    led_profile: str  # RGB, RGBW, etc.


class TwinklyAPIError(Exception):
    """Error communicating with Twinkly device."""

    pass


class TwinklyClient:
    """Client for Twinkly REST API.

    Handles authentication, device info, and mode control.
    """

    def __init__(self, host: str, port: int = 80, timeout: float = 5.0):
        """Initialize the Twinkly client.

        Args:
            host: IP address or hostname of the Twinkly device
            port: HTTP port (default: 80)
            timeout: Request timeout in seconds
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.base_url = f"http://{host}:{port}/xled/v1"
        self._token: str | None = None
        self._token_expires: float = 0
        self._device_info: DeviceInfo | None = None

    def _request(
        self,
        method: str,
        endpoint: str,
        json_data: dict | None = None,
        data: bytes | None = None,
        auth: bool = True,
    ) -> dict | None:
        """Make an HTTP request to the device.

        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint (e.g., "/login")
            json_data: JSON body data
            data: Raw binary data
            auth: Whether to include auth token

        Returns:
            JSON response dict or None for binary responses
        """
        url = f"{self.base_url}{endpoint}"
        headers = {}

        if auth and self._token:
            headers["X-Auth-Token"] = self._token

        if data is not None:
            headers["Content-Type"] = "application/octet-stream"

        try:
            response = requests.request(
                method,
                url,
                json=json_data,
                data=data,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()

            if response.content:
                return response.json()
            return None

        except requests.exceptions.RequestException as e:
            raise TwinklyAPIError(f"Request failed: {e}") from e

    def login(self) -> None:
        """Authenticate with the device and get an auth token."""
        # Generate a random 32-byte challenge
        challenge = base64.b64encode(os.urandom(32)).decode("utf-8")

        result = self._request(
            "POST",
            "/login",
            json_data={"challenge": challenge},
            auth=False,
        )

        if not result or "authentication_token" not in result:
            raise TwinklyAPIError("Login failed: no token received")

        self._token = result["authentication_token"]
        expires_in = result.get("authentication_token_expires_in", 14400)
        self._token_expires = time.time() + expires_in

        # Verify the token
        self._request("POST", "/verify", json_data={})
        logger.info(f"Authenticated with Twinkly at {self.host}")

    def ensure_auth(self) -> None:
        """Ensure we have a valid auth token, refreshing if needed."""
        if not self._token or time.time() >= self._token_expires - 60:
            self.login()

    def logout(self) -> None:
        """Log out and invalidate the token."""
        if self._token:
            try:
                self._request("POST", "/logout", json_data={})
            except TwinklyAPIError:
                pass  # Ignore logout errors
            self._token = None

    def get_device_info(self) -> DeviceInfo:
        """Get device information.

        Returns:
            DeviceInfo object with device details
        """
        result = self._request("GET", "/gestalt", auth=False)

        if not result:
            raise TwinklyAPIError("Failed to get device info")

        self._device_info = DeviceInfo(
            product_name=result.get("product_name", "Unknown"),
            hardware_version=result.get("hw_id", "Unknown"),
            firmware_version=result.get("fw_family", "Unknown"),
            mac=result.get("mac", ""),
            uuid=result.get("uuid", ""),
            number_of_led=result.get("number_of_led", 0),
            led_profile=result.get("led_profile", "RGB"),
        )

        return self._device_info

    def get_mode(self) -> str:
        """Get current LED operation mode.

        Returns:
            Mode string: off, color, demo, effect, movie, playlist, rt
        """
        self.ensure_auth()
        result = self._request("GET", "/led/mode")
        return result.get("mode", "off") if result else "off"

    def set_mode(self, mode: str) -> None:
        """Set LED operation mode.

        Args:
            mode: One of: off, color, demo, effect, movie, playlist, rt
        """
        self.ensure_auth()
        self._request("POST", "/led/mode", json_data={"mode": mode})
        logger.debug(f"Set mode to: {mode}")

    def set_brightness(self, value: int) -> None:
        """Set LED brightness.

        Args:
            value: Brightness value 0-100
        """
        self.ensure_auth()
        self._request(
            "POST",
            "/led/out/brightness",
            json_data={"mode": "enabled", "type": "A", "value": max(0, min(100, value))},
        )

    def get_brightness(self) -> int:
        """Get current brightness.

        Returns:
            Brightness value 0-100
        """
        self.ensure_auth()
        result = self._request("GET", "/led/out/brightness")
        return result.get("value", 100) if result else 100


class TwinklyOutput:
    """Frame output target for Twinkly devices.

    Sends frames to the device using the realtime frame API.
    """

    def __init__(
        self,
        host: str,
        port: int = 80,
        brightness: int = 100,
        led_profile: str = "RGB",
        mirror_h: bool = False,
        mirror_v: bool = False,
    ):
        """Initialize Twinkly output.

        Args:
            host: IP address of Twinkly device
            port: HTTP port
            brightness: Initial brightness 0-100
            led_profile: LED color profile (RGB, RGBW)
            mirror_h: Mirror horizontally (flip left-right)
            mirror_v: Mirror vertically (flip top-bottom)
        """
        self.client = TwinklyClient(host, port)
        self.brightness = brightness
        self.led_profile = led_profile
        self.mirror_h = mirror_h
        self.mirror_v = mirror_v
        self.orientation = Orientation.horizontal
        self._frame_count = 0

    def start(self) -> None:
        """Initialize connection and set realtime mode."""
        # Get device info
        info = self.client.get_device_info()
        logger.info(
            f"Connected to {info.product_name} ({info.number_of_led} LEDs, {info.led_profile})"
        )
        self.led_profile = info.led_profile

        # Authenticate and set realtime mode
        self.client.login()
        self.client.set_brightness(self.brightness)
        self.client.set_mode("rt")
        logger.info("Twinkly set to realtime mode")

    def stop(self) -> None:
        """Turn off and disconnect."""
        try:
            self.client.set_mode("off")
            self.client.logout()
        except TwinklyAPIError:
            pass
        logger.info("Twinkly disconnected")

    def turn_off(self) -> None:
        """Turn off the LEDs (set mode to off)."""
        try:
            self.client.ensure_auth()
            self.client.set_mode("off")
            logger.info("Twinkly LEDs turned off")
        except TwinklyAPIError as e:
            logger.warning(f"Failed to turn off Twinkly: {e}")

    def turn_on(self) -> None:
        """Turn on the LEDs (set mode to realtime)."""
        try:
            self.client.ensure_auth()
            self.client.set_mode("rt")
            logger.info("Twinkly set to realtime mode")
        except TwinklyAPIError as e:
            logger.warning(f"Failed to turn on Twinkly: {e}")

    def _frame_to_bytes(self, frame: Frame) -> bytes:
        """Convert a frame to Twinkly binary format.

        The Twinkly Matrix 500 has two strips of 250 LEDs each:
        - Physical layout: 10 vertical strands × 50 LEDs per strand
        - Strip 1 (LEDs 0-249): Strands 4,3,2,1,0 (center to left), serpentine
        - Strip 2 (LEDs 250-499): Strands 5,6,7,8,9 (center to right), serpentine

        The frame comes in as 10 rows × 50 columns (HEIGHT=10, WIDTH=50) for
        horizontal display. We need to rotate it 90° clockwise to map to
        the physical vertical strand layout:
        - Frame row 0 (top) -> Physical strand 9 (rightmost)
        - Frame row 9 (bottom) -> Physical strand 0 (leftmost)
        - Frame column 0 (left) -> Physical LED position 0 (top of strand)
        - Frame column 49 (right) -> Physical LED position 49 (bottom of strand)

        After rotation: physical_strand = 9 - frame_row, led_pos = frame_col

        Args:
            frame: 2D array of RGB tuples [y][x], 10 rows × 50 cols

        Returns:
            Binary data for the frame
        """
        data = bytearray()
        if len(frame) != HEIGHT or any(len(row) != WIDTH for row in frame):
            raise ValueError(f"Twinkly frames must be {WIDTH}×{HEIGHT} after mapping")

        # After 90° clockwise rotation:
        # Physical strand = 9 - frame_row
        # LED position in strand = frame_col

        # Strip 1: Physical strands 4,3,2,1,0 in that order
        # strand 4 = frame_row 5, strand 3 = frame_row 6, etc.
        strip1_mapping = [(4, 5), (3, 6), (2, 7), (1, 8), (0, 9)]

        for strand_idx, (physical_strand, frame_row) in enumerate(strip1_mapping):
            if strand_idx % 2 == 0:
                # Even strand index in strip: LED 0 at bottom, so traverse cols in reverse
                for col in range(WIDTH - 1, -1, -1):
                    r, g, b = frame[frame_row][col]
                    if self.led_profile == "RGBW":
                        data.extend([r, g, b, 0])
                    else:
                        data.extend([r, g, b])
            else:
                # Odd strand index in strip: LED 0 at top, so traverse cols forward
                for col in range(WIDTH):
                    r, g, b = frame[frame_row][col]
                    if self.led_profile == "RGBW":
                        data.extend([r, g, b, 0])
                    else:
                        data.extend([r, g, b])

        # Strip 2: Physical strands 5,6,7,8,9 in that order
        # strand 5 = frame_row 4, strand 6 = frame_row 3, etc.
        strip2_mapping = [(5, 4), (6, 3), (7, 2), (8, 1), (9, 0)]

        for strand_idx, (physical_strand, frame_row) in enumerate(strip2_mapping):
            if strand_idx % 2 == 0:
                # Even strand index in strip: LED 0 at bottom, so traverse cols in reverse
                for col in range(WIDTH - 1, -1, -1):
                    r, g, b = frame[frame_row][col]
                    if self.led_profile == "RGBW":
                        data.extend([r, g, b, 0])
                    else:
                        data.extend([r, g, b])
            else:
                # Odd strand index in strip: LED 0 at top, so traverse cols forward
                for col in range(WIDTH):
                    r, g, b = frame[frame_row][col]
                    if self.led_profile == "RGBW":
                        data.extend([r, g, b, 0])
                    else:
                        data.extend([r, g, b])

        return bytes(data)

    def send_frame(self, frame: Frame) -> None:
        """Send a frame to the Twinkly device.

        Args:
            frame: 2D array of RGB tuples
        """
        self.client.ensure_auth()

        viewed = apply_orientation(
            frame, self.orientation, mirror_h=self.mirror_h, mirror_v=self.mirror_v
        )
        # Undo the physical mount rotation before encoding the fixed strand layout.
        rotation = mount_rotation(self.orientation)
        if rotation:
            viewed = rotate_frame(viewed, -rotation)
        frame_data = self._frame_to_bytes(viewed)

        try:
            self.client._request(
                "POST",
                "/led/rt/frame",
                data=frame_data,
            )
            self._frame_count += 1
        except TwinklyAPIError as e:
            logger.warning(f"Failed to send frame: {e}")
            # Try to recover by re-authenticating
            try:
                self.client.login()
                self.client.set_mode("rt")
            except TwinklyAPIError:
                pass
