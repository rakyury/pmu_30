"""
Device Controller for PMU-30

Handles communication with PMU-30 device via USB, Emulator, WiFi, Bluetooth, or CAN Bus.

Owner: R2 m-sport
© 2025 R2 m-sport. All rights reserved.
"""

import logging
import struct
import sys
import threading
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

import serial
import serial.tools.list_ports

# Add shared library to path for channel_config import
_shared_path = Path(__file__).parent.parent.parent.parent / "shared" / "python"
if str(_shared_path) not in sys.path:
    sys.path.insert(0, str(_shared_path))

from communication.protocol import MessageType, build_min_frame, MINFrameParser
from communication.telemetry import parse_telemetry
from binascii import crc32
from dataclasses import dataclass

# New modular components
from .transport import TransportFactory, MINSerialTransport
from .telemetry_manager import TelemetryManager, TelemetryState
from .protocol_handler import ConfigAssembler, ProtocolHandler
from .connection_recovery import ConnectionRecoveryMachine, ConnectionConfig, ConnectionState


logger = logging.getLogger(__name__)


@dataclass
class DeviceCapabilities:
    """Device hardware capabilities received from firmware.

    Replaces hardcoded values in ChannelDisplayService.
    Requested via GET_CAPABILITIES (0x30), response via CAPABILITIES (0x31).
    """
    device_type: int = 0        # 0=PMU-30, 1=PMU-30 Pro, 2=PMU-16 Mini
    fw_version: str = "0.0.0"   # Firmware version string
    output_count: int = 30      # Power output channels
    analog_input_count: int = 10  # Analog input channels
    digital_input_count: int = 8  # Digital input channels
    hbridge_count: int = 2      # H-Bridge channels
    can_bus_count: int = 2      # CAN bus interfaces

    @property
    def device_type_name(self) -> str:
        """Human-readable device type name."""
        names = {0: "PMU-30", 1: "PMU-30 Pro", 2: "PMU-16 Mini"}
        return names.get(self.device_type, f"Unknown ({self.device_type})")

    @classmethod
    def from_payload(cls, payload: bytes) -> "DeviceCapabilities":
        """Parse capabilities from firmware response payload.

        Payload format (10 bytes):
        [0] device_type, [1] fw_major, [2] fw_minor, [3] fw_patch,
        [4] output_count, [5] analog_input_count, [6] digital_input_count,
        [7] hbridge_count, [8] can_bus_count, [9] reserved
        """
        if len(payload) < 10:
            logger.warning(f"Capabilities payload too short: {len(payload)} bytes")
            return cls()

        return cls(
            device_type=payload[0],
            fw_version=f"{payload[1]}.{payload[2]}.{payload[3]}",
            output_count=payload[4],
            analog_input_count=payload[5],
            digital_input_count=payload[6],
            hbridge_count=payload[7],
            can_bus_count=payload[8],
        )


