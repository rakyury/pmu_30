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

    def __init__(self):
        super().__init__()

        self._connection = None
        self._connection_type = None
        self._is_connected = False
        self._receive_thread = None
        self._stop_thread = threading.Event()
        self._telemetry_enabled = False
        self._rx_buffer = bytearray()

    def is_connected(self) -> bool:
        """Check if device is connected."""
        return self._is_connected

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
            self.connected.emit()

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

        # Subscribe to telemetry
        self.subscribe_telemetry()

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
        """Disconnect from device."""

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

                logger.info("Disconnected from device")

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

    def read_configuration(self) -> Optional[dict]:
        """
        Read configuration from device.

        Returns:
            Configuration dictionary or None
        """

        logger.info("Reading configuration from device...")

        # TODO: Implement configuration read protocol
        # - Send READ_CONFIG command
        # - Parse response
        # - Return structured configuration

        return None

    def write_configuration(self, config: dict) -> bool:
        """
        Write configuration to device.

        Args:
            config: Configuration dictionary

        Returns:
            True if successful
        """

        logger.info("Writing configuration to device...")

        # TODO: Implement configuration write protocol
        # - Serialize configuration
        # - Send WRITE_CONFIG command
        # - Wait for acknowledgment

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
        while not self._stop_thread.is_set():
            try:
                if isinstance(self._connection, socket.socket):
                    try:
                        data = self._connection.recv(4096)
                        if data:
                            self._rx_buffer.extend(data)
                            self._process_rx_buffer()
                        elif data == b'':
                            # Empty data means connection closed
                            logger.warning("Connection closed by remote")
                            self._handle_connection_lost()
                            break
                    except BlockingIOError:
                        pass  # No data available
                    except ConnectionResetError:
                        logger.warning("Connection reset by remote")
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

    def _process_rx_buffer(self):
        """Process received data and extract frames."""
        while len(self._rx_buffer) >= 6:  # Minimum frame size
            # Find start byte (must search for bytes, not int)
            start_idx = self._rx_buffer.find(bytes([FRAME_START_BYTE]))
            if start_idx == -1:
                self._rx_buffer.clear()
                return
            if start_idx > 0:
                del self._rx_buffer[:start_idx]

            if len(self._rx_buffer) < 6:
                return

            # Parse header
            payload_len = self._rx_buffer[1] | (self._rx_buffer[2] << 8)
            msg_type = self._rx_buffer[3]

            frame_len = 4 + payload_len + 2  # Header + payload + CRC

            if len(self._rx_buffer) < frame_len:
                return  # Need more data

            # Extract frame
            frame = bytes(self._rx_buffer[:frame_len])
            del self._rx_buffer[:frame_len]

            # Verify CRC
            expected_crc = crc16_ccitt(frame[1:-2])
            received_crc = frame[-2] | (frame[-1] << 8)

            if expected_crc != received_crc:
                logger.warning(f"CRC mismatch: {expected_crc:04X} != {received_crc:04X}")
                continue

            # Process message
            payload = frame[4:-2]
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
                logger.info("Config ACK received")

            elif msg_type == MessageType.FLASH_ACK:
                logger.info("Flash save ACK received")

            elif msg_type == MessageType.RESTART_ACK:
                logger.info("Restart ACK received")

            elif msg_type == MessageType.CHANNEL_ACK:
                logger.debug("Channel ACK received")

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

    def save_to_flash(self) -> bool:
        """Save current configuration to flash."""
        frame = self._build_frame(MessageType.SAVE_TO_FLASH)

        if self._send_frame(frame):
            logger.info("Save to flash requested")
            return True
        return False

    def restart_device(self) -> bool:
        """Restart the device."""
        frame = self._build_frame(MessageType.RESTART_DEVICE)

        if self._send_frame(frame):
            logger.info("Device restart requested")
            return True
        return False
