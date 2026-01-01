"""
PMU-30 Telemetry Codec - Python implementation

Mirrors telemetry_codec.h/.c for Python compatibility.
Provides parse_telemetry() function for configurator use.
"""

import struct
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional


# Section flags
TELEM_HAS_ADC = 0x0001
TELEM_HAS_OUTPUTS = 0x0002
TELEM_HAS_HBRIDGE = 0x0004
TELEM_HAS_DIN = 0x0008
TELEM_HAS_VIRTUALS = 0x0010
TELEM_HAS_FAULTS = 0x0020
TELEM_HAS_CURRENTS = 0x0040
TELEM_HAS_EXTENDED = 0x0080

# Constants
TELEM_ADC_COUNT = 20
TELEM_OUTPUT_COUNT = 30
TELEM_HBRIDGE_COUNT = 4
TELEM_VIRTUAL_MAX = 32

# Header size: 4+4+2+2+2+4+2 = 20 bytes
HEADER_SIZE = 20


class TelemetryResult(IntEnum):
    """Result codes for telemetry parsing"""

    OK = 0
    ERR_NULL_PARAM = 1
    ERR_BUFFER_TOO_SMALL = 2
    ERR_TOO_SHORT = 3
    ERR_BAD_FLAGS = 4
    ERR_TRUNCATED = 5


@dataclass
class TelemetryPacket:
    """Complete telemetry packet (parsed result)"""

    # Header fields (always present)
    stream_counter: int = 0
    timestamp_ms: int = 0
    input_voltage_mv: int = 0
    mcu_temp_c10: int = 0
    board_temp_c10: int = 0
    total_current_ma: int = 0
    flags: int = 0

    # ADC section
    adc_values: List[int] = field(default_factory=lambda: [0] * TELEM_ADC_COUNT)

    # Output states section
    output_states: List[int] = field(default_factory=lambda: [0] * TELEM_OUTPUT_COUNT)

    # Digital inputs section
    din_bitmask: int = 0

    # Virtual channels section
    virtual_channels: Dict[int, int] = field(default_factory=dict)

    # Faults section
    fault_status: int = 0
    fault_flags: int = 0

    # Currents section
    output_currents: List[int] = field(default_factory=lambda: [0] * TELEM_OUTPUT_COUNT)

    # H-Bridge section
    hbridge_positions: List[int] = field(default_factory=lambda: [0] * TELEM_HBRIDGE_COUNT)
    hbridge_currents: List[int] = field(default_factory=lambda: [0] * TELEM_HBRIDGE_COUNT)

    def has_section(self, flag: int) -> bool:
        """Check if a section is present"""
        return (self.flags & flag) != 0

    def get_virtual_value(self, channel_id: int) -> Optional[int]:
        """Get virtual channel value by ID"""
        return self.virtual_channels.get(channel_id)

    def get_din(self, pin: int) -> bool:
        """Get digital input state by pin number (0-19)"""
        if 0 <= pin < 20:
            return bool(self.din_bitmask & (1 << pin))
        return False

    @property
    def mcu_temp_c(self) -> float:
        """MCU temperature in °C"""
        return self.mcu_temp_c10 / 10.0

    @property
    def board_temp_c(self) -> float:
        """Board temperature in °C"""
        return self.board_temp_c10 / 10.0

    @property
    def input_voltage_v(self) -> float:
        """Input voltage in V"""
        return self.input_voltage_mv / 1000.0

    @property
    def total_current_a(self) -> float:
        """Total current in A"""
        return self.total_current_ma / 1000.0


def _get_min_size(flags: int) -> int:
    """Calculate minimum packet size for given flags"""
    size = HEADER_SIZE

    if flags & TELEM_HAS_ADC:
        size += TELEM_ADC_COUNT * 2  # 40 bytes
    if flags & TELEM_HAS_OUTPUTS:
        size += TELEM_OUTPUT_COUNT  # 30 bytes
    if flags & TELEM_HAS_HBRIDGE:
        size += TELEM_HBRIDGE_COUNT * 4  # 16 bytes (positions + currents)
    if flags & TELEM_HAS_DIN:
        size += 4  # uint32 bitmask
    if flags & TELEM_HAS_VIRTUALS:
        size += 2  # At least count field
    if flags & TELEM_HAS_FAULTS:
        size += 4  # status + flags + reserved
    if flags & TELEM_HAS_CURRENTS:
        size += TELEM_OUTPUT_COUNT * 2  # 60 bytes

    return size


