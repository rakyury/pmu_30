"""
PMU-30 Telemetry Data Structures

This module defines the telemetry packet format and data structures
for real-time monitoring of PMU-30 device state.

Telemetry Packet Structure (119 bytes at 50Hz):
- timestamp_ms: 4 bytes (uint32)
- channel_states: 30 bytes (1 byte per channel)
- analog_values: 16 bytes (8 x uint16)
- output_currents: 60 bytes (30 x uint16, mA)
- input_voltage: 2 bytes (uint16, mV)
- temperature: 1 byte (int8, Celsius)
- fault_flags: 4 bytes (uint32)
- crc16: 2 bytes
"""

from dataclasses import dataclass, field
from enum import IntFlag, IntEnum
from typing import Optional
import struct
import time


class ChannelState(IntEnum):
    """Individual channel state values."""
    OFF = 0
    ON = 1
    FAULT_OVERCURRENT = 2
    FAULT_OVERHEAT = 3
    FAULT_SHORT = 4
    FAULT_OPEN = 5
    PWM_ACTIVE = 6
    DISABLED = 7


class FaultFlags(IntFlag):
    """System-wide fault flags (32 bits)."""
    NONE = 0
    OVERVOLTAGE = 1 << 0
    UNDERVOLTAGE = 1 << 1
    OVERTEMPERATURE = 1 << 2
    CAN1_ERROR = 1 << 3
    CAN2_ERROR = 1 << 4
    FLASH_ERROR = 1 << 5
    CONFIG_ERROR = 1 << 6
    WATCHDOG_RESET = 1 << 7
    POWER_FAIL = 1 << 8
    GROUND_FAULT = 1 << 9
    REVERSE_POLARITY = 1 << 10
    SENSOR_ERROR = 1 << 11
    LUA_ERROR = 1 << 12
    LOGIC_ERROR = 1 << 13
    CHANNEL_FAULT_1 = 1 << 16  # Channels 1-8 have fault
    CHANNEL_FAULT_2 = 1 << 17  # Channels 9-16 have fault
    CHANNEL_FAULT_3 = 1 << 18  # Channels 17-24 have fault
    CHANNEL_FAULT_4 = 1 << 19  # Channels 25-30 have fault


@dataclass
class TelemetryPacket:
    """
    Real-time telemetry data from PMU-30.

    This packet is sent at 50Hz when telemetry streaming is enabled.
    """

    # Timing
    timestamp_ms: int = 0
    local_timestamp: float = field(default_factory=time.time)

    # Channel states (30 channels)
    channel_states: list[ChannelState] = field(
        default_factory=lambda: [ChannelState.OFF] * 30
    )

    # Analog input values (8 primary ADC channels)
    analog_values: list[int] = field(default_factory=lambda: [0] * 8)

    # Output currents in mA (30 channels)
    output_currents: list[int] = field(default_factory=lambda: [0] * 30)

    # System values
    input_voltage_mv: int = 0
    temperature_c: int = 0
    fault_flags: FaultFlags = FaultFlags.NONE

    @property
    def input_voltage(self) -> float:
        """Get input voltage in volts."""
        return self.input_voltage_mv / 1000.0

    @property
    def has_faults(self) -> bool:
        """Check if any fault flags are set."""
        return self.fault_flags != FaultFlags.NONE

    @property
    def active_channels(self) -> list[int]:
        """Get list of active (ON or PWM) channel indices."""
        return [
            i for i, state in enumerate(self.channel_states)
            if state in (ChannelState.ON, ChannelState.PWM_ACTIVE)
        ]

    @property
    def faulted_channels(self) -> list[int]:
        """Get list of faulted channel indices."""
        return [
            i for i, state in enumerate(self.channel_states)
            if state in (
                ChannelState.FAULT_OVERCURRENT,
                ChannelState.FAULT_OVERHEAT,
                ChannelState.FAULT_SHORT,
                ChannelState.FAULT_OPEN
            )
        ]

    @property
    def total_current_ma(self) -> int:
        """Get total current draw in mA."""
        return sum(self.output_currents)

    @property
    def total_current_a(self) -> float:
        """Get total current draw in amps."""
        return self.total_current_ma / 1000.0

    @property
    def total_power_w(self) -> float:
        """Get total power consumption in watts."""
        return self.input_voltage * self.total_current_a

    def get_channel_current_a(self, channel: int) -> float:
        """Get current for specific channel in amps."""
        if 0 <= channel < 30:
            return self.output_currents[channel] / 1000.0
        return 0.0

    def get_fault_descriptions(self) -> list[str]:
        """Get human-readable descriptions of active faults."""
        descriptions = []
        if self.fault_flags & FaultFlags.OVERVOLTAGE:
            descriptions.append("Input overvoltage")
        if self.fault_flags & FaultFlags.UNDERVOLTAGE:
            descriptions.append("Input undervoltage")
        if self.fault_flags & FaultFlags.OVERTEMPERATURE:
            descriptions.append("Board overtemperature")
        if self.fault_flags & FaultFlags.CAN1_ERROR:
            descriptions.append("CAN1 bus error")
        if self.fault_flags & FaultFlags.CAN2_ERROR:
            descriptions.append("CAN2 bus error")
        if self.fault_flags & FaultFlags.FLASH_ERROR:
            descriptions.append("Flash memory error")
        if self.fault_flags & FaultFlags.CONFIG_ERROR:
            descriptions.append("Configuration error")
        if self.fault_flags & FaultFlags.WATCHDOG_RESET:
            descriptions.append("Watchdog reset occurred")
        if self.fault_flags & FaultFlags.POWER_FAIL:
            descriptions.append("Power failure detected")
        if self.fault_flags & FaultFlags.GROUND_FAULT:
            descriptions.append("Ground fault detected")
        if self.fault_flags & FaultFlags.REVERSE_POLARITY:
            descriptions.append("Reverse polarity detected")
        if self.fault_flags & FaultFlags.SENSOR_ERROR:
            descriptions.append("Sensor error")
        if self.fault_flags & FaultFlags.LUA_ERROR:
            descriptions.append("Lua script error")
        if self.fault_flags & FaultFlags.LOGIC_ERROR:
            descriptions.append("Logic function error")
        return descriptions


