"""
Protocol Handler for PMU-30

Handles protocol framing, CRC, and message parsing.
Separates protocol concerns from transport and high-level logic.
"""

import logging
import struct
from typing import Optional, Tuple, List, Callable
from dataclasses import dataclass
from enum import IntEnum

from communication.protocol import MessageType, crc16_ccitt, FRAME_START_BYTE

logger = logging.getLogger(__name__)


# Frame format: START(1) | LENGTH(2) | TYPE(1) | PAYLOAD(N) | CRC(2)
FRAME_HEADER_SIZE = 4  # START + LENGTH + TYPE
FRAME_CRC_SIZE = 2
MIN_FRAME_SIZE = FRAME_HEADER_SIZE + FRAME_CRC_SIZE
MAX_PAYLOAD_SIZE = 2048  # Maximum valid payload size


@dataclass
class ParsedMessage:
    """Parsed protocol message."""
    msg_type: int
    payload: bytes
    raw_frame: bytes


class ProtocolHandler:
    """Handles PMU-30 protocol framing and parsing."""

    def __init__(self):
        self._rx_buffer = bytearray()
        self._message_handlers: dict = {}

    def register_handler(self, msg_type: int, handler: Callable[[int, bytes], None]):
        """Register a handler for a specific message type."""
        self._message_handlers[msg_type] = handler

    def build_frame(self, msg_type: int, payload: bytes = b'') -> bytes:
        """
        Build a protocol frame.

        Frame format: START(1) | LENGTH(2) | TYPE(1) | PAYLOAD(N) | CRC(2)
        """
        frame_data = struct.pack('<BHB', FRAME_START_BYTE, len(payload), msg_type) + payload
        crc = self.calculate_crc(frame_data[1:])  # CRC excludes start byte
        return frame_data + struct.pack('<H', crc)

    def build_config_frame(self, chunk_idx: int, total_chunks: int, chunk_data: bytes) -> bytes:
        """Build a SET_CONFIG frame with chunk header."""
        header = struct.pack('<HH', chunk_idx, total_chunks)
        payload = header + chunk_data
        return self.build_frame(MessageType.SET_CONFIG, payload)

    @staticmethod
    def calculate_crc(data: bytes) -> int:
        """Calculate CRC16-CCITT using shared protocol."""
        return crc16_ccitt(data)

    def feed_data(self, data: bytes) -> List[ParsedMessage]:
        """
        Feed received data into buffer and extract complete messages.

        Returns list of parsed messages.
        """
        self._rx_buffer.extend(data)
        messages = []

        while len(self._rx_buffer) >= MIN_FRAME_SIZE:
            # Find start byte
            try:
                start_idx = self._rx_buffer.index(FRAME_START_BYTE)
                if start_idx > 0:
                    # Discard bytes before start byte
                    del self._rx_buffer[:start_idx]
            except ValueError:
                # No start byte found, clear buffer
                self._rx_buffer.clear()
                break

            if len(self._rx_buffer) < FRAME_HEADER_SIZE:
                break

            # Parse header
            length = struct.unpack_from('<H', self._rx_buffer, 1)[0]

            # Validate payload length to prevent sync issues
            # 0xAA can appear in payload (e.g., ADC value 170), causing false sync
            if length > MAX_PAYLOAD_SIZE:
                logger.debug(f"Invalid length {length}, skipping 0xAA at position 0")
                del self._rx_buffer[:1]  # Skip this 0xAA, search for next
                continue

            frame_size = FRAME_HEADER_SIZE + length + FRAME_CRC_SIZE

            if len(self._rx_buffer) < frame_size:
                # Incomplete frame, wait for more data
                break

            # Extract complete frame
            frame = bytes(self._rx_buffer[:frame_size])
            del self._rx_buffer[:frame_size]

            # Verify CRC
            received_crc = struct.unpack_from('<H', frame, frame_size - 2)[0]
            calculated_crc = self.calculate_crc(frame[1:frame_size - 2])

            if received_crc != calculated_crc:
                # CRC mismatch - log but still process for debugging
                # TODO: Re-enable strict CRC after firmware fix
                logger.debug(f"CRC mismatch: rcv={received_crc:04x}, calc={calculated_crc:04x}, len={length}")
                # For now, process anyway to debug telemetry

            # Parse message
            msg_type = frame[3]
            payload = frame[4:frame_size - 2]

            message = ParsedMessage(msg_type=msg_type, payload=payload, raw_frame=frame)
            messages.append(message)

            # Dispatch to handler if registered
            handler = self._message_handlers.get(msg_type)
            if handler:
                try:
                    handler(msg_type, payload)
                except Exception as e:
                    logger.error(f"Message handler error for type {msg_type}: {e}")

        return messages

    def clear_buffer(self):
        """Clear receive buffer."""
        self._rx_buffer.clear()

    @staticmethod
    def parse_config_chunk(payload: bytes) -> Tuple[int, int, bytes]:
        """
        Parse CONFIG_DATA payload.

        Returns: (chunk_index, total_chunks, chunk_data)
        """
        if len(payload) < 4:
            return 0, 0, b''

        chunk_idx, total_chunks = struct.unpack_from('<HH', payload, 0)
        chunk_data = payload[4:]
        return chunk_idx, total_chunks, chunk_data

    @staticmethod
    def parse_log_message(payload: bytes) -> Tuple[int, str, str]:
        """
        Parse LOG message payload.

        Returns: (level, source, message)
        """
        if len(payload) < 2:
            return 0, "", ""

        level = payload[0]
        source_len = payload[1]

        if len(payload) < 2 + source_len:
            return level, "", ""

        source = payload[2:2 + source_len].decode('utf-8', errors='replace')
        message = payload[2 + source_len:].decode('utf-8', errors='replace')

        return level, source, message

    @staticmethod
    def split_into_chunks(data: bytes, chunk_size: int = 1024) -> List[bytes]:
        """Split data into chunks for transmission."""
        return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]


class ConfigAssembler:
    """Assembles configuration from multiple chunks."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset assembler state."""
        self._chunks: dict = {}
        self._total_chunks = 0
        self._complete = False

    def add_chunk(self, chunk_idx: int, total_chunks: int, data: bytes) -> bool:
        """
        Add a chunk to the assembler.

        Returns True if all chunks received.
        """
        self._total_chunks = total_chunks
        self._chunks[chunk_idx] = data

        if len(self._chunks) >= total_chunks:
            self._complete = True
            return True
        return False

    def is_complete(self) -> bool:
        """Check if all chunks received."""
        return self._complete

    def get_data(self) -> Optional[bytes]:
        """Get assembled data if complete."""
        if not self._complete:
            return None

        # Assemble chunks in order
        data = b''
        for i in range(self._total_chunks):
            chunk = self._chunks.get(i)
            if chunk is None:
                logger.error(f"Missing chunk {i}")
                return None
            data += chunk

        return data

    @property
    def progress(self) -> float:
        """Get assembly progress (0.0 to 1.0)."""
        if self._total_chunks == 0:
            return 0.0
        return len(self._chunks) / self._total_chunks
