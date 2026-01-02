"""
Connection Recovery Machine for PMU-30

A state machine that handles connection lifecycle and automatic recovery:
- State machine pattern for reliable state transitions
- Exponential backoff for reconnection attempts
- Connection health monitoring via PING/PONG
- Clean separation of connection state logic

Owner: R2 m-sport
"""

import logging
import threading
import time
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Connection state machine states."""
    DISCONNECTED = auto()    # Not connected, not trying
    CONNECTING = auto()       # Initial connection attempt
    CONNECTED = auto()        # Connected and healthy
    RECONNECTING = auto()     # Lost connection, attempting recovery
    SUSPENDED = auto()        # User-initiated disconnect, no auto-reconnect


class ConnectionEvent(Enum):
    """Events that trigger state transitions."""
    CONNECT_REQUEST = auto()      # User requests connection
    CONNECT_SUCCESS = auto()       # Connection established
    CONNECT_FAILURE = auto()       # Connection attempt failed
    DISCONNECT_REQUEST = auto()    # User requests disconnect
    CONNECTION_LOST = auto()       # Unexpected connection loss
    HEALTH_CHECK_FAILED = auto()   # Device not responding to PING
    RECONNECT_SUCCESS = auto()     # Reconnection succeeded
    RECONNECT_EXHAUSTED = auto()   # Max reconnect attempts reached


@dataclass
class ConnectionConfig:
    """Configuration for connection recovery behavior."""
    # Reconnection settings
    auto_reconnect: bool = True
    max_reconnect_attempts: int = 10  # 0 = unlimited
    initial_reconnect_delay: float = 1.0  # seconds
    max_reconnect_delay: float = 30.0  # seconds
    backoff_multiplier: float = 1.5  # Exponential backoff factor

    # Health check settings
    health_check_enabled: bool = True
    health_check_interval: float = 10.0  # seconds
    health_check_timeout: float = 2.0  # seconds
    max_consecutive_failures: int = 3  # Trigger reconnect after N failures


@dataclass
class ConnectionStats:
    """Statistics about connection state."""
    state: ConnectionState = ConnectionState.DISCONNECTED
    connected_since: Optional[datetime] = None
    disconnected_at: Optional[datetime] = None
    reconnect_attempts: int = 0
    total_reconnects: int = 0
    last_health_check: Optional[datetime] = None
    consecutive_health_failures: int = 0


class ConnectionRecoveryMachine:
    """
    State machine for managing device connection lifecycle.

    States:
        DISCONNECTED -> CONNECTING -> CONNECTED
                                   -> RECONNECTING -> CONNECTED
                                                   -> DISCONNECTED
        CONNECTED -> SUSPENDED (user disconnect)

    Usage:
        recovery = ConnectionRecoveryMachine(
            connect_fn=controller.connect,
            disconnect_fn=controller.disconnect,
            health_check_fn=controller.ping
        )
        recovery.on_state_changed = update_ui

        # User connects
        recovery.request_connect(config)

        # Connection lost (call from error handler)
        recovery.handle_connection_lost()

        # User disconnects
        recovery.request_disconnect()
    """

    def __init__(
        self,
        connect_fn: Callable[[Dict[str, Any]], bool],
        disconnect_fn: Callable[[], None],
        health_check_fn: Callable[[float], bool],
        config: ConnectionConfig = None
    ):
        """
        Initialize the recovery machine.

        Args:
            connect_fn: Function to establish connection, returns success bool
            disconnect_fn: Function to close connection
            health_check_fn: Function to check connection health (e.g., ping), returns success bool
            config: Connection configuration
        """
        self._connect_fn = connect_fn
        self._disconnect_fn = disconnect_fn
        self._health_check_fn = health_check_fn
        self._config = config or ConnectionConfig()

        # State
        self._state = ConnectionState.DISCONNECTED
        self._lock = threading.RLock()
        self._stats = ConnectionStats()

        # Connection config for reconnection
        self._last_connection_config: Optional[Dict[str, Any]] = None

        # Reconnection state
        self._reconnect_thread: Optional[threading.Thread] = None
        self._stop_reconnect = threading.Event()
        self._current_reconnect_delay = self._config.initial_reconnect_delay

        # Health check state
        self._health_check_thread: Optional[threading.Thread] = None
        self._stop_health_check = threading.Event()

        # Callbacks
        self.on_state_changed: Optional[Callable[[ConnectionState, ConnectionState], None]] = None
        self.on_reconnecting: Optional[Callable[[int, int], None]] = None  # (attempt, max)
        self.on_reconnect_failed: Optional[Callable[[], None]] = None
        self.on_health_check_failed: Optional[Callable[[int], None]] = None  # (consecutive_failures)

    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
        with self._lock:
            return self._state

    @property
    def is_connected(self) -> bool:
        """Check if connection is active."""
        with self._lock:
            return self._state == ConnectionState.CONNECTED

    @property
    def stats(self) -> ConnectionStats:
        """Get connection statistics."""
        with self._lock:
            return ConnectionStats(
                state=self._stats.state,
                connected_since=self._stats.connected_since,
                disconnected_at=self._stats.disconnected_at,
                reconnect_attempts=self._stats.reconnect_attempts,
                total_reconnects=self._stats.total_reconnects,
                last_health_check=self._stats.last_health_check,
                consecutive_health_failures=self._stats.consecutive_health_failures
            )

    def configure(self, **kwargs):
        """Update configuration settings.

        Args:
            auto_reconnect: Enable/disable auto-reconnect
            max_reconnect_attempts: Maximum reconnection attempts
            initial_reconnect_delay: Initial delay before first reconnect
            max_reconnect_delay: Maximum delay between attempts
            backoff_multiplier: Exponential backoff factor
            health_check_enabled: Enable/disable health monitoring
            health_check_interval: Seconds between health checks
        """
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._config, key):
                    setattr(self._config, key, value)
                    logger.debug(f"Config updated: {key}={value}")

    # ========================================================================
    # Public API - State Transitions
    # ========================================================================

    def request_connect(self, config: Dict[str, Any]) -> bool:
        """Request connection to device.

        Args:
            config: Connection configuration dict

        Returns:
            True if connection attempt started
        """
        with self._lock:
            if self._state in (ConnectionState.CONNECTED, ConnectionState.CONNECTING):
                logger.warning(f"Cannot connect: already in state {self._state.name}")
                return False

            # Stop any ongoing reconnection
            self._stop_reconnection()

            # Transition to CONNECTING
            old_state = self._state
            self._state = ConnectionState.CONNECTING
            self._last_connection_config = config.copy()
            self._stats.state = self._state

        self._notify_state_change(old_state, ConnectionState.CONNECTING)

        # Attempt connection
        try:
            if self._connect_fn(config):
                self._handle_event(ConnectionEvent.CONNECT_SUCCESS)
                return True
            else:
                self._handle_event(ConnectionEvent.CONNECT_FAILURE)
                return False
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self._handle_event(ConnectionEvent.CONNECT_FAILURE)
            return False

    def request_disconnect(self):
        """Request graceful disconnection (user-initiated)."""
        with self._lock:
            if self._state == ConnectionState.DISCONNECTED:
                return

            # Stop reconnection and health checks
            self._stop_reconnection()
            self._stop_health_monitoring()

            old_state = self._state
            self._state = ConnectionState.SUSPENDED
            self._stats.state = self._state
            self._stats.disconnected_at = datetime.now()

        self._notify_state_change(old_state, ConnectionState.SUSPENDED)

        try:
            self._disconnect_fn()
        except Exception as e:
            logger.error(f"Disconnect error: {e}")

        with self._lock:
            self._state = ConnectionState.DISCONNECTED
            self._stats.state = self._state

        self._notify_state_change(ConnectionState.SUSPENDED, ConnectionState.DISCONNECTED)

    def handle_connection_lost(self):
        """Handle unexpected connection loss. Call from error handlers."""
        with self._lock:
            if self._state != ConnectionState.CONNECTED:
                logger.debug(f"Connection lost ignored: not in CONNECTED state ({self._state.name})")
                return

            self._stop_health_monitoring()

            old_state = self._state
            self._stats.disconnected_at = datetime.now()
            self._stats.consecutive_health_failures = 0

            if self._config.auto_reconnect and self._last_connection_config:
                self._state = ConnectionState.RECONNECTING
                self._stats.state = self._state
                self._stats.reconnect_attempts = 0
                self._current_reconnect_delay = self._config.initial_reconnect_delay

                self._notify_state_change(old_state, ConnectionState.RECONNECTING)
                self._start_reconnection()
            else:
                self._state = ConnectionState.DISCONNECTED
                self._stats.state = self._state
                self._notify_state_change(old_state, ConnectionState.DISCONNECTED)

    def force_reconnect(self):
        """Force immediate reconnection attempt."""
        with self._lock:
            if self._state != ConnectionState.CONNECTED:
                return

            self._stop_health_monitoring()

        # Disconnect and trigger reconnection
        try:
            self._disconnect_fn()
        except:
            pass

        self.handle_connection_lost()

    # ========================================================================
    # Internal - Event Handling
    # ========================================================================

    def _handle_event(self, event: ConnectionEvent):
        """Process state machine event."""
        with self._lock:
            old_state = self._state
            new_state = self._transition(old_state, event)

            if new_state == old_state:
                return

            self._state = new_state
            self._stats.state = new_state

            # Update stats based on transition
            if new_state == ConnectionState.CONNECTED:
                self._stats.connected_since = datetime.now()
                self._stats.consecutive_health_failures = 0
                if old_state == ConnectionState.RECONNECTING:
                    self._stats.total_reconnects += 1
            elif new_state in (ConnectionState.DISCONNECTED, ConnectionState.SUSPENDED):
                self._stats.disconnected_at = datetime.now()

        self._notify_state_change(old_state, new_state)

        # Trigger actions based on new state
        if new_state == ConnectionState.CONNECTED:
            self._start_health_monitoring()
        elif new_state == ConnectionState.RECONNECTING:
            self._start_reconnection()
        elif new_state == ConnectionState.DISCONNECTED:
            self._stop_reconnection()
            self._stop_health_monitoring()

    def _transition(self, state: ConnectionState, event: ConnectionEvent) -> ConnectionState:
        """Calculate next state based on current state and event."""
        transitions = {
            (ConnectionState.DISCONNECTED, ConnectionEvent.CONNECT_REQUEST): ConnectionState.CONNECTING,
            (ConnectionState.CONNECTING, ConnectionEvent.CONNECT_SUCCESS): ConnectionState.CONNECTED,
            (ConnectionState.CONNECTING, ConnectionEvent.CONNECT_FAILURE): ConnectionState.DISCONNECTED,
            (ConnectionState.CONNECTED, ConnectionEvent.DISCONNECT_REQUEST): ConnectionState.SUSPENDED,
            (ConnectionState.CONNECTED, ConnectionEvent.CONNECTION_LOST): ConnectionState.RECONNECTING,
            (ConnectionState.CONNECTED, ConnectionEvent.HEALTH_CHECK_FAILED): ConnectionState.RECONNECTING,
            (ConnectionState.RECONNECTING, ConnectionEvent.RECONNECT_SUCCESS): ConnectionState.CONNECTED,
            (ConnectionState.RECONNECTING, ConnectionEvent.RECONNECT_EXHAUSTED): ConnectionState.DISCONNECTED,
            (ConnectionState.RECONNECTING, ConnectionEvent.DISCONNECT_REQUEST): ConnectionState.SUSPENDED,
            (ConnectionState.SUSPENDED, ConnectionEvent.CONNECT_REQUEST): ConnectionState.CONNECTING,
        }

        return transitions.get((state, event), state)

    def _notify_state_change(self, old_state: ConnectionState, new_state: ConnectionState):
        """Notify listeners of state change."""
        logger.info(f"Connection state: {old_state.name} -> {new_state.name}")

        if self.on_state_changed:
            try:
                self.on_state_changed(old_state, new_state)
            except Exception as e:
                logger.error(f"State change callback error: {e}")

    # ========================================================================
    # Internal - Reconnection
    # ========================================================================

    def _start_reconnection(self):
        """Start reconnection background thread."""
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            return

        self._stop_reconnect.clear()
        self._reconnect_thread = threading.Thread(target=self._reconnect_loop, daemon=True)
        self._reconnect_thread.start()
        logger.info("Reconnection started")

    def _stop_reconnection(self):
        """Stop reconnection background thread."""
        self._stop_reconnect.set()
        if self._reconnect_thread:
            self._reconnect_thread.join(timeout=2.0)
            self._reconnect_thread = None
        logger.debug("Reconnection stopped")

    def _reconnect_loop(self):
        """Background loop for reconnection attempts with exponential backoff."""
        while not self._stop_reconnect.is_set():
            with self._lock:
                self._stats.reconnect_attempts += 1
                attempt = self._stats.reconnect_attempts
                max_attempts = self._config.max_reconnect_attempts
                delay = self._current_reconnect_delay

            # Check if max attempts reached
            if max_attempts > 0 and attempt > max_attempts:
                logger.warning(f"Max reconnection attempts ({max_attempts}) exhausted")
                self._handle_event(ConnectionEvent.RECONNECT_EXHAUSTED)
                if self.on_reconnect_failed:
                    try:
                        self.on_reconnect_failed()
                    except Exception as e:
                        logger.error(f"Reconnect failed callback error: {e}")
                break

            logger.info(f"Reconnection attempt {attempt}/{max_attempts or '∞'} (delay: {delay:.1f}s)")

            # Notify listeners
            if self.on_reconnecting:
                try:
                    self.on_reconnecting(attempt, max_attempts)
                except Exception as e:
                    logger.error(f"Reconnecting callback error: {e}")

            # Wait before attempting
            if self._stop_reconnect.wait(delay):
                break  # Stop requested

            # Attempt reconnection
            try:
                config = self._last_connection_config
                if config and self._connect_fn(config):
                    logger.info(f"Reconnection successful after {attempt} attempts")
                    self._handle_event(ConnectionEvent.RECONNECT_SUCCESS)
                    break
            except Exception as e:
                logger.debug(f"Reconnection attempt {attempt} failed: {e}")

            # Exponential backoff
            with self._lock:
                self._current_reconnect_delay = min(
                    self._current_reconnect_delay * self._config.backoff_multiplier,
                    self._config.max_reconnect_delay
                )

        logger.debug("Reconnect loop ended")

    # ========================================================================
    # Internal - Health Monitoring
    # ========================================================================

    def _start_health_monitoring(self):
        """Start health check background thread."""
        if not self._config.health_check_enabled:
            return

        if self._health_check_thread and self._health_check_thread.is_alive():
            return

        self._stop_health_check.clear()
        self._health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self._health_check_thread.start()
        logger.debug("Health monitoring started")

    def _stop_health_monitoring(self):
        """Stop health check background thread."""
        self._stop_health_check.set()
        if self._health_check_thread:
            self._health_check_thread.join(timeout=2.0)
            self._health_check_thread = None
        logger.debug("Health monitoring stopped")

    def _health_check_loop(self):
        """Background loop for periodic health checks."""
        while not self._stop_health_check.is_set():
            # Wait for next check interval
            if self._stop_health_check.wait(self._config.health_check_interval):
                break  # Stop requested

            # Skip if not connected
            with self._lock:
                if self._state != ConnectionState.CONNECTED:
                    break

            # Perform health check
            try:
                healthy = self._health_check_fn(self._config.health_check_timeout)

                with self._lock:
                    self._stats.last_health_check = datetime.now()

                    if healthy:
                        self._stats.consecutive_health_failures = 0
                    else:
                        self._stats.consecutive_health_failures += 1
                        failures = self._stats.consecutive_health_failures

                        logger.warning(f"Health check failed ({failures}/{self._config.max_consecutive_failures})")

                        if self.on_health_check_failed:
                            try:
                                self.on_health_check_failed(failures)
                            except Exception as e:
                                logger.error(f"Health check failed callback error: {e}")

                        if failures >= self._config.max_consecutive_failures:
                            logger.error("Max consecutive health check failures, triggering reconnect")
                            self._handle_event(ConnectionEvent.HEALTH_CHECK_FAILED)
                            break

            except Exception as e:
                logger.error(f"Health check error: {e}")

        logger.debug("Health check loop ended")
