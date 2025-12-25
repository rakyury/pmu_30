"""
Transport Layer Abstraction for PMU-30

Provides unified interface for different connection types:
- USB Serial
- TCP Socket (Emulator, WiFi)
- Bluetooth
- CAN Bus
"""

import logging
import socket
import threading
from abc import ABC, abstractmethod
from typing import Optional, Callable
import serial

logger = logging.getLogger(__name__)


class Transport(ABC):
    """Abstract base class for transport implementations."""

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection. Returns True on success."""
        pass

    @abstractmethod
    def disconnect(self):
        """Close connection."""
        pass

    @abstractmethod
    def send(self, data: bytes) -> bool:
        """Send data. Returns True on success."""
        pass

    @abstractmethod
    def receive(self, size: int, timeout: float = 1.0) -> Optional[bytes]:
        """Receive up to size bytes. Returns None on timeout/error."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connection is active."""
        pass

    @property
    def transport_type(self) -> str:
        """Return transport type name."""
        return self.__class__.__name__


class SerialTransport(Transport):
    """USB Serial transport implementation."""

    def __init__(self, port: str, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self._serial: Optional[serial.Serial] = None
        self._lock = threading.Lock()

    def connect(self) -> bool:
        try:
            # Extract just the port name if format is "COMx - description"
            port_name = self.port.split(" - ")[0] if " - " in self.port else self.port

            self._serial = serial.Serial(
                port=port_name,
                baudrate=self.baudrate,
                timeout=1.0,
                write_timeout=1.0
            )
            logger.info(f"Serial connected: {port_name} @ {self.baudrate}")
            return True
        except Exception as e:
            logger.error(f"Serial connection failed: {e}")
            return False

    def disconnect(self):
        with self._lock:
            if self._serial and self._serial.is_open:
                try:
                    self._serial.close()
                except Exception as e:
                    logger.error(f"Serial close error: {e}")
                self._serial = None
        logger.info("Serial disconnected")

    def send(self, data: bytes) -> bool:
        with self._lock:
            if not self._serial or not self._serial.is_open:
                return False
            try:
                self._serial.write(data)
                return True
            except Exception as e:
                logger.error(f"Serial send error: {e}")
                return False

    def receive(self, size: int, timeout: float = 1.0) -> Optional[bytes]:
        with self._lock:
            if not self._serial or not self._serial.is_open:
                return None
            try:
                self._serial.timeout = timeout
                data = self._serial.read(size)
                return data if data else None
            except Exception as e:
                logger.error(f"Serial receive error: {e}")
                return None

    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open


class SocketTransport(Transport):
    """TCP Socket transport for Emulator and WiFi connections."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self._socket: Optional[socket.socket] = None
        self._lock = threading.Lock()

    def connect(self) -> bool:
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(5.0)
            self._socket.connect((self.host, self.port))
            self._socket.settimeout(0.1)  # Non-blocking for receive loop
            logger.info(f"Socket connected: {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Socket connection failed: {e}")
            self._socket = None
            return False

    def disconnect(self):
        with self._lock:
            if self._socket:
                try:
                    self._socket.close()
                except Exception as e:
                    logger.error(f"Socket close error: {e}")
                self._socket = None
        logger.info("Socket disconnected")

    def send(self, data: bytes) -> bool:
        with self._lock:
            if not self._socket:
                return False
            try:
                self._socket.sendall(data)
                return True
            except Exception as e:
                logger.error(f"Socket send error: {e}")
                return False

    def receive(self, size: int, timeout: float = 1.0) -> Optional[bytes]:
        if not self._socket:
            return None
        try:
            self._socket.settimeout(timeout)
            data = self._socket.recv(size)
            return data if data else None
        except socket.timeout:
            return None
        except Exception as e:
            logger.debug(f"Socket receive error: {e}")
            return None

    def is_connected(self) -> bool:
        if not self._socket:
            return False
        try:
            # Check if socket is still valid
            self._socket.getpeername()
            return True
        except Exception:
            return False


class BluetoothTransport(Transport):
    """Bluetooth transport (placeholder implementation)."""

    def __init__(self, address: str):
        self.address = address
        self._connected = False

    def connect(self) -> bool:
        # TODO: Implement Bluetooth connection
        logger.warning("Bluetooth transport not yet implemented")
        return False

    def disconnect(self):
        self._connected = False

    def send(self, data: bytes) -> bool:
        return False

    def receive(self, size: int, timeout: float = 1.0) -> Optional[bytes]:
        return None

    def is_connected(self) -> bool:
        return self._connected


class CANTransport(Transport):
    """CAN Bus transport (placeholder implementation)."""

    def __init__(self, interface: str, bitrate: int = 500000):
        self.interface = interface
        self.bitrate = bitrate
        self._connected = False

    def connect(self) -> bool:
        # TODO: Implement CAN connection using python-can
        logger.warning("CAN transport not yet implemented")
        return False

    def disconnect(self):
        self._connected = False

    def send(self, data: bytes) -> bool:
        return False

    def receive(self, size: int, timeout: float = 1.0) -> Optional[bytes]:
        return None

    def is_connected(self) -> bool:
        return self._connected


class TransportFactory:
    """Factory for creating transport instances."""

    @staticmethod
    def create(config: dict) -> Optional[Transport]:
        """
        Create transport based on configuration.

        Args:
            config: Dict with 'type' and type-specific parameters

        Returns:
            Transport instance or None on error
        """
        conn_type = config.get("type", "")

        if conn_type == "USB Serial":
            port = config.get("port", "")
            baudrate = config.get("baudrate", 115200)
            return SerialTransport(port, baudrate)

        elif conn_type == "Emulator":
            address = config.get("address", "localhost:9876")
            host, port = TransportFactory._parse_address(address, 9876)
            return SocketTransport(host, port)

        elif conn_type == "WiFi":
            address = config.get("address", "")
            host, port = TransportFactory._parse_address(address, 80)
            return SocketTransport(host, port)

        elif conn_type == "Bluetooth":
            address = config.get("address", "")
            return BluetoothTransport(address)

        elif conn_type == "CAN Bus":
            interface = config.get("interface", "can0")
            bitrate = config.get("bitrate", 500000)
            return CANTransport(interface, bitrate)

        else:
            logger.error(f"Unknown transport type: {conn_type}")
            return None

    @staticmethod
    def _parse_address(address: str, default_port: int) -> tuple:
        """Parse host:port address string."""
        if ":" in address:
            parts = address.split(":")
            return parts[0], int(parts[1])
        return address, default_port
