"""
PMU-30 Binary Protocol Implementation v2 with SeqID

Uses shared protocol from shared/python/protocol.py for CRC calculation.
Provides configurator-specific message types and frame builders.

Frame Format v2 (matches firmware pmu_protocol.h):
┌──────┬────────┬───────┬───────┬─────────────┬───────┐
│ 0xAA │ Length │ SeqID │ MsgID │   Payload   │ CRC16 │
│ 1B   │ 2B LE  │ 2B LE │ 1B    │ Variable    │ 2B LE │
└──────┴────────┴───────┴───────┴─────────────┴───────┘

- Start byte: 0xAA (fixed)
- Length: 2 bytes, little-endian (payload length only)
- SeqID: 2 bytes, sequence ID for request-response correlation
  - 0x0000: Broadcast (no response expected)
  - 0x0001-0xFFFE: Normal requests (response echoes same SeqID)
  - 0xFFFF: Reserved
- MsgID: 1 byte message type identifier
- Payload: Variable length data
- CRC16: 2 bytes, CRC-16-CCITT over Length+SeqID+MsgID+Payload
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional
import struct
import sys
from pathlib import Path

# Add shared path for protocol imports
# Path: communication/protocol.py -> src -> configurator -> pmu_30 -> shared/python
_shared_path = Path(__file__).parent.parent.parent.parent / "shared" / "python"
if str(_shared_path) not in sys.path:
    sys.path.insert(0, str(_shared_path))

# Import CRC calculation from shared protocol
from protocol import calc_crc16 as _shared_crc16


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
    CLEAR_CONFIG = 0x26     # Clear config from memory and flash
    CLEAR_CONFIG_ACK = 0x27 # Clear config acknowledgment

    # Telemetry streaming
    SUBSCRIBE_TELEMETRY = 0x30
    UNSUBSCRIBE_TELEMETRY = 0x31
    TELEMETRY_DATA = 0x32

    # Channel control
    SET_CHANNEL = 0x40
    CHANNEL_ACK = 0x41
    SET_HBRIDGE = 0x42       # Set H-Bridge mode and PWM
    GET_CHANNEL = 0x43       # Shifted from 0x42
    CHANNEL_DATA = 0x44      # Shifted from 0x43

    # Atomic channel configuration update
    SET_CHANNEL_CONFIG = 0x66    # Update single channel config
    CHANNEL_CONFIG_ACK = 0x67    # Channel config update response
    LOAD_BINARY_CONFIG = 0x68    # Load binary configuration (chunked)
    BINARY_CONFIG_ACK = 0x69     # Binary config acknowledgment

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
    BOOT_COMPLETE = 0x72      # Sent by device after successful boot/restart

    # Emulator control (0x80+)
    EMU_INJECT_FAULT = 0x80
    EMU_CLEAR_FAULT = 0x81
    EMU_SET_VOLTAGE = 0x82
    EMU_SET_TEMPERATURE = 0x83
    EMU_SET_DIGITAL_INPUT = 0x84
    EMU_SET_OUTPUT = 0x85
    EMU_SET_ANALOG_INPUT = 0x86
    EMU_INJECT_CAN = 0x88  # Inject CAN message for testing
    EMU_ACK = 0x8F


class ProtocolError(Exception):
    """Protocol-related errors."""
    pass


# Protocol constants
FRAME_START_BYTE = 0xAA
FRAME_HEADER_SIZE = 6  # Start(1) + Length(2) + SeqID(2) + MsgID(1)
FRAME_CRC_SIZE = 2
FRAME_MIN_SIZE = FRAME_HEADER_SIZE + FRAME_CRC_SIZE
FRAME_MAX_PAYLOAD = 4096
FRAME_MAX_SIZE = FRAME_HEADER_SIZE + FRAME_MAX_PAYLOAD + FRAME_CRC_SIZE

# Sequence ID constants
SEQ_ID_BROADCAST = 0x0000  # Broadcast - no response expected
SEQ_ID_RESERVED = 0xFFFF   # Reserved

# Sequence ID generator for request-response correlation
_next_seq_id = 1


def get_next_seq_id() -> int:
    """
    Get the next sequence ID for request-response correlation.

    Returns:
        Sequence ID in range 0x0001-0xFFFE
    """
    global _next_seq_id
    seq_id = _next_seq_id
    _next_seq_id += 1
    if _next_seq_id >= SEQ_ID_RESERVED:
        _next_seq_id = 1
    return seq_id


@dataclass
class ProtocolFrame:
    """Represents a protocol frame with sequence ID."""

    msg_type: MessageType
    payload: bytes
    seq_id: int = 0  # 0 = broadcast, 1-0xFFFE = request/response

    @property
    def length(self) -> int:
        """Return payload length."""
        return len(self.payload)


def crc16_ccitt(data: bytes, initial: int = 0xFFFF) -> int:
    """
    Calculate CRC-16-CCITT checksum.

    Uses shared protocol implementation for consistency with firmware.

    Args:
        data: Data bytes to calculate CRC over
        initial: Initial CRC value (default 0xFFFF, only value supported)

    Returns:
        16-bit CRC value
    """
    # Use shared protocol CRC (always uses 0xFFFF initial)
    return _shared_crc16(data)


def encode_frame(frame: ProtocolFrame) -> bytes:
    """
    Encode a protocol frame to bytes (v2 format with SeqID).

    Args:
        frame: ProtocolFrame to encode

    Returns:
        Encoded frame bytes

    Raises:
        ProtocolError: If payload exceeds maximum size
    """
    if len(frame.payload) > FRAME_MAX_PAYLOAD:
        raise ProtocolError(f"Payload size {len(frame.payload)} exceeds maximum {FRAME_MAX_PAYLOAD}")

    # Build frame without CRC: Start(1) + Length(2) + SeqID(2) + MsgID(1)
    header = struct.pack("<BHHB", FRAME_START_BYTE, len(frame.payload), frame.seq_id, frame.msg_type)
    # CRC covers Length(2) + SeqID(2) + MsgID(1) + Payload
    crc_data = header[1:] + frame.payload

    # Calculate and append CRC
    crc = crc16_ccitt(crc_data)

    return header + frame.payload + struct.pack("<H", crc)


def decode_frame(data: bytes) -> tuple[Optional[ProtocolFrame], int]:
    """
    Decode a protocol frame from bytes (v2 format with SeqID).

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

    # Need at least header (6 bytes: Start + Length + SeqID + MsgID)
    if len(data) < FRAME_HEADER_SIZE:
        return None, 0  # Need more data

    # Parse header: Start(1) + Length(2) + SeqID(2) + MsgID(1)
    _, payload_len, seq_id, msg_type = struct.unpack("<BHHB", data[:FRAME_HEADER_SIZE])

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

    # Verify CRC (over Length+SeqID+MsgID+Payload)
    crc_data = data[1:frame_size - FRAME_CRC_SIZE]  # Skip start byte
    calculated_crc = crc16_ccitt(crc_data)

    if received_crc != calculated_crc:
        raise ProtocolError(f"CRC mismatch: received 0x{received_crc:04X}, calculated 0x{calculated_crc:04X}")

    # Validate message type
    try:
        msg_type_enum = MessageType(msg_type)
    except ValueError:
        raise ProtocolError(f"Unknown message type: 0x{msg_type:02X}")

    return ProtocolFrame(msg_type=msg_type_enum, payload=payload, seq_id=seq_id), frame_size


