"""
Device Controller for PMU-30

Handles communication with PMU-30 device via USB, WiFi, Bluetooth, or Emulator.

Owner: R2 m-sport
© 2025 R2 m-sport. All rights reserved.
"""

import logging
import socket
from typing import List, Optional, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal

import serial
import serial.tools.list_ports


logger = logging.getLogger(__name__)


class DeviceController(QObject):
    """Controller for PMU-30 device communication."""

    # Signals
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    data_received = pyqtSignal(bytes)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        self._connection = None
        self._connection_type = None
        self._is_connected = False

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

        self._connection = sock
        logger.info(f"Connected to emulator at {host}:{port}")

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

        if self._connection:
            try:
                if isinstance(self._connection, serial.Serial):
                    self._connection.close()
                elif isinstance(self._connection, socket.socket):
                    self._connection.close()

                self._connection = None
                self._is_connected = False
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

        if not self._is_connected:
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
                # Wait for response
                response = self._connection.recv(4096)
                return response

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