# Telemetry packet format string for struct.unpack
# Total size: 119 bytes
TELEMETRY_FORMAT = "<" + "".join([
    "I",      # timestamp_ms (4 bytes)
    "30B",    # channel_states (30 bytes)
    "8H",     # analog_values (16 bytes)
    "30H",    # output_currents (60 bytes)
    "H",      # input_voltage_mv (2 bytes)
    "b",      # temperature_c (1 byte)
    "I",      # fault_flags (4 bytes)
    "H",      # crc16 (2 bytes)
])

TELEMETRY_PACKET_SIZE = 119


def parse_telemetry(data: bytes) -> TelemetryPacket:
    """
    Parse telemetry data from raw bytes.

    Args:
        data: Raw telemetry packet bytes (119 bytes)

    Returns:
        Parsed TelemetryPacket

    Raises:
        ValueError: If data is invalid or CRC fails
    """
    if len(data) < TELEMETRY_PACKET_SIZE:
        raise ValueError(f"Telemetry packet too short: {len(data)} < {TELEMETRY_PACKET_SIZE}")

    # Unpack all fields
    values = struct.unpack(TELEMETRY_FORMAT, data[:TELEMETRY_PACKET_SIZE])

    # Parse fields
    idx = 0
    timestamp_ms = values[idx]
    idx += 1

    channel_states = [ChannelState(v) for v in values[idx:idx + 30]]
    idx += 30

    analog_values = list(values[idx:idx + 8])
    idx += 8

    output_currents = list(values[idx:idx + 30])
    idx += 30

    input_voltage_mv = values[idx]
    idx += 1

    temperature_c = values[idx]
    idx += 1

    fault_flags = FaultFlags(values[idx])
    idx += 1

    # Note: CRC is at values[idx], already validated by protocol layer

    return TelemetryPacket(
        timestamp_ms=timestamp_ms,
        channel_states=channel_states,
        analog_values=analog_values,
        output_currents=output_currents,
        input_voltage_mv=input_voltage_mv,
        temperature_c=temperature_c,
        fault_flags=fault_flags,
    )


def create_telemetry_bytes(packet: TelemetryPacket, crc: int = 0) -> bytes:
    """
    Create raw bytes from a telemetry packet.

    Used for testing and simulation.

    Args:
        packet: TelemetryPacket to serialize
        crc: CRC value to include (usually calculated by caller)

    Returns:
        Raw bytes representation
    """
    return struct.pack(
        TELEMETRY_FORMAT,
        packet.timestamp_ms,
        *[s.value for s in packet.channel_states],
        *packet.analog_values,
        *packet.output_currents,
        packet.input_voltage_mv,
        packet.temperature_c,
        packet.fault_flags.value,
        crc,
    )


@dataclass
class DeviceInfo:
    """Device information from INFO_RESP message."""

    firmware_version: str = "0.0.0"
    hardware_revision: int = 0
    serial_number: str = ""
    device_name: str = "PMU-30"
    output_count: int = 30
    input_count: int = 20
    hbridge_count: int = 4
    can_bus_count: int = 4
    uptime_ms: int = 0

    @property
    def uptime_str(self) -> str:
        """Get uptime as human-readable string."""
        seconds = self.uptime_ms // 1000
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"


@dataclass
class ChannelStatus:
    """Status information for a single channel."""

    channel_id: int
    name: str = ""
    state: ChannelState = ChannelState.OFF
    current_ma: int = 0
    duty_cycle: float = 0.0
    fault_count: int = 0
    enabled: bool = True

    @property
    def current_a(self) -> float:
        """Get current in amps."""
        return self.current_ma / 1000.0

    @property
    def is_active(self) -> bool:
        """Check if channel is actively conducting."""
        return self.state in (ChannelState.ON, ChannelState.PWM_ACTIVE)

    @property
    def is_faulted(self) -> bool:
        """Check if channel is in fault state."""
        return self.state in (
            ChannelState.FAULT_OVERCURRENT,
            ChannelState.FAULT_OVERHEAT,
            ChannelState.FAULT_SHORT,
            ChannelState.FAULT_OPEN
        )

    @property
    def state_str(self) -> str:
        """Get human-readable state string."""
        state_names = {
            ChannelState.OFF: "Off",
            ChannelState.ON: "On",
            ChannelState.FAULT_OVERCURRENT: "Overcurrent",
            ChannelState.FAULT_OVERHEAT: "Overheat",
            ChannelState.FAULT_SHORT: "Short Circuit",
            ChannelState.FAULT_OPEN: "Open Load",
            ChannelState.PWM_ACTIVE: "PWM",
            ChannelState.DISABLED: "Disabled",
        }
        return state_names.get(self.state, "Unknown")