class FrameBuilder:
    """Helper class to build protocol frames with payloads and auto-assigned SeqIDs."""

    @staticmethod
    def ping() -> ProtocolFrame:
        """Create a PING frame with auto-assigned SeqID."""
        return ProtocolFrame(msg_type=MessageType.PING, payload=b"", seq_id=get_next_seq_id())

    @staticmethod
    def pong(seq_id: int = 0) -> ProtocolFrame:
        """Create a PONG frame (response, uses provided seq_id)."""
        return ProtocolFrame(msg_type=MessageType.PONG, payload=b"", seq_id=seq_id)

    @staticmethod
    def get_info() -> ProtocolFrame:
        """Create a GET_INFO frame with auto-assigned SeqID."""
        return ProtocolFrame(msg_type=MessageType.GET_INFO, payload=b"", seq_id=get_next_seq_id())

    @staticmethod
    def get_config() -> ProtocolFrame:
        """Create a GET_CONFIG frame with auto-assigned SeqID."""
        return ProtocolFrame(msg_type=MessageType.GET_CONFIG, payload=b"", seq_id=get_next_seq_id())

    @staticmethod
    def set_config(config_data: bytes, chunk_index: int, total_chunks: int) -> ProtocolFrame:
        """
        Create a SET_CONFIG frame for binary configuration upload with auto-assigned SeqID.

        Args:
            config_data: Binary configuration data chunk (.pmu30 format)
            chunk_index: Current chunk index (0-based)
            total_chunks: Total number of chunks
        """
        header = struct.pack("<HH", chunk_index, total_chunks)
        return ProtocolFrame(msg_type=MessageType.SET_CONFIG, payload=header + config_data, seq_id=get_next_seq_id())

    @staticmethod
    def set_binary_config(binary_data: bytes, chunk_size: int = 1024) -> list:
        """
        Create SET_CONFIG frames for a complete binary configuration.

        Splits large configurations into chunks for reliable transfer.
        Each frame gets its own SeqID for individual acknowledgment.

        Args:
            binary_data: Complete binary configuration (.pmu30 format)
            chunk_size: Maximum chunk size (default 1024 bytes)

        Returns:
            List of ProtocolFrame objects to send sequentially
        """
        frames = []
        total_chunks = (len(binary_data) + chunk_size - 1) // chunk_size

        for i in range(total_chunks):
            start = i * chunk_size
            end = min(start + chunk_size, len(binary_data))
            chunk = binary_data[start:end]

            header = struct.pack("<HH", i, total_chunks)
            frames.append(ProtocolFrame(
                msg_type=MessageType.SET_CONFIG,
                payload=header + chunk,
                seq_id=get_next_seq_id()
            ))

        return frames

    @staticmethod
    def subscribe_telemetry(rate_hz: int = 50) -> ProtocolFrame:
        """
        Create a SUBSCRIBE_TELEMETRY frame with auto-assigned SeqID.

        Args:
            rate_hz: Telemetry update rate in Hz (default 50)
        """
        payload = struct.pack("<H", rate_hz)
        return ProtocolFrame(msg_type=MessageType.SUBSCRIBE_TELEMETRY, payload=payload, seq_id=get_next_seq_id())

    @staticmethod
    def unsubscribe_telemetry() -> ProtocolFrame:
        """Create an UNSUBSCRIBE_TELEMETRY frame with auto-assigned SeqID."""
        return ProtocolFrame(msg_type=MessageType.UNSUBSCRIBE_TELEMETRY, payload=b"", seq_id=get_next_seq_id())

    @staticmethod
    def set_channel(channel_id: int, value: float) -> ProtocolFrame:
        """
        Create a SET_CHANNEL frame with auto-assigned SeqID.

        Args:
            channel_id: Channel identifier
            value: New channel value
        """
        payload = struct.pack("<Hf", channel_id, value)
        return ProtocolFrame(msg_type=MessageType.SET_CHANNEL, payload=payload, seq_id=get_next_seq_id())

    @staticmethod
    def set_hbridge(bridge: int, mode: int, duty: int, target: int = 0) -> ProtocolFrame:
        """
        Create a SET_HBRIDGE frame with auto-assigned SeqID.

        Args:
            bridge: Bridge number (0-3)
            mode: Operating mode (0=COAST, 1=FORWARD, 2=REVERSE, 3=BRAKE, 4=WIPER_PARK, 5=PID)
            duty: PWM duty cycle (0-1000 = 0-100%)
            target: Target position for PID mode (0-1000)

        Returns:
            ProtocolFrame ready to send
        """
        # Pack: bridge(1) + mode(1) + duty(2) + target(2)
        payload = struct.pack("<BBHH", bridge, mode, duty, target)
        return ProtocolFrame(msg_type=MessageType.SET_HBRIDGE, payload=payload, seq_id=get_next_seq_id())

    @staticmethod
    def set_channel_config(channel_type: int, channel_id: int, config_json: bytes) -> ProtocolFrame:
        """
        Create a SET_CHANNEL_CONFIG frame for atomic channel updates with auto-assigned SeqID.

        Args:
            channel_type: Channel type discriminator:
                0x01=power_output, 0x02=hbridge, 0x03=digital_input, 0x04=analog_input,
                0x05=logic, 0x06=number, 0x07=timer, 0x08=filter, 0x09=switch,
                0x0A=table_2d, 0x0B=table_3d, 0x0C=can_rx, 0x0D=can_tx, 0x0E=pid
            channel_id: Numeric channel ID
            config_json: JSON configuration as bytes (UTF-8)

        Returns:
            ProtocolFrame ready to send
        """
        # Pack: channel_type(1) + channel_id(2) + json_len(2) + json_data
        json_len = len(config_json)
        payload = struct.pack("<BHH", channel_type, channel_id, json_len) + config_json
        return ProtocolFrame(msg_type=MessageType.SET_CHANNEL_CONFIG, payload=payload, seq_id=get_next_seq_id())

    @staticmethod
    def get_channel(channel_id: int) -> ProtocolFrame:
        """
        Create a GET_CHANNEL frame with auto-assigned SeqID.

        Args:
            channel_id: Channel identifier
        """
        payload = struct.pack("<H", channel_id)
        return ProtocolFrame(msg_type=MessageType.GET_CHANNEL, payload=payload, seq_id=get_next_seq_id())

    @staticmethod
    def error(error_code: int, message: str = "") -> ProtocolFrame:
        """
        Create an ERROR frame (broadcast, no response expected).

        Args:
            error_code: Error code
            message: Optional error message
        """
        msg_bytes = message.encode("utf-8")[:255]  # Limit message length
        payload = struct.pack("<HB", error_code, len(msg_bytes)) + msg_bytes
        return ProtocolFrame(msg_type=MessageType.ERROR, payload=payload, seq_id=SEQ_ID_BROADCAST)

    @staticmethod
    def restart_device() -> ProtocolFrame:
        """Create a RESTART_DEVICE frame with auto-assigned SeqID."""
        return ProtocolFrame(msg_type=MessageType.RESTART_DEVICE, payload=b"", seq_id=get_next_seq_id())

    @staticmethod
    def save_to_flash() -> ProtocolFrame:
        """Create a SAVE_TO_FLASH frame with auto-assigned SeqID."""
        return ProtocolFrame(msg_type=MessageType.SAVE_TO_FLASH, payload=b"", seq_id=get_next_seq_id())

    @staticmethod
    def clear_config() -> ProtocolFrame:
        """Create a CLEAR_CONFIG frame with auto-assigned SeqID."""
        return ProtocolFrame(msg_type=MessageType.CLEAR_CONFIG, payload=b"", seq_id=get_next_seq_id())

    @staticmethod
    def load_binary_config(binary_data: bytes, chunk_index: int = 0, total_chunks: int = 1) -> ProtocolFrame:
        """
        Create a LOAD_BINARY_CONFIG frame with auto-assigned SeqID.

        Args:
            binary_data: Binary configuration data chunk
            chunk_index: Current chunk index (0-based)
            total_chunks: Total number of chunks
        """
        header = struct.pack("<HH", chunk_index, total_chunks)
        return ProtocolFrame(msg_type=MessageType.LOAD_BINARY_CONFIG, payload=header + binary_data, seq_id=get_next_seq_id())

    @staticmethod
    def load_binary_config_chunked(binary_data: bytes, chunk_size: int = 1024) -> list:
        """
        Create LOAD_BINARY_CONFIG frames for a complete binary configuration.

        Splits large configurations into chunks for reliable transfer.
        Each frame gets its own SeqID for individual acknowledgment.

        Args:
            binary_data: Complete binary configuration
            chunk_size: Maximum chunk size (default 1024 bytes)

        Returns:
            List of ProtocolFrame objects to send sequentially
        """
        frames = []
        total_chunks = (len(binary_data) + chunk_size - 1) // chunk_size
        if total_chunks == 0:
            total_chunks = 1  # At least one chunk even if empty

        for i in range(total_chunks):
            start = i * chunk_size
            end = min(start + chunk_size, len(binary_data))
            chunk = binary_data[start:end]

            header = struct.pack("<HH", i, total_chunks)
            frames.append(ProtocolFrame(
                msg_type=MessageType.LOAD_BINARY_CONFIG,
                payload=header + chunk,
                seq_id=get_next_seq_id()
            ))

        return frames

    # ===== Emulator Control Commands =====

    @staticmethod
    def emu_inject_fault(channel: int, fault_type: int) -> ProtocolFrame:
        """
        Inject a fault on an output channel (emulator only) with auto-assigned SeqID.

        Args:
            channel: Channel number (0-29)
            fault_type: Fault type bitmask (1=OC, 2=OT, 4=SC, 8=OL)
        """
        payload = struct.pack("<BB", channel, fault_type)
        return ProtocolFrame(msg_type=MessageType.EMU_INJECT_FAULT, payload=payload, seq_id=get_next_seq_id())

    @staticmethod
    def emu_clear_fault(channel: int) -> ProtocolFrame:
        """
        Clear fault on an output channel (emulator only) with auto-assigned SeqID.

        Args:
            channel: Channel number (0-29)
        """
        payload = struct.pack("<B", channel)
        return ProtocolFrame(msg_type=MessageType.EMU_CLEAR_FAULT, payload=payload, seq_id=get_next_seq_id())

    @staticmethod
    def emu_set_voltage(voltage_mv: int) -> ProtocolFrame:
        """
        Set battery voltage (emulator only) with auto-assigned SeqID.

        Args:
            voltage_mv: Voltage in millivolts (6000-18000)
        """
        payload = struct.pack("<H", voltage_mv)
        return ProtocolFrame(msg_type=MessageType.EMU_SET_VOLTAGE, payload=payload, seq_id=get_next_seq_id())

    @staticmethod
    def emu_set_temperature(temp_c: int) -> ProtocolFrame:
        """
        Set temperature (emulator only) with auto-assigned SeqID.

        Args:
            temp_c: Temperature in Celsius (-40 to 150)
        """
        payload = struct.pack("<h", temp_c)
        return ProtocolFrame(msg_type=MessageType.EMU_SET_TEMPERATURE, payload=payload, seq_id=get_next_seq_id())

    @staticmethod
    def emu_set_digital_input(channel: int, state: bool) -> ProtocolFrame:
        """
        Set digital input state (emulator only) with auto-assigned SeqID.

        Args:
            channel: Digital input channel (0-19)
            state: Input state (True=HIGH, False=LOW)
        """
        payload = struct.pack("<BB", channel, 1 if state else 0)
        return ProtocolFrame(msg_type=MessageType.EMU_SET_DIGITAL_INPUT, payload=payload, seq_id=get_next_seq_id())

    @staticmethod
    def emu_set_output(channel: int, on: bool, pwm: int) -> ProtocolFrame:
        """
        Set output channel state (emulator only) with auto-assigned SeqID.

        Args:
            channel: Output channel (0-29)
            on: Output state (True=ON, False=OFF)
            pwm: PWM duty cycle (0-1000 = 0-100%)
        """
        payload = struct.pack("<BBH", channel, 1 if on else 0, pwm)
        return ProtocolFrame(msg_type=MessageType.EMU_SET_OUTPUT, payload=payload, seq_id=get_next_seq_id())

    @staticmethod
    def emu_set_analog_input(channel: int, voltage_mv: int) -> ProtocolFrame:
        """
        Set analog input voltage (emulator only) with auto-assigned SeqID.

        Args:
            channel: Analog input channel (0-15)
            voltage_mv: Voltage in millivolts (0-5000)
        """
        payload = struct.pack("<BH", channel, voltage_mv)
        return ProtocolFrame(msg_type=MessageType.EMU_SET_ANALOG_INPUT, payload=payload, seq_id=get_next_seq_id())

    @staticmethod
    def emu_inject_can(bus_id: int, can_id: int, data: bytes) -> ProtocolFrame:
        """
        Inject CAN message for testing CAN input channels (emulator only) with auto-assigned SeqID.

        Args:
            bus_id: CAN bus index (0 or 1)
            can_id: CAN message ID (11-bit or 29-bit)
            data: CAN data bytes (up to 8 bytes)

        Payload format: [bus_id:1][can_id:4][dlc:1][data:0-8]
        """
        dlc = min(len(data), 8)
        # Pad data to 8 bytes
        padded_data = data[:8].ljust(8, b'\x00')
        payload = struct.pack("<BI", bus_id, can_id) + struct.pack("<B", dlc) + padded_data[:dlc]
        return ProtocolFrame(msg_type=MessageType.EMU_INJECT_CAN, payload=payload, seq_id=get_next_seq_id())


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

    @staticmethod
    def parse_channel_config_ack(payload: bytes) -> tuple[int, bool, int, str]:
        """
        Parse CHANNEL_CONFIG_ACK payload.

        Returns:
            Tuple of (channel_id, success, error_code, error_message)
        """
        if len(payload) < 5:
            raise ProtocolError("CHANNEL_CONFIG_ACK payload too short")

        channel_id = struct.unpack("<H", payload[0:2])[0]
        success = payload[2] != 0
        error_code = struct.unpack("<H", payload[3:5])[0]
        error_message = ""
        if len(payload) > 5:
            error_message = payload[5:].decode("utf-8", errors="replace")

        return channel_id, success, error_code, error_message