class DeviceController(QObject):
    """Controller for PMU-30 device communication."""

    # Signals
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    data_received = pyqtSignal(bytes)
    error = pyqtSignal(str)

    # New signals for telemetry and logs
    telemetry_received = pyqtSignal(object)  # TelemetryPacket
    log_received = pyqtSignal(int, str, str)  # level, source, message
    config_received = pyqtSignal(dict)  # Configuration dictionary
    boot_complete = pyqtSignal()  # Device finished boot/restart - config should be re-read

    # Auto-reconnect signals
    reconnecting = pyqtSignal(int, int)  # attempt, max_attempts
    reconnect_failed = pyqtSignal()  # all attempts exhausted

    def __init__(self):
        super().__init__()

        # Transport (T-MIN for USB Serial)
        self._transport = None
        self._config_assembler = ConfigAssembler()

        self._connection_type = None
        self._is_connected = False
        self._receive_thread = None
        self._stop_thread = threading.Event()
        self._telemetry_enabled = False

        # Telemetry manager for centralized control
        self._telemetry_manager = TelemetryManager(self)

        # Serial telemetry polling timer
        self._serial_poll_timer = QTimer()
        self._serial_poll_timer.timeout.connect(self._poll_serial_telemetry)

        # Config receive state
        self._config_event = threading.Event()

        # Config write state
        self._config_ack_event = threading.Event()
        self._config_ack_success = False
        self._config_ack_error = 0

        # Flash save state
        self._flash_ack_event = threading.Event()
        self._flash_ack_success = False

        # Atomic channel config update state
        self._channel_config_ack_event = threading.Event()
        self._channel_config_ack_success = False
        self._channel_config_ack_error_msg = ""

        # Binary config upload state
        self._binary_config_ack_event = threading.Event()
        self._binary_config_ack_success = False
        self._binary_config_ack_error = 0
        self._binary_config_channels_loaded = 0

        # PING/PONG health check state
        self._pong_event = threading.Event()

        # Device capabilities state
        self._capabilities_event = threading.Event()
        self._device_capabilities: Optional[DeviceCapabilities] = None

        # Connection Recovery Machine (replaces manual reconnect logic)
        self._recovery = ConnectionRecoveryMachine(
            connect_fn=self._do_connect,
            disconnect_fn=self._do_disconnect,
            health_check_fn=self.ping,
            config=ConnectionConfig(
                auto_reconnect=True,
                max_reconnect_attempts=10,
                initial_reconnect_delay=1.0,
                max_reconnect_delay=30.0,
                backoff_multiplier=1.5,
                health_check_enabled=False,  # Manual health checks for now
            )
        )
        # Wire up recovery callbacks to Qt signals
        self._recovery.on_state_changed = self._on_recovery_state_changed
        self._recovery.on_reconnecting = lambda attempt, max_attempts: self.reconnecting.emit(attempt, max_attempts)
        self._recovery.on_reconnect_failed = lambda: self.reconnect_failed.emit()

        # Legacy state for backward compatibility
        self._user_disconnected = False

    def is_connected(self) -> bool:
        """Check if device is connected."""
        return self._is_connected

    @property
    def telemetry(self) -> TelemetryManager:
        """Get telemetry manager for stream control.

        Usage:
            controller.telemetry.start(rate_hz=10)
            controller.telemetry.stop()

            # Auto-restart after operations:
            with controller.telemetry.paused("config_upload"):
                controller.upload_binary_config(data)
        """
        return self._telemetry_manager

    def set_auto_reconnect(self, enabled: bool, interval: float = 3.0, max_attempts: int = 10):
        """
        Configure auto-reconnect settings.

        Args:
            enabled: Enable/disable auto-reconnect
            interval: Seconds between reconnection attempts (initial delay)
            max_attempts: Maximum number of attempts (0 = unlimited)
        """
        self._recovery.configure(
            auto_reconnect=enabled,
            max_reconnect_attempts=max_attempts,
            initial_reconnect_delay=max(1.0, interval),
        )
        logger.info(f"Auto-reconnect: enabled={enabled}, interval={interval}s, max_attempts={max_attempts}")

    def is_auto_reconnect_enabled(self) -> bool:
        """Check if auto-reconnect is enabled."""
        return self._recovery._config.auto_reconnect

    def stop_reconnect(self):
        """Stop any ongoing reconnection attempts."""
        self._recovery._stop_reconnection()
        logger.info("Reconnection attempts stopped")

    @property
    def connection_state(self) -> ConnectionState:
        """Get current connection state from recovery machine."""
        return self._recovery.state

    def get_available_serial_ports(self) -> List[str]:
        """Get list of available serial ports."""

        ports = []
        for port in serial.tools.list_ports.comports():
            # Filter for STM32 devices or USB-Serial adapters
            port_str = f"{port.device} - {port.description}"
            ports.append(port_str)

        logger.debug(f"Found {len(ports)} serial ports")
        return ports

    def get_available_bluetooth_devices(self) -> List[str]:
        """Get list of available Bluetooth devices."""

        # TODO: Implement Bluetooth device discovery
        devices = []
        logger.debug("Bluetooth device discovery not yet implemented")
        return devices

    def connect(self, config: Dict[str, Any]) -> bool:
        """
        Connect to PMU-30 device.

        Args:
            config: Connection configuration dictionary with:
                - type: Connection type (USB Serial, Emulator, WiFi, Bluetooth, CAN Bus)
                - Additional type-specific parameters

        Returns:
            True if connection successful
        """
        self._user_disconnected = False
        return self._recovery.request_connect(config)

    def _do_connect(self, config: Dict[str, Any]) -> bool:
        """Internal connection implementation called by recovery machine.

        This performs the actual transport connection without triggering
        the recovery machine (which would cause recursion).
        """
        connection_type = config.get("type", "")

        try:
            # Use TransportFactory to create appropriate transport
            self._transport = TransportFactory.create(config)
            if not self._transport.connect():
                raise ConnectionError("Transport connect() returned False")

            self._connection_type = connection_type
            self._is_connected = True

            # Reset config assembler
            self._config_assembler.reset()

            # Start receive thread for async transports
            if connection_type in ("Emulator", "WiFi"):
                self._start_receive_thread()

            # Subscribe to telemetry after connection is established
            # Note: For Serial, telemetry starts after config is loaded (see _post_connection_setup)
            if connection_type == "Emulator":
                self.subscribe_telemetry()

            logger.info(f"Connected via {connection_type}")
            return True

        except Exception as e:
            error_msg = f"Connection failed: {str(e)}"
            logger.error(error_msg)
            self._transport = None
            return False

    def _do_disconnect(self):
        """Internal disconnect implementation called by recovery machine."""
        # Stop serial polling timer if running
        if self._serial_poll_timer.isActive():
            self._serial_poll_timer.stop()
            logger.debug("Stopped serial polling timer")

        # Stop receive thread
        self._stop_receive_thread()

        if self._transport:
            try:
                self._transport.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting: {e}")
            finally:
                self._transport = None

        self._is_connected = False
        self._telemetry_enabled = False

    def _on_recovery_state_changed(self, old_state: ConnectionState, new_state: ConnectionState):
        """Handle state changes from the recovery machine."""
        if new_state == ConnectionState.CONNECTED:
            self.connected.emit()
        elif new_state in (ConnectionState.DISCONNECTED, ConnectionState.SUSPENDED):
            self.disconnected.emit()
            if old_state == ConnectionState.CONNECTED:
                self.error.emit("Connection lost")

    def disconnect(self):
        """Disconnect from device (user-initiated)."""
        self._user_disconnected = True
        self._recovery.request_disconnect()
        logger.info("Disconnected from device (user-initiated)")


    def ping(self, timeout: float = 1.0) -> bool:
        """Send PING and wait for PONG response.

        Args:
            timeout: Maximum time to wait for PONG response

        Returns:
            True if PONG received within timeout, False otherwise
        """
        if not self._is_connected or not self._transport:
            return False

        self._pong_event.clear()

        # Use T-MIN queue_frame for reliable delivery
        if not self._queue_frame(MessageType.PING):
            return False

        # Wait for PONG by polling T-MIN
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                if isinstance(self._transport, MINSerialTransport):
                    frames = self._transport.poll()
                    for frame in frames:
                        if frame.min_id == MessageType.PONG:
                            return True
                        # Handle other messages
                        self._handle_message(frame.min_id, frame.payload)
                else:
                    # For async transports, wait on event
                    if self._pong_event.wait(0.1):
                        return True
            except Exception:
                pass
            time.sleep(0.01)

        return False

    def get_capabilities(self, timeout: float = 1.0) -> Optional[DeviceCapabilities]:
        """Request device capabilities.

        Args:
            timeout: Maximum time to wait for response

        Returns:
            DeviceCapabilities object or None if failed
        """
        if not self._is_connected or not self._transport:
            return None

        self._capabilities_event.clear()
        self._device_capabilities = None

        # Send GET_CAPABILITIES request
        if not self._queue_frame(MessageType.GET_CAPABILITIES):
            return None

        # Wait for CAPABILITIES response by polling T-MIN
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                if isinstance(self._transport, MINSerialTransport):
                    frames = self._transport.poll()
                    for frame in frames:
                        if frame.min_id == MessageType.CAPABILITIES:
                            self._device_capabilities = DeviceCapabilities.from_payload(frame.payload)
                            return self._device_capabilities
                        # Handle other messages
                        self._handle_message(frame.min_id, frame.payload)
                else:
                    # For async transports, wait on event
                    if self._capabilities_event.wait(0.1):
                        return self._device_capabilities
            except Exception as e:
                logger.warning(f"Error polling for capabilities: {e}")
            time.sleep(0.01)

        return None

    @property
    def capabilities(self) -> Optional[DeviceCapabilities]:
        """Get last received device capabilities (cached)."""
        return self._device_capabilities

    def _wait_for_device_ready(self, max_wait: float = 5.0, poll_interval: float = 0.5) -> bool:
        """Wait for device to become responsive using PING/PONG.

        After STOP_STREAM, firmware has a "dead period" where it doesn't respond.
        This method polls with PING until device responds with PONG.

        Args:
            max_wait: Maximum total wait time in seconds
            poll_interval: Time between PING attempts

        Returns:
            True if device responded, False if timeout
        """
        start_time = time.time()
        attempts = 0

        while time.time() - start_time < max_wait:
            attempts += 1
            if self.ping(timeout=poll_interval):
                logger.debug(f"Device ready after {attempts} PING attempt(s), "
                           f"{time.time() - start_time:.2f}s elapsed")
                return True
            # Small delay before next attempt
            time.sleep(0.1)

        logger.warning(f"Device not ready after {max_wait}s ({attempts} PING attempts)")
        return False

    def send_command(self, command: bytes) -> Optional[bytes]:
        """
        Send command to device and get response.

        Args:
            command: Command bytes to send

        Returns:
            Response bytes or None (empty bytes if async receive thread handles it)
        """
        if not self._is_connected or not self._transport:
            logger.warning("Cannot send command: not connected")
            return None

        try:
            if not self._transport.send(command):
                raise ConnectionError("Transport send() failed")

            # If receive thread is running, responses come via signals
            if self._receive_thread and self._receive_thread.is_alive():
                return b''

            # Synchronous receive for serial
            response = self._transport.receive(4096, timeout=2.0)
            return response or b''

        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as e:
            logger.error(f"Connection lost: {e}")
            self._handle_connection_lost()
            return None
        except Exception as e:
            error_msg = f"Communication error: {str(e)}"
            logger.error(error_msg)
            self.error.emit(error_msg)
            return None

    def read_configuration(self, timeout: float = 5.0) -> Optional[dict]:
        """
        Read configuration from device.

        Uses PMUSerialTransfer directly to avoid poll thread interference.

        Args:
            timeout: Timeout in seconds

        Returns:
            Configuration dictionary or None
        """
        if not self._is_connected:
            logger.warning("Cannot read config: not connected")
            return None

        if not isinstance(self._transport, MINSerialTransport):
            logger.error("Cannot read config - not USB Serial connection")
            return None

        logger.info("Reading configuration from device...")

        # Get port info before disconnecting
        port_name = self._transport.port.split(" - ")[0] if " - " in self._transport.port else self._transport.port
        baudrate = self._transport.baudrate

        # Stop serial polling timer
        polling_was_active = self._serial_poll_timer.isActive()
        if polling_was_active:
            self._serial_poll_timer.stop()
            logger.debug("Stopped polling timer for config read")

        # Disconnect transport to stop background poll thread
        logger.debug(f"Disconnecting transport for fresh serial access on {port_name}")
        self._transport.disconnect()
        time.sleep(0.5)  # Windows needs time to release COM port

        config = None
        try:
            # Use PMUSerialTransfer directly (same as test scripts)
            from serial_transfer_protocol import PMUSerialTransfer

            logger.debug(f"Opening SerialTransfer connection: {port_name} @ {baudrate}")
            pmu = PMUSerialTransfer(port_name, baudrate, timeout=timeout)

            if not pmu.connect():
                logger.error("Failed to open SerialTransfer connection")
                raise ConnectionError("Cannot connect to device")

            try:
                # STEP 1: Resync firmware parser
                logger.debug("Resync: sending garbage bytes to reset firmware parser...")
                pmu._port.write(b'\x81\x81\x81\x81')
                pmu._port.flush()
                time.sleep(0.1)
                pmu._port.reset_input_buffer()
                pmu._port.reset_output_buffer()

                # STEP 2: Stop telemetry stream (method already drains buffer)
                logger.debug("Stopping telemetry stream...")
                pmu.stop_stream()  # Drains up to 20 packets internally

                # STEP 3: Verify device is responsive
                if pmu.ping(timeout=1.0):
                    logger.debug("PING OK - device responsive")
                else:
                    logger.warning("No PONG response - device may be slow")

                # STEP 4: Read config
                logger.debug("Sending GET_CONFIG...")
                config_data = pmu.read_config()

                if config_data is None:
                    logger.error("Failed to read config - no response")
                else:
                    logger.debug(f"Received config: {len(config_data)} bytes")

                    # Parse binary config
                    from models.binary_config import BinaryConfigManager
                    binary_manager = BinaryConfigManager()
                    success, error = binary_manager.load_from_raw_bytes(config_data)

                    if not success:
                        logger.error(f"Failed to parse binary config: {error}")
                    else:
                        # Convert binary channels to UI config format
                        config = {"channels": []}
                        for ch in binary_manager.channels:
                            ch_dict = _channel_to_dict(ch)
                            if ch_dict:
                                config["channels"].append(ch_dict)

                        logger.info(f"Configuration received: {len(config_data)} bytes, {len(config['channels'])} channels")

            finally:
                pmu.disconnect()
                logger.debug("SerialTransfer connection closed")

        except Exception as e:
            logger.error(f"Config read error: {e}")

        # Reconnect transport
        time.sleep(0.1)
        logger.debug("Reconnecting transport...")
        if self._transport.connect():
            logger.debug("Transport reconnected")
        else:
            logger.error("Failed to reconnect transport!")
            self._is_connected = False

        # Restart polling timer if it was active
        if polling_was_active:
            self._serial_poll_timer.start()
            logger.debug("Restarted polling timer")

        return config

    def _restore_polling(self, was_active: bool):
        """Restore serial polling timer if it was active before."""
        if was_active and not self._serial_poll_timer.isActive():
            self._serial_poll_timer.start()
            logger.debug("Restored serial polling after config read")

    def update_firmware(self, firmware_path: str, progress_callback=None) -> bool:
        """
        Update device firmware.

        Args:
            firmware_path: Path to firmware file (.bin or .hex)
            progress_callback: Optional callback for progress updates

        Returns:
            True if successful
        """

        logger.info(f"Updating firmware from {firmware_path}...")

        # TODO: Implement firmware update protocol
        # - Enter bootloader mode
        # - Erase flash
        # - Write firmware sectors with progress
        # - Verify
        # - Reset device

        return False

    # --- New methods for telemetry and device control ---

    def _start_receive_thread(self):
        """Start background thread for receiving data (for socket transports)."""
        self._stop_thread.clear()
        self._receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._receive_thread.start()
        logger.debug("Receive thread started")

    def _stop_receive_thread(self):
        """Stop background receive thread."""
        self._stop_thread.set()
        if self._receive_thread:
            self._receive_thread.join(timeout=2.0)
            self._receive_thread = None
        logger.debug("Receive thread stopped")

    def _receive_loop(self):
        """Background loop for receiving data from socket transports."""
        from communication.protocol import MINFrameParser
        parser = MINFrameParser()

        logger.debug("Receive loop started")
        while not self._stop_thread.is_set():
            try:
                if not self._transport or not self._transport.is_connected():
                    logger.warning("Transport not connected in receive loop")
                    self._handle_connection_lost()
                    break

                # Try to receive data (non-blocking with short timeout)
                data = self._transport.receive(4096, timeout=0.01)

                if data:
                    logger.debug(f"Received {len(data)} bytes: {data[:50].hex()}...")
                    # Parse MIN frames and process messages
                    frames = parser.feed(data)
                    for min_id, payload, seq, is_transport in frames:
                        self._handle_message(min_id, payload)
                elif data == b'':
                    # Empty bytes means connection closed (for socket)
                    logger.warning("Connection closed by remote")
                    self._handle_connection_lost()
                    break

                time.sleep(0.01)  # 10ms polling interval

            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as e:
                if not self._stop_thread.is_set():
                    logger.warning(f"Connection error: {e}")
                    self._handle_connection_lost()
                    break
            except Exception as e:
                if not self._stop_thread.is_set():
                    logger.error(f"Receive error: {e}")
                    self._handle_connection_lost()
                    break

    def _handle_connection_lost(self):
        """Handle unexpected connection loss."""
        self._is_connected = False
        self._telemetry_enabled = False

        # Stop serial polling timer if running
        if self._serial_poll_timer.isActive():
            self._serial_poll_timer.stop()

        if self._transport:
            try:
                self._transport.disconnect()
            except:
                pass
            self._transport = None

        # Notify recovery machine (handles auto-reconnect if enabled)
        if not self._user_disconnected:
            self._recovery.handle_connection_lost()

    def _handle_message(self, msg_type: int, payload: bytes):
        """Handle incoming MIN protocol message.

        Args:
            msg_type: Message type (MIN command ID)
            payload: Message payload
        """
        try:
            # Debug: log all non-telemetry messages
            if msg_type != MessageType.TELEMETRY_DATA:
                logger.debug(f"RX msg_type=0x{msg_type:02X}, payload={len(payload)} bytes")

            if msg_type == MessageType.PONG:
                # PING response - signal the event
                self._pong_event.set()
                logger.debug("PONG received")

            elif msg_type == MessageType.TELEMETRY_DATA:
                telemetry = parse_telemetry(payload)
                self.telemetry_received.emit(telemetry)

            elif msg_type == MessageType.LOG_MESSAGE:
                # Use protocol handler to parse log message
                level, source, message = ProtocolHandler.parse_log_message(payload)
                if source or message:
                    self.log_received.emit(level, source, message)

            elif msg_type == MessageType.CONFIG_ACK:
                # Parse ACK: success (1B) + error_code (1B) + reserved (1B)
                if len(payload) >= 2:
                    self._config_ack_success = payload[0] == 1
                    self._config_ack_error = payload[1]
                else:
                    self._config_ack_success = True
                    self._config_ack_error = 0
                self._config_ack_event.set()
                logger.info(f"Config ACK received: success={self._config_ack_success}, error={self._config_ack_error}")

            elif msg_type == MessageType.FLASH_ACK:
                # Parse ACK: success (1B) + error_code (2B)
                if len(payload) >= 1:
                    self._flash_ack_success = payload[0] == 1
                else:
                    self._flash_ack_success = True
                self._flash_ack_event.set()
                logger.info(f"Flash save ACK received: success={self._flash_ack_success}")

            elif msg_type == MessageType.RESTART_ACK:
                logger.info("Restart ACK received")

            elif msg_type == MessageType.BOOT_COMPLETE:
                # Device finished boot/restart - emit signal to reload config
                logger.info("BOOT_COMPLETE received - device finished initialization")
                self.boot_complete.emit()

            elif msg_type == MessageType.OUTPUT_ACK:
                logger.debug("Output ACK received")

            elif msg_type == MessageType.CAPABILITIES:
                # Parse device capabilities response
                self._device_capabilities = DeviceCapabilities.from_payload(payload)
                self._capabilities_event.set()
                logger.info(f"Device capabilities: {self._device_capabilities.device_type_name}, "
                           f"FW v{self._device_capabilities.fw_version}, "
                           f"{self._device_capabilities.output_count} outputs, "
                           f"{self._device_capabilities.analog_input_count} analog inputs")

            elif msg_type == MessageType.CHANNEL_CONFIG_ACK:
                # Parse atomic channel config ACK
                from communication.protocol import FrameParser
                try:
                    channel_id, success, error_code, error_msg = FrameParser.parse_channel_config_ack(payload)
                    self._channel_config_ack_success = success
                    self._channel_config_ack_error_msg = error_msg
                    logger.info(f"Channel config ACK: channel={channel_id}, success={success}, error={error_msg}")
                except Exception as e:
                    logger.error(f"Failed to parse channel config ACK: {e}")
                    self._channel_config_ack_success = False
                    self._channel_config_ack_error_msg = str(e)
                self._channel_config_ack_event.set()

            elif msg_type == MessageType.BINARY_CONFIG_ACK:
                # Parse binary config ACK: success (1B) + error_code (1B) + channels_loaded (2B) + ...
                if len(payload) >= 4:
                    self._binary_config_ack_success = payload[0] == 1
                    self._binary_config_ack_error = payload[1]
                    self._binary_config_channels_loaded = payload[2] | (payload[3] << 8)
                else:
                    self._binary_config_ack_success = len(payload) >= 1 and payload[0] == 1
                    self._binary_config_ack_error = payload[1] if len(payload) >= 2 else 0
                    self._binary_config_channels_loaded = 0
                self._binary_config_ack_event.set()
                logger.info(f"Binary config ACK: success={self._binary_config_ack_success}, "
                           f"error={self._binary_config_ack_error}, channels={self._binary_config_channels_loaded}")

            elif msg_type == MessageType.CONFIG_DATA:
                # Use protocol handler to parse config chunk
                chunk_idx, total_chunks, chunk_data = ProtocolHandler.parse_config_chunk(payload)
                if total_chunks > 0:
                    logger.debug(f"CONFIG_DATA chunk {chunk_idx + 1}/{total_chunks}, {len(chunk_data)} bytes")

                    # Use ConfigAssembler to collect chunks
                    if self._config_assembler.add_chunk(chunk_idx, total_chunks, chunk_data):
                        self._config_event.set()

            else:
                logger.debug(f"Received message type 0x{msg_type:02X}, {len(payload)} bytes")

        except Exception as e:
            logger.error(f"Error handling message 0x{msg_type:02X}: {e}")

    def _queue_frame(self, cmd_id: int, payload: bytes = b'') -> bool:
        """Queue frame for reliable T-MIN delivery (auto-retransmit until ACK)."""
        if not self._is_connected or not self._transport:
            logger.warning("Cannot send: not connected")
            return False

        try:
            if isinstance(self._transport, MINSerialTransport):
                return self._transport.queue_frame(cmd_id, payload)
            else:
                # Fallback for non-T-MIN transports (socket)
                from communication.protocol import build_min_frame
                return self._transport.send(build_min_frame(cmd_id, payload))
        except Exception as e:
            logger.error(f"Queue frame error: {e}")
            self._handle_connection_lost()
            return False

    def _send_frame_unreliable(self, cmd_id: int, payload: bytes = b'') -> bool:
        """Send frame without ACK (for telemetry subscription commands)."""
        if not self._is_connected or not self._transport:
            logger.warning("Cannot send: not connected")
            return False

        try:
            if isinstance(self._transport, MINSerialTransport):
                return self._transport.send_frame(cmd_id, payload)
            else:
                from communication.protocol import build_min_frame
                return self._transport.send(build_min_frame(cmd_id, payload))
        except Exception as e:
            logger.error(f"Send frame error: {e}")
            self._handle_connection_lost()
            return False

    def _drain_serial(self, ser, duration_ms: int = 100):
        """Drain serial buffer for fixed duration (like tests do).

        Time-based drain is more reliable than read-until-empty because
        USB serial buffers may have asynchronous arrivals.
        """
        deadline = time.time() + (duration_ms / 1000.0)
        old_timeout = ser.timeout
        ser.timeout = 0.01
        while time.time() < deadline:
            ser.read(1024)
        ser.timeout = old_timeout
        ser.reset_input_buffer()

    def _direct_transact(self, ser, cmd: int, payload: bytes = b'',
                         timeout: float = 3.0, expected_cmd: int = None):
        """Send command via direct serial and wait for response (like tests do).

        Returns list of (cmd, payload, seq) tuples.
        """
        # Time-based drain before sending
        self._drain_serial(ser, 50)

        # Build and send simple MIN frame
        frame = build_min_frame(cmd, payload)
        ser.write(frame)
        ser.flush()

        # Small delay for USB VCP buffer
        time.sleep(0.08)

        # Read responses
        parser = MINFrameParser()
        start = time.time()
        results = []

        old_timeout = ser.timeout
        ser.timeout = 0.15
        try:
            while time.time() - start < timeout:
                chunk = ser.read(512)
                if chunk:
                    frames = parser.feed(chunk)
                    for cmd_rx, payload_rx, seq_rx, _ in frames:
                        # Skip telemetry DATA when looking for specific command
                        if cmd_rx == MessageType.TELEMETRY_DATA and expected_cmd and expected_cmd != MessageType.TELEMETRY_DATA:
                            continue
                        results.append((cmd_rx, payload_rx, seq_rx))
                        if expected_cmd is not None and cmd_rx == expected_cmd:
                            return results
        finally:
            ser.timeout = old_timeout

        return results

    def subscribe_telemetry(self, rate_hz: int = 10):
        """Subscribe to telemetry streaming.

        Note: Prefer using self.telemetry.start() for managed streaming
        with proper state tracking and auto-restart capabilities.
        """
        payload = struct.pack('<H', rate_hz)

        # Use T-MIN queue_frame for reliable delivery
        if self._queue_frame(MessageType.SUBSCRIBE_TELEMETRY, payload):
            self._telemetry_enabled = True
            # Sync TelemetryManager state
            self._telemetry_manager._state = TelemetryState.STREAMING
            self._telemetry_manager._rate_hz = rate_hz
            logger.info(f"Subscribed to telemetry at {rate_hz}Hz")

            # For T-MIN Serial, start polling timer to process incoming frames
            if self._connection_type == "USB Serial":
                poll_interval = max(20, 1000 // rate_hz // 2)  # Poll faster than telemetry rate
                self._serial_poll_timer.start(poll_interval)
                logger.info(f"Started T-MIN polling at {poll_interval}ms interval")

    def unsubscribe_telemetry(self):
        """Unsubscribe from telemetry streaming.

        Note: Prefer using self.telemetry.stop() for managed streaming
        with proper state tracking.
        """
        # Stop serial polling timer if running
        if self._serial_poll_timer.isActive():
            self._serial_poll_timer.stop()
            logger.info("Stopped T-MIN polling")

        # Use T-MIN queue_frame for reliable delivery
        if self._queue_frame(MessageType.UNSUBSCRIBE_TELEMETRY):
            self._telemetry_enabled = False
            # Sync TelemetryManager state (if not paused - pause handles its own state)
            if self._telemetry_manager._state != TelemetryState.PAUSED:
                self._telemetry_manager._state = TelemetryState.STOPPED
            logger.info("Unsubscribed from telemetry")

    def _poll_serial_telemetry(self):
        """Poll T-MIN transport for incoming frames (called by timer)."""
        if not self._is_connected or not self._transport:
            return

        try:
            if isinstance(self._transport, MINSerialTransport):
                # T-MIN: get all received frames from poll queue
                frames = self._transport.poll()
                for frame in frames:
                    self._handle_message(frame.min_id, frame.payload)
            else:
                # Fallback for socket transports
                from communication.protocol import MINFrameParser
                data = self._transport.receive(1024, timeout=0.01)
                if data:
                    if not hasattr(self, '_socket_parser'):
                        self._socket_parser = MINFrameParser()
                    parsed = self._socket_parser.feed(data)
                    for min_id, payload, seq, is_transport in parsed:
                        self._handle_message(min_id, payload)
        except Exception as e:
            logger.warning(f"T-MIN poll error: {e}")

    def set_output(self, output_index: int, state: bool) -> bool:
        """Set output state (on/off) via SET_OUTPUT command.

        Args:
            output_index: Output channel index (0-29)
            state: True for ON, False for OFF

        Returns:
            True if command was sent successfully
        """
        payload = struct.pack('<BB', output_index, 1 if state else 0)

        if self._queue_frame(MessageType.SET_OUTPUT, payload):
            logger.debug(f"Set output {output_index} = {'ON' if state else 'OFF'}")
            return True
        return False

    def upload_binary_config(self, binary_data: bytes, timeout: float = 5.0) -> bool:
        """Upload binary configuration to device and wait for ACK.

        Uses PMUSerialTransfer (COBS + CRC8) protocol - same as firmware.
        The existing transport is disconnected during upload to avoid conflicts.

        Args:
            binary_data: Binary config data (serialized channels)
            timeout: Timeout in seconds to wait for ACK

        Returns:
            True if config was uploaded successfully (ACK received)
        """
        if not self._is_connected:
            logger.warning("Cannot upload config: not connected")
            return False

        if not isinstance(self._transport, MINSerialTransport):
            logger.error("Cannot upload config - not USB Serial connection")
            return False

        # Get port info before disconnecting
        port_name = self._transport.port.split(" - ")[0] if " - " in self._transport.port else self._transport.port
        baudrate = self._transport.baudrate

        # CRITICAL: Stop QTimer
        polling_was_active = self._serial_poll_timer.isActive()
        if polling_was_active:
            self._serial_poll_timer.stop()
            logger.debug("Stopped polling timer for config upload")

        # CRITICAL: Fully disconnect transport to release serial port
        logger.debug(f"Disconnecting transport for fresh serial access on {port_name}")
        self._transport.disconnect()
        time.sleep(0.5)  # Allow port to be released (Windows needs more time)

        success = False
        try:
            # Use PMUSerialTransfer for proper protocol handling
            from serial_transfer_protocol import PMUSerialTransfer

            logger.debug(f"Opening SerialTransfer connection: {port_name} @ {baudrate}")
            pmu = PMUSerialTransfer(port_name, baudrate, timeout=timeout)

            if not pmu.connect():
                logger.error("Failed to open SerialTransfer connection")
                raise ConnectionError("Cannot connect to device")

            try:
                # STEP 1: Resync firmware parser - send garbage to trigger stale timeout
                # Firmware parser has 50ms stale packet timeout, after which it resets
                logger.debug("Resync: sending garbage bytes to reset firmware parser...")
                pmu._port.write(b'\x81\x81\x81\x81')  # STOP_BYTE sequence (invalid)
                pmu._port.flush()
                time.sleep(0.1)  # Wait for stale packet timeout (50ms)
                pmu._port.reset_input_buffer()
                pmu._port.reset_output_buffer()

                # STEP 2: Stop telemetry stream (method already drains buffer)
                logger.debug("Stopping telemetry stream...")
                pmu.stop_stream()  # Drains up to 20 packets internally

                # STEP 3: Verify device is responsive
                if pmu.ping(timeout=1.0):
                    logger.debug("PING OK - device responsive")
                else:
                    logger.warning("No PONG response - device may be slow")

                # STEP 4: Clear existing config first (workaround for firmware bug)
                # Firmware doesn't properly handle re-uploading when config exists
                # Uses proper ACK-based waiting (no magic sleeps!)
                logger.debug("Clearing existing config before upload...")
                clear_ok = pmu.clear_config()  # Waits for CLEAR_CONFIG_ACK (timeout=3s)
                if clear_ok:
                    logger.debug("Config cleared successfully (CLEAR_CONFIG_ACK received)")
                else:
                    logger.warning("Clear config: no ACK received (continuing anyway)")

                # STEP 5: Upload config
                logger.info(f"Uploading binary config: {len(binary_data)} bytes")
                pmu._port.reset_input_buffer()  # Clear any stale data before upload
                upload_success, channels = pmu.upload_config(binary_data)

                if upload_success:
                    logger.info(f"Binary config uploaded: {channels} channels loaded")
                    self._binary_config_channels_loaded = channels
                    success = True
                else:
                    logger.error("Config upload failed: no ACK received")

            finally:
                pmu.disconnect()
                logger.debug("SerialTransfer connection closed")

        except Exception as e:
            logger.error(f"Config upload error: {e}")

        # ================================================================
        # Reconnect transport
        # ================================================================
        time.sleep(0.1)  # Allow port to be released
        logger.debug("Reconnecting transport...")
        if self._transport.connect():
            logger.debug("Transport reconnected")
        else:
            logger.error("Failed to reconnect transport!")
            self._is_connected = False

        # Restart QTimer if it was active
        if polling_was_active:
            self._serial_poll_timer.start()
            logger.debug("Restarted polling timer")

        return success

    def save_to_flash(self, timeout: float = 5.0) -> bool:
        """Save current configuration to flash."""
        if not self._is_connected:
            logger.warning("Cannot save to flash: not connected")
            return False

        # Stop serial polling timer during operation
        polling_was_active = self._serial_poll_timer.isActive()
        if polling_was_active:
            self._serial_poll_timer.stop()
            logger.debug("Stopped T-MIN polling for flash save")

        # Reset ACK state
        self._flash_ack_event.clear()
        self._flash_ack_success = False

        if not self._queue_frame(MessageType.SAVE_TO_FLASH):
            logger.error("Failed to queue SAVE_TO_FLASH command")
            if polling_was_active:
                self._serial_poll_timer.start()
            return False

        logger.info("Save to flash requested, waiting for ACK...")

        try:
            # Wait for ACK by polling T-MIN
            start_time = time.time()
            while time.time() - start_time < timeout:
                if isinstance(self._transport, MINSerialTransport):
                    frames = self._transport.poll()
                    for frame in frames:
                        self._handle_message(frame.min_id, frame.payload)

                if self._flash_ack_event.is_set():
                    break

                time.sleep(0.05)

            if self._flash_ack_success:
                logger.info("Configuration saved to flash successfully")
                return True
            else:
                if not self._flash_ack_event.is_set():
                    logger.error(f"Timeout waiting for flash ACK ({timeout}s)")
                else:
                    logger.error("Flash save failed")
                return False
        finally:
            # Always restart polling timer if it was active
            if polling_was_active:
                self._serial_poll_timer.start()
                logger.debug("Restarted T-MIN polling after flash save")


# ============================================================================
# Helper Functions for Binary Config Conversion
# ============================================================================

def _channel_to_dict(channel) -> Optional[Dict[str, Any]]:
    """
    Convert binary Channel object to UI-compatible dict format.

    Args:
        channel: Channel object from binary_config.py

    Returns:
        Dict compatible with UI project_tree format
    """
    from channel_config import ChannelType, HwDevice, CH_REF_NONE

    # Channel type mapping (binary -> UI string)
    TYPE_MAP = {
        ChannelType.DIGITAL_INPUT: "digital_input",
        ChannelType.ANALOG_INPUT: "analog_input",
        ChannelType.FREQUENCY_INPUT: "frequency_input",
        ChannelType.CAN_INPUT: "can_rx",
        ChannelType.POWER_OUTPUT: "power_output",
        ChannelType.PWM_OUTPUT: "pwm_output",
        ChannelType.HBRIDGE: "hbridge",
        ChannelType.CAN_OUTPUT: "can_tx",
        ChannelType.TIMER: "timer",
        ChannelType.LOGIC: "logic",
        ChannelType.MATH: "math",
        ChannelType.TABLE_2D: "table_2d",
        ChannelType.TABLE_3D: "table_3d",
        ChannelType.FILTER: "filter",
        ChannelType.PID: "pid",
        ChannelType.NUMBER: "number",
        ChannelType.SWITCH: "switch",
        ChannelType.ENUM: "enum",
        ChannelType.COUNTER: "counter",
        ChannelType.HYSTERESIS: "hysteresis",
        ChannelType.FLIPFLOP: "flipflop",
    }

    ch_type_str = TYPE_MAP.get(channel.type)
    if not ch_type_str:
        logger.debug(f"Unknown channel type: {channel.type}")
        return None

    result = {
        "channel_id": channel.id,
        "channel_type": ch_type_str,
        "name": channel.name,
        "enabled": bool(channel.flags & 0x01),
    }

    # Add source_id if set
    logger.info(f"[DEBUG] _channel_to_dict: id={channel.id}, type={ch_type_str}, source_id={channel.source_id}, CH_REF_NONE={CH_REF_NONE}")
    if channel.source_id != CH_REF_NONE:
        result["source_channel"] = channel.source_id

    # Add hardware info
    if channel.hw_device != HwDevice.NONE:
        result["hw_device"] = channel.hw_device
        result["hw_index"] = channel.hw_index
        # Also save as pins[] for serialization compatibility
        result["pins"] = [channel.hw_index]

    # Parse type-specific config
    if channel.config:
        _parse_channel_config(result, ch_type_str, channel.config)

    return result


def _parse_channel_config(result: Dict, ch_type: str, config) -> None:
    """Parse type-specific channel config into UI dict format."""
    from channel_config import CH_REF_NONE

    # Hardware input channels
    if ch_type == "digital_input":
        # Preserve raw values for correct roundtrip (don't convert to bool)
        result["debounce_ms"] = int(getattr(config, 'debounce_ms', 0))
        result["active_high"] = int(getattr(config, 'active_high', 1))
        result["use_pullup"] = int(getattr(config, 'use_pullup', 1))

    elif ch_type == "analog_input":
        result["raw_min"] = getattr(config, 'raw_min', 0)
        result["raw_max"] = getattr(config, 'raw_max', 4095)
        result["scaled_min"] = getattr(config, 'scaled_min', 0)
        result["scaled_max"] = getattr(config, 'scaled_max', 1000)
        result["filter_ms"] = getattr(config, 'filter_ms', 0)
        result["samples"] = getattr(config, 'samples', 1)

    elif ch_type == "frequency_input":
        result["min_freq_hz"] = getattr(config, 'min_freq_hz', 0)
        result["max_freq_hz"] = getattr(config, 'max_freq_hz', 10000)
        result["edge_mode"] = getattr(config, 'edge_mode', 0)

    elif ch_type == "can_rx":
        result["can_id"] = getattr(config, 'can_id', 0)
        result["bus"] = getattr(config, 'bus', 0)
        result["is_extended"] = bool(getattr(config, 'is_extended', 0))
        result["start_bit"] = getattr(config, 'start_bit', 0)
        result["bit_length"] = getattr(config, 'bit_length', 8)

    # Hardware output channels
    elif ch_type == "power_output":
        # Extract ALL fields for correct roundtrip (match CfgPowerOutput_t)
        result["current_limit_ma"] = int(getattr(config, 'current_limit_ma', 0))
        result["inrush_limit_ma"] = int(getattr(config, 'inrush_limit_ma', 0))
        result["inrush_time_ms"] = int(getattr(config, 'inrush_time_ms', 0))
        result["retry_count"] = int(getattr(config, 'retry_count', 0))
        result["retry_delay_s"] = int(getattr(config, 'retry_delay_s', 0))
        result["pwm_frequency"] = int(getattr(config, 'pwm_frequency', 0))
        result["soft_start_ms"] = int(getattr(config, 'soft_start_ms', 0))
        result["flags"] = int(getattr(config, 'flags', 0))

    elif ch_type == "pwm_output":
        result["frequency_hz"] = getattr(config, 'frequency_hz', 1000)
        result["min_duty"] = getattr(config, 'min_duty', 0)
        result["max_duty"] = getattr(config, 'max_duty', 10000)

    elif ch_type == "hbridge":
        result["frequency_hz"] = getattr(config, 'frequency_hz', 1000)
        result["deadband_us"] = getattr(config, 'deadband_us', 0)

    # Virtual channels
    elif ch_type == "timer":
        result["timer_mode"] = _timer_mode_name(config.mode)
        result["start_channel"] = config.trigger_id if config.trigger_id != CH_REF_NONE else None
        # Convert delay_ms to hours/minutes/seconds
        total_seconds = config.delay_ms // 1000
        result["limit_hours"] = total_seconds // 3600
        result["limit_minutes"] = (total_seconds % 3600) // 60
        result["limit_seconds"] = total_seconds % 60

    elif ch_type == "logic":
        result["operation"] = _logic_op_name(config.operation)
        result["input_channels"] = [ch for ch in config.inputs[:config.input_count] if ch != CH_REF_NONE]
        result["compare_value"] = config.compare_value
        result["invert_output"] = bool(config.invert_output)

    elif ch_type == "filter":
        result["input_channel"] = config.input_id if config.input_id != CH_REF_NONE else None
        result["time_constant"] = config.time_constant_ms / 1000.0

    elif ch_type == "table_2d":
        result["x_axis_channel"] = config.input_id if config.input_id != CH_REF_NONE else None
        result["x_values"] = list(config.x_values[:config.point_count])
        result["output_values"] = list(config.y_values[:config.point_count])

    elif ch_type == "number":
        result["constant_value"] = config.value / 100.0
        result["min_value"] = config.min_value
        result["max_value"] = config.max_value
        result["step"] = config.step

    elif ch_type == "pid":
        result["setpoint_channel"] = config.setpoint_id if config.setpoint_id != CH_REF_NONE else None
        result["feedback_channel"] = config.feedback_id if config.feedback_id != CH_REF_NONE else None
        result["kp"] = config.kp / 1000.0
        result["ki"] = config.ki / 1000.0
        result["kd"] = config.kd / 1000.0
        result["output_min"] = config.output_min
        result["output_max"] = config.output_max

    elif ch_type == "math":
        result["operation"] = _math_op_name(config.operation)
        result["input_channels"] = [ch for ch in config.inputs[:config.input_count] if ch != CH_REF_NONE]
        result["constant"] = config.constant
        result["min_value"] = config.min_value
        result["max_value"] = config.max_value


def _timer_mode_name(mode: int) -> str:
    """Convert timer mode int to string."""
    modes = {0: "one_shot", 1: "retriggerable", 2: "delay", 3: "pulse", 4: "blink"}
    return modes.get(mode, "one_shot")


def _logic_op_name(op: int) -> str:
    """Convert logic operation int to string."""
    ops = {
        0x00: "and", 0x01: "or", 0x02: "xor", 0x03: "nand", 0x04: "nor",
        0x06: "is_true", 0x07: "is_false",
        0x10: "greater", 0x11: "greater_equal", 0x12: "less", 0x13: "less_equal",
        0x14: "equal", 0x15: "not_equal",
        0x20: "range", 0x21: "outside"
    }
    return ops.get(op, "is_true")


def _math_op_name(op: int) -> str:
    """Convert math operation int to string."""
    ops = {0: "add", 1: "sub", 2: "mul", 3: "div", 4: "min", 5: "max",
           6: "abs", 7: "neg", 8: "avg", 9: "scale", 10: "clamp"}
    return ops.get(op, "add")
