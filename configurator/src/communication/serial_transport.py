"""
PMU-30 USB Serial Transport Implementation

This module implements the USB Serial transport for communicating with PMU-30 devices.
It uses pyserial and pyserial-asyncio for async serial communication.
"""

import asyncio
from typing import Optional, AsyncIterator
import logging

try:
    import serial
    import serial.tools.list_ports
    from serial_asyncio import open_serial_connection
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

from .transport_base import (
    TransportBase,
    TransportInfo,
    TransportState,
    TransportError,
    ConnectionError,
    TimeoutError,
)


logger = logging.getLogger(__name__)


# PMU-30 USB identifiers
PMU30_VID = 0x0483  # STMicroelectronics
PMU30_PID = 0x5740  # Virtual COM Port

# Default serial settings
DEFAULT_BAUDRATE = 115200
DEFAULT_TIMEOUT = 1.0
READ_BUFFER_SIZE = 4096


class SerialTransport(TransportBase):
    """
    USB Serial transport for PMU-30 communication.

    Uses pyserial-asyncio for async serial I/O with proper buffering
    and error handling.
    """

    def __init__(self):
        super().__init__()
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._port_info: Optional[TransportInfo] = None
        self._read_task: Optional[asyncio.Task] = None
        self._rx_buffer = asyncio.Queue(maxsize=1000)

    @staticmethod
    def list_ports() -> list[TransportInfo]:
        """
        List available serial ports.

        Returns:
            List of TransportInfo for each available port,
            with is_pmu30=True for detected PMU-30 devices.
        """
        if not SERIAL_AVAILABLE:
            logger.warning("pyserial not installed, cannot list ports")
            return []

        ports = []
        for port in serial.tools.list_ports.comports():
            is_pmu30 = (
                port.vid == PMU30_VID and port.pid == PMU30_PID
            ) or "PMU" in (port.description or "").upper()

            ports.append(TransportInfo(
                port=port.device,
                description=port.description or "",
                hardware_id=port.hwid or "",
                manufacturer=port.manufacturer or "",
                is_pmu30=is_pmu30
            ))

        # Sort with PMU-30 devices first
        ports.sort(key=lambda p: (not p.is_pmu30, p.port))
        return ports

    async def connect(
        self,
        port: str,
        baudrate: int = DEFAULT_BAUDRATE,
        **kwargs
    ) -> None:
        """
        Connect to the specified serial port.

        Args:
            port: Serial port name (e.g., "COM3" or "/dev/ttyUSB0")
            baudrate: Baud rate (default 115200)
            **kwargs: Additional serial settings

        Raises:
            ConnectionError: If connection fails
        """
        if not SERIAL_AVAILABLE:
            raise ConnectionError("pyserial not installed")

        if self.is_connected:
            await self.disconnect()

        self._set_state(TransportState.CONNECTING)

        try:
            # Open serial connection
            self._reader, self._writer = await open_serial_connection(
                url=port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                xonxoff=False,
                rtscts=False,
                **kwargs
            )

            # Find port info
            for info in self.list_ports():
                if info.port == port:
                    self._port_info = info
                    break
            else:
                self._port_info = TransportInfo(port=port, description="")

            # Start background read task
            self._read_task = asyncio.create_task(self._read_loop())

            self._set_state(TransportState.CONNECTED)
            logger.info(f"Connected to {port} at {baudrate} baud")

        except Exception as e:
            self._set_state(TransportState.ERROR)
            raise ConnectionError(f"Failed to connect to {port}: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from the serial port."""
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
            self._read_task = None

        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception as e:
                logger.warning(f"Error closing serial port: {e}")
            self._writer = None
            self._reader = None

        self._port_info = None
        self._set_state(TransportState.DISCONNECTED)
        logger.info("Disconnected from serial port")

    async def send(self, data: bytes) -> None:
        """
        Send data to the connected device.

        Args:
            data: Data bytes to send

        Raises:
            ConnectionError: If not connected
            TransportError: If send fails
        """
        if not self.is_connected or not self._writer:
            raise ConnectionError("Not connected")

        try:
            self._writer.write(data)
            await self._writer.drain()
            logger.debug(f"Sent {len(data)} bytes")
        except Exception as e:
            self._set_state(TransportState.ERROR)
            raise TransportError(f"Send failed: {e}") from e

    async def receive(self, timeout: Optional[float] = None) -> bytes:
        """
        Receive data from the connected device.

        Args:
            timeout: Receive timeout in seconds

        Returns:
            Received data bytes

        Raises:
            ConnectionError: If not connected
            TimeoutError: If timeout expires
        """
        if not self.is_connected:
            raise ConnectionError("Not connected")

        try:
            data = await asyncio.wait_for(
                self._rx_buffer.get(),
                timeout=timeout or DEFAULT_TIMEOUT
            )
            return data
        except asyncio.TimeoutError:
            raise TimeoutError("Receive timeout")

    async def receive_stream(self) -> AsyncIterator[bytes]:
        """
        Create an async iterator for receiving data.

        Yields:
            Received data bytes as they arrive
        """
        if not self.is_connected:
            raise ConnectionError("Not connected")

        while self.is_connected:
            try:
                data = await asyncio.wait_for(self._rx_buffer.get(), timeout=0.1)
                yield data
            except asyncio.TimeoutError:
                continue

    def get_port_info(self) -> Optional[TransportInfo]:
        """Get information about the connected port."""
        return self._port_info

    async def _read_loop(self) -> None:
        """Background task to read from serial port."""
        while self.is_connected and self._reader:
            try:
                data = await self._reader.read(READ_BUFFER_SIZE)
                if data:
                    logger.debug(f"Received {len(data)} bytes")
                    await self._rx_buffer.put(data)
                    self._on_data_received(data)
                else:
                    # Empty read usually means disconnection
                    logger.warning("Empty read, possible disconnection")
                    break
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Read error: {e}")
                self._set_state(TransportState.ERROR)
                break

    async def flush_input(self) -> None:
        """Flush the input buffer."""
        while not self._rx_buffer.empty():
            try:
                self._rx_buffer.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def flush_output(self) -> None:
        """Flush the output buffer."""
        if self._writer:
            await self._writer.drain()


def find_pmu30_ports() -> list[TransportInfo]:
    """
    Find all connected PMU-30 devices.

    Returns:
        List of TransportInfo for PMU-30 devices only
    """
    return [p for p in SerialTransport.list_ports() if p.is_pmu30]


async def auto_connect() -> Optional[SerialTransport]:
    """
    Automatically connect to the first available PMU-30 device.

    Returns:
        Connected SerialTransport, or None if no device found
    """
    pmu_ports = find_pmu30_ports()
    if not pmu_ports:
        logger.warning("No PMU-30 devices found")
        return None

    transport = SerialTransport()
    try:
        await transport.connect(pmu_ports[0].port)
        return transport
    except ConnectionError as e:
        logger.error(f"Auto-connect failed: {e}")
        return None
