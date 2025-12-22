"""
PMU-30 Protocol Tests
Tests for protocol encoding, decoding, and CRC calculation
"""

import pytest
import struct
from src.communication.protocol import (
    MessageType,
    ProtocolFrame,
    ProtocolError,
    crc16_ccitt,
    encode_frame,
    decode_frame,
    FrameBuilder,
    FrameParser,
    FRAME_START_BYTE,
    FRAME_HEADER_SIZE,
    FRAME_CRC_SIZE,
)


class TestCRC16:
    """Test CRC-16-CCITT calculation."""

    def test_empty_data(self):
        """CRC of empty data should be initial value."""
        assert crc16_ccitt(b"") == 0xFFFF

    def test_known_values(self):
        """Test against known CRC values."""
        # "123456789" should give 0x29B1 for CRC-16-CCITT
        assert crc16_ccitt(b"123456789") == 0x29B1

    def test_single_byte(self):
        """Test single byte CRC."""
        crc = crc16_ccitt(b"\x00")
        assert isinstance(crc, int)
        assert 0 <= crc <= 0xFFFF

    def test_consistency(self):
        """Same data should give same CRC."""
        data = b"test data for crc"
        assert crc16_ccitt(data) == crc16_ccitt(data)

    def test_different_data(self):
        """Different data should give different CRC."""
        assert crc16_ccitt(b"data1") != crc16_ccitt(b"data2")


class TestFrameEncoding:
    """Test frame encoding."""

    def test_encode_empty_payload(self):
        """Encode frame with empty payload."""
        frame = ProtocolFrame(msg_type=MessageType.PING, payload=b"")
        encoded = encode_frame(frame)

        # Start byte + 2 length + 1 msgtype + 0 payload + 2 CRC = 6 bytes
        assert len(encoded) == 6
        assert encoded[0] == FRAME_START_BYTE
        assert struct.unpack("<H", encoded[1:3])[0] == 0  # Length
        assert encoded[3] == MessageType.PING

    def test_encode_with_payload(self):
        """Encode frame with payload."""
        payload = b"\x01\x02\x03\x04"
        frame = ProtocolFrame(msg_type=MessageType.SET_CHANNEL, payload=payload)
        encoded = encode_frame(frame)

        assert len(encoded) == FRAME_HEADER_SIZE + len(payload) + FRAME_CRC_SIZE
        assert encoded[0] == FRAME_START_BYTE
        assert struct.unpack("<H", encoded[1:3])[0] == len(payload)
        assert encoded[3] == MessageType.SET_CHANNEL
        assert encoded[4:4 + len(payload)] == payload

    def test_encode_preserves_crc(self):
        """CRC should be valid after encoding."""
        frame = ProtocolFrame(msg_type=MessageType.GET_INFO, payload=b"test")
        encoded = encode_frame(frame)

        # Decode and verify CRC matches
        decoded, _ = decode_frame(encoded)
        assert decoded is not None
        assert decoded.msg_type == MessageType.GET_INFO
        assert decoded.payload == b"test"


class TestFrameDecoding:
    """Test frame decoding."""

    def test_decode_valid_frame(self):
        """Decode a valid frame."""
        frame = ProtocolFrame(msg_type=MessageType.PONG, payload=b"")
        encoded = encode_frame(frame)

        decoded, consumed = decode_frame(encoded)

        assert decoded is not None
        assert consumed == len(encoded)
        assert decoded.msg_type == MessageType.PONG
        assert decoded.payload == b""

    def test_decode_with_payload(self):
        """Decode frame with payload."""
        payload = b"\x10\x20\x30\x40\x50"
        frame = ProtocolFrame(msg_type=MessageType.CONFIG_DATA, payload=payload)
        encoded = encode_frame(frame)

        decoded, consumed = decode_frame(encoded)

        assert decoded is not None
        assert decoded.payload == payload

    def test_decode_skips_garbage(self):
        """Decoder should skip garbage before start byte."""
        frame = ProtocolFrame(msg_type=MessageType.PING, payload=b"")
        encoded = encode_frame(frame)
        data_with_garbage = b"\x00\x01\x02\x03" + encoded

        decoded, consumed = decode_frame(data_with_garbage)

        # First call should skip 4 garbage bytes
        assert decoded is None
        assert consumed == 4

        # Second call should decode frame
        decoded, consumed = decode_frame(data_with_garbage[4:])
        assert decoded is not None
        assert decoded.msg_type == MessageType.PING

    def test_decode_incomplete_header(self):
        """Decoder should wait for complete header."""
        decoded, consumed = decode_frame(b"\xAA\x00")
        assert decoded is None
        assert consumed == 0

    def test_decode_incomplete_frame(self):
        """Decoder should wait for complete frame."""
        frame = ProtocolFrame(msg_type=MessageType.PING, payload=b"data")
        encoded = encode_frame(frame)

        # Provide only partial frame
        decoded, consumed = decode_frame(encoded[:-2])
        assert decoded is None
        assert consumed == 0

    def test_decode_bad_crc(self):
        """Decoder should reject frame with bad CRC."""
        frame = ProtocolFrame(msg_type=MessageType.PING, payload=b"")
        encoded = bytearray(encode_frame(frame))
        encoded[-1] ^= 0xFF  # Corrupt CRC

        with pytest.raises(ProtocolError, match="CRC"):
            decode_frame(bytes(encoded))


