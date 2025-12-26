"""
Shared helpers for integration tests.

Provides configuration templates and async test utilities.
"""

import asyncio
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from communication.emulator_transport import EmulatorTransport
from communication.telemetry import TelemetryPacket, parse_telemetry, ChannelState
from communication.protocol import MessageType
from controllers.protocol_handler import ProtocolHandler


# Re-export commonly used types
__all__ = [
    'ChannelState',
    'TelemetryPacket',
    'MessageType',
    'ConfigResponse',
    'AsyncProtocolHandler',
    'EmulatorTransport',
    'BASE_CONFIG',
    'make_output_config',
    'make_digital_input_config',
    'make_analog_input_config',
    'make_logic_config',
]


@dataclass
class ConfigResponse:
    """Response from send_config operation."""
    success: bool
    error: Optional[str] = None


class AsyncProtocolHandler:
    """
    Async wrapper for emulator communication.

    Provides an async interface compatible with integration tests.
    """

    def __init__(self, transport: EmulatorTransport):
        self.transport = transport
        self._protocol = ProtocolHandler()
        self._last_telemetry: Optional[TelemetryPacket] = None
        self._receive_task: Optional[asyncio.Task] = None

    async def start(self):
        """Start receiving messages."""
        self._receive_task = asyncio.create_task(self._receive_loop())

    async def stop(self):
        """Stop receiving messages."""
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass

    async def _receive_loop(self):
        """Background task to receive and parse messages."""
        while True:
            try:
                data = await asyncio.wait_for(
                    self.transport.read(1024),
                    timeout=0.1
                )
                if data:
                    messages = self._protocol.feed_data(data)
                    for msg in messages:
                        if msg.msg_type == MessageType.TELEMETRY:
                            self._last_telemetry = parse_telemetry(msg.payload)
            except asyncio.TimeoutError:
                pass
            except Exception:
                pass
            await asyncio.sleep(0.01)

    async def send_config(self, config_json: str) -> ConfigResponse:
        """Send configuration to the device."""
        try:
            config_bytes = config_json.encode('utf-8')
            chunk_size = 4000
            chunks = [config_bytes[i:i+chunk_size]
                     for i in range(0, len(config_bytes), chunk_size)]

            for idx, chunk in enumerate(chunks):
                frame = self._protocol.build_config_frame(idx, len(chunks), chunk)
                await self.transport.write(frame)
                await asyncio.sleep(0.05)

            return ConfigResponse(success=True)
        except Exception as e:
            return ConfigResponse(success=False, error=str(e))

    async def set_digital_input(self, channel: int, state: bool):
        """Set a digital input state (for emulator testing)."""
        payload = bytes([channel, 1 if state else 0])
        frame = self._protocol.build_frame(MessageType.SET_INPUT, payload)
        await self.transport.write(frame)

    async def set_analog_input(self, channel: int, value: int):
        """Set an analog input value (for emulator testing)."""
        import struct
        payload = struct.pack('<BH', channel, value)
        frame = self._protocol.build_frame(MessageType.SET_INPUT, payload)
        await self.transport.write(frame)

    async def get_telemetry(self) -> Optional[TelemetryPacket]:
        """Get the latest telemetry packet."""
        frame = self._protocol.build_frame(MessageType.GET_TELEMETRY)
        await self.transport.write(frame)
        await asyncio.sleep(0.2)
        return self._last_telemetry

    async def subscribe_telemetry(self, rate_hz: int = 10):
        """Subscribe to telemetry updates."""
        import struct
        payload = struct.pack('<B', rate_hz)
        frame = self._protocol.build_frame(MessageType.SUBSCRIBE_TELEMETRY, payload)
        await self.transport.write(frame)

    async def save_to_flash(self) -> bool:
        """Save current configuration to flash."""
        frame = self._protocol.build_frame(MessageType.SAVE_TO_FLASH)
        await self.transport.write(frame)
        await asyncio.sleep(0.5)
        return True


# Test configuration templates
BASE_CONFIG = {
    "version": "1.0",
    "device": {"name": "Test PMU", "type": "PMU-30"},
    "channels": []
}


def make_output_config(output_num: int, name: str, source_channel: str,
                       pwm_enabled: bool = False, pwm_frequency: int = 1000,
                       soft_start: bool = False) -> dict:
    """Create power output configuration."""
    config = {
        "channel_id": 100 + output_num,
        "channel_type": "power_output",
        "id": name,
        "name": name,
        "channel": output_num - 1,
        "source_channel": source_channel,
        "output_mode": "pwm" if pwm_enabled else "on_off",
        "max_current": 10000,
        "soft_start": soft_start,
    }
    if pwm_enabled:
        config["pwm_frequency"] = pwm_frequency
    return config


def make_digital_input_config(input_num: int, name: str,
                              input_type: str = "switch_active_high",
                              debounce_ms: int = 10) -> dict:
    """Create digital input configuration."""
    return {
        "channel_id": 200 + input_num,
        "channel_type": "digital_input",
        "id": name,
        "name": name,
        "channel": input_num - 1,
        "input_type": input_type,
        "debounce_ms": debounce_ms,
    }


def make_analog_input_config(input_num: int, name: str,
                             input_type: str = "voltage",
                             scale: float = 1.0,
                             offset: float = 0.0) -> dict:
    """Create analog input configuration."""
    return {
        "channel_id": 300 + input_num,
        "channel_type": "analog_input",
        "id": name,
        "name": name,
        "channel": input_num - 1,
        "input_type": input_type,
        "scale": scale,
        "offset": offset,
    }


def make_logic_config(channel_id: int, name: str, operation: str,
                      input1: str, input2: str = None,
                      constant: float = None) -> dict:
    """Create logic channel configuration."""
    config = {
        "channel_id": channel_id,
        "channel_type": "logic",
        "id": name,
        "name": name,
        "operation": operation,
        "input1_channel": input1,
    }
    if input2:
        config["input2_channel"] = input2
    if constant is not None:
        config["constant"] = constant
    return config


def make_timer_config(channel_id: int, name: str, start_channel: str,
                      mode: str = "oneshot", duration_ms: int = 1000) -> dict:
    """Create timer channel configuration."""
    return {
        "channel_id": channel_id,
        "channel_type": "timer",
        "id": name,
        "name": name,
        "start_channel": start_channel,
        "mode": mode,
        "duration_ms": duration_ms,
    }


def make_filter_config(channel_id: int, name: str, input_channel: str,
                       filter_type: str = "lowpass", cutoff_hz: float = 10.0) -> dict:
    """Create filter channel configuration."""
    return {
        "channel_id": channel_id,
        "channel_type": "filter",
        "id": name,
        "name": name,
        "input_channel": input_channel,
        "filter_type": filter_type,
        "cutoff_hz": cutoff_hz,
    }


def make_switch_config(channel_id: int, name: str, input_channel: str,
                       cases: list = None) -> dict:
    """Create switch channel configuration."""
    return {
        "channel_id": channel_id,
        "channel_type": "switch",
        "id": name,
        "name": name,
        "input_channel": input_channel,
        "cases": cases or [],
    }


def make_table_2d_config(channel_id: int, name: str, input_channel: str,
                         x_values: list = None, y_values: list = None) -> dict:
    """Create 2D table channel configuration."""
    return {
        "channel_id": channel_id,
        "channel_type": "table_2d",
        "id": name,
        "name": name,
        "input_channel": input_channel,
        "x_values": x_values or [0, 100],
        "y_values": y_values or [0, 100],
    }
