"""
PMU-30 Device Simulator
Simulates a PMU-30 device for testing the configurator without hardware.

Implements:
- Protocol responses (PING, GET_INFO, CONFIG, TELEMETRY)
- Simulated telemetry data
- Configuration storage
- Channel state simulation
"""

import asyncio
import struct
import random
import time
import json
import logging
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field

from .protocol import (
    MessageType, ProtocolFrame, encode_frame, decode_frame,
    FrameBuilder, FrameParser, crc16_ccitt
)
from .telemetry import (
    TelemetryPacket, ChannelState, FaultFlags,
    create_telemetry_bytes, TELEMETRY_PACKET_SIZE
)

logger = logging.getLogger(__name__)


@dataclass
class SimulatedChannel:
    """Simulated output channel state."""
    state: ChannelState = ChannelState.OFF
    target_duty: int = 0  # 0-1000
    current_ma: int = 0
    temperature_c: int = 25
    fault_count: int = 0


@dataclass
class SimulatorState:
    """Complete simulator state."""
    # Device info
    firmware_version: str = "1.2.3"
    hardware_revision: int = 5
    serial_number: str = "PMU30-SIM-001"
    device_name: str = "PMU-30 Simulator"

    # System state
    input_voltage_mv: int = 13500
    temperature_c: int = 35
    uptime_ms: int = 0
    fault_flags: FaultFlags = FaultFlags.NONE

    # Channels
    channels: list = field(default_factory=lambda: [SimulatedChannel() for _ in range(30)])
    analog_inputs: list = field(default_factory=lambda: [0] * 20)

    # Configuration
    config_data: bytes = b'{}'

    # Telemetry
    telemetry_rate_hz: int = 0
    telemetry_enabled: bool = False


