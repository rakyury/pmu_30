"""
Device Controller for PMU-30

Handles communication with PMU-30 device via USB, Emulator, WiFi, Bluetooth, or CAN Bus.

Owner: R2 m-sport
© 2025 R2 m-sport. All rights reserved.
"""

import logging
import struct
import threading
import time
from typing import List, Optional, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal

import serial.tools.list_ports

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

        # For Serial transport, do synchronous receive (no receive thread running)
        if self._connection_type == "USB Serial":
            start_time = time.time()
            while time.time() - start_time < timeout:
                # Read available data
                data = self._transport.receive(4096, timeout=0.5)
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
        else:
            # For async transports (Emulator, WiFi), wait for event from receive thread
            if not self._config_event.wait(timeout):
                logger.error(f"Timeout waiting for config ({timeout}s)")
                return None

        # Get assembled config data
        config_data = self._config_assembler.get_data()
        if config_data is None:
            logger.error("Failed to assemble config chunks")
            return None

        # Parse JSON
        try:
            import json
            config_str = config_data.decode('utf-8')
            config = json.loads(config_str)
            logger.info(f"Configuration received: {len(config_str)} bytes")
            return config
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse config JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing config: {e}")
            return None

    def write_configuration(self, config: dict, timeout: float = 10.0) -> bool:
        """
        Write configuration to device.

        Args:
            config: Configuration dictionary
            timeout: Timeout in seconds for ACK

        Returns:
            True if successful
        """
        import json

        if not self._is_connected:
            logger.warning("Cannot write config: not connected")
            return False

        logger.info("Writing configuration to device...")

        # Serialize config to JSON
        try:
            config_json = json.dumps(config, ensure_ascii=False, separators=(',', ':'))
            config_bytes = config_json.encode('utf-8')
            logger.info(f"Config serialized: {len(config_bytes)} bytes")
        except Exception as e:
            logger.error(f"Failed to serialize config: {e}")
            return False

        # Split into chunks using protocol handler
        chunks = ProtocolHandler.split_into_chunks(config_bytes, chunk_size=4000)
        total_chunks = len(chunks)
        logger.info(f"Sending config in {total_chunks} chunks")

        # Reset ACK state
        self._config_ack_event.clear()
        self._config_ack_success = False
        self._config_ack_error = 0

        # Send each chunk using protocol handler
        for chunk_idx, chunk_data in enumerate(chunks):
            frame = self._protocol.build_config_frame(chunk_idx, total_chunks, chunk_data)
            logger.debug(f"Sending chunk {chunk_idx + 1}/{total_chunks}, {len(chunk_data)} bytes")

            if not self._send_frame(frame):
                logger.error(f"Failed to send config chunk {chunk_idx}")
                return False

            # Small delay between chunks to not overwhelm device
            time.sleep(0.01)

        # Wait for CONFIG_ACK after all chunks sent
        logger.info("All chunks sent, waiting for ACK...")

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

                    if self._config_ack_event.is_set():
                        break
                else:
                    time.sleep(0.05)
        else:
            if not self._config_ack_event.wait(timeout):
                logger.error(f"Timeout waiting for config ACK ({timeout}s)")
                return False

        if self._config_ack_success:
            logger.info("Configuration written successfully")
            return True
        else:
            logger.error(f"Config write failed, error code: {self._config_ack_error}")
            return False

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

    def unsubscribe_telemetry(self):
        """Unsubscribe from telemetry streaming."""
        frame = self._protocol.build_frame(MessageType.UNSUBSCRIBE_TELEMETRY)

        if self._send_frame(frame):
            self._telemetry_enabled = False
            logger.info("Unsubscribed from telemetry")

    def set_channel(self, channel_id: int, value: float) -> bool:
        """Set channel value (live, not saved to flash)."""
        payload = struct.pack('<Hf', channel_id, value)
        frame = self._protocol.build_frame(MessageType.SET_CHANNEL, payload)

        if self._send_frame(frame):
            logger.debug(f"Set channel {channel_id} = {value}")
            return True
        return False

    def save_to_flash(self, timeout: float = 5.0) -> bool:
        """Save current configuration to flash."""
        if not self._is_connected:
            logger.warning("Cannot save to flash: not connected")
            return False

        # Reset ACK state
        self._flash_ack_event.clear()
        self._flash_ack_success = False

        frame = self._protocol.build_frame(MessageType.SAVE_TO_FLASH)

        if not self._send_frame(frame):
            logger.error("Failed to send SAVE_TO_FLASH command")
            return False

        logger.info("Save to flash requested, waiting for ACK...")

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

    # ========== Atomic Channel Configuration Update ==========

    # Channel type mapping for protocol
    CHANNEL_TYPE_MAP = {
        "power_output": 0x01,
        "hbridge": 0x02,
        "digital_input": 0x03,
        "analog_input": 0x04,
        "logic": 0x05,
        "number": 0x06,
        "timer": 0x07,
        "filter": 0x08,
        "switch": 0x09,
        "table_2d": 0x0A,
        "table_3d": 0x0B,
        "can_rx": 0x0C,
        "can_tx": 0x0D,
        "pid": 0x0E,
        "lua_script": 0x0F,
        "handler": 0x10,
        "blinkmarine_keypad": 0x11,
    }

    def update_channel_config(self, channel_type: str, channel_id: int, config: dict, timeout: float = 3.0) -> bool:
        """
        Update a single channel's configuration on the device atomically.

        This pushes individual channel changes without requiring a full configuration reload.

        Args:
            channel_type: Channel type string (e.g., "power_output", "logic")
            channel_id: Numeric channel ID
            config: Configuration dictionary for the channel
            timeout: Response timeout in seconds

        Returns:
            True if update successful
        """
        import json
        from communication.protocol import FrameBuilder, encode_frame

        if not self._is_connected:
            logger.debug("Cannot update channel config: not connected")
            return False

        # Map channel type string to protocol value
        type_code = self.CHANNEL_TYPE_MAP.get(channel_type.lower())
        if type_code is None:
            logger.error(f"Unknown channel type for atomic update: {channel_type}")
            return False

        # Serialize config to compact JSON
        try:
            config_json = json.dumps(config, separators=(',', ':')).encode('utf-8')
        except Exception as e:
            logger.error(f"Failed to serialize channel config: {e}")
            return False

        # Build and send frame
        frame = FrameBuilder.set_channel_config(type_code, channel_id, config_json)
        frame_bytes = encode_frame(frame)

        # Reset ACK state
        self._channel_config_ack_event.clear()
        self._channel_config_ack_success = False
        self._channel_config_ack_error_msg = ""

        if not self._send_frame(frame_bytes):
            logger.error("Failed to send channel config update")
            return False

        # Wait for ACK
        if not self._channel_config_ack_event.wait(timeout):
            logger.warning(f"Timeout waiting for channel config ACK ({timeout}s)")
            return False

        if self._channel_config_ack_success:
            logger.info(f"Channel {channel_id} ({channel_type}) config updated successfully")
            return True
        else:
            logger.warning(f"Channel config update failed: {self._channel_config_ack_error_msg}")
            return False
