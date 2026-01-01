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


class HBridgeMode(IntEnum):
    """H-Bridge operating modes."""
    COAST = 0
    FORWARD = 1
    REVERSE = 2
    BRAKE = 3
    WIPER_PARK = 4
    PID_POSITION = 5


class HBridgeState(IntEnum):
    """H-Bridge state values."""
    IDLE = 0
    RUNNING = 1
    STALLED = 2
    FAULT = 3
    OVERCURRENT = 4
    OVERTEMP = 5


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

    # Extended system values
    board_temp_2: int = 0       # Second temperature sensor (°C)
    output_5v_mv: int = 5000    # 5V rail voltage (mV)
    output_3v3_mv: int = 3300   # 3.3V rail voltage (mV)
    flash_temp: int = 0         # Flash temperature (°C)
    system_status: int = 0      # System status flags (bitfield)

    # Fault flags
    fault_flags: FaultFlags = FaultFlags.NONE

    # Digital inputs (20 inputs as list of 0/1)
    digital_inputs: list[int] = field(default_factory=lambda: [0] * 20)

    # Virtual channels (logic, timer, switch, number, etc.)
    # Dictionary mapping channel_id -> value
    virtual_channels: dict[int, int] = field(default_factory=dict)

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

    def get_hbridge_telemetry(self, bridge_id: int) -> Optional['HBridgeTelemetry']:
        """Get basic H-Bridge telemetry for specified bridge.

        Note: This provides basic state/position data from the standard telemetry packet.
        Extended telemetry (current, speed, temperature) requires emulator or extended protocol.
        """
        if 0 <= bridge_id < 4:
            state = self.hbridge_states[bridge_id]
            position = self.hbridge_positions[bridge_id]
            # Create basic telemetry from available data
            return HBridgeTelemetry(
                bridge_id=bridge_id,
                mode=HBridgeMode(state & 0x07),  # Lower 3 bits = mode
                state=HBridgeState((state >> 3) & 0x07),  # Next 3 bits = state
                direction=(state >> 6) & 0x03,  # Top 2 bits = direction
                position=position,
            )
        return None

    def get_all_hbridge_telemetry(self) -> list['HBridgeTelemetry']:
        """Get telemetry for all 4 H-Bridges."""
        return [self.get_hbridge_telemetry(i) for i in range(4)]

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
# Total size: 174 bytes (extended format with system fields)
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
    # Extended system fields (16 bytes)
    "h",      # board_temp_2 (2 bytes, signed)
    "H",      # 5v_output_mv (2 bytes)
    "H",      # 3v3_output_mv (2 bytes)
    "h",      # flash_temp (2 bytes, signed)
    "I",      # system_status (4 bytes) - bit flags
    "I",      # fault_flags (4 bytes) - FaultFlags bitmask
    "I",      # digital_inputs (4 bytes) - bitmask for 20 inputs
])

TELEMETRY_PACKET_SIZE = 174
TELEMETRY_NUCLEO_MIN_SIZE = 80  # Minimum size for Nucleo F446RE format


def parse_telemetry(data: bytes) -> TelemetryPacket:
    """
    Parse telemetry data from raw bytes.

    Supports two formats:
    - Full PMU-30 format: 174 bytes
    - Nucleo F446RE format: ~104 bytes (reduced hardware)

    Args:
        data: Raw telemetry packet bytes

    Returns:
        Parsed TelemetryPacket

    Raises:
        ValueError: If data is invalid
    """
    # Try Nucleo format first if packet is smaller than full format
    if len(data) < TELEMETRY_PACKET_SIZE and len(data) >= TELEMETRY_NUCLEO_MIN_SIZE:
        return _parse_telemetry_nucleo(data)

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
    idx += 4

    # Extended system fields
    board_temp_2 = values[idx]
    idx += 1

    output_5v_mv = values[idx]
    idx += 1

    output_3v3_mv = values[idx]
    idx += 1

    flash_temp = values[idx]
    idx += 1

    system_status = values[idx]
    idx += 1

    fault_flags_raw = values[idx]
    idx += 1

    # Digital inputs bitmask
    digital_inputs_raw = values[idx]
    digital_inputs = [(digital_inputs_raw >> i) & 1 for i in range(20)]

    # Parse virtual channels if present (extended format)
    virtual_channels = {}
    remaining_data = data[TELEMETRY_PACKET_SIZE:]
    if len(remaining_data) >= 2:
        # Virtual channel count
        virtual_count = struct.unpack("<H", remaining_data[:2])[0]
        offset = 2

        # Parse each virtual channel: id (2 bytes) + value (4 bytes) = 6 bytes each
        for _ in range(virtual_count):
            if offset + 6 <= len(remaining_data):
                ch_id, ch_value = struct.unpack("<Hi", remaining_data[offset:offset + 6])
                virtual_channels[ch_id] = ch_value
                offset += 6
            else:
                break

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
        board_temp_2=board_temp_2,
        output_5v_mv=output_5v_mv,
        output_3v3_mv=output_3v3_mv,
        flash_temp=flash_temp,
        system_status=system_status,
        fault_flags=FaultFlags(fault_flags_raw),
        digital_inputs=digital_inputs,
        virtual_channels=virtual_channels,
    )


