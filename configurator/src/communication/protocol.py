"""
PMU-30 Binary Protocol Implementation

Frame Format:
┌──────┬────────┬───────┬─────────────┬───────┐
│ 0xAA │ Length │ MsgID │   Payload   │ CRC16 │
│ 1B   │ 2B     │ 1B    │ Variable    │ 2B    │
└──────┴────────┴───────┴─────────────┴───────┘

- Start byte: 0xAA (fixed)
- Length: 2 bytes, little-endian (payload length only)
- MsgID: 1 byte message type identifier
- Payload: Variable length data
- CRC16: 2 bytes, CRC-16-CCITT over Length+MsgID+Payload
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional
import struct


class MessageType(IntEnum):
    """Protocol message types."""

    # Connection management
    PING = 0x01
    PONG = 0x02

    # Device information
    GET_INFO = 0x10
    INFO_RESP = 0x11

    # Configuration transfer
    GET_CONFIG = 0x20
    CONFIG_DATA = 0x21
    SET_CONFIG = 0x22
    CONFIG_ACK = 0x23
    SAVE_TO_FLASH = 0x24    # Save current config to flash
    FLASH_ACK = 0x25        # Flash save acknowledgment

    # Telemetry streaming
    SUBSCRIBE_TELEMETRY = 0x30
    UNSUBSCRIBE_TELEMETRY = 0x31
    TELEMETRY_DATA = 0x32

    # Channel control
    SET_CHANNEL = 0x40
    CHANNEL_ACK = 0x41
    GET_CHANNEL = 0x42
    CHANNEL_DATA = 0x43

    # Error handling
    ERROR = 0x50

    # Log messages (from device/scripts)
    LOG_MESSAGE = 0x55

    # Firmware update
    BOOTLOADER_ENTER = 0x60
    BOOTLOADER_DATA = 0x61
    BOOTLOADER_ACK = 0x62
    BOOTLOADER_EXIT = 0x63

    # Device control
    RESTART_DEVICE = 0x70
    RESTART_ACK = 0x71


class ProtocolError(Exception):
    """Protocol-related errors."""
    pass


# Protocol constants
FRAME_START_BYTE = 0xAA
FRAME_HEADER_SIZE = 4  # Start(1) + Length(2) + MsgID(1)
FRAME_CRC_SIZE = 2
FRAME_MIN_SIZE = FRAME_HEADER_SIZE + FRAME_CRC_SIZE
FRAME_MAX_PAYLOAD = 4096
FRAME_MAX_SIZE = FRAME_HEADER_SIZE + FRAME_MAX_PAYLOAD + FRAME_CRC_SIZE


@dataclass
class ProtocolFrame:
    """Represents a protocol frame."""

    msg_type: MessageType
    payload: bytes

    @property
    def length(self) -> int:
        """Return payload length."""
        return len(self.payload)


def crc16_ccitt(data: bytes, initial: int = 0xFFFF) -> int:
    """
    Calculate CRC-16-CCITT checksum.

    Args:
        data: Data bytes to calculate CRC over
        initial: Initial CRC value (default 0xFFFF)

    Returns:
        16-bit CRC value
    """
    crc = initial
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc


def encode_frame(frame: ProtocolFrame) -> bytes:
    """
    Encode a protocol frame to bytes.

    Args:
        frame: ProtocolFrame to encode

    Returns:
        Encoded frame bytes

    Raises:
        ProtocolError: If payload exceeds maximum size
    """
    if len(frame.payload) > FRAME_MAX_PAYLOAD:
        raise ProtocolError(f"Payload size {len(frame.payload)} exceeds maximum {FRAME_MAX_PAYLOAD}")

    # Build frame without CRC
    header = struct.pack("<BHB", FRAME_START_BYTE, len(frame.payload), frame.msg_type)
    frame_data = header[1:] + frame.payload  # CRC covers Length+MsgID+Payload

    # Calculate and append CRC
    crc = crc16_ccitt(frame_data)

    return header + frame.payload + struct.pack("<H", crc)


def decode_frame(data: bytes) -> tuple[Optional[ProtocolFrame], int]:
    """
    Decode a protocol frame from bytes.

    Args:
        data: Input bytes buffer

    Returns:
        Tuple of (decoded frame or None, bytes consumed)
        If frame is None, bytes_consumed indicates how many bytes to skip

    Raises:
        ProtocolError: If frame is malformed
    """
    # Find start byte
    start_idx = 0
    while start_idx < len(data) and data[start_idx] != FRAME_START_BYTE:
        start_idx += 1

    if start_idx > 0:
        # Skipped some bytes to find start
        return None, start_idx

    # Need at least header
    if len(data) < FRAME_HEADER_SIZE:
        return None, 0  # Need more data

    # Parse header
    _, payload_len, msg_type = struct.unpack("<BHB", data[:FRAME_HEADER_SIZE])

    # Validate payload length
    if payload_len > FRAME_MAX_PAYLOAD:
        raise ProtocolError(f"Invalid payload length: {payload_len}")

    # Calculate total frame size
    frame_size = FRAME_HEADER_SIZE + payload_len + FRAME_CRC_SIZE

    # Need complete frame
    if len(data) < frame_size:
        return None, 0  # Need more data

    # Extract payload and CRC
    payload = data[FRAME_HEADER_SIZE:FRAME_HEADER_SIZE + payload_len]
    received_crc = struct.unpack("<H", data[frame_size - FRAME_CRC_SIZE:frame_size])[0]

    # Verify CRC (over Length+MsgID+Payload)
    crc_data = data[1:frame_size - FRAME_CRC_SIZE]  # Skip start byte
    calculated_crc = crc16_ccitt(crc_data)

    if received_crc != calculated_crc:
        raise ProtocolError(f"CRC mismatch: received 0x{received_crc:04X}, calculated 0x{calculated_crc:04X}")

    # Validate message type
    try:
        msg_type_enum = MessageType(msg_type)
    except ValueError:
        raise ProtocolError(f"Unknown message type: 0x{msg_type:02X}")

    return ProtocolFrame(msg_type=msg_type_enum, payload=payload), frame_size


class FrameBuilder:
    """Helper class to build protocol frames with payloads."""

    @staticmethod
    def ping() -> ProtocolFrame:
        """Create a PING frame."""
        return ProtocolFrame(msg_type=MessageType.PING, payload=b"")

    @staticmethod
    def pong() -> ProtocolFrame:
        """Create a PONG frame."""
        return ProtocolFrame(msg_type=MessageType.PONG, payload=b"")

    @staticmethod
    def get_info() -> ProtocolFrame:
        """Create a GET_INFO frame."""
        return ProtocolFrame(msg_type=MessageType.GET_INFO, payload=b"")

    @staticmethod
    def get_config() -> ProtocolFrame:
        """Create a GET_CONFIG frame."""
        return ProtocolFrame(msg_type=MessageType.GET_CONFIG, payload=b"")

    @staticmethod
    def set_config(config_data: bytes, chunk_index: int, total_chunks: int) -> ProtocolFrame:
        """
        Create a SET_CONFIG frame.

        Args:
            config_data: Configuration data chunk
            chunk_index: Current chunk index (0-based)
            total_chunks: Total number of chunks
        """
        header = struct.pack("<HH", chunk_index, total_chunks)
        return ProtocolFrame(msg_type=MessageType.SET_CONFIG, payload=header + config_data)

    @staticmethod
    def subscribe_telemetry(rate_hz: int = 50) -> ProtocolFrame:
        """
        Create a SUBSCRIBE_TELEMETRY frame.

        Args:
            rate_hz: Telemetry update rate in Hz (default 50)
        """
        payload = struct.pack("<H", rate_hz)
        return ProtocolFrame(msg_type=MessageType.SUBSCRIBE_TELEMETRY, payload=payload)

    @staticmethod
    def unsubscribe_telemetry() -> ProtocolFrame:
        """Create an UNSUBSCRIBE_TELEMETRY frame."""
        return ProtocolFrame(msg_type=MessageType.UNSUBSCRIBE_TELEMETRY, payload=b"")

    @staticmethod
    def set_channel(channel_id: int, value: float) -> ProtocolFrame:
        """
        Create a SET_CHANNEL frame.

        Args:
            channel_id: Channel identifier
            value: New channel value
        """
        payload = struct.pack("<Hf", channel_id, value)
        return ProtocolFrame(msg_type=MessageType.SET_CHANNEL, payload=payload)

    @staticmethod
    def get_channel(channel_id: int) -> ProtocolFrame:
        """
        Create a GET_CHANNEL frame.

        Args:
            channel_id: Channel identifier
        """
        payload = struct.pack("<H", channel_id)
        return ProtocolFrame(msg_type=MessageType.GET_CHANNEL, payload=payload)

    @staticmethod
    def error(error_code: int, message: str = "") -> ProtocolFrame:
        """
        Create an ERROR frame.

        Args:
            error_code: Error code
            message: Optional error message
        """
        msg_bytes = message.encode("utf-8")[:255]  # Limit message length
        payload = struct.pack("<HB", error_code, len(msg_bytes)) + msg_bytes
        return ProtocolFrame(msg_type=MessageType.ERROR, payload=payload)


class FrameParser:
    """Helper class to parse protocol frame payloads."""

    @staticmethod
    def parse_info_response(payload: bytes) -> dict:
        """
        Parse INFO_RESP payload.

        Returns:
            Dictionary with device information
        """
        if len(payload) < 32:
            raise ProtocolError("INFO_RESP payload too short")

        # Parse fixed fields
        fw_major, fw_minor, fw_patch = struct.unpack("<BBB", payload[0:3])
        hw_revision = payload[3]
        serial_number = payload[4:20].rstrip(b"\x00").decode("utf-8", errors="replace")
        device_name = payload[20:52].rstrip(b"\x00").decode("utf-8", errors="replace")

        return {
            "firmware_version": f"{fw_major}.{fw_minor}.{fw_patch}",
            "hardware_revision": hw_revision,
            "serial_number": serial_number,
            "device_name": device_name,
        }

    @staticmethod
    def parse_config_data(payload: bytes) -> tuple[int, int, bytes]:
        """
        Parse CONFIG_DATA payload.

        Returns:
            Tuple of (chunk_index, total_chunks, config_data)
        """
        if len(payload) < 4:
            raise ProtocolError("CONFIG_DATA payload too short")

        chunk_index, total_chunks = struct.unpack("<HH", payload[0:4])
        config_data = payload[4:]

        return chunk_index, total_chunks, config_data

    @staticmethod
    def parse_config_ack(payload: bytes) -> tuple[bool, int]:
        """
        Parse CONFIG_ACK payload.

        Returns:
            Tuple of (success, error_code)
        """
        if len(payload) < 3:
            raise ProtocolError("CONFIG_ACK payload too short")

        success = payload[0] != 0
        error_code = struct.unpack("<H", payload[1:3])[0]

        return success, error_code

    @staticmethod
    def parse_channel_ack(payload: bytes) -> tuple[int, bool, int]:
        """
        Parse CHANNEL_ACK payload.

        Returns:
            Tuple of (channel_id, success, error_code)
        """
        if len(payload) < 5:
            raise ProtocolError("CHANNEL_ACK payload too short")

        channel_id = struct.unpack("<H", payload[0:2])[0]
        success = payload[2] != 0
        error_code = struct.unpack("<H", payload[3:5])[0]

        return channel_id, success, error_code

    @staticmethod
    def parse_error(payload: bytes) -> tuple[int, str]:
        """
        Parse ERROR payload.

        Returns:
            Tuple of (error_code, error_message)
        """
        if len(payload) < 3:
            raise ProtocolError("ERROR payload too short")

        error_code = struct.unpack("<H", payload[0:2])[0]
        msg_len = payload[2]
        message = payload[3:3 + msg_len].decode("utf-8", errors="replace")

        return error_code, message
