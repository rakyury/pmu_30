"""
PMU-30 Transport Base Interface

This module defines the abstract base class for all transport implementations.
Transport classes handle the low-level communication with the PMU-30 device.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Callable, AsyncIterator
import asyncio


class TransportError(Exception):
    """Base exception for transport errors."""
    pass


class ConnectionError(TransportError):
    """Connection-related errors."""
    pass


class TimeoutError(TransportError):
    """Timeout-related errors."""
    pass


class TransportState(Enum):
    """Transport connection state."""
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    ERROR = auto()


@dataclass
class TransportInfo:
    """Information about a transport endpoint."""
    port: str
    description: str
    hardware_id: str = ""
    manufacturer: str = ""
    is_pmu30: bool = False


class TransportBase(ABC):
    """
    Abstract base class for transport implementations.

    All transport classes (Serial, WiFi, Bluetooth) must implement this interface.
    """

    def __init__(self):
        self._state = TransportState.DISCONNECTED
        self._state_callback: Optional[Callable[[TransportState], None]] = None
        self._data_callback: Optional[Callable[[bytes], None]] = None

    @property
    def state(self) -> TransportState:
        """Get current transport state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if transport is connected."""
        return self._state == TransportState.CONNECTED

    def set_state_callback(self, callback: Optional[Callable[[TransportState], None]]) -> None:
        """
        Set callback for state changes.

        Args:
            callback: Function to call when state changes, or None to clear
        """
        self._state_callback = callback

    def set_data_callback(self, callback: Optional[Callable[[bytes], None]]) -> None:
        """
        Set callback for received data.

        Args:
            callback: Function to call when data is received, or None to clear
        """
        self._data_callback = callback

    def _set_state(self, new_state: TransportState) -> None:
        """
        Update transport state and notify callback.

        Args:
            new_state: New transport state
        """
        if self._state != new_state:
            self._state = new_state
            if self._state_callback:
                self._state_callback(new_state)

    def _on_data_received(self, data: bytes) -> None:
        """
        Handle received data and notify callback.

        Args:
            data: Received data bytes
        """
        if self._data_callback:
            self._data_callback(data)

    @staticmethod
    @abstractmethod
    def list_ports() -> list[TransportInfo]:
        """
        List available ports for this transport type.

        Returns:
            List of TransportInfo objects describing available ports
        """
        pass

    @abstractmethod
    async def connect(self, port: str, **kwargs) -> None:
        """
        Connect to the specified port.

        Args:
            port: Port identifier (e.g., "COM3" for serial)
            **kwargs: Transport-specific connection parameters

        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """
        Disconnect from the current port.

        This method should be safe to call even if not connected.
        """
        pass

    @abstractmethod
    async def send(self, data: bytes) -> None:
        """
        Send data to the connected device.

        Args:
            data: Data bytes to send

        Raises:
            ConnectionError: If not connected
            TransportError: If send fails
        """
        pass

    @abstractmethod
    async def receive(self, timeout: Optional[float] = None) -> bytes:
        """
        Receive data from the connected device.

        Args:
            timeout: Receive timeout in seconds, None for default

        Returns:
            Received data bytes

        Raises:
            ConnectionError: If not connected
            TimeoutError: If timeout expires
        """
        pass

    @abstractmethod
    async def receive_stream(self) -> AsyncIterator[bytes]:
        """
        Create an async iterator for receiving data.

        Yields:
            Received data bytes as they arrive

        Raises:
            ConnectionError: If not connected
        """
        pass

    async def send_and_receive(
        self, data: bytes, timeout: float = 1.0
    ) -> bytes:
        """
        Send data and wait for response.

        Args:
            data: Data to send
            timeout: Response timeout in seconds

        Returns:
            Response data

        Raises:
            TimeoutError: If no response within timeout
        """
        await self.send(data)
        return await self.receive(timeout)

    @abstractmethod
    def get_port_info(self) -> Optional[TransportInfo]:
        """
        Get information about the currently connected port.

        Returns:
            TransportInfo for current port, or None if not connected
        """
        pass


class MockTransport(TransportBase):
    """
    Mock transport for testing purposes.

    This transport can be used for unit testing and development
    without a physical PMU-30 device.
    """

    def __init__(self):
        super().__init__()
        self._rx_buffer = asyncio.Queue()
        self._tx_log: list[bytes] = []
        self._connected_port: Optional[str] = None
        self._auto_response: Optional[Callable[[bytes], Optional[bytes]]] = None

    def set_auto_response(self, handler: Optional[Callable[[bytes], Optional[bytes]]]) -> None:
        """
        Set auto-response handler for testing.

        Args:
            handler: Function that receives sent data and returns response, or None
        """
        self._auto_response = handler

    def inject_data(self, data: bytes) -> None:
        """
        Inject data into the receive buffer for testing.

        Args:
            data: Data to inject
        """
        self._rx_buffer.put_nowait(data)

    def get_tx_log(self) -> list[bytes]:
        """Get log of all transmitted data."""
        return self._tx_log.copy()

    def clear_tx_log(self) -> None:
        """Clear the transmission log."""
        self._tx_log.clear()

    @staticmethod
    def list_ports() -> list[TransportInfo]:
        """List mock ports."""
        return [
            TransportInfo(
                port="MOCK1",
                description="Mock PMU-30 Device 1",
                hardware_id="MOCK_001",
                is_pmu30=True
            ),
            TransportInfo(
                port="MOCK2",
                description="Mock PMU-30 Device 2",
                hardware_id="MOCK_002",
                is_pmu30=True
            ),
        ]

    async def connect(self, port: str, **kwargs) -> None:
        """Connect to mock port."""
        self._set_state(TransportState.CONNECTING)
        await asyncio.sleep(0.1)  # Simulate connection delay
        self._connected_port = port
        self._set_state(TransportState.CONNECTED)

    async def disconnect(self) -> None:
        """Disconnect from mock port."""
        self._connected_port = None
        self._set_state(TransportState.DISCONNECTED)

    async def send(self, data: bytes) -> None:
        """Send data (logs to tx_log)."""
        if not self.is_connected:
            raise ConnectionError("Not connected")
        self._tx_log.append(data)

        # Auto-response if handler is set
        if self._auto_response:
            response = self._auto_response(data)
            if response:
                self._rx_buffer.put_nowait(response)

    async def receive(self, timeout: Optional[float] = None) -> bytes:
        """Receive data from buffer."""
        if not self.is_connected:
            raise ConnectionError("Not connected")
        try:
            return await asyncio.wait_for(
                self._rx_buffer.get(),
                timeout=timeout or 1.0
            )
        except asyncio.TimeoutError:
            raise TimeoutError("Receive timeout")

    async def receive_stream(self) -> AsyncIterator[bytes]:
        """Stream data from buffer."""
        if not self.is_connected:
            raise ConnectionError("Not connected")
        while self.is_connected:
            try:
                data = await asyncio.wait_for(self._rx_buffer.get(), timeout=0.1)
                yield data
            except asyncio.TimeoutError:
                continue

    def get_port_info(self) -> Optional[TransportInfo]:
        """Get current port info."""
        if not self._connected_port:
            return None
        return TransportInfo(
            port=self._connected_port,
            description=f"Mock Port {self._connected_port}",
            is_pmu30=True
        )
