"""
PMU-30 Emulator Transport Implementation

This module implements a TCP transport for connecting to the PMU-30 hardware emulator.
It allows the configurator to communicate with the emulator running on the same machine
or on a remote host.
"""

import asyncio
import socket
from typing import Optional, AsyncIterator
import logging

from .transport_base import (
    TransportBase,
    TransportInfo,
    TransportState,
    TransportError,
    ConnectionError,
    TimeoutError,
)


logger = logging.getLogger(__name__)


# Default emulator settings
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 9876
DEFAULT_TIMEOUT = 5.0
READ_BUFFER_SIZE = 8192


class EmulatorTransport(TransportBase):
    """
    TCP transport for connecting to PMU-30 hardware emulator.

    The emulator runs a TCP server that accepts connections and
    responds to the same protocol as the real hardware.

    Usage:
        transport = EmulatorTransport()
        await transport.connect("localhost:9876")
        # or
        await transport.connect("localhost")  # uses default port 9876
    """

    def __init__(self):
        super().__init__()
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._port_info: Optional[TransportInfo] = None
        self._read_task: Optional[asyncio.Task] = None
        self._rx_buffer = asyncio.Queue(maxsize=1000)
        self._host: str = ""
        self._port: int = DEFAULT_PORT

    @staticmethod
    def list_ports() -> list[TransportInfo]:
        """
        List available emulator endpoints.

        Returns a list of default emulator endpoints that can be connected to.
        Also tries to detect running emulators by probing common ports.
        """
        ports = []

        # Default localhost entry
        ports.append(TransportInfo(
            port=f"localhost:{DEFAULT_PORT}",
            description="PMU-30 Emulator (localhost)",
            hardware_id="EMULATOR",
            manufacturer="R2 m-sport",
            is_pmu30=True
        ))

        # Try to detect running emulator
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex((DEFAULT_HOST, DEFAULT_PORT))
            sock.close()

            if result == 0:
                # Emulator is running
                ports[0] = TransportInfo(
                    port=f"localhost:{DEFAULT_PORT}",
                    description="PMU-30 Emulator (ONLINE)",
                    hardware_id="EMULATOR",
                    manufacturer="R2 m-sport",
                    is_pmu30=True
                )
        except Exception:
            pass

        return ports

    @staticmethod
    def is_emulator_running(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> bool:
        """
        Check if an emulator is running at the specified address.

        Args:
            host: Hostname or IP address
            port: Port number

        Returns:
            True if emulator is accepting connections
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    async def connect(
        self,
        port: str,
        timeout: float = DEFAULT_TIMEOUT,
        **kwargs
    ) -> None:
        """
        Connect to the emulator.

        Args:
            port: Address in format "host:port" or just "host" (uses default port)
            timeout: Connection timeout in seconds
            **kwargs: Additional settings (ignored)

        Raises:
            ConnectionError: If connection fails
        """
        if self.is_connected:
            await self.disconnect()

        self._set_state(TransportState.CONNECTING)

        # Parse address
        if ":" in port:
            parts = port.split(":")
            self._host = parts[0]
            self._port = int(parts[1])
        else:
            self._host = port
            self._port = DEFAULT_PORT

        try:
            # Open TCP connection
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=timeout
            )

            # Create port info
            self._port_info = TransportInfo(
                port=f"{self._host}:{self._port}",
                description=f"PMU-30 Emulator at {self._host}:{self._port}",
                hardware_id="EMULATOR",
                manufacturer="R2 m-sport",
                is_pmu30=True
            )

            # Start background read task
            self._read_task = asyncio.create_task(self._read_loop())

            self._set_state(TransportState.CONNECTED)
            logger.info(f"Connected to emulator at {self._host}:{self._port}")

        except asyncio.TimeoutError:
            self._set_state(TransportState.ERROR)
            raise ConnectionError(f"Connection timeout to {self._host}:{self._port}")
        except Exception as e:
            self._set_state(TransportState.ERROR)
            raise ConnectionError(f"Failed to connect to {self._host}:{self._port}: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from the emulator."""
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
                logger.warning(f"Error closing connection: {e}")
            self._writer = None
            self._reader = None

        self._port_info = None
        self._set_state(TransportState.DISCONNECTED)
        logger.info("Disconnected from emulator")

    async def send(self, data: bytes) -> None:
        """
        Send data to the emulator.

        Args:
            data: Data bytes to send

        Raises:
            ConnectionError: If not connected
            TransportError: If send fails
        """
        if not self.is_connected or not self._writer:
            raise ConnectionError("Not connected to emulator")

        try:
            self._writer.write(data)
            await self._writer.drain()
            logger.debug(f"Sent {len(data)} bytes to emulator")
        except Exception as e:
            self._set_state(TransportState.ERROR)
            raise TransportError(f"Send failed: {e}") from e

    async def receive(self, timeout: Optional[float] = None) -> bytes:
        """
        Receive data from the emulator.

        Args:
            timeout: Receive timeout in seconds

        Returns:
            Received data bytes

        Raises:
            ConnectionError: If not connected
            TimeoutError: If timeout expires
        """
        if not self.is_connected:
            raise ConnectionError("Not connected to emulator")

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
            raise ConnectionError("Not connected to emulator")

        while self.is_connected:
            try:
                data = await asyncio.wait_for(self._rx_buffer.get(), timeout=0.1)
                yield data
            except asyncio.TimeoutError:
                continue

    def get_port_info(self) -> Optional[TransportInfo]:
        """Get information about the connected emulator."""
        return self._port_info

    async def _read_loop(self) -> None:
        """Background task to read from TCP connection."""
        while self.is_connected and self._reader:
            try:
                data = await self._reader.read(READ_BUFFER_SIZE)
                if data:
                    logger.debug(f"Received {len(data)} bytes from emulator")
                    await self._rx_buffer.put(data)
                    self._on_data_received(data)
                else:
                    # Empty read usually means disconnection
                    logger.warning("Empty read, emulator disconnected")
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


def find_emulators(hosts: list[str] = None, ports: list[int] = None) -> list[TransportInfo]:
    """
    Scan for running emulators.

    Args:
        hosts: List of hosts to scan (default: ["localhost"])
        ports: List of ports to scan (default: [9876])

    Returns:
        List of TransportInfo for detected emulators
    """
    if hosts is None:
        hosts = ["localhost", "127.0.0.1"]
    if ports is None:
        ports = [DEFAULT_PORT]

    found = []
    for host in hosts:
        for port in ports:
            if EmulatorTransport.is_emulator_running(host, port):
                found.append(TransportInfo(
                    port=f"{host}:{port}",
                    description=f"PMU-30 Emulator at {host}:{port}",
                    hardware_id="EMULATOR",
                    manufacturer="R2 m-sport",
                    is_pmu30=True
                ))

    return found


async def auto_connect_emulator() -> Optional[EmulatorTransport]:
    """
    Automatically connect to a running emulator.

    Returns:
        Connected EmulatorTransport, or None if no emulator found
    """
    if not EmulatorTransport.is_emulator_running():
        logger.warning("No PMU-30 emulator found")
        return None

    transport = EmulatorTransport()
    try:
        await transport.connect(f"{DEFAULT_HOST}:{DEFAULT_PORT}")
        return transport
    except ConnectionError as e:
        logger.error(f"Auto-connect to emulator failed: {e}")
        return None
