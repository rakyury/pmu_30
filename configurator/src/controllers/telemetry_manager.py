"""
Telemetry Manager - centralized control of telemetry streaming.

This class manages telemetry stream lifecycle:
- Start/stop streaming
- Automatic pause/resume around blocking operations
- State tracking and logging
- Auto-restart after config operations

Usage:
    manager = TelemetryManager(device_controller)

    # Simple start/stop
    manager.start(rate_hz=10)
    manager.stop()

    # Context manager for operations that need to pause telemetry
    with manager.paused("config_upload"):
        device_controller.upload_binary_config(data)
    # Telemetry auto-restarts here

    # Check state
    if manager.is_streaming:
        print("Telemetry active")
"""

import logging
import time
from contextlib import contextmanager
from enum import Enum
from typing import TYPE_CHECKING, Optional
from dataclasses import dataclass, field
from datetime import datetime

if TYPE_CHECKING:
    from controllers.device_controller import DeviceController

logger = logging.getLogger(__name__)


class TelemetryState(Enum):
    """Telemetry streaming states."""
    STOPPED = "stopped"
    STARTING = "starting"
    STREAMING = "streaming"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class TelemetryStats:
    """Statistics about telemetry streaming."""
    packets_received: int = 0
    last_packet_time: Optional[datetime] = None
    pause_count: int = 0
    restart_count: int = 0
    errors: int = 0
    current_rate_hz: int = 10


class TelemetryManager:
    """Centralized telemetry stream management.

    Provides a clean interface for managing telemetry streams with:
    - Explicit state tracking (stopped, streaming, paused)
    - Context manager for auto-restart after operations
    - Statistics and logging
    - Graceful error handling
    """

    def __init__(self, device_controller: "DeviceController"):
        """Initialize TelemetryManager.

        Args:
            device_controller: The DeviceController instance to manage
        """
        self._controller = device_controller
        self._state = TelemetryState.STOPPED
        self._pause_reason: Optional[str] = None
        self._rate_hz = 10
        self._stats = TelemetryStats()
        self._was_streaming_before_pause = False

    @property
    def state(self) -> TelemetryState:
        """Current telemetry state."""
        return self._state

    @property
    def is_streaming(self) -> bool:
        """Check if telemetry is actively streaming."""
        return self._state == TelemetryState.STREAMING

    @property
    def is_paused(self) -> bool:
        """Check if telemetry is paused."""
        return self._state == TelemetryState.PAUSED

    @property
    def pause_reason(self) -> Optional[str]:
        """Get reason for current pause, or None if not paused."""
        return self._pause_reason if self._state == TelemetryState.PAUSED else None

    @property
    def stats(self) -> TelemetryStats:
        """Get telemetry statistics."""
        return self._stats

    def start(self, rate_hz: int = 10) -> bool:
        """Start telemetry streaming.

        Args:
            rate_hz: Telemetry rate in Hz (default 10)

        Returns:
            True if started successfully, False otherwise
        """
        if not self._controller.is_connected():
            logger.warning("Cannot start telemetry: not connected")
            return False

        if self._state == TelemetryState.STREAMING:
            logger.debug("Telemetry already streaming")
            return True

        self._state = TelemetryState.STARTING
        self._rate_hz = rate_hz

        try:
            self._controller.subscribe_telemetry(rate_hz=rate_hz)
            self._state = TelemetryState.STREAMING
            self._stats.restart_count += 1
            logger.info(f"Telemetry started at {rate_hz}Hz")
            return True
        except Exception as e:
            self._state = TelemetryState.ERROR
            self._stats.errors += 1
            logger.error(f"Failed to start telemetry: {e}")
            return False

    def stop(self) -> bool:
        """Stop telemetry streaming.

        Returns:
            True if stopped successfully, False otherwise
        """
        if self._state == TelemetryState.STOPPED:
            logger.debug("Telemetry already stopped")
            return True

        try:
            self._controller.unsubscribe_telemetry()
            self._state = TelemetryState.STOPPED
            self._pause_reason = None
            logger.info("Telemetry stopped")
            return True
        except Exception as e:
            self._stats.errors += 1
            logger.error(f"Failed to stop telemetry: {e}")
            return False

    def pause(self, reason: str) -> bool:
        """Pause telemetry streaming.

        Args:
            reason: Reason for pausing (for logging/debugging)

        Returns:
            True if paused successfully, False otherwise
        """
        self._was_streaming_before_pause = self._state == TelemetryState.STREAMING

        if not self._was_streaming_before_pause:
            logger.debug(f"Telemetry pause requested ({reason}) but not streaming")
            self._state = TelemetryState.PAUSED
            self._pause_reason = reason
            return True

        try:
            self._controller.unsubscribe_telemetry()
            self._state = TelemetryState.PAUSED
            self._pause_reason = reason
            self._stats.pause_count += 1
            logger.info(f"Telemetry paused: {reason}")
            return True
        except Exception as e:
            self._stats.errors += 1
            logger.error(f"Failed to pause telemetry: {e}")
            return False

    def resume(self) -> bool:
        """Resume telemetry streaming after pause.

        Returns:
            True if resumed successfully, False otherwise
        """
        if self._state != TelemetryState.PAUSED:
            logger.debug("Telemetry resume requested but not paused")
            return True

        if not self._was_streaming_before_pause:
            logger.debug("Not resuming - wasn't streaming before pause")
            self._state = TelemetryState.STOPPED
            self._pause_reason = None
            return True

        reason = self._pause_reason
        self._pause_reason = None

        return self.start(rate_hz=self._rate_hz)

    @contextmanager
    def paused(self, reason: str):
        """Context manager for operations that need telemetry paused.

        Usage:
            with telemetry_manager.paused("config_upload"):
                device_controller.upload_binary_config(data)
            # Telemetry auto-restarts here

        Args:
            reason: Reason for pausing (for logging)

        Yields:
            None
        """
        self.pause(reason)
        try:
            yield
        finally:
            self.resume()

    def record_packet(self):
        """Record that a telemetry packet was received."""
        self._stats.packets_received += 1
        self._stats.last_packet_time = datetime.now()

    def on_connection_lost(self):
        """Handle connection lost event."""
        self._state = TelemetryState.STOPPED
        self._pause_reason = None
        logger.info("Telemetry stopped due to connection loss")

    def on_connection_restored(self):
        """Handle connection restored event - restart telemetry if it was streaming."""
        if self._was_streaming_before_pause or self._stats.restart_count > 0:
            logger.info("Connection restored, restarting telemetry")
            self.start(rate_hz=self._rate_hz)

    def get_status_string(self) -> str:
        """Get human-readable status string."""
        if self._state == TelemetryState.STREAMING:
            return f"Streaming at {self._rate_hz}Hz"
        elif self._state == TelemetryState.PAUSED:
            return f"Paused: {self._pause_reason}"
        elif self._state == TelemetryState.ERROR:
            return "Error"
        else:
            return "Stopped"
