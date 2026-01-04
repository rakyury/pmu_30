"""
PMU-30 MIN Protocol Implementation

Uses MIN Protocol v2.0 for reliable serial communication with firmware.
MIN provides CRC32 checksums and byte stuffing for robust framing.

MIN Frame Format:
┌────────────────┬────────────┬────────┬─────────────┬───────┬─────┐
│ 0xAA 0xAA 0xAA │ ID/Control │ Length │   Payload   │ CRC32 │ EOF │
│    3 bytes     │   1 byte   │   1B   │   0-255B    │  4B   │ 1B  │
└────────────────┴────────────┴────────┴─────────────┴───────┴─────┘

- Header: Triple 0xAA (frame start)
- ID/Control: Command ID (0-63), bit 7 = transport flag
- Length: Payload length (0-255)
- Payload: Command-specific data
- CRC32: 4 bytes, big-endian, over ID+Length+Payload
- EOF: 0x55 (end of frame marker)

Byte stuffing: Insert 0x55 after every two consecutive 0xAA in payload.
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional, List, Tuple
import struct
from binascii import crc32


class MessageType(IntEnum):
    """MIN Protocol Command IDs (0-63 range).

    These match the firmware's MIN command definitions in pmu_min_port.h.
    """

    # Connection management
    PING = 0x01
    PONG = 0x02

    # Configuration transfer
    GET_CONFIG = 0x10        # Request config from device
    CONFIG_DATA = 0x11       # Config data response (chunked)
    LOAD_CONFIG = 0x12       # Load JSON config (deprecated)
    CONFIG_ACK = 0x13        # Config load acknowledgment
    SAVE_TO_FLASH = 0x14     # Save current config to flash
    FLASH_ACK = 0x15         # Flash save acknowledgment
    CLEAR_CONFIG = 0x16      # Clear config from memory and flash
    CLEAR_CONFIG_ACK = 0x17  # Clear config acknowledgment
    LOAD_BINARY_CONFIG = 0x18  # Load binary configuration (chunked)
    BINARY_CONFIG_ACK = 0x19   # Binary config acknowledgment

    # Telemetry streaming
    SUBSCRIBE_TELEMETRY = 0x20    # START_STREAM in MIN
    UNSUBSCRIBE_TELEMETRY = 0x21  # STOP_STREAM in MIN
    TELEMETRY_DATA = 0x22         # DATA in MIN

    # Channel control
    SET_OUTPUT = 0x28         # Set output state
    OUTPUT_ACK = 0x29         # Output set acknowledgment

    # Device capabilities
    GET_CAPABILITIES = 0x30   # Request device capabilities
    CAPABILITIES = 0x31       # Device capabilities response

    # CAN testing (for loopback tests)
    CAN_INJECT = 0x40         # Inject CAN message for testing
    CAN_INJECT_ACK = 0x41     # CAN inject acknowledgment

    # Logging and diagnostics (future)
    LOG_MESSAGE = 0x32        # Log message from device (future)
    RESTART_DEVICE = 0x33     # Restart device command (future)
    RESTART_ACK = 0x34        # Restart acknowledgment (future)
    BOOT_COMPLETE = 0x35      # Device boot complete notification (future)

    # Atomic channel config (future)
    SET_CHANNEL_CONFIG = 0x36     # Set single channel config
    CHANNEL_CONFIG_ACK = 0x37     # Channel config acknowledgment

    # Response codes
    ACK = 0x3E                # Generic ACK
    NACK = 0x3F               # Generic NACK


class ProtocolError(Exception):
    """Protocol-related errors."""
    pass


# MIN Protocol constants
HEADER_BYTE = 0xAA
STUFF_BYTE = 0x55
EOF_BYTE = 0x55
MAX_PAYLOAD = 255


@dataclass
class ProtocolFrame:
    """Represents a MIN protocol frame."""

    msg_type: MessageType
    payload: bytes
    seq_id: int = 0

    @property
    def length(self) -> int:
        """Return payload length."""
        return len(self.payload)


def build_min_frame(min_id: int, payload: bytes = b'') -> bytes:
    """
    Build a MIN protocol frame.

    Args:
        min_id: Command ID (0-63)
        payload: Payload data (0-255 bytes)

    Returns:
        Complete MIN frame bytes
    """
    if min_id > 63:
        raise ProtocolError(f"MIN ID must be 0-63, got {min_id}")
    if len(payload) > MAX_PAYLOAD:
        raise ProtocolError(f"Payload too large: {len(payload)}")

    # Build prolog: ID + Length + Payload
    prolog = bytes([min_id, len(payload)]) + payload

    # Calculate CRC32 (big-endian)
    crc = crc32(prolog, 0)

    # Build raw frame (before stuffing)
    raw = prolog + struct.pack(">I", crc)

    # Stuff bytes (insert 0x55 after every two consecutive 0xAA)
    stuffed = bytearray([HEADER_BYTE, HEADER_BYTE, HEADER_BYTE])
    count = 0
    for byte in raw:
        stuffed.append(byte)
        if byte == HEADER_BYTE:
            count += 1
            if count == 2:
                stuffed.append(STUFF_BYTE)
                count = 0
        else:
            count = 0

    stuffed.append(EOF_BYTE)
    return bytes(stuffed)


def encode_frame(frame: ProtocolFrame) -> bytes:
    """
    Encode a ProtocolFrame to MIN protocol bytes.

    Args:
        frame: ProtocolFrame to encode

    Returns:
        Encoded MIN frame bytes
    """
    return build_min_frame(frame.msg_type, frame.payload)


class MINFrameParser:
    """Parser for MIN protocol frames."""

    SEARCHING_FOR_SOF = 0
    RECEIVING_ID_CONTROL = 1
    RECEIVING_SEQ = 2
    RECEIVING_LENGTH = 3
    RECEIVING_PAYLOAD = 4
    RECEIVING_CHECKSUM_3 = 5
    RECEIVING_CHECKSUM_2 = 6
    RECEIVING_CHECKSUM_1 = 7
    RECEIVING_CHECKSUM_0 = 8
    RECEIVING_EOF = 9

    def __init__(self):
        self.reset()

    def reset(self):
        self._state = self.SEARCHING_FOR_SOF
        self._header_bytes_seen = 0
        self._id_control = 0
        self._seq = 0
        self._length = 0
        self._payload = bytearray()
        self._checksum = 0
        self._frames: List[Tuple[int, bytes, int, bool]] = []

    def feed(self, data: bytes) -> List[Tuple[int, bytes, int, bool]]:
        """
        Feed bytes into the parser.

        Returns:
            List of (min_id, payload, seq, is_transport) tuples
        """
        self._frames = []

        for byte in data:
            # Handle byte stuffing
            if self._header_bytes_seen == 2:
                self._header_bytes_seen = 0
                if byte == HEADER_BYTE:
                    self._state = self.RECEIVING_ID_CONTROL
                    continue
                if byte == STUFF_BYTE:
                    continue  # Discard stuff byte
                # Something wrong, reset
                self._state = self.SEARCHING_FOR_SOF
                continue

            if byte == HEADER_BYTE:
                self._header_bytes_seen += 1
            else:
                self._header_bytes_seen = 0

            # State machine
            if self._state == self.SEARCHING_FOR_SOF:
                pass
            elif self._state == self.RECEIVING_ID_CONTROL:
                self._id_control = byte
                if self._id_control & 0x80:  # Transport frame
                    self._state = self.RECEIVING_SEQ
                else:
                    self._seq = 0
                    self._state = self.RECEIVING_LENGTH
            elif self._state == self.RECEIVING_SEQ:
                self._seq = byte
                self._state = self.RECEIVING_LENGTH
            elif self._state == self.RECEIVING_LENGTH:
                self._length = byte
                self._payload = bytearray()
                if self._length > 0:
                    self._state = self.RECEIVING_PAYLOAD
                else:
                    self._state = self.RECEIVING_CHECKSUM_3
            elif self._state == self.RECEIVING_PAYLOAD:
                self._payload.append(byte)
                if len(self._payload) >= self._length:
                    self._state = self.RECEIVING_CHECKSUM_3
            elif self._state == self.RECEIVING_CHECKSUM_3:
                self._checksum = byte << 24
                self._state = self.RECEIVING_CHECKSUM_2
            elif self._state == self.RECEIVING_CHECKSUM_2:
                self._checksum |= byte << 16
                self._state = self.RECEIVING_CHECKSUM_1
            elif self._state == self.RECEIVING_CHECKSUM_1:
                self._checksum |= byte << 8
                self._state = self.RECEIVING_CHECKSUM_0
            elif self._state == self.RECEIVING_CHECKSUM_0:
                self._checksum |= byte
                # Verify CRC
                if self._id_control & 0x80:
                    prolog = bytes([self._id_control, self._seq, len(self._payload)]) + self._payload
                else:
                    prolog = bytes([self._id_control, len(self._payload)]) + self._payload
                computed = crc32(prolog, 0) & 0xFFFFFFFF
                if self._checksum == computed:
                    self._state = self.RECEIVING_EOF
                else:
                    self._state = self.SEARCHING_FOR_SOF
            elif self._state == self.RECEIVING_EOF:
                if byte == EOF_BYTE:
                    # Frame received OK
                    min_id = self._id_control & 0x3F
                    is_transport = bool(self._id_control & 0x80)
                    self._frames.append((min_id, bytes(self._payload), self._seq, is_transport))
                self._state = self.SEARCHING_FOR_SOF

        return self._frames


def decode_frame(data: bytes) -> tuple[Optional[ProtocolFrame], int]:
    """
    Decode a MIN protocol frame from bytes.

    Args:
        data: Input bytes buffer

    Returns:
        Tuple of (decoded frame or None, bytes consumed)
        If frame is None, bytes_consumed indicates how many bytes to skip
    """
    parser = MINFrameParser()
    frames = parser.feed(data)

    if not frames:
        # No complete frame found - we consumed some bytes but need more
        return None, 0

    # Return first frame
    min_id, payload, seq, is_transport = frames[0]

    try:
        msg_type = MessageType(min_id)
    except ValueError:
        # Unknown message type - still return a frame
        msg_type = min_id

    # Estimate bytes consumed (not exact due to stuffing, but close enough)
    # MIN frame: 3 (header) + 1 (id) + 1 (len) + len(payload) + 4 (crc) + 1 (eof)
    consumed = 10 + len(payload)

    return ProtocolFrame(msg_type=msg_type, payload=payload, seq_id=seq), consumed


class FrameBuilder:
    """Helper class to build MIN protocol frames."""

    @staticmethod
    def ping() -> ProtocolFrame:
        """Create a PING frame."""
        return ProtocolFrame(msg_type=MessageType.PING, payload=b"")

    @staticmethod
    def pong() -> ProtocolFrame:
        """Create a PONG frame."""
        return ProtocolFrame(msg_type=MessageType.PONG, payload=b"")

    @staticmethod
    def get_config() -> ProtocolFrame:
        """Create a GET_CONFIG frame."""
        return ProtocolFrame(msg_type=MessageType.GET_CONFIG, payload=b"")

    @staticmethod
    def subscribe_telemetry(rate_hz: int = 50) -> ProtocolFrame:
        """
        Create a SUBSCRIBE_TELEMETRY (START_STREAM) frame.

        Args:
            rate_hz: Telemetry update rate in Hz (default 50)
        """
        payload = struct.pack("<H", rate_hz)
        return ProtocolFrame(msg_type=MessageType.SUBSCRIBE_TELEMETRY, payload=payload)

    @staticmethod
    def unsubscribe_telemetry() -> ProtocolFrame:
        """Create an UNSUBSCRIBE_TELEMETRY (STOP_STREAM) frame."""
        return ProtocolFrame(msg_type=MessageType.UNSUBSCRIBE_TELEMETRY, payload=b"")

    @staticmethod
    def set_output(channel: int, state: int) -> ProtocolFrame:
        """
        Create a SET_OUTPUT frame.

        Args:
            channel: Output channel index
            state: Output state (0=OFF, 1=ON)
        """
        payload = struct.pack("<BB", channel, state)
        return ProtocolFrame(msg_type=MessageType.SET_OUTPUT, payload=payload)

    @staticmethod
    def save_to_flash() -> ProtocolFrame:
        """Create a SAVE_TO_FLASH frame."""
        return ProtocolFrame(msg_type=MessageType.SAVE_TO_FLASH, payload=b"")

    @staticmethod
    def clear_config() -> ProtocolFrame:
        """Create a CLEAR_CONFIG frame."""
        return ProtocolFrame(msg_type=MessageType.CLEAR_CONFIG, payload=b"")

    @staticmethod
    def load_binary_config(binary_data: bytes, chunk_index: int = 0, total_chunks: int = 1) -> ProtocolFrame:
        """
        Create a LOAD_BINARY_CONFIG frame.

        Args:
            binary_data: Binary configuration data chunk
            chunk_index: Current chunk index (0-based)
            total_chunks: Total number of chunks
        """
        header = struct.pack("<HH", chunk_index, total_chunks)
        return ProtocolFrame(msg_type=MessageType.LOAD_BINARY_CONFIG, payload=header + binary_data)

    @staticmethod
    def load_binary_config_chunked(binary_data: bytes, chunk_size: int = 200) -> list:
        """
        Create LOAD_BINARY_CONFIG frames for a complete binary configuration.

        Note: MIN protocol has 255-byte payload limit, so we use smaller chunks
        (200 bytes) to leave room for the 4-byte header.

        Args:
            binary_data: Complete binary configuration
            chunk_size: Maximum chunk size (default 200 bytes for MIN)

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
                payload=header + chunk
            ))

        return frames


class FrameParser:
    """Helper class to parse MIN protocol frame payloads."""

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
        Parse CONFIG_ACK or BINARY_CONFIG_ACK payload.

        Returns:
            Tuple of (success, channels_loaded)
        """
        if len(payload) < 1:
            return False, 0

        success = payload[0] == 1
        channels_loaded = 0
        if len(payload) >= 4:
            channels_loaded = struct.unpack("<H", payload[2:4])[0]

        return success, channels_loaded

    @staticmethod
    def parse_flash_ack(payload: bytes) -> bool:
        """
        Parse FLASH_ACK payload.

        Returns:
            True if save was successful
        """
        if len(payload) < 1:
            return False
        return payload[0] == 1

    @staticmethod
    def parse_clear_config_ack(payload: bytes) -> bool:
        """
        Parse CLEAR_CONFIG_ACK payload.

        Returns:
            True if clear was successful
        """
        if len(payload) < 1:
            return False
        return payload[0] == 1

    @staticmethod
    def parse_output_ack(payload: bytes) -> tuple[int, bool]:
        """
        Parse OUTPUT_ACK payload.

        Returns:
            Tuple of (channel, success)
        """
        if len(payload) < 2:
            return 0, False
        return payload[0], payload[1] == 1
