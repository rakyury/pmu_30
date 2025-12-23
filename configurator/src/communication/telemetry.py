"""
PMU-30 Telemetry Data Structures

This module defines the telemetry packet format and data structures
for real-time monitoring of PMU-30 device state.

Telemetry Packet Structure (154 bytes at configurable rate):
- timestamp_ms: 4 bytes (uint32)
- voltage_mv: 2 bytes (uint16) - battery voltage in mV
- temperature_c: 2 bytes (int16) - board temperature in Celsius
- total_current_ma: 4 bytes (uint32) - total current in mA
- adc_values: 40 bytes (20 x uint16) - raw ADC readings
- profet_states: 30 bytes (30 x uint8) - PROFET channel states
- profet_duties: 60 bytes (30 x uint16) - PROFET PWM duties (0-1000)
- hbridge_states: 4 bytes (4 x uint8) - H-Bridge states
- hbridge_positions: 8 bytes (4 x uint16) - H-Bridge positions
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

    This packet is sent at configurable rate when telemetry streaming is enabled.
    """

    # Timing
    timestamp_ms: int = 0
    local_timestamp: float = field(default_factory=time.time)

    # System values
    input_voltage_mv: int = 0
    temperature_c: int = 0
    total_current_ma: int = 0

    # ADC values (20 channels, raw 12-bit values 0-4095)
    adc_values: list[int] = field(default_factory=lambda: [0] * 20)

    # PROFET channel states (30 channels)
    profet_states: list[ChannelState] = field(
        default_factory=lambda: [ChannelState.OFF] * 30
    )

    # PROFET PWM duties (30 channels, 0-1000 = 0-100.0%)
    profet_duties: list[int] = field(default_factory=lambda: [0] * 30)

    # H-Bridge states (4 bridges)
    hbridge_states: list[int] = field(default_factory=lambda: [0] * 4)

    # H-Bridge positions (4 bridges)
    hbridge_positions: list[int] = field(default_factory=lambda: [0] * 4)

    # Legacy compatibility fields (derived)
    fault_flags: FaultFlags = FaultFlags.NONE

    @property
    def channel_states(self) -> list[ChannelState]:
        """Alias for profet_states for legacy code."""
        return self.profet_states

    @property
    def analog_values(self) -> list[int]:
        """Get first 8 ADC values (primary analog inputs)."""
        return self.adc_values[:8]

    @property
    def output_currents(self) -> list[int]:
        """Estimate output currents from PWM duty cycles (placeholder)."""
        # Real current sensing would come from ADC channels
        return [duty for duty in self.profet_duties]

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
    def calculated_total_current_ma(self) -> int:
        """Get calculated total current draw from duties in mA."""
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
# Total size: 154 bytes (matching emulator format)
TELEMETRY_FORMAT = "<" + "".join([
    "I",      # timestamp_ms (4 bytes)
    "H",      # voltage_mv (2 bytes)
    "h",      # temperature_c (2 bytes, signed)
    "I",      # total_current_ma (4 bytes)
    "20H",    # adc_values (40 bytes)
    "30B",    # profet_states (30 bytes)
    "30H",    # profet_duties (60 bytes)
    "4B",     # hbridge_states (4 bytes)
    "4H",     # hbridge_positions (8 bytes)
])

TELEMETRY_PACKET_SIZE = 154


def parse_telemetry(data: bytes) -> TelemetryPacket:
    """
    Parse telemetry data from raw bytes.

    Args:
        data: Raw telemetry packet bytes (154 bytes)

    Returns:
        Parsed TelemetryPacket

    Raises:
        ValueError: If data is invalid
    """
    if len(data) < TELEMETRY_PACKET_SIZE:
        raise ValueError(f"Telemetry packet too short: {len(data)} < {TELEMETRY_PACKET_SIZE}")

    # Unpack all fields
    values = struct.unpack(TELEMETRY_FORMAT, data[:TELEMETRY_PACKET_SIZE])

    # Parse fields
    idx = 0
    timestamp_ms = values[idx]
    idx += 1

    voltage_mv = values[idx]
    idx += 1

    temperature_c = values[idx]
    idx += 1

    total_current_ma = values[idx]
    idx += 1

    adc_values = list(values[idx:idx + 20])
    idx += 20

    profet_states = [ChannelState(min(v, 7)) for v in values[idx:idx + 30]]
    idx += 30

    profet_duties = list(values[idx:idx + 30])
    idx += 30

    hbridge_states = list(values[idx:idx + 4])
    idx += 4

    hbridge_positions = list(values[idx:idx + 4])

    return TelemetryPacket(
        timestamp_ms=timestamp_ms,
        input_voltage_mv=voltage_mv,
        temperature_c=temperature_c,
        total_current_ma=total_current_ma,
        adc_values=adc_values,
        profet_states=profet_states,
        profet_duties=profet_duties,
        hbridge_states=hbridge_states,
        hbridge_positions=hbridge_positions,
    )


def create_telemetry_bytes(packet: TelemetryPacket) -> bytes:
    """
    Create raw bytes from a telemetry packet.

    Used for testing and simulation.

    Args:
        packet: TelemetryPacket to serialize

    Returns:
        Raw bytes representation
    """
    return struct.pack(
        TELEMETRY_FORMAT,
        packet.timestamp_ms,
        packet.input_voltage_mv,
        packet.temperature_c,
        packet.total_current_ma,
        *packet.adc_values,
        *[s.value if isinstance(s, ChannelState) else s for s in packet.profet_states],
        *packet.profet_duties,
        *packet.hbridge_states,
        *packet.hbridge_positions,
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