def parse_telemetry(data: bytes) -> tuple[TelemetryResult, TelemetryPacket]:
    """
    Parse telemetry packet from raw bytes.

    Args:
        data: Raw packet data (after protocol framing removed)

    Returns:
        Tuple of (result_code, parsed_packet)
    """
    packet = TelemetryPacket()

    if len(data) < HEADER_SIZE:
        return TelemetryResult.ERR_TOO_SHORT, packet

    # Parse header
    idx = 0
    (
        packet.stream_counter,
        packet.timestamp_ms,
        packet.input_voltage_mv,
        packet.mcu_temp_c10,
        packet.board_temp_c10,
        packet.total_current_ma,
        packet.flags,
    ) = struct.unpack_from("<IIHhhIH", data, idx)
    idx += HEADER_SIZE

    flags = packet.flags

    # Check minimum size
    if len(data) < _get_min_size(flags):
        return TelemetryResult.ERR_TOO_SHORT, packet

    # Parse ADC section
    if flags & TELEM_HAS_ADC:
        if idx + TELEM_ADC_COUNT * 2 > len(data):
            return TelemetryResult.ERR_TRUNCATED, packet
        packet.adc_values = list(struct.unpack_from(f"<{TELEM_ADC_COUNT}H", data, idx))
        idx += TELEM_ADC_COUNT * 2

    # Parse Outputs section
    if flags & TELEM_HAS_OUTPUTS:
        if idx + TELEM_OUTPUT_COUNT > len(data):
            return TelemetryResult.ERR_TRUNCATED, packet
        packet.output_states = list(data[idx : idx + TELEM_OUTPUT_COUNT])
        idx += TELEM_OUTPUT_COUNT

    # Parse H-Bridge section
    if flags & TELEM_HAS_HBRIDGE:
        if idx + TELEM_HBRIDGE_COUNT * 4 > len(data):
            return TelemetryResult.ERR_TRUNCATED, packet
        packet.hbridge_positions = list(
            struct.unpack_from(f"<{TELEM_HBRIDGE_COUNT}h", data, idx)
        )
        idx += TELEM_HBRIDGE_COUNT * 2
        packet.hbridge_currents = list(
            struct.unpack_from(f"<{TELEM_HBRIDGE_COUNT}H", data, idx)
        )
        idx += TELEM_HBRIDGE_COUNT * 2

    # Parse Digital Inputs section
    if flags & TELEM_HAS_DIN:
        if idx + 4 > len(data):
            return TelemetryResult.ERR_TRUNCATED, packet
        (packet.din_bitmask,) = struct.unpack_from("<I", data, idx)
        idx += 4

    # Parse Virtual Channels section
    if flags & TELEM_HAS_VIRTUALS:
        if idx + 2 > len(data):
            return TelemetryResult.ERR_TRUNCATED, packet
        (count,) = struct.unpack_from("<H", data, idx)
        idx += 2

        if count > TELEM_VIRTUAL_MAX:
            count = TELEM_VIRTUAL_MAX

        packet.virtual_channels = {}
        for _ in range(count):
            if idx + 6 > len(data):
                return TelemetryResult.ERR_TRUNCATED, packet
            channel_id, value = struct.unpack_from("<Hi", data, idx)
            packet.virtual_channels[channel_id] = value
            idx += 6

    # Parse Faults section
    if flags & TELEM_HAS_FAULTS:
        if idx + 4 > len(data):
            return TelemetryResult.ERR_TRUNCATED, packet
        packet.fault_status = data[idx]
        packet.fault_flags = data[idx + 1]
        idx += 4

    # Parse Currents section
    if flags & TELEM_HAS_CURRENTS:
        if idx + TELEM_OUTPUT_COUNT * 2 > len(data):
            return TelemetryResult.ERR_TRUNCATED, packet
        packet.output_currents = list(
            struct.unpack_from(f"<{TELEM_OUTPUT_COUNT}H", data, idx)
        )
        idx += TELEM_OUTPUT_COUNT * 2

    return TelemetryResult.OK, packet


def get_section_flags_str(flags: int) -> str:
    """Get human-readable string of section flags"""
    sections = []
    if flags & TELEM_HAS_ADC:
        sections.append("ADC")
    if flags & TELEM_HAS_OUTPUTS:
        sections.append("OUTPUTS")
    if flags & TELEM_HAS_HBRIDGE:
        sections.append("HBRIDGE")
    if flags & TELEM_HAS_DIN:
        sections.append("DIN")
    if flags & TELEM_HAS_VIRTUALS:
        sections.append("VIRTUALS")
    if flags & TELEM_HAS_FAULTS:
        sections.append("FAULTS")
    if flags & TELEM_HAS_CURRENTS:
        sections.append("CURRENTS")
    return "|".join(sections) if sections else "NONE"
