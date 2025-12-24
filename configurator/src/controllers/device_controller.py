"""
Device Controller for PMU-30

Handles communication with PMU-30 device via USB, Emulator, WiFi, Bluetooth, or CAN Bus.

Owner: R2 m-sport
© 2025 R2 m-sport. All rights reserved.
"""

import logging
import socket
import struct
import threading
import time
from typing import List, Optional, Dict, Any, Callable
from PyQt6.QtCore import QObject, pyqtSignal

import serial
import serial.tools.list_ports

from communication.protocol import MessageType, crc16_ccitt, FRAME_START_BYTE
from communication.telemetry import parse_telemetry, TelemetryPacket


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

    # Auto-reconnect signals
    reconnecting = pyqtSignal(int, int)  # attempt, max_attempts
    reconnect_failed = pyqtSignal()  # all attempts exhausted

    def __init__(self):
        super().__init__()

        self._connection = None
        self._connection_type = None
        self._is_connected = False
        self._receive_thread = None
        self._stop_thread = threading.Event()
        self._telemetry_enabled = False
        self._rx_buffer = bytearray()

        # Config receive state
        self._config_chunks = {}  # chunk_idx -> data
        self._config_total_chunks = 0
        self._config_event = threading.Event()

        # Config write state
        self._config_ack_event = threading.Event()
        self._config_ack_success = False
        self._config_ack_error = 0

        # Flash save state
        self._flash_ack_event = threading.Event()
        self._flash_ack_success = False

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
            if connection_type == "USB Serial":
                port = config.get("port", "")
                baudrate = config.get("baudrate", 115200)
                self._connect_usb(port, baudrate)
            elif connection_type == "Emulator":
                address = config.get("address", "localhost:9876")
                self._connect_emulator(address)
            elif connection_type == "WiFi":
                ip = config.get("ip", "")
                port = config.get("port", 8080)
                self._connect_wifi(f"{ip}:{port}")
            elif connection_type == "Bluetooth":
                device = config.get("device", "")
                self._connect_bluetooth(device)
            elif connection_type == "CAN Bus":
                interface = config.get("interface", "can0")
                self._connect_can(interface, config)
            else:
                raise ValueError(f"Unknown connection type: {connection_type}")

            self._connection_type = connection_type
            self._is_connected = True
            self._user_disconnected = False
            self._last_connection_config = config.copy()  # Save for auto-reconnect
            self._reconnect_attempt = 0
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
            return False

    def _connect_usb(self, port: str, baudrate: int = 115200):
        """Connect via USB serial."""

        # Extract port name from selection string
        port_name = port.split(" - ")[0] if " - " in port else port

        self._connection = serial.Serial(
            port=port_name,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1.0
        )

        logger.debug(f"USB serial connection established: {port_name} @ {baudrate}")

    def _connect_emulator(self, address: str):
        """Connect to PMU-30 emulator via TCP."""

        # Parse address
        if ":" in address:
            host, port_str = address.split(":")
            port = int(port_str)
        else:
            host = address
            port = 9876  # Default emulator port

        # Create TCP socket connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect((host, port))
        sock.setblocking(False)  # Non-blocking for receive thread

        self._connection = sock
        logger.info(f"Connected to emulator at {host}:{port}")

        # Start receive thread
        self._start_receive_thread()

    def _connect_can(self, interface: str, config: Dict[str, Any]):
        """Connect via CAN bus."""

        # TODO: Implement CAN bus connection
        logger.warning("CAN bus connection not yet implemented")
        raise NotImplementedError("CAN bus connection not yet implemented")

    def _connect_wifi(self, address: str):
        """Connect via WiFi."""

        # TODO: Implement WiFi connection
        # Use WebSocket or HTTP REST API
        logger.warning("WiFi connection not yet implemented")
        raise NotImplementedError("WiFi connection not yet implemented")

    def _connect_bluetooth(self, address: str):
        """Connect via Bluetooth."""

        # TODO: Implement Bluetooth connection
        logger.warning("Bluetooth connection not yet implemented")
        raise NotImplementedError("Bluetooth connection not yet implemented")

    def disconnect(self):
        """Disconnect from device (user-initiated)."""
        # Mark as user-disconnected to prevent auto-reconnect
        self._user_disconnected = True

        # Stop any ongoing reconnection attempts
        self.stop_reconnect()

        # Stop receive thread first
        self._stop_receive_thread()

        if self._connection:
            try:
                if isinstance(self._connection, serial.Serial):
                    self._connection.close()
                elif isinstance(self._connection, socket.socket):
                    self._connection.close()

                self._connection = None
                self._is_connected = False
                self._telemetry_enabled = False
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
            Response bytes or None
        """

        if not self._is_connected or not self._connection:
            logger.warning("Cannot send command: not connected")
            return None

        try:
            if isinstance(self._connection, serial.Serial):
                self._connection.write(command)
                # Wait for response
                response = self._connection.read(1024)
                return response
            elif isinstance(self._connection, socket.socket):
                # When receive thread is running, just send without blocking recv
                # Responses will be handled by receive thread via signals
                if self._receive_thread and self._receive_thread.is_alive():
                    self._connection.sendall(command)
                    return b''  # Response handled by receive thread
                else:
                    self._connection.sendall(command)
                    # Wait for response (with timeout)
                    self._connection.setblocking(True)
                    self._connection.settimeout(2.0)
                    try:
                        response = self._connection.recv(4096)
                    finally:
                        self._connection.setblocking(False)
                    return response

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

        # Reset config receive state
        self._config_chunks.clear()
        self._config_total_chunks = 0
        self._config_event.clear()

        # Send GET_CONFIG command
        frame = self._build_frame(MessageType.GET_CONFIG)
        logger.debug(f"Sending GET_CONFIG frame: {frame.hex()}")
        if not self._send_frame(frame):
            logger.error("Failed to send GET_CONFIG")
            return None
        logger.debug("GET_CONFIG sent successfully, waiting for response...")

        # Wait for all chunks
        if not self._config_event.wait(timeout):
            logger.error(f"Timeout waiting for config ({timeout}s)")
            return None

        # Reassemble chunks in order
        config_data = bytearray()
        for i in range(self._config_total_chunks):
            if i in self._config_chunks:
                config_data.extend(self._config_chunks[i])
            else:
                logger.error(f"Missing config chunk {i}")
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

        # Split into chunks (max 4000 bytes per chunk to stay under FRAME_MAX_PAYLOAD)
        CHUNK_SIZE = 4000
        chunks = []
        for i in range(0, len(config_bytes), CHUNK_SIZE):
            chunks.append(config_bytes[i:i + CHUNK_SIZE])

        total_chunks = len(chunks)
        logger.info(f"Sending config in {total_chunks} chunks")

        # Reset ACK state
        self._config_ack_event.clear()
        self._config_ack_success = False
        self._config_ack_error = 0

        # Send each chunk
        for chunk_idx, chunk_data in enumerate(chunks):
            # Build payload: chunk_idx (2B) + total_chunks (2B) + data
            payload = struct.pack('<HH', chunk_idx, total_chunks) + chunk_data
            frame = self._build_frame(MessageType.SET_CONFIG, payload)

            logger.debug(f"Sending chunk {chunk_idx + 1}/{total_chunks}, {len(chunk_data)} bytes")

            if not self._send_frame(frame):
                logger.error(f"Failed to send config chunk {chunk_idx}")
                return False

            # Small delay between chunks to not overwhelm device
            time.sleep(0.01)

        # Wait for CONFIG_ACK after all chunks sent
        logger.info("All chunks sent, waiting for ACK...")
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
        self._rx_buffer = bytearray()
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
                if isinstance(self._connection, socket.socket):
                    try:
                        data = self._connection.recv(4096)
                        if data:
                            logger.debug(f"Received {len(data)} bytes: {data[:50].hex()}...")
                            self._rx_buffer.extend(data)
                            self._process_rx_buffer()
                        elif data == b'':
                            # Empty data means connection closed
                            logger.warning("Connection closed by remote (recv returned empty)")
                            self._handle_connection_lost()
                            break
                    except BlockingIOError:
                        pass  # No data available
                    except ConnectionResetError as e:
                        logger.warning(f"Connection reset by remote: {e}")
                        self._handle_connection_lost()
                        break
                    except ConnectionAbortedError:
                        logger.warning("Connection aborted")
                        self._handle_connection_lost()
                        break
                    except socket.error as e:
                        if not self._stop_thread.is_set():
                            logger.error(f"Socket error: {e}")
                            self._handle_connection_lost()
                            break
                elif isinstance(self._connection, serial.Serial):
                    if self._connection.in_waiting > 0:
                        data = self._connection.read(self._connection.in_waiting)
                        if data:
                            self._rx_buffer.extend(data)
                            self._process_rx_buffer()

                time.sleep(0.01)  # 10ms polling interval

            except Exception as e:
                if not self._stop_thread.is_set():
                    logger.error(f"Receive error: {e}")
                    self._handle_connection_lost()
                    break

    def _handle_connection_lost(self):
        """Handle unexpected connection loss."""
        self._is_connected = False
        self._telemetry_enabled = False
        if self._connection:
            try:
                self._connection.close()
            except:
                pass
            self._connection = None
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

            # Try to reconnect
            try:
                config = self._last_connection_config
                connection_type = config.get("type", "")

                if connection_type == "USB Serial":
                    port = config.get("port", "")
                    baudrate = config.get("baudrate", 115200)
                    self._connect_usb(port, baudrate)
                elif connection_type == "Emulator":
                    address = config.get("address", "localhost:9876")
                    self._connect_emulator(address)
                elif connection_type == "WiFi":
                    ip = config.get("ip", "")
                    port = config.get("port", 8080)
                    self._connect_wifi(f"{ip}:{port}")
                elif connection_type == "Bluetooth":
                    device = config.get("device", "")
                    self._connect_bluetooth(device)

                # Success!
                self._connection_type = connection_type
                self._is_connected = True
                self._reconnect_attempt = 0
                self.connected.emit()

                # Resubscribe to telemetry
                if connection_type == "Emulator":
                    self.subscribe_telemetry()

                logger.info(f"Reconnected via {connection_type}")
                break

            except Exception as e:
                logger.debug(f"Reconnection attempt {self._reconnect_attempt} failed: {e}")
                # Continue trying

        logger.debug("Reconnect loop ended")

    def _process_rx_buffer(self):
        """Process received data and extract frames."""
        logger.debug(f"Processing rx buffer: {len(self._rx_buffer)} bytes")
        while len(self._rx_buffer) >= 6:  # Minimum frame size
            # Find start byte (must search for bytes, not int)
            start_idx = self._rx_buffer.find(bytes([FRAME_START_BYTE]))
            if start_idx == -1:
                logger.debug(f"No start byte found in buffer, clearing {len(self._rx_buffer)} bytes")
                self._rx_buffer.clear()
                return
            if start_idx > 0:
                logger.debug(f"Discarding {start_idx} bytes before start byte")
                del self._rx_buffer[:start_idx]

            if len(self._rx_buffer) < 6:
                return

            # Parse header
            payload_len = self._rx_buffer[1] | (self._rx_buffer[2] << 8)
            msg_type = self._rx_buffer[3]

            frame_len = 4 + payload_len + 2  # Header + payload + CRC
            logger.debug(f"Frame header: msg_type=0x{msg_type:02X}, payload_len={payload_len}, frame_len={frame_len}")

            if len(self._rx_buffer) < frame_len:
                logger.debug(f"Need more data: have {len(self._rx_buffer)}, need {frame_len}")
                return  # Need more data

            # Extract frame
            frame = bytes(self._rx_buffer[:frame_len])
            del self._rx_buffer[:frame_len]

            # Verify CRC
            expected_crc = crc16_ccitt(frame[1:-2])
            received_crc = frame[-2] | (frame[-1] << 8)

            if expected_crc != received_crc:
                logger.warning(f"CRC mismatch: expected=0x{expected_crc:04X}, received=0x{received_crc:04X}, frame={frame[:20].hex()}...")
                continue

            # Process message
            payload = frame[4:-2]
            logger.debug(f"Frame OK: msg_type=0x{msg_type:02X}, payload={len(payload)} bytes")
            self._handle_message(msg_type, payload)

    def _handle_message(self, msg_type: int, payload: bytes):
        """Handle incoming message."""
        try:
            if msg_type == MessageType.TELEMETRY_DATA:
                telemetry = parse_telemetry(payload)
                self.telemetry_received.emit(telemetry)

            elif msg_type == MessageType.LOG_MESSAGE:
                # Parse log message
                if len(payload) >= 3:
                    level = payload[0]
                    source_len = payload[1]
                    source = payload[2:2 + source_len].decode('utf-8', errors='replace')
                    msg_len = payload[2 + source_len]
                    message = payload[3 + source_len:3 + source_len + msg_len].decode('utf-8', errors='replace')
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

            elif msg_type == MessageType.CHANNEL_ACK:
                logger.debug("Channel ACK received")

            elif msg_type == MessageType.CONFIG_DATA:
                # Parse config chunk
                if len(payload) >= 4:
                    chunk_idx = payload[0] | (payload[1] << 8)
                    total_chunks = payload[2] | (payload[3] << 8)
                    chunk_data = payload[4:]

                    logger.debug(f"CONFIG_DATA chunk {chunk_idx + 1}/{total_chunks}, {len(chunk_data)} bytes")

                    self._config_total_chunks = total_chunks
                    self._config_chunks[chunk_idx] = chunk_data

                    # Check if all chunks received
                    if len(self._config_chunks) >= total_chunks:
                        self._config_event.set()

            else:
                logger.debug(f"Received message type 0x{msg_type:02X}, {len(payload)} bytes")

        except Exception as e:
            logger.error(f"Error handling message 0x{msg_type:02X}: {e}")

    def _build_frame(self, msg_type: int, payload: bytes = b'') -> bytes:
        """Build a protocol frame."""
        header = struct.pack('<BHB', FRAME_START_BYTE, len(payload), msg_type)
        crc_data = header[1:] + payload
        crc = crc16_ccitt(crc_data)
        return header + payload + struct.pack('<H', crc)

    def _send_frame(self, frame: bytes) -> bool:
        """Send a frame to the device with error handling."""
        if not self._is_connected or not self._connection:
            logger.warning("Cannot send: not connected")
            return False

        try:
            if isinstance(self._connection, socket.socket):
                self._connection.sendall(frame)
            elif isinstance(self._connection, serial.Serial):
                self._connection.write(frame)
            return True
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
        frame = self._build_frame(MessageType.SUBSCRIBE_TELEMETRY, payload)

        if self._send_frame(frame):
            self._telemetry_enabled = True
            logger.info(f"Subscribed to telemetry at {rate_hz}Hz")

    def unsubscribe_telemetry(self):
        """Unsubscribe from telemetry streaming."""
        frame = self._build_frame(MessageType.UNSUBSCRIBE_TELEMETRY)

        if self._send_frame(frame):
            self._telemetry_enabled = False
            logger.info("Unsubscribed from telemetry")

    def set_channel(self, channel_id: int, value: float) -> bool:
        """Set channel value (live, not saved to flash)."""
        payload = struct.pack('<Hf', channel_id, value)
        frame = self._build_frame(MessageType.SET_CHANNEL, payload)

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

        frame = self._build_frame(MessageType.SAVE_TO_FLASH)

        if not self._send_frame(frame):
            logger.error("Failed to send SAVE_TO_FLASH command")
            return False

        logger.info("Save to flash requested, waiting for ACK...")

        # Wait for FLASH_ACK
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
        frame = self._build_frame(MessageType.RESTART_DEVICE)

        if self._send_frame(frame):
            logger.info("Device restart requested")
            return True
        return False