def _parse_telemetry_nucleo(data: bytes) -> TelemetryPacket:
    """
    Parse Nucleo F446RE telemetry format (~104 bytes).

    Nucleo format (reduced hardware):
    - stream_counter: 4 bytes
    - timestamp: 4 bytes
    - output_states: 30 bytes (1 byte per output)
    - adc_values: 40 bytes (20 x uint16)
    - digital_inputs: 1 byte (packed)
    - debug_flags: 1 byte
    - timer_debug: ~15 bytes
    - voltage_mv: 2 bytes
    - current_ma: 2 bytes
    - mcu_temp: 2 bytes
    - board_temp: 2 bytes
    - fault_status: 2 bytes
    """
    idx = 0

    # Stream counter (4 bytes)
    stream_counter = struct.unpack_from("<I", data, idx)[0]
    idx += 4

    # Timestamp (4 bytes)
    timestamp_ms = struct.unpack_from("<I", data, idx)[0]
    idx += 4

    # Output states (30 bytes)
    profet_states = []
    for i in range(30):
        if idx < len(data):
            state_val = data[idx]
            profet_states.append(ChannelState(min(state_val, 7)))
            idx += 1
        else:
            profet_states.append(ChannelState.OFF)

    # ADC values (40 bytes = 20 x uint16)
    adc_values = []
    for i in range(20):
        if idx + 1 < len(data):
            val = struct.unpack_from("<H", data, idx)[0]
            adc_values.append(val)
            idx += 2
        else:
            adc_values.append(0)

    # Digital inputs byte (packed bitmask)
    din_byte = data[idx] if idx < len(data) else 0
    idx += 1
    digital_inputs = [(din_byte >> i) & 1 for i in range(8)] + [0] * 12

    # Debug flags byte
    if idx < len(data):
        idx += 1  # Skip debug flags

    # Timer debug section (~15 bytes) - skip for basic parsing
    timer_debug_size = 15
    idx += min(timer_debug_size, len(data) - idx)

    # Voltage and current (4 bytes)
    voltage_mv = 0
    current_ma = 0
    if idx + 3 < len(data):
        voltage_mv = struct.unpack_from("<H", data, idx)[0]
        idx += 2
        current_ma = struct.unpack_from("<H", data, idx)[0]
        idx += 2

    # Temperature (4 bytes)
    mcu_temp = 0
    board_temp = 0
    if idx + 3 < len(data):
        mcu_temp = struct.unpack_from("<h", data, idx)[0]
        idx += 2
        board_temp = struct.unpack_from("<h", data, idx)[0]
        idx += 2

    # Fault status (2 bytes)
    fault_status = 0
    fault_flags = 0
    if idx + 1 < len(data):
        fault_status = data[idx]
        idx += 1
        fault_flags = data[idx] if idx < len(data) else 0
        idx += 1

    return TelemetryPacket(
        timestamp_ms=timestamp_ms,
        input_voltage_mv=voltage_mv,
        temperature_c=mcu_temp,
        total_current_ma=current_ma,
        adc_values=adc_values,
        profet_states=profet_states,
        profet_duties=[0] * 30,  # Not sent in Nucleo format
        hbridge_states=[0, 0, 0, 0],
        hbridge_positions=[0, 0, 0, 0],
        board_temp_2=board_temp,
        output_5v_mv=0,
        output_3v3_mv=0,
        flash_temp=0,
        system_status=0,
        fault_flags=FaultFlags(fault_flags),
        digital_inputs=digital_inputs,
        virtual_channels={},
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
    # Convert digital_inputs list to bitmask
    di_bitmask = sum((1 if v else 0) << i for i, v in enumerate(packet.digital_inputs[:20]))

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
        # Extended fields
        packet.board_temp_2,
        packet.output_5v_mv,
        packet.output_3v3_mv,
        packet.flash_temp,
        packet.system_status,
        packet.fault_flags.value if isinstance(packet.fault_flags, FaultFlags) else packet.fault_flags,
        di_bitmask,
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


@dataclass
class HBridgeTelemetry:
    """Extended telemetry data for a single H-Bridge channel."""

    bridge_id: int = 0

    # Operating mode and state
    mode: HBridgeMode = HBridgeMode.COAST
    state: HBridgeState = HBridgeState.IDLE
    direction: int = 0  # 0=coast, 1=forward, 2=reverse, 3=brake

    # Control values
    pwm: int = 0  # 0-255
    target_position: int = 0

    # Motor feedback
    current_ma: int = 0  # Motor current in mA
    position: int = 0  # Position feedback (raw ADC or encoder)
    omega: float = 0.0  # Angular velocity (rad/s)
    theta: float = 0.0  # Angular position (rad)
    back_emf_v: float = 0.0  # Back-EMF voltage

    # Thermal
    temperature_c: float = 25.0  # Motor/driver temperature

    # Motor physics (from emulator)
    torque_nm: float = 0.0  # Motor torque (Nm)

    # Status flags
    stalled: bool = False
    at_endstop: int = 0  # 0=free, 1=min, 2=max
    fault: int = 0  # Fault code

    @property
    def current_a(self) -> float:
        """Get current in amps."""
        return self.current_ma / 1000.0

    @property
    def speed_rpm(self) -> float:
        """Get motor speed in RPM."""
        return abs(self.omega) * 9.549  # rad/s to RPM (30/pi)

    @property
    def position_degrees(self) -> float:
        """Get position in degrees."""
        return self.theta * 57.2958  # rad to degrees (180/pi)

    @property
    def duty_percent(self) -> float:
        """Get PWM duty as percentage."""
        return (self.pwm / 255.0) * 100.0

    @property
    def direction_str(self) -> str:
        """Get human-readable direction string."""
        return {0: "Coast", 1: "FWD", 2: "REV", 3: "Brake"}.get(self.direction, "?")

    @property
    def mode_str(self) -> str:
        """Get human-readable mode string."""
        mode_names = {
            HBridgeMode.COAST: "Coast",
            HBridgeMode.FORWARD: "Forward",
            HBridgeMode.REVERSE: "Reverse",
            HBridgeMode.BRAKE: "Brake",
            HBridgeMode.WIPER_PARK: "Wiper Park",
            HBridgeMode.PID_POSITION: "PID Position",
        }
        return mode_names.get(self.mode, "Unknown")

    @property
    def state_str(self) -> str:
        """Get human-readable state string."""
        state_names = {
            HBridgeState.IDLE: "Idle",
            HBridgeState.RUNNING: "Running",
            HBridgeState.STALLED: "Stalled",
            HBridgeState.FAULT: "Fault",
            HBridgeState.OVERCURRENT: "Overcurrent",
            HBridgeState.OVERTEMP: "Overtemp",
        }
        return state_names.get(self.state, "Unknown")

    @property
    def is_running(self) -> bool:
        """Check if motor is running."""
        return self.state == HBridgeState.RUNNING and self.pwm > 0

    @property
    def is_faulted(self) -> bool:
        """Check if H-Bridge is in fault state."""
        return self.state in (
            HBridgeState.FAULT,
            HBridgeState.OVERCURRENT,
            HBridgeState.OVERTEMP
        ) or self.fault != 0

    def to_dict(self) -> dict:
        """Convert to dictionary for HBridgeMonitor."""
        return {
            'bridge': self.bridge_id,
            'mode': self.mode.value if isinstance(self.mode, HBridgeMode) else self.mode,
            'state': self.state.value if isinstance(self.state, HBridgeState) else self.state,
            'direction': self.direction,
            'pwm': self.pwm,
            'current': self.current_ma,
            'omega': self.omega,
            'theta': self.theta,
            'backEmf': self.back_emf_v,
            'torque': self.torque_nm,
            'temp': self.temperature_c,
            'stalled': 1 if self.stalled else 0,
            'endstop': self.at_endstop,
            'fault': self.fault,
            'position': self.position,
            'target': self.target_position,
        }
