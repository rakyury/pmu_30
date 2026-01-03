"""
PMU-30 Communication Package

Provides MIN protocol implementation and telemetry parsing.
"""

from .protocol import (
    MessageType,
    build_min_frame,
    MINFrameParser,
    FrameParser,
    MAX_PAYLOAD,
)
from .telemetry import (
    TelemetryPacket,
    parse_telemetry,
    TELEMETRY_PACKET_SIZE,
)

__all__ = [
    # Protocol
    "MessageType",
    "build_min_frame",
    "MINFrameParser",
    "FrameParser",
    "MAX_PAYLOAD",
    # Telemetry
    "TelemetryPacket",
    "parse_telemetry",
    "TELEMETRY_PACKET_SIZE",
]

__version__ = "2.0.0"
