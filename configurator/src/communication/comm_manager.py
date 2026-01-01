"""
PMU-30 Communication Manager

High-level communication manager that handles:
- Connection lifecycle management
- Protocol message encoding/decoding
- Telemetry streaming
- Configuration upload/download
- Automatic reconnection
- Keep-alive (ping/pong)
"""

import asyncio
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Callable, AsyncIterator
import logging
import time

from .protocol import (
    MessageType,
    ProtocolFrame,
    ProtocolError,
    encode_frame,
    decode_frame,
    FrameBuilder,
    FrameParser,
)
from .transport_base import TransportBase, TransportState, TransportInfo
from .telemetry import (
    TelemetryPacket,
    DeviceInfo,
    parse_telemetry,
    TELEMETRY_PACKET_SIZE,
)


logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """High-level connection state."""
    DISCONNECTED = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    STREAMING = auto()
    ERROR = auto()
    RECONNECTING = auto()


@dataclass
class ConnectionStats:
    """Connection statistics."""
    connected_at: Optional[float] = None
    last_rx_time: Optional[float] = None
    last_tx_time: Optional[float] = None
    packets_received: int = 0
    packets_sent: int = 0
    bytes_received: int = 0
    bytes_sent: int = 0
    errors: int = 0
    reconnects: int = 0

    @property
    def uptime(self) -> float:
        """Get connection uptime in seconds."""
        if self.connected_at:
            return time.time() - self.connected_at
        return 0.0

    @property
    def time_since_rx(self) -> Optional[float]:
        """Get time since last receive in seconds."""
        if self.last_rx_time:
            return time.time() - self.last_rx_time
        return None