class TestFrameBuilder:
    """Test FrameBuilder helper class."""

    def test_ping(self):
        """Build PING frame."""
        frame = FrameBuilder.ping()
        assert frame.msg_type == MessageType.PING
        assert frame.payload == b""

    def test_pong(self):
        """Build PONG frame."""
        frame = FrameBuilder.pong()
        assert frame.msg_type == MessageType.PONG

    def test_get_info(self):
        """Build GET_INFO frame."""
        frame = FrameBuilder.get_info()
        assert frame.msg_type == MessageType.GET_INFO

    def test_subscribe_telemetry(self):
        """Build SUBSCRIBE_TELEMETRY frame."""
        frame = FrameBuilder.subscribe_telemetry(rate_hz=100)
        assert frame.msg_type == MessageType.SUBSCRIBE_TELEMETRY

        rate = struct.unpack("<H", frame.payload)[0]
        assert rate == 100

    def test_set_channel(self):
        """Build SET_CHANNEL frame."""
        frame = FrameBuilder.set_channel(channel_id=5, value=12.5)
        assert frame.msg_type == MessageType.SET_CHANNEL

        ch_id, value = struct.unpack("<Hf", frame.payload)
        assert ch_id == 5
        assert abs(value - 12.5) < 0.001

    def test_set_config(self):
        """Build SET_CONFIG frame."""
        config_data = b'{"test": "data"}'
        frame = FrameBuilder.set_config(config_data, chunk_index=0, total_chunks=1)
        assert frame.msg_type == MessageType.SET_CONFIG

        chunk_idx, total = struct.unpack("<HH", frame.payload[:4])
        assert chunk_idx == 0
        assert total == 1
        assert frame.payload[4:] == config_data


class TestFrameParser:
    """Test FrameParser helper class."""

    def test_parse_info_response(self):
        """Parse INFO_RESP payload."""
        # Build test payload: 3 bytes version + 1 hw rev + 16 serial + 32 name
        payload = struct.pack("<BBB", 1, 2, 3)  # FW version
        payload += struct.pack("<B", 5)  # HW revision
        payload += b"SERIAL12345\x00\x00\x00\x00\x00"  # 16 bytes serial
        payload += b"PMU-30 Device\x00" + b"\x00" * 18  # 32 bytes name

        result = FrameParser.parse_info_response(payload)

        assert result["firmware_version"] == "1.2.3"
        assert result["hardware_revision"] == 5
        assert result["serial_number"] == "SERIAL12345"
        assert "PMU-30" in result["device_name"]

    def test_parse_config_data(self):
        """Parse CONFIG_DATA payload."""
        chunk_data = b'{"key": "value"}'
        payload = struct.pack("<HH", 2, 5) + chunk_data  # chunk 2 of 5

        chunk_idx, total, data = FrameParser.parse_config_data(payload)

        assert chunk_idx == 2
        assert total == 5
        assert data == chunk_data

    def test_parse_config_ack_success(self):
        """Parse CONFIG_ACK success."""
        payload = struct.pack("<BH", 1, 0)  # success=1, error=0

        success, error_code = FrameParser.parse_config_ack(payload)

        assert success is True
        assert error_code == 0

    def test_parse_config_ack_failure(self):
        """Parse CONFIG_ACK failure."""
        payload = struct.pack("<BH", 0, 42)  # success=0, error=42

        success, error_code = FrameParser.parse_config_ack(payload)

        assert success is False
        assert error_code == 42

    def test_parse_error(self):
        """Parse ERROR payload."""
        message = "Something went wrong"
        msg_bytes = message.encode("utf-8")
        payload = struct.pack("<HB", 123, len(msg_bytes)) + msg_bytes

        error_code, msg = FrameParser.parse_error(payload)

        assert error_code == 123
        assert msg == message


class TestRoundTrip:
    """Test encoding and decoding together."""

    @pytest.mark.parametrize("msg_type,payload", [
        (MessageType.PING, b""),
        (MessageType.PONG, b""),
        (MessageType.GET_INFO, b""),
        (MessageType.SET_CHANNEL, b"\x01\x00\x00\x00\x80\x3f"),
        (MessageType.CONFIG_DATA, b'{"config": "data", "value": 123}'),
        (MessageType.TELEMETRY_DATA, bytes(range(119))),
    ])
    def test_round_trip(self, msg_type, payload):
        """Frame should survive encode/decode round trip."""
        original = ProtocolFrame(msg_type=msg_type, payload=payload)
        encoded = encode_frame(original)
        decoded, _ = decode_frame(encoded)

        assert decoded is not None
        assert decoded.msg_type == original.msg_type
        assert decoded.payload == original.payload

    def test_multiple_frames_in_stream(self):
        """Decode multiple consecutive frames."""
        frames = [
            ProtocolFrame(msg_type=MessageType.PING, payload=b""),
            ProtocolFrame(msg_type=MessageType.PONG, payload=b""),
            ProtocolFrame(msg_type=MessageType.GET_INFO, payload=b"test"),
        ]

        stream = b"".join(encode_frame(f) for f in frames)
        decoded_frames = []

        while stream:
            frame, consumed = decode_frame(stream)
            if frame:
                decoded_frames.append(frame)
                stream = stream[consumed:]
            elif consumed > 0:
                stream = stream[consumed:]
            else:
                break

        assert len(decoded_frames) == len(frames)
        for original, decoded in zip(frames, decoded_frames):
            assert decoded.msg_type == original.msg_type
            assert decoded.payload == original.payload


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