class DeviceSimulator:
    """
    PMU-30 Device Simulator.

    Provides a virtual serial port interface that responds to
    protocol commands like a real device.
    """

    def __init__(self):
        self.state = SimulatorState()
        self._running = False
        self._telemetry_task: Optional[asyncio.Task] = None
        self._rx_queue: asyncio.Queue = asyncio.Queue()
        self._tx_queue: asyncio.Queue = asyncio.Queue()
        self._on_telemetry: Optional[Callable] = None
        self._start_time = time.time()

    async def start(self):
        """Start the simulator."""
        self._running = True
        self._start_time = time.time()
        logger.info("Device simulator started")

    async def stop(self):
        """Stop the simulator."""
        self._running = False
        if self._telemetry_task:
            self._telemetry_task.cancel()
            try:
                await self._telemetry_task
            except asyncio.CancelledError:
                pass
        logger.info("Device simulator stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    async def process_frame(self, data: bytes) -> Optional[bytes]:
        """
        Process incoming frame and return response.

        Args:
            data: Raw frame bytes

        Returns:
            Response frame bytes or None
        """
        try:
            frame, consumed = decode_frame(data)
            if frame is None:
                return None

            return await self._handle_message(frame)

        except Exception as e:
            logger.error(f"Simulator error processing frame: {e}")
            return self._create_error_response(0xFF, str(e))

    async def _handle_message(self, frame: ProtocolFrame) -> Optional[bytes]:
        """Handle decoded message and generate response."""
        msg_type = frame.msg_type
        payload = frame.payload

        if msg_type == MessageType.PING:
            return self._handle_ping()

        elif msg_type == MessageType.GET_INFO:
            return self._handle_get_info()

        elif msg_type == MessageType.GET_CONFIG:
            return self._handle_get_config()

        elif msg_type == MessageType.SET_CONFIG:
            return self._handle_set_config(payload)

        elif msg_type == MessageType.SET_CHANNEL:
            return self._handle_set_channel(payload)

        elif msg_type == MessageType.SUBSCRIBE_TELEMETRY:
            return await self._handle_subscribe_telemetry(payload)

        elif msg_type == MessageType.UNSUBSCRIBE_TELEMETRY:
            return self._handle_unsubscribe_telemetry()

        else:
            return self._create_error_response(0x03, f"Unknown message type: {msg_type}")

    def _handle_ping(self) -> bytes:
        """Handle PING -> PONG."""
        frame = FrameBuilder.pong()
        return encode_frame(frame)

    def _handle_get_info(self) -> bytes:
        """Handle GET_INFO -> INFO_RESP."""
        # Build info response payload
        # 3 bytes version + 1 hw rev + 16 serial + 32 name
        version_parts = self.state.firmware_version.split('.')
        version_bytes = struct.pack("BBB",
            int(version_parts[0]),
            int(version_parts[1]),
            int(version_parts[2])
        )

        hw_rev = struct.pack("B", self.state.hardware_revision)

        serial = self.state.serial_number.encode('utf-8')[:15].ljust(16, b'\x00')

        name = self.state.device_name.encode('utf-8')[:31].ljust(32, b'\x00')

        payload = version_bytes + hw_rev + serial + name

        frame = ProtocolFrame(msg_type=MessageType.INFO_RESP, payload=payload)
        return encode_frame(frame)

    def _handle_get_config(self) -> bytes:
        """Handle GET_CONFIG -> CONFIG_DATA chunks."""
        config = self.state.config_data
        chunk_size = 512

        # For simplicity, send as single chunk
        chunks = [config[i:i+chunk_size] for i in range(0, len(config), chunk_size)]
        if not chunks:
            chunks = [b'{}']

        # Send first chunk (caller should handle multi-chunk)
        total = len(chunks)
        chunk_data = chunks[0]

        payload = struct.pack("<HH", 0, total) + chunk_data
        frame = ProtocolFrame(msg_type=MessageType.CONFIG_DATA, payload=payload)
        return encode_frame(frame)

    def _handle_set_config(self, payload: bytes) -> bytes:
        """Handle SET_CONFIG -> CONFIG_ACK."""
        try:
            chunk_idx, total = struct.unpack("<HH", payload[:4])
            chunk_data = payload[4:]

            # For simplicity, assume single chunk
            if chunk_idx == 0:
                self.state.config_data = chunk_data
            else:
                self.state.config_data += chunk_data

            # Validate JSON
            try:
                json.loads(self.state.config_data)
                success = True
                error_code = 0
            except json.JSONDecodeError:
                if chunk_idx < total - 1:
                    # Not complete yet
                    success = True
                    error_code = 0
                else:
                    success = False
                    error_code = 0x20  # Parse error

            payload = struct.pack("<BH", 1 if success else 0, error_code)
            frame = ProtocolFrame(msg_type=MessageType.CONFIG_ACK, payload=payload)
            return encode_frame(frame)

        except Exception as e:
            logger.error(f"Config error: {e}")
            payload = struct.pack("<BH", 0, 0x21)  # Validation error
            frame = ProtocolFrame(msg_type=MessageType.CONFIG_ACK, payload=payload)
            return encode_frame(frame)

    def _handle_set_channel(self, payload: bytes) -> bytes:
        """Handle SET_CHANNEL -> CHANNEL_ACK."""
        try:
            channel_id, value = struct.unpack("<Hf", payload)

            if channel_id >= 30:
                payload = struct.pack("<BH", 0, channel_id)
                frame = ProtocolFrame(msg_type=MessageType.CHANNEL_ACK, payload=payload)
                return encode_frame(frame)

            # Update channel state
            duty = int(value * 10)  # Convert 0-100 to 0-1000
            self.state.channels[channel_id].target_duty = duty

            if duty == 0:
                self.state.channels[channel_id].state = ChannelState.OFF
            elif duty == 1000:
                self.state.channels[channel_id].state = ChannelState.ON
            else:
                self.state.channels[channel_id].state = ChannelState.PWM_ACTIVE

            # Simulate current draw
            self.state.channels[channel_id].current_ma = int(duty * 5)  # ~5A max

            payload = struct.pack("<BH", 1, channel_id)
            frame = ProtocolFrame(msg_type=MessageType.CHANNEL_ACK, payload=payload)
            return encode_frame(frame)

        except Exception as e:
            logger.error(f"Set channel error: {e}")
            payload = struct.pack("<BH", 0, 0xFFFF)
            frame = ProtocolFrame(msg_type=MessageType.CHANNEL_ACK, payload=payload)
            return encode_frame(frame)

    async def _handle_subscribe_telemetry(self, payload: bytes) -> bytes:
        """Handle SUBSCRIBE_TELEMETRY - start telemetry stream."""
        rate_hz = struct.unpack("<H", payload)[0]

        self.state.telemetry_rate_hz = min(rate_hz, 100)  # Max 100 Hz
        self.state.telemetry_enabled = True

        # Start telemetry task
        if self._telemetry_task:
            self._telemetry_task.cancel()

        self._telemetry_task = asyncio.create_task(self._telemetry_loop())

        # Return ACK (empty PONG for now)
        return encode_frame(FrameBuilder.pong())

    def _handle_unsubscribe_telemetry(self) -> bytes:
        """Handle UNSUBSCRIBE_TELEMETRY - stop telemetry stream."""
        self.state.telemetry_enabled = False
        self.state.telemetry_rate_hz = 0

        if self._telemetry_task:
            self._telemetry_task.cancel()
            self._telemetry_task = None

        return encode_frame(FrameBuilder.pong())

    async def _telemetry_loop(self):
        """Generate telemetry data at specified rate."""
        try:
            while self.state.telemetry_enabled and self._running:
                interval = 1.0 / max(self.state.telemetry_rate_hz, 1)

                # Generate telemetry packet
                packet = self._generate_telemetry()

                # Notify callback
                if self._on_telemetry:
                    frame_data = create_telemetry_bytes(packet)
                    frame = ProtocolFrame(msg_type=MessageType.TELEMETRY_DATA, payload=frame_data)
                    await self._tx_queue.put(encode_frame(frame))

                await asyncio.sleep(interval)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Telemetry loop error: {e}")

    def _generate_telemetry(self) -> TelemetryPacket:
        """Generate simulated telemetry data."""
        # Update uptime
        self.state.uptime_ms = int((time.time() - self._start_time) * 1000)

        # Simulate voltage fluctuation
        self.state.input_voltage_mv = 13500 + random.randint(-100, 100)

        # Simulate temperature drift
        self.state.temperature_c = 35 + random.randint(-2, 2)

        # Simulate analog inputs
        for i in range(20):
            self.state.analog_inputs[i] = random.randint(0, 4095)

        # Build packet
        channel_states = [ch.state for ch in self.state.channels]
        output_currents = [ch.current_ma for ch in self.state.channels]

        return TelemetryPacket(
            timestamp_ms=self.state.uptime_ms,
            channel_states=channel_states,
            analog_values=self.state.analog_inputs[:8],
            output_currents=output_currents,
            input_voltage_mv=self.state.input_voltage_mv,
            temperature_c=self.state.temperature_c,
            fault_flags=self.state.fault_flags,
        )

    def _create_error_response(self, error_code: int, message: str) -> bytes:
        """Create ERROR response frame."""
        msg_bytes = message.encode('utf-8')[:255]
        payload = struct.pack("<HB", error_code, len(msg_bytes)) + msg_bytes
        frame = ProtocolFrame(msg_type=MessageType.ERROR, payload=payload)
        return encode_frame(frame)

    def set_channel_state(self, channel: int, state: ChannelState):
        """Manually set channel state (for testing)."""
        if 0 <= channel < 30:
            self.state.channels[channel].state = state

    def set_fault(self, fault: FaultFlags):
        """Set system fault flag (for testing)."""
        self.state.fault_flags |= fault

    def clear_fault(self, fault: FaultFlags):
        """Clear system fault flag (for testing)."""
        self.state.fault_flags &= ~fault

    def set_voltage(self, voltage_v: float):
        """Set input voltage (for testing)."""
        self.state.input_voltage_mv = int(voltage_v * 1000)

    def set_temperature(self, temp_c: int):
        """Set board temperature (for testing)."""
        self.state.temperature_c = temp_c

    async def get_response(self, timeout: float = 1.0) -> Optional[bytes]:
        """Get next response from TX queue."""
        try:
            return await asyncio.wait_for(self._tx_queue.get(), timeout)
        except asyncio.TimeoutError:
            return None


class VirtualSerialPort:
    """
    Virtual serial port that connects to DeviceSimulator.

    Implements the same interface as serial.Serial for drop-in replacement.
    """

    def __init__(self, simulator: DeviceSimulator):
        self.simulator = simulator
        self._is_open = False
        self._rx_buffer = bytearray()

    @property
    def is_open(self) -> bool:
        return self._is_open

    async def open(self):
        """Open virtual port."""
        self._is_open = True
        await self.simulator.start()

    async def close(self):
        """Close virtual port."""
        self._is_open = False
        await self.simulator.stop()

    async def write(self, data: bytes) -> int:
        """Write data to simulator."""
        if not self._is_open:
            raise IOError("Port not open")

        response = await self.simulator.process_frame(data)
        if response:
            self._rx_buffer.extend(response)

        return len(data)

    async def read(self, size: int = 1) -> bytes:
        """Read data from simulator."""
        if not self._is_open:
            raise IOError("Port not open")

        # Check for telemetry data
        try:
            telemetry_data = await asyncio.wait_for(
                self.simulator._tx_queue.get(),
                timeout=0.01
            )
            self._rx_buffer.extend(telemetry_data)
        except asyncio.TimeoutError:
            pass

        if len(self._rx_buffer) >= size:
            data = bytes(self._rx_buffer[:size])
            self._rx_buffer = self._rx_buffer[size:]
            return data

        return bytes(self._rx_buffer)

    @property
    def in_waiting(self) -> int:
        """Number of bytes waiting to be read."""
        return len(self._rx_buffer)
