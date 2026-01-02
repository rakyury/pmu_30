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

import serial.tools.list_ports

# Add shared library to path for channel_config import
_shared_path = Path(__file__).parent.parent.parent.parent / "shared" / "python"
if str(_shared_path) not in sys.path:
    sys.path.insert(0, str(_shared_path))

from communication.protocol import MessageType
from communication.telemetry import parse_telemetry

# New modular components
from .transport import TransportFactory
from .protocol_handler import ProtocolHandler, ConfigAssembler


logger = logging.getLogger(__name__)


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

        # Transport and protocol handlers
        self._transport = None
        self._protocol = ProtocolHandler()
        self._config_assembler = ConfigAssembler()

        self._connection_type = None
        self._is_connected = False
        self._receive_thread = None
        self._stop_thread = threading.Event()
        self._telemetry_enabled = False

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

        # Auto-reconnect state
        self._auto_reconnect_enabled = True
        self._reconnect_interval = 3.0  # seconds between attempts
        self._max_reconnect_attempts = 10
        self._last_connection_config = None
        self._reconnect_thread = None
        self._reconnect_attempt = 0
        self._stop_reconnect = threading.Event()
        self._user_disconnected = False  # True if user explicitly disconnected

    def is_connected(self) -> bool:
        """Check if device is connected."""
        return self._is_connected

    def set_auto_reconnect(self, enabled: bool, interval: float = 3.0, max_attempts: int = 10):
        """
        Configure auto-reconnect settings.

        Args:
            enabled: Enable/disable auto-reconnect
            interval: Seconds between reconnection attempts
            max_attempts: Maximum number of attempts (0 = unlimited)
        """
        self._auto_reconnect_enabled = enabled
        self._reconnect_interval = max(1.0, interval)
        self._max_reconnect_attempts = max(0, max_attempts)
        logger.info(f"Auto-reconnect: enabled={enabled}, interval={interval}s, max_attempts={max_attempts}")

    def is_auto_reconnect_enabled(self) -> bool:
        """Check if auto-reconnect is enabled."""
        return self._auto_reconnect_enabled

    def stop_reconnect(self):
        """Stop any ongoing reconnection attempts."""
        self._stop_reconnect.set()
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            self._reconnect_thread.join(timeout=1.0)
        self._reconnect_thread = None
        self._reconnect_attempt = 0
        logger.info("Reconnection attempts stopped")

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
        # Stop any ongoing reconnection attempts
        self.stop_reconnect()

        connection_type = config.get("type", "")

        try:
            # Use TransportFactory to create appropriate transport
            self._transport = TransportFactory.create(config)
            if not self._transport.connect():
                raise ConnectionError("Transport connect() returned False")

            self._connection_type = connection_type
            self._is_connected = True
            self._user_disconnected = False
            self._last_connection_config = config.copy()  # Save for auto-reconnect
            self._reconnect_attempt = 0

            # Clear protocol buffers
            self._protocol.clear_buffer()
            self._config_assembler.reset()

            # Start receive thread for async transports
            if connection_type in ("Emulator", "WiFi"):
                self._start_receive_thread()

            self.connected.emit()

            # Subscribe to telemetry after connection is established
            # Note: For Serial, telemetry starts after config is loaded (see _post_connection_setup)
            if connection_type == "Emulator":
                self.subscribe_telemetry()

            logger.info(f"Connected via {connection_type}")
            return True

        except Exception as e:
            error_msg = f"Connection failed: {str(e)}"
            logger.error(error_msg)
            self.error.emit(error_msg)
            self._transport = None
            return False

    def disconnect(self):
        """Disconnect from device (user-initiated)."""
        # Mark as user-disconnected to prevent auto-reconnect
        self._user_disconnected = True

        # Stop any ongoing reconnection attempts
        self.stop_reconnect()

        # Stop serial polling timer if running
        if self._serial_poll_timer.isActive():
            self._serial_poll_timer.stop()
            logger.debug("Stopped serial polling timer")

        # Stop receive thread first
        self._stop_receive_thread()

        if self._transport:
            try:
                self._transport.disconnect()
                self._transport = None
                self._is_connected = False
                self._telemetry_enabled = False
                self._protocol.clear_buffer()
                self.disconnected.emit()

                logger.info("Disconnected from device (user-initiated)")

            except Exception as e:
                logger.error(f"Error disconnecting: {e}")

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

        Args:
            timeout: Timeout in seconds

        Returns:
            Configuration dictionary or None
        """
        if not self._is_connected:
            logger.warning("Cannot read config: not connected")
            return None

        logger.info("Reading configuration from device...")

        # Stop telemetry stream first to avoid interference
        stop_frame = self._protocol.build_frame(MessageType.UNSUBSCRIBE_TELEMETRY)
        self._send_frame(stop_frame)
        time.sleep(0.5)  # Give device time to stop stream and flush

        # Clear any pending data from transport buffer (multiple attempts)
        if hasattr(self._transport, 'receive'):
            for _ in range(5):
                try:
                    data = self._transport.receive(4096, timeout=0.1)
                    if not data:
                        break
                    logger.debug(f"Cleared {len(data)} bytes from buffer")
                    time.sleep(0.05)
                except Exception:
                    break

        # Clear protocol handler's internal buffer
        self._protocol.clear_buffer()

        # Reset config assembler
        self._config_assembler.reset()
        self._config_event.clear()

        # Send GET_CONFIG command using protocol handler
        frame = self._protocol.build_frame(MessageType.GET_CONFIG)
        logger.debug(f"Sending GET_CONFIG frame: {frame.hex()}")
        if not self._send_frame(frame):
            logger.error("Failed to send GET_CONFIG")
            return None
        logger.debug("GET_CONFIG sent successfully, waiting for response...")

        # Small delay to let device prepare response
        time.sleep(0.3)

        # For Serial transport, do synchronous receive (no receive thread running)
        if self._connection_type == "USB Serial":
            start_time = time.time()
            while time.time() - start_time < timeout:
                # Read available data with longer timeout for complete frames
                data = self._transport.receive(4096, timeout=1.0)
                if data:
                    logger.debug(f"Serial RX: {len(data)} bytes: {data[:50].hex()}...")
                    # Feed to protocol handler
                    messages = self._protocol.feed_data(data)
                    for msg in messages:
                        self._handle_message(msg.msg_type, msg.payload)

                    # Check if config complete
                    if self._config_event.is_set():
                        break
                else:
                    time.sleep(0.05)

            # Check if we exited due to timeout
            if not self._config_event.is_set():
                logger.error(f"Timeout waiting for config ({timeout}s) - no CONFIG_DATA received")
                return None
        else:
            # For async transports (Emulator, WiFi), wait for event from receive thread
            if not self._config_event.wait(timeout):
                logger.error(f"Timeout waiting for config ({timeout}s)")
                return None

        # Get assembled config data
        config_data = self._config_assembler.get_data()
        if config_data is None:
            logger.error("Failed to assemble config chunks - incomplete data")
            return None

        # Parse binary config (raw channel data without file header)
        try:
            from models.binary_config import BinaryConfigManager
            binary_manager = BinaryConfigManager()
            success, error = binary_manager.load_from_raw_bytes(config_data)

            if not success:
                logger.error(f"Failed to parse binary config: {error}")
                return None

            # Convert binary channels to UI config format
            config = {"channels": []}
            for ch in binary_manager.channels:
                ch_dict = _channel_to_dict(ch)
                if ch_dict:
                    config["channels"].append(ch_dict)

            logger.info(f"Configuration received: {len(config_data)} bytes, {len(config['channels'])} channels")
            return config

        except Exception as e:
            logger.error(f"Error processing binary config: {e}")
            return None

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
        """Start background thread for receiving data."""
        self._stop_thread.clear()
        self._protocol.clear_buffer()
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
        """Background loop for receiving data from device."""
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
                    # Feed data to protocol handler and process messages
                    messages = self._protocol.feed_data(data)
                    for msg in messages:
                        self._handle_message(msg.msg_type, msg.payload)
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
        self._protocol.clear_buffer()
        self.disconnected.emit()
        self.error.emit("Connection lost")

        # Start auto-reconnect if enabled and not user-disconnected
        if (self._auto_reconnect_enabled and
            not self._user_disconnected and
            self._last_connection_config):
            self._start_reconnect()

    def _start_reconnect(self):
        """Start auto-reconnect background thread."""
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            return  # Already reconnecting

        self._stop_reconnect.clear()
        self._reconnect_attempt = 0
        self._reconnect_thread = threading.Thread(target=self._reconnect_loop, daemon=True)
        self._reconnect_thread.start()
        logger.info("Auto-reconnect started")

    def _reconnect_loop(self):
        """Background loop for reconnection attempts."""
        while not self._stop_reconnect.is_set():
            self._reconnect_attempt += 1

            # Check if max attempts reached
            if self._max_reconnect_attempts > 0 and self._reconnect_attempt > self._max_reconnect_attempts:
                logger.warning(f"Max reconnection attempts ({self._max_reconnect_attempts}) reached")
                self.reconnect_failed.emit()
                break

            logger.info(f"Reconnection attempt {self._reconnect_attempt}/{self._max_reconnect_attempts or '∞'}")
            self.reconnecting.emit(self._reconnect_attempt, self._max_reconnect_attempts)

            # Wait before attempting
            if self._stop_reconnect.wait(self._reconnect_interval):
                break  # Stop requested

            # Try to reconnect using TransportFactory
            try:
                config = self._last_connection_config
                connection_type = config.get("type", "")

                self._transport = TransportFactory.create(config)
                if not self._transport.connect():
                    raise ConnectionError("Transport connect() returned False")

                # Success!
                self._connection_type = connection_type
                self._is_connected = True
                self._reconnect_attempt = 0
                self._protocol.clear_buffer()

                # Start receive thread for async transports
                if connection_type in ("Emulator", "WiFi"):
                    self._start_receive_thread()

                self.connected.emit()

                # Resubscribe to telemetry
                if connection_type == "Emulator":
                    self.subscribe_telemetry()

                logger.info(f"Reconnected via {connection_type}")
                break

            except Exception as e:
                logger.debug(f"Reconnection attempt {self._reconnect_attempt} failed: {e}")
                self._transport = None
                # Continue trying

        logger.debug("Reconnect loop ended")

    def _handle_message(self, msg_type: int, payload: bytes):
        """Handle incoming message."""
        try:
            # Debug: log all non-telemetry messages
            if msg_type != MessageType.TELEMETRY_DATA:
                logger.debug(f"RX msg_type=0x{msg_type:02X}, payload={len(payload)} bytes")

            if msg_type == MessageType.TELEMETRY_DATA:
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

            elif msg_type == MessageType.CHANNEL_ACK:
                logger.debug("Channel ACK received")

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

    def _send_frame(self, frame: bytes) -> bool:
        """Send a frame to the device with error handling."""
        if not self._is_connected or not self._transport:
            logger.warning("Cannot send: not connected")
            return False

        try:
            return self._transport.send(frame)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError) as e:
            logger.error(f"Connection lost while sending: {e}")
            self._handle_connection_lost()
            return False
        except Exception as e:
            logger.error(f"Send error: {e}")
            return False

    def subscribe_telemetry(self, rate_hz: int = 10):
        """Subscribe to telemetry streaming."""
        payload = struct.pack('<H', rate_hz)
        frame = self._protocol.build_frame(MessageType.SUBSCRIBE_TELEMETRY, payload)

        if self._send_frame(frame):
            self._telemetry_enabled = True
            logger.info(f"Subscribed to telemetry at {rate_hz}Hz")

            # For Serial connections, start polling timer (async transports use receive thread)
            if self._connection_type == "USB Serial":
                poll_interval = max(50, 1000 // rate_hz)  # Convert rate to interval, min 50ms
                self._serial_poll_timer.start(poll_interval)
                logger.info(f"Started serial polling at {poll_interval}ms interval")

    def unsubscribe_telemetry(self):
        """Unsubscribe from telemetry streaming."""
        # Stop serial polling timer if running
        if self._serial_poll_timer.isActive():
            self._serial_poll_timer.stop()
            logger.info("Stopped serial polling")

        frame = self._protocol.build_frame(MessageType.UNSUBSCRIBE_TELEMETRY)

        if self._send_frame(frame):
            self._telemetry_enabled = False
            logger.info("Unsubscribed from telemetry")

    def _poll_serial_telemetry(self):
        """Poll serial port for telemetry data (called by timer)."""
        if not self._is_connected or not self._transport:
            return

        try:
            data = self._transport.receive(1024, timeout=0.01)
            if data:
                logger.debug(f"Serial poll RX: {len(data)} bytes")
                messages = self._protocol.feed_data(data)
                if messages:
                    logger.debug(f"Parsed {len(messages)} messages")
                for msg in messages:
                    self._handle_message(msg.msg_type, msg.payload)
        except Exception as e:
            logger.warning(f"Serial poll error: {e}")

    def set_channel(self, channel_id: int, value: float) -> bool:
        """Set channel value (live, not saved to flash)."""
        payload = struct.pack('<Hf', channel_id, value)
        frame = self._protocol.build_frame(MessageType.SET_CHANNEL, payload)

        if self._send_frame(frame):
            logger.debug(f"Set channel {channel_id} = {value}")
            return True
        return False

    def upload_binary_config(self, binary_data: bytes, timeout: float = 5.0) -> bool:
        """Upload binary configuration to device and wait for ACK.

        Args:
            binary_data: Binary config data (serialized channels)
            timeout: Timeout in seconds to wait for ACK

        Returns:
            True if config was uploaded successfully (ACK received)
        """
        if not self._is_connected:
            logger.warning("Cannot upload config: not connected")
            return False

        # Stop serial polling timer to prevent it from stealing our ACK
        polling_was_active = self._serial_poll_timer.isActive()
        if polling_was_active:
            self._serial_poll_timer.stop()
            logger.debug("Stopped serial polling for config upload")

        # Reset ACK state (use BINARY_CONFIG_ACK, not CONFIG_ACK!)
        self._binary_config_ack_event.clear()
        self._binary_config_ack_success = False
        self._binary_config_ack_error = 0
        self._binary_config_channels_loaded = 0

        # Send in chunks
        chunk_size = 1024
        chunks = [binary_data[i:i + chunk_size] for i in range(0, len(binary_data), chunk_size)]
        total_chunks = len(chunks)

        logger.info(f"Uploading binary config: {len(binary_data)} bytes in {total_chunks} chunks")

        for idx, chunk in enumerate(chunks):
            frame = self._build_binary_config_frame(idx, total_chunks, chunk)
            if not self._send_frame(frame):
                logger.error(f"Failed to send chunk {idx + 1}/{total_chunks}")
                return False
            # Small delay between chunks to avoid overwhelming device
            time.sleep(0.02)

        logger.info("All chunks sent, waiting for BINARY_CONFIG_ACK (0x69)...")

        try:
            # For Serial transport, do synchronous receive (no receive thread running)
            if self._connection_type == "USB Serial":
                start_time = time.time()
                while time.time() - start_time < timeout:
                    data = self._transport.receive(4096, timeout=0.5)
                    if data:
                        logger.debug(f"Serial RX: {len(data)} bytes: {data[:50].hex()}...")
                        messages = self._protocol.feed_data(data)
                        for msg in messages:
                            self._handle_message(msg.msg_type, msg.payload)

                        if self._binary_config_ack_event.is_set():
                            break
                    else:
                        time.sleep(0.05)
            else:
                # For async transports (Emulator, WiFi), wait for event from receive thread
                if not self._binary_config_ack_event.wait(timeout):
                    logger.error(f"Timeout waiting for BINARY_CONFIG_ACK ({timeout}s)")
                    return False

            if self._binary_config_ack_success:
                logger.info(f"Binary config uploaded successfully: {self._binary_config_channels_loaded} channels loaded")
                return True
            else:
                logger.error(f"Config upload failed: error code {self._binary_config_ack_error}")
                return False
        finally:
            # Always restart polling timer if it was active
            if polling_was_active:
                self._serial_poll_timer.start()
                logger.debug("Restarted serial polling after config upload")

    def _build_binary_config_frame(self, chunk_idx: int, total_chunks: int, chunk: bytes) -> bytes:
        """Build protocol frame for binary config chunk."""
        header = struct.pack('<HH', chunk_idx, total_chunks)
        payload = header + chunk
        return self._protocol.build_frame(MessageType.LOAD_BINARY_CONFIG, payload)

    def save_to_flash(self, timeout: float = 5.0) -> bool:
        """Save current configuration to flash."""
        if not self._is_connected:
            logger.warning("Cannot save to flash: not connected")
            return False

        # Stop serial polling timer to prevent it from stealing our ACK
        polling_was_active = self._serial_poll_timer.isActive()
        if polling_was_active:
            self._serial_poll_timer.stop()
            logger.debug("Stopped serial polling for flash save")

        # Reset ACK state
        self._flash_ack_event.clear()
        self._flash_ack_success = False

        frame = self._protocol.build_frame(MessageType.SAVE_TO_FLASH)

        if not self._send_frame(frame):
            logger.error("Failed to send SAVE_TO_FLASH command")
            if polling_was_active:
                self._serial_poll_timer.start()
            return False

        logger.info("Save to flash requested, waiting for ACK...")

        try:
            # For Serial transport, do synchronous receive (no receive thread)
            if self._connection_type == "USB Serial":
                start_time = time.time()
                while time.time() - start_time < timeout:
                    data = self._transport.receive(4096, timeout=0.5)
                    if data:
                        logger.debug(f"Serial RX: {len(data)} bytes: {data[:50].hex()}...")
                        messages = self._protocol.feed_data(data)
                        for msg in messages:
                            self._handle_message(msg.msg_type, msg.payload)

                        if self._flash_ack_event.is_set():
                            break
                    else:
                        time.sleep(0.05)
            else:
                if not self._flash_ack_event.wait(timeout):
                    logger.error(f"Timeout waiting for flash ACK ({timeout}s)")
                    return False

            if self._flash_ack_success:
                logger.info("Configuration saved to flash successfully")
                return True
            else:
                logger.error("Flash save failed")
                return False
        finally:
            # Always restart polling timer if it was active
            if polling_was_active:
                self._serial_poll_timer.start()
                logger.debug("Restarted serial polling after flash save")

    def restart_device(self) -> bool:
        """Restart the device."""
        frame = self._protocol.build_frame(MessageType.RESTART_DEVICE)

        if self._send_frame(frame):
            logger.info("Device restart requested")
            return True
        return False

    # ========== Emulator-only methods ==========

    def set_digital_input(self, channel: int, state: bool) -> bool:
        """Set digital input state (emulator only).

        Args:
            channel: Digital input channel (0-19)
            state: Input state (True=HIGH, False=LOW)
        """
        from communication.protocol import FrameBuilder, encode_frame
        frame = FrameBuilder.emu_set_digital_input(channel, state)
        frame_bytes = encode_frame(frame)
        if self._send_frame(frame_bytes):
            logger.debug(f"Set digital input {channel} = {state}")
            return True
        return False

    def set_analog_input(self, channel: int, voltage: float) -> bool:
        """Set analog input voltage (emulator only).

        Args:
            channel: Analog input channel (0-19)
            voltage: Voltage in volts (0.0-5.0)
        """
        from communication.protocol import FrameBuilder, encode_frame
        voltage_mv = int(voltage * 1000)
        frame = FrameBuilder.emu_set_analog_input(channel, voltage_mv)
        frame_bytes = encode_frame(frame)
        if self._send_frame(frame_bytes):
            logger.debug(f"Set analog input {channel} = {voltage}V")
            return True
        return False

    def inject_can_message(self, bus_id: int, can_id: int, data: bytes) -> bool:
        """Inject CAN message for testing (emulator only).

        Args:
            bus_id: CAN bus index (0 or 1)
            can_id: CAN message ID
            data: CAN data bytes (up to 8)
        """
        from communication.protocol import FrameBuilder, encode_frame
        frame = FrameBuilder.emu_inject_can(bus_id, can_id, data)
        frame_bytes = encode_frame(frame)
        if self._send_frame(frame_bytes):
            logger.debug(f"Injected CAN message bus={bus_id} id=0x{can_id:X}")
            return True
        return False


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
    if channel.source_id != CH_REF_NONE:
        result["source_channel"] = channel.source_id

    # Add hardware info
    if channel.hw_device != HwDevice.NONE:
        result["hw_device"] = channel.hw_device
        result["hw_index"] = channel.hw_index

    # Parse type-specific config
    if channel.config:
        _parse_channel_config(result, ch_type_str, channel.config)

    return result


def _parse_channel_config(result: Dict, ch_type: str, config) -> None:
    """Parse type-specific channel config into UI dict format."""
    from channel_config import CH_REF_NONE

    # Hardware input channels
    if ch_type == "digital_input":
        result["debounce_ms"] = getattr(config, 'debounce_ms', 0)
        result["active_high"] = bool(getattr(config, 'active_high', 1))
        result["use_pullup"] = bool(getattr(config, 'use_pullup', 1))

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
        result["current_limit_ma"] = getattr(config, 'current_limit_ma', 5000)
        result["inrush_time_ms"] = getattr(config, 'inrush_time_ms', 100)
        result["inrush_limit_ma"] = getattr(config, 'inrush_limit_ma', 5000)

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
