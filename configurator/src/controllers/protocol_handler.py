"""
Protocol Handler for PMU-30

Handles MIN protocol framing and message parsing.
Separates protocol concerns from transport and high-level logic.

MIN Frame Format:
┌────────────────┬────────────┬────────┬─────────────┬───────┬─────┐
│ 0xAA 0xAA 0xAA │ ID/Control │ Length │   Payload   │ CRC32 │ EOF │
│    3 bytes     │   1 byte   │   1B   │   0-255B    │  4B   │ 1B  │
└────────────────┴────────────┴────────┴─────────────┴───────┴─────┘
"""

import logging
import struct
from typing import Optional, Tuple, List, Callable
from dataclasses import dataclass

from communication.protocol import (
    MessageType, build_min_frame, MINFrameParser, MAX_PAYLOAD
)

logger = logging.getLogger(__name__)


@dataclass
class ParsedMessage:
    """Parsed MIN protocol message."""
    msg_type: int
    payload: bytes


class ProtocolHandler:
    """Handles PMU-30 MIN protocol framing and parsing."""

    def __init__(self):
        self._parser = MINFrameParser()
        self._message_handlers: dict = {}

    def register_handler(self, msg_type: int, handler: Callable[[int, bytes], None]):
        """Register a handler for a specific message type.

        Handler signature: handler(msg_type: int, payload: bytes)
        """
        self._message_handlers[msg_type] = handler

    def build_frame(self, msg_type: int, payload: bytes = b'') -> bytes:
        """
        Build a MIN protocol frame.

        Args:
            msg_type: Message type (MIN command ID, 0-63)
            payload: Payload data (0-255 bytes)

        Returns:
            Encoded MIN frame bytes
        """
        return build_min_frame(msg_type, payload)

    def build_config_frame(self, chunk_idx: int, total_chunks: int, chunk_data: bytes) -> bytes:
        """Build a LOAD_BINARY_CONFIG frame with chunk header."""
        header = struct.pack('<HH', chunk_idx, total_chunks)
        payload = header + chunk_data
        return self.build_frame(MessageType.LOAD_BINARY_CONFIG, payload)

    def feed_data(self, data: bytes) -> List[ParsedMessage]:
        """
        Feed received data into parser and extract complete messages.

        Returns list of parsed messages.
        """
        frames = self._parser.feed(data)
        messages = []

        for min_id, payload, seq, is_transport in frames:
            message = ParsedMessage(msg_type=min_id, payload=payload)
            messages.append(message)

            # Dispatch to handler if registered
            handler = self._message_handlers.get(min_id)
            if handler:
                try:
                    handler(min_id, payload)
                except Exception as e:
                    logger.error(f"Message handler error for type 0x{min_id:02X}: {e}")

        return messages

    def clear_buffer(self):
        """Clear receive buffer and reset parser state."""
        self._parser.reset()

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
    def split_into_chunks(data: bytes, chunk_size: int = 200) -> List[bytes]:
        """Split data into chunks for transmission.

        Note: MIN protocol has 255-byte payload limit, so we use smaller chunks
        (200 bytes default) to leave room for chunk headers.
        """
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
