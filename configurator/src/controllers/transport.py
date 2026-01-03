"""
Transport Layer Abstraction for PMU-30

Provides unified interface for different connection types:
- USB Serial (with T-MIN protocol support)
- TCP Socket (Emulator, WiFi)
- Bluetooth
- CAN Bus
"""

import logging
import socket
import sys
import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Callable, List, Tuple

import serial

# Add shared library to path for MIN protocol
_shared_path = Path(__file__).parent.parent.parent.parent / "shared" / "python"
if str(_shared_path) not in sys.path:
    sys.path.insert(0, str(_shared_path))

from min_protocol import MINTransportSerial, MINFrame, MINConnectionError

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
                self._serial.flush()  # Ensure data is sent immediately
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


class MINSerialTransport(Transport):
    """
    USB Serial transport with T-MIN protocol support.

    T-MIN provides reliable message delivery with:
    - Automatic retransmission of lost frames
    - Sliding window for efficient throughput
    - ACK/NACK handling
    - Frame sequence tracking

    Usage:
        transport = MINSerialTransport("COM11", 115200)
        transport.connect()

        # Reliable send (auto-retransmit until ACK)
        transport.queue_frame(0x10, payload)

        # Unreliable send (for telemetry, no retransmit)
        transport.send_frame(0x22, payload)

        # Poll for incoming frames
        frames = transport.poll()
        for frame in frames:
            handle_message(frame.min_id, frame.payload)
    """

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        idle_timeout_ms: int = 5000,
        frame_retransmit_timeout_ms: int = 100,
    ):
        """
        Initialize T-MIN serial transport.

        Args:
            port: Serial port name (e.g., "COM11")
            baudrate: Serial baudrate (default 115200)
            idle_timeout_ms: Time before connection considered dead (default 5s)
            frame_retransmit_timeout_ms: Time before frame retransmit (default 100ms)
        """
        self.port = port
        self.baudrate = baudrate
        self._idle_timeout_ms = idle_timeout_ms
        self._frame_retransmit_timeout_ms = frame_retransmit_timeout_ms
        self._min_transport: Optional[MINTransportSerial] = None
        self._lock = threading.Lock()
        self._poll_thread: Optional[threading.Thread] = None
        self._stop_poll = threading.Event()
        self._rx_queue: List[MINFrame] = []
        self._rx_lock = threading.Lock()

    def connect(self) -> bool:
        """Establish T-MIN connection over serial."""
        try:
            # Extract just the port name if format is "COMx - description"
            port_name = self.port.split(" - ")[0] if " - " in self.port else self.port

            self._min_transport = MINTransportSerial(
                port=port_name,
                baudrate=self.baudrate,
            )
            # Configure T-MIN timeouts
            self._min_transport.idle_timeout_ms = self._idle_timeout_ms
            self._min_transport.frame_retransmit_timeout_ms = self._frame_retransmit_timeout_ms

            # Start background poll thread for T-MIN state machine
            self._stop_poll.clear()
            self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
            self._poll_thread.start()

            logger.info(f"T-MIN Serial connected: {port_name} @ {self.baudrate}")
            return True

        except MINConnectionError as e:
            logger.error(f"T-MIN connection failed: {e}")
            self._min_transport = None
            return False
        except Exception as e:
            logger.error(f"T-MIN connection error: {e}")
            self._min_transport = None
            return False

    def disconnect(self):
        """Close T-MIN connection."""
        # Stop poll thread
        self._stop_poll.set()
        if self._poll_thread:
            self._poll_thread.join(timeout=2.0)
            self._poll_thread = None

        with self._lock:
            if self._min_transport:
                try:
                    self._min_transport.transport_reset()
                    self._min_transport.close()
                except Exception as e:
                    logger.error(f"T-MIN close error: {e}")
                self._min_transport = None

        # Clear receive queue
        with self._rx_lock:
            self._rx_queue.clear()

        logger.info("T-MIN Serial disconnected")

    def send(self, data: bytes) -> bool:
        """
        Send raw bytes (bypasses T-MIN framing).

        Note: Prefer using queue_frame() or send_frame() for proper T-MIN protocol.
        This method is for backwards compatibility only.
        """
        # This shouldn't be used with T-MIN, but kept for interface compatibility
        logger.warning("send() called on MINSerialTransport - use queue_frame() instead")
        return False

    def receive(self, size: int, timeout: float = 1.0) -> Optional[bytes]:
        """
        Receive raw bytes (bypasses T-MIN framing).

        Note: Prefer using poll() or get_frames() for proper T-MIN protocol.
        This method is for backwards compatibility only.
        """
        # This shouldn't be used with T-MIN
        logger.warning("receive() called on MINSerialTransport - use poll() instead")
        return None

    def is_connected(self) -> bool:
        """Check if T-MIN connection is active."""
        return self._min_transport is not None

    # -------------------------------------------------------------------------
    # T-MIN specific methods
    # -------------------------------------------------------------------------

    def queue_frame(self, min_id: int, payload: bytes = b'') -> bool:
        """
        Queue frame for reliable delivery (T-MIN transport mode).

        The frame will be automatically retransmitted until acknowledged
        by the remote side or the connection times out.

        Args:
            min_id: MIN message ID (0-63)
            payload: Message payload (0-255 bytes)

        Returns:
            True if queued successfully
        """
        with self._lock:
            if not self._min_transport:
                return False
            try:
                self._min_transport.queue_frame(min_id, payload)
                logger.debug(f"T-MIN queued: id=0x{min_id:02X}, len={len(payload)}")
                return True
            except MINConnectionError as e:
                logger.error(f"T-MIN queue error: {e}")
                return False
            except ValueError as e:
                logger.error(f"T-MIN queue value error: {e}")
                return False

    def send_frame(self, min_id: int, payload: bytes = b'') -> bool:
        """
        Send frame without acknowledgment (MIN non-transport mode).

        Use this for high-frequency data like telemetry where
        occasional packet loss is acceptable.

        Args:
            min_id: MIN message ID (0-63)
            payload: Message payload (0-255 bytes)

        Returns:
            True if sent successfully
        """
        with self._lock:
            if not self._min_transport:
                return False
            try:
                self._min_transport.send_frame(min_id, payload)
                logger.debug(f"T-MIN sent: id=0x{min_id:02X}, len={len(payload)}")
                return True
            except ValueError as e:
                logger.error(f"T-MIN send value error: {e}")
                return False

    def poll(self) -> List[MINFrame]:
        """
        Get all received frames since last poll.

        This is the primary method for receiving T-MIN messages.
        Call frequently to process incoming data and maintain
        the T-MIN state machine.

        Returns:
            List of received MINFrame objects
        """
        with self._rx_lock:
            frames = self._rx_queue.copy()
            self._rx_queue.clear()
        return frames

    def get_transport_stats(self) -> Tuple:
        """
        Get T-MIN transport statistics.

        Returns tuple of:
            (longest_fifo, last_sent_time, seq_drops, retransmits,
             resets, duplicates, mismatched_acks, spurious_acks)
        """
        with self._lock:
            if not self._min_transport:
                return (0, 0, 0, 0, 0, 0, 0, 0)
            return self._min_transport.transport_stats()

    def transport_reset(self):
        """
        Reset T-MIN transport state.

        Sends RESET to remote side and clears all queues.
        Use when connection needs to be re-synchronized.
        """
        with self._lock:
            if self._min_transport:
                self._min_transport.transport_reset()
                logger.info("T-MIN transport reset")

    def _poll_loop(self):
        """Background loop for T-MIN state machine."""
        logger.debug("T-MIN poll loop started")
        while not self._stop_poll.is_set():
            try:
                with self._lock:
                    if not self._min_transport:
                        break
                    # Poll T-MIN - processes RX data, handles ACKs, retransmits
                    frames = self._min_transport.poll()

                # Add received frames to queue
                if frames:
                    with self._rx_lock:
                        for frame in frames:
                            self._rx_queue.append(frame)
                            logger.debug(f"T-MIN RX: id=0x{frame.min_id:02X}, "
                                       f"len={len(frame.payload)}, transport={frame.is_transport}")

                # Small sleep to prevent CPU spinning
                time.sleep(0.001)  # 1ms poll interval

            except Exception as e:
                if not self._stop_poll.is_set():
                    logger.error(f"T-MIN poll error: {e}")
                    time.sleep(0.1)  # Back off on error

        logger.debug("T-MIN poll loop stopped")


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
            # Use T-MIN transport for reliable communication
            return MINSerialTransport(port, baudrate)

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
