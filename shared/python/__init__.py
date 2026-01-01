"""
PMU-30 Shared Library - Python Bindings

Pure Python implementation of the shared library components.
Mirrors the C structures and functions for cross-platform compatibility.
"""

from .telemetry import (
    TelemetryPacket,
    TelemetryResult,
    parse_telemetry,
    TELEM_HAS_ADC,
    TELEM_HAS_OUTPUTS,
    TELEM_HAS_HBRIDGE,
    TELEM_HAS_DIN,
    TELEM_HAS_VIRTUALS,
    TELEM_HAS_FAULTS,
    TELEM_HAS_CURRENTS,
)

from .channel_types import (
    ChannelType,
    HwDevice,
    DataType,
    ChannelFlags,
)

from .crc import crc32, crc16_ccitt

__version__ = "1.0.0"
__all__ = [
    "TelemetryPacket",
    "TelemetryResult",
    "parse_telemetry",
    "ChannelType",
    "HwDevice",
    "DataType",
    "ChannelFlags",
    "crc32",
    "crc16_ccitt",
]