class CommManager:
    """
    High-level communication manager for PMU-30.

    This class provides a high-level interface for communicating with PMU-30
    devices, handling protocol encoding/decoding, telemetry streaming, and
    connection management.

    Example usage:
        transport = SerialTransport()
        manager = CommManager(transport)

        await manager.connect("COM3")

        # Get device info
        info = await manager.get_device_info()
        print(f"Connected to {info.device_name}")

        # Stream telemetry
        await manager.start_telemetry()
        async for packet in manager.telemetry_stream():
            print(f"Voltage: {packet.input_voltage}V")
    """

    def __init__(
        self,
        transport: TransportBase,
        ping_interval: float = 5.0,
        ping_timeout: float = 2.0,
        auto_reconnect: bool = True,
        reconnect_delay: float = 1.0,
    ):
        """
        Initialize communication manager.

        Args:
            transport: Transport instance for communication
            ping_interval: Interval between ping messages (seconds)
            ping_timeout: Timeout for ping response (seconds)
            auto_reconnect: Enable automatic reconnection
            reconnect_delay: Delay before reconnection attempt (seconds)
        """
        self._transport = transport
        self._ping_interval = ping_interval
        self._ping_timeout = ping_timeout
        self._auto_reconnect = auto_reconnect
        self._reconnect_delay = reconnect_delay

        self._state = ConnectionState.DISCONNECTED
        self._state_callbacks: list[Callable[[ConnectionState], None]] = []
        self._telemetry_callbacks: list[Callable[[TelemetryPacket], None]] = []
        self._error_callbacks: list[Callable[[int, str], None]] = []

        self._rx_buffer = bytearray()
        self._pending_requests: dict[MessageType, asyncio.Future] = {}
        self._telemetry_queue: asyncio.Queue[TelemetryPacket] = asyncio.Queue(maxsize=100)

        self._stats = ConnectionStats()
        self._device_info: Optional[DeviceInfo] = None
        self._current_port: Optional[str] = None

        self._read_task: Optional[asyncio.Task] = None
        self._ping_task: Optional[asyncio.Task] = None
        self._is_streaming = False

        # Set up transport callback
        self._transport.set_data_callback(self._on_data_received)

    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if connected to device."""
        return self._state in (ConnectionState.CONNECTED, ConnectionState.STREAMING)

    @property
    def is_streaming(self) -> bool:
        """Check if telemetry streaming is active."""
        return self._is_streaming

    @property
    def stats(self) -> ConnectionStats:
        """Get connection statistics."""
        return self._stats

    @property
    def device_info(self) -> Optional[DeviceInfo]:
        """Get cached device info."""
        return self._device_info

    def add_state_callback(self, callback: Callable[[ConnectionState], None]) -> None:
        """Add callback for state changes."""
        self._state_callbacks.append(callback)

    def remove_state_callback(self, callback: Callable[[ConnectionState], None]) -> None:
        """Remove state change callback."""
        if callback in self._state_callbacks:
            self._state_callbacks.remove(callback)

    def add_telemetry_callback(self, callback: Callable[[TelemetryPacket], None]) -> None:
        """Add callback for telemetry packets."""
        self._telemetry_callbacks.append(callback)

    def remove_telemetry_callback(self, callback: Callable[[TelemetryPacket], None]) -> None:
        """Remove telemetry callback."""
        if callback in self._telemetry_callbacks:
            self._telemetry_callbacks.remove(callback)

    def add_error_callback(self, callback: Callable[[int, str], None]) -> None:
        """Add callback for error messages."""
        self._error_callbacks.append(callback)

    def _set_state(self, new_state: ConnectionState) -> None:
        """Update state and notify callbacks."""
        if self._state != new_state:
            old_state = self._state
            self._state = new_state
            logger.info(f"Connection state: {old_state.name} -> {new_state.name}")
            for callback in self._state_callbacks:
                try:
                    callback(new_state)
                except Exception as e:
                    logger.error(f"State callback error: {e}")

    async def connect(self, port: str, **kwargs) -> bool:
        """
        Connect to PMU-30 device.

        Args:
            port: Port identifier
            **kwargs: Transport-specific connection parameters

        Returns:
            True if connection successful
        """
        if self.is_connected:
            await self.disconnect()

        self._set_state(ConnectionState.CONNECTING)
        self._current_port = port

        try:
            await self._transport.connect(port, **kwargs)

            # Reset stats
            self._stats = ConnectionStats(connected_at=time.time())

            # Start background tasks
            self._read_task = asyncio.create_task(self._read_loop())
            self._ping_task = asyncio.create_task(self._ping_loop())

            # Get device info
            try:
                self._device_info = await self.get_device_info(timeout=2.0)
                logger.info(f"Connected to {self._device_info.device_name} "
                           f"(FW: {self._device_info.firmware_version})")
            except Exception as e:
                logger.warning(f"Could not get device info: {e}")

            self._set_state(ConnectionState.CONNECTED)
            return True

        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self._set_state(ConnectionState.ERROR)
            self._stats.errors += 1
            return False

    async def disconnect(self) -> None:
        """Disconnect from device."""
        # Stop streaming
        if self._is_streaming:
            try:
                await self.stop_telemetry()
            except Exception:
                pass

        # Cancel tasks
        if self._ping_task:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
            self._ping_task = None

        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
            self._read_task = None

        # Disconnect transport
        await self._transport.disconnect()

        self._rx_buffer.clear()
        self._pending_requests.clear()
        self._device_info = None
        self._current_port = None
        self._set_state(ConnectionState.DISCONNECTED)

    async def send_frame(self, frame: ProtocolFrame) -> None:
        """
        Send a protocol frame.

        Args:
            frame: Frame to send
        """
        data = encode_frame(frame)
        await self._transport.send(data)
        self._stats.packets_sent += 1
        self._stats.bytes_sent += len(data)
        self._stats.last_tx_time = time.time()

    async def send_and_wait(
        self,
        frame: ProtocolFrame,
        response_type: MessageType,
        timeout: float = 2.0,
    ) -> ProtocolFrame:
        """
        Send frame and wait for specific response.

        Args:
            frame: Frame to send
            response_type: Expected response message type
            timeout: Response timeout in seconds

        Returns:
            Response frame

        Raises:
            TimeoutError: If no response within timeout
            ProtocolError: If error response received
        """
        future: asyncio.Future[ProtocolFrame] = asyncio.get_event_loop().create_future()
        self._pending_requests[response_type] = future

        try:
            await self.send_frame(frame)
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"No response for {frame.msg_type.name}")
        finally:
            self._pending_requests.pop(response_type, None)

    async def get_device_info(self, timeout: float = 2.0) -> DeviceInfo:
        """
        Request device information.

        Args:
            timeout: Response timeout

        Returns:
            DeviceInfo from device
        """
        frame = FrameBuilder.get_info()
        response = await self.send_and_wait(frame, MessageType.INFO_RESP, timeout)

        info_dict = FrameParser.parse_info_response(response.payload)
        return DeviceInfo(
            firmware_version=info_dict["firmware_version"],
            hardware_revision=info_dict["hardware_revision"],
            serial_number=info_dict["serial_number"],
            device_name=info_dict["device_name"],
        )

    async def start_telemetry(self, rate_hz: int = 50) -> None:
        """
        Start telemetry streaming.

        Args:
            rate_hz: Telemetry update rate in Hz
        """
        frame = FrameBuilder.subscribe_telemetry(rate_hz)
        await self.send_frame(frame)
        self._is_streaming = True
        self._set_state(ConnectionState.STREAMING)
        logger.info(f"Telemetry streaming started at {rate_hz}Hz")

    async def stop_telemetry(self) -> None:
        """Stop telemetry streaming."""
        frame = FrameBuilder.unsubscribe_telemetry()
        await self.send_frame(frame)
        self._is_streaming = False
        if self._transport.is_connected:
            self._set_state(ConnectionState.CONNECTED)
        logger.info("Telemetry streaming stopped")

    async def telemetry_stream(self) -> AsyncIterator[TelemetryPacket]:
        """
        Async iterator for telemetry packets.

        Yields:
            TelemetryPacket as they arrive
        """
        while self.is_connected:
            try:
                packet = await asyncio.wait_for(
                    self._telemetry_queue.get(),
                    timeout=0.5
                )
                yield packet
            except asyncio.TimeoutError:
                continue

    async def set_channel(self, channel_id: int, value: float) -> bool:
        """
        Set channel value.

        Args:
            channel_id: Channel identifier
            value: New value

        Returns:
            True if successful
        """
        frame = FrameBuilder.set_channel(channel_id, value)
        try:
            response = await self.send_and_wait(frame, MessageType.CHANNEL_ACK, timeout=1.0)
            ch_id, success, error_code = FrameParser.parse_channel_ack(response.payload)
            return success
        except Exception as e:
            logger.error(f"Set channel failed: {e}")
            return False

    async def set_hbridge(self, bridge: int, mode: int, duty: int, target: int = 0) -> bool:
        """
        Set H-Bridge mode and PWM.

        Args:
            bridge: Bridge number (0-3)
            mode: Operating mode (0=COAST, 1=FWD, 2=REV, 3=BRAKE, 4=WIPER_PARK, 5=PID)
            duty: PWM duty cycle (0-1000)
            target: Target position for PID mode (0-1000)

        Returns:
            True if successful
        """
        frame = FrameBuilder.set_hbridge(bridge, mode, duty, target)
        try:
            response = await self.send_and_wait(frame, MessageType.CHANNEL_ACK, timeout=1.0)
            return True
        except Exception as e:
            logger.error(f"Set H-Bridge failed: {e}")
            return False

    async def set_digital_input(self, channel: int, state: bool) -> bool:
        """
        Set digital input state (emulator only).

        Args:
            channel: Digital input channel (0-19)
            state: Input state (True=HIGH, False=LOW)

        Returns:
            True if successful
        """
        frame = FrameBuilder.emu_set_digital_input(channel, state)
        try:
            await self.send_frame(frame)
            return True
        except Exception as e:
            logger.error(f"Set digital input failed: {e}")
            return False

    async def set_analog_input(self, channel: int, voltage: float) -> bool:
        """
        Set analog input voltage (emulator only).

        Args:
            channel: Analog input channel (0-19)
            voltage: Voltage in volts (0.0-5.0)

        Returns:
            True if successful
        """
        voltage_mv = int(voltage * 1000)
        frame = FrameBuilder.emu_set_analog_input(channel, voltage_mv)
        try:
            await self.send_frame(frame)
            return True
        except Exception as e:
            logger.error(f"Set analog input failed: {e}")
            return False

    async def inject_can_message(self, bus_id: int, can_id: int, data: bytes) -> bool:
        """
        Inject CAN message for testing (emulator only).

        Args:
            bus_id: CAN bus index (0 or 1)
            can_id: CAN message ID
            data: CAN data bytes (up to 8)

        Returns:
            True if successful
        """
        frame = FrameBuilder.emu_inject_can(bus_id, can_id, data)
        try:
            await self.send_frame(frame)
            return True
        except Exception as e:
            logger.error(f"Inject CAN message failed: {e}")
            return False

    async def get_configuration(self) -> bytes:
        """
        Download binary configuration from device.

        Returns:
            Configuration data as bytes (.pmu30 binary format)
        """
        # Stop telemetry stream first to avoid interference
        stop_frame = FrameBuilder.unsubscribe_telemetry()
        await self.send_frame(stop_frame)
        await asyncio.sleep(0.1)  # Give device time to stop stream

        # Clear any pending telemetry data
        self._pending_requests.clear()

        frame = FrameBuilder.get_config()
        await self.send_frame(frame)

        chunks: dict[int, bytes] = {}
        total_chunks = 0

        while True:
            try:
                response = await asyncio.wait_for(
                    self._wait_for_message(MessageType.CONFIG_DATA),
                    timeout=5.0
                )
                chunk_idx, total, data = FrameParser.parse_config_data(response.payload)
                chunks[chunk_idx] = data
                total_chunks = total

                if len(chunks) == total_chunks:
                    break
            except asyncio.TimeoutError:
                raise TimeoutError("Configuration download timeout")

        # Reassemble chunks
        config_data = b"".join(chunks[i] for i in range(total_chunks))
        logger.info(f"Downloaded {len(config_data)} bytes of configuration")
        return config_data

    async def set_configuration(self, config_data: bytes, chunk_size: int = 1024) -> bool:
        """
        Upload binary configuration to device.

        Args:
            config_data: Binary configuration data (.pmu30 format)
            chunk_size: Size of each chunk

        Returns:
            True if successful
        """
        # Split into chunks
        chunks = [
            config_data[i:i + chunk_size]
            for i in range(0, len(config_data), chunk_size)
        ]
        total_chunks = len(chunks)

        for idx, chunk in enumerate(chunks):
            frame = FrameBuilder.set_config(chunk, idx, total_chunks)
            await self.send_frame(frame)
            await asyncio.sleep(0.01)  # Small delay between chunks

        # Wait for final acknowledgment
        try:
            response = await asyncio.wait_for(
                self._wait_for_message(MessageType.CONFIG_ACK),
                timeout=5.0
            )
            success, error_code = FrameParser.parse_config_ack(response.payload)
            if success:
                logger.info("Configuration uploaded successfully")
            else:
                logger.error(f"Configuration upload failed: error {error_code}")
            return success
        except asyncio.TimeoutError:
            logger.error("Configuration upload timeout")
            return False

    async def ping(self) -> float:
        """
        Send ping and measure round-trip time.

        Returns:
            Round-trip time in milliseconds
        """
        start = time.time()
        frame = FrameBuilder.ping()
        await self.send_and_wait(frame, MessageType.PONG, timeout=self._ping_timeout)
        return (time.time() - start) * 1000

    def _on_data_received(self, data: bytes) -> None:
        """Handle data from transport."""
        self._rx_buffer.extend(data)
        self._stats.bytes_received += len(data)
        self._stats.last_rx_time = time.time()

    async def _read_loop(self) -> None:
        """Background task to process received data."""
        while self.is_connected:
            await asyncio.sleep(0.001)  # Yield to other tasks

            while len(self._rx_buffer) >= 6:  # Minimum frame size
                try:
                    frame, consumed = decode_frame(bytes(self._rx_buffer))
                    if frame is None:
                        if consumed > 0:
                            # Skip invalid bytes
                            del self._rx_buffer[:consumed]
                        else:
                            # Need more data
                            break
                    else:
                        del self._rx_buffer[:consumed]
                        self._stats.packets_received += 1
                        await self._handle_frame(frame)
                except ProtocolError as e:
                    logger.warning(f"Protocol error: {e}")
                    self._stats.errors += 1
                    # Try to resync by skipping a byte
                    if self._rx_buffer:
                        del self._rx_buffer[0]

    async def _handle_frame(self, frame: ProtocolFrame) -> None:
        """Handle received protocol frame."""
        logger.debug(f"Received {frame.msg_type.name} ({len(frame.payload)} bytes)")

        # Handle telemetry data
        if frame.msg_type == MessageType.TELEMETRY_DATA:
            try:
                packet = parse_telemetry(frame.payload)
                # Notify callbacks
                for callback in self._telemetry_callbacks:
                    try:
                        callback(packet)
                    except Exception as e:
                        logger.error(f"Telemetry callback error: {e}")
                # Add to queue
                try:
                    self._telemetry_queue.put_nowait(packet)
                except asyncio.QueueFull:
                    # Drop oldest
                    try:
                        self._telemetry_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                    self._telemetry_queue.put_nowait(packet)
            except Exception as e:
                logger.error(f"Telemetry parse error: {e}")
            return

        # Handle error messages
        if frame.msg_type == MessageType.ERROR:
            error_code, message = FrameParser.parse_error(frame.payload)
            logger.error(f"Device error {error_code}: {message}")
            for callback in self._error_callbacks:
                try:
                    callback(error_code, message)
                except Exception as e:
                    logger.error(f"Error callback error: {e}")
            return

        # Handle pending requests
        if frame.msg_type in self._pending_requests:
            future = self._pending_requests[frame.msg_type]
            if not future.done():
                future.set_result(frame)

    async def _wait_for_message(self, msg_type: MessageType) -> ProtocolFrame:
        """Wait for a specific message type."""
        future: asyncio.Future[ProtocolFrame] = asyncio.get_event_loop().create_future()
        self._pending_requests[msg_type] = future
        try:
            return await future
        finally:
            self._pending_requests.pop(msg_type, None)

    async def _ping_loop(self) -> None:
        """Background task for keep-alive pings."""
        while self.is_connected:
            await asyncio.sleep(self._ping_interval)
            if not self._is_streaming:  # Don't ping during streaming
                try:
                    rtt = await self.ping()
                    logger.debug(f"Ping RTT: {rtt:.1f}ms")
                except Exception as e:
                    logger.warning(f"Ping failed: {e}")
                    if self._auto_reconnect and self._current_port:
                        await self._attempt_reconnect()

    async def _attempt_reconnect(self) -> None:
        """Attempt to reconnect to device."""
        if not self._current_port:
            return

        self._set_state(ConnectionState.RECONNECTING)
        self._stats.reconnects += 1

        await self._transport.disconnect()
        await asyncio.sleep(self._reconnect_delay)

        try:
            await self._transport.connect(self._current_port)
            self._set_state(ConnectionState.CONNECTED)
            logger.info("Reconnected successfully")

            # Resume streaming if it was active
            if self._is_streaming:
                await self.start_telemetry()
        except Exception as e:
            logger.error(f"Reconnect failed: {e}")
            self._set_state(ConnectionState.ERROR)
