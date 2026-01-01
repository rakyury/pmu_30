"""
PMU-30 Unified Binary Protocol - Python Implementation

Provides frame parsing, building, and protocol constants.
Mirrors protocol.h/.c for Python compatibility.
"""

import struct
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Callable, Optional, List, Tuple, Any


# ============================================================================
# Protocol Constants
# ============================================================================

PROTO_SYNC_H = 0xAA
PROTO_SYNC_L = 0x55
PROTO_HEADER_SIZE = 5    # SYNC(2) + CMD(1) + LEN(2)
PROTO_CRC_SIZE = 2
PROTO_OVERHEAD = PROTO_HEADER_SIZE + PROTO_CRC_SIZE
PROTO_MAX_PAYLOAD = 1024
PROTO_MAX_FRAME = PROTO_OVERHEAD + PROTO_MAX_PAYLOAD


# ============================================================================
# Command Codes
# ============================================================================

class Cmd(IntEnum):
    """Protocol command codes"""
    # System Commands (0x00-0x0F)
    NOP = 0x00
    PING = 0x01
    PONG = 0x02
    GET_CAPS = 0x03
    CAPS_RESP = 0x04
    RESET = 0x05
    BOOTLOADER = 0x06

    # Configuration Commands (0x10-0x1F)
    GET_CONFIG = 0x10
    CONFIG_DATA = 0x11
    SET_CONFIG = 0x12
    CONFIG_ACK = 0x13
    SAVE_CONFIG = 0x14
    LOAD_CONFIG = 0x15
    CLEAR_CONFIG = 0x16

    # Telemetry Commands (0x20-0x2F)
    TELEM_START = 0x20
    TELEM_STOP = 0x21
    TELEM_DATA = 0x22
    TELEM_CONFIG = 0x23

    # Channel Commands (0x30-0x3F)
    CH_GET_VALUE = 0x30
    CH_SET_VALUE = 0x31
    CH_VALUE_RESP = 0x32
    CH_GET_INFO = 0x33
    CH_INFO_RESP = 0x34
    CH_GET_LIST = 0x35
    CH_LIST_RESP = 0x36

    # Debug Commands (0x40-0x4F)
    DEBUG_CONFIG = 0x40
    DEBUG_MSG = 0x41
    DEBUG_VAR_GET = 0x42
    DEBUG_VAR_SET = 0x43
    DEBUG_VAR_RESP = 0x44

    # CAN Commands (0x50-0x5F)
    CAN_SEND = 0x50
    CAN_RECV = 0x51
    CAN_CONFIG = 0x52
    CAN_STATUS = 0x53

    # Firmware Update (0x60-0x6F)
    FW_BEGIN = 0x60
    FW_DATA = 0x61
    FW_END = 0x62
    FW_VERIFY = 0x63
    FW_STATUS = 0x64

    # Datalog Commands (0x70-0x7F)
    LOG_START = 0x70
    LOG_STOP = 0x71
    LOG_STATUS = 0x72
    LOG_GET_DATA = 0x73
    LOG_DATA = 0x74
    LOG_CLEAR = 0x75

    # Error/Status (0xF0-0xFF)
    ERROR = 0xF0
    STATUS = 0xF1


class Error(IntEnum):
    """Protocol error codes"""
    OK = 0x00
    UNKNOWN_CMD = 0x01
    INVALID_PARAM = 0x02
    INVALID_LENGTH = 0x03
    CRC_MISMATCH = 0x04
    BUFFER_FULL = 0x05
    NOT_SUPPORTED = 0x06
    BUSY = 0x07
    TIMEOUT = 0x08
    FLASH_ERROR = 0x09
    CHANNEL_INVALID = 0x0A
    CONFIG_INVALID = 0x0B
    NOT_CONNECTED = 0x0C


class TelemSection(IntEnum):
    """Telemetry section flags"""
    HEADER = 0x0001
    OUTPUTS = 0x0002
    CURRENTS = 0x0004
    ADC = 0x0008
    DIN = 0x0010
    HBRIDGE = 0x0020
    VIRTUALS = 0x0040
    FAULTS = 0x0080
    EXTENDED = 0x0100
    DEBUG = 0x8000


# ============================================================================
# CRC-16-CCITT
# ============================================================================

CRC16_TABLE = [
    0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50A5, 0x60C6, 0x70E7,
    0x8108, 0x9129, 0xA14A, 0xB16B, 0xC18C, 0xD1AD, 0xE1CE, 0xF1EF,
    0x1231, 0x0210, 0x3273, 0x2252, 0x52B5, 0x4294, 0x72F7, 0x62D6,
    0x9339, 0x8318, 0xB37B, 0xA35A, 0xD3BD, 0xC39C, 0xF3FF, 0xE3DE,
    0x2462, 0x3443, 0x0420, 0x1401, 0x64E6, 0x74C7, 0x44A4, 0x5485,
    0xA56A, 0xB54B, 0x8528, 0x9509, 0xE5EE, 0xF5CF, 0xC5AC, 0xD58D,
    0x3653, 0x2672, 0x1611, 0x0630, 0x76D7, 0x66F6, 0x5695, 0x46B4,
    0xB75B, 0xA77A, 0x9719, 0x8738, 0xF7DF, 0xE7FE, 0xD79D, 0xC7BC,
    0x48C4, 0x58E5, 0x6886, 0x78A7, 0x0840, 0x1861, 0x2802, 0x3823,
    0xC9CC, 0xD9ED, 0xE98E, 0xF9AF, 0x8948, 0x9969, 0xA90A, 0xB92B,
    0x5AF5, 0x4AD4, 0x7AB7, 0x6A96, 0x1A71, 0x0A50, 0x3A33, 0x2A12,
    0xDBFD, 0xCBDC, 0xFBBF, 0xEB9E, 0x9B79, 0x8B58, 0xBB3B, 0xAB1A,
    0x6CA6, 0x7C87, 0x4CE4, 0x5CC5, 0x2C22, 0x3C03, 0x0C60, 0x1C41,
    0xEDAE, 0xFD8F, 0xCDEC, 0xDDCD, 0xAD2A, 0xBD0B, 0x8D68, 0x9D49,
    0x7E97, 0x6EB6, 0x5ED5, 0x4EF4, 0x3E13, 0x2E32, 0x1E51, 0x0E70,
    0xFF9F, 0xEFBE, 0xDFDD, 0xCFFC, 0xBF1B, 0xAF3A, 0x9F59, 0x8F78,
    0x9188, 0x81A9, 0xB1CA, 0xA1EB, 0xD10C, 0xC12D, 0xF14E, 0xE16F,
    0x1080, 0x00A1, 0x30C2, 0x20E3, 0x5004, 0x4025, 0x7046, 0x6067,
    0x83B9, 0x9398, 0xA3FB, 0xB3DA, 0xC33D, 0xD31C, 0xE37F, 0xF35E,
    0x02B1, 0x1290, 0x22F3, 0x32D2, 0x4235, 0x5214, 0x6277, 0x7256,
    0xB5EA, 0xA5CB, 0x95A8, 0x8589, 0xF56E, 0xE54F, 0xD52C, 0xC50D,
    0x34E2, 0x24C3, 0x14A0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
    0xA7DB, 0xB7FA, 0x8799, 0x97B8, 0xE75F, 0xF77E, 0xC71D, 0xD73C,
    0x26D3, 0x36F2, 0x0691, 0x16B0, 0x6657, 0x7676, 0x4615, 0x5634,
    0xD94C, 0xC96D, 0xF90E, 0xE92F, 0x99C8, 0x89E9, 0xB98A, 0xA9AB,
    0x5844, 0x4865, 0x7806, 0x6827, 0x18C0, 0x08E1, 0x3882, 0x28A3,
    0xCB7D, 0xDB5C, 0xEB3F, 0xFB1E, 0x8BF9, 0x9BD8, 0xABBB, 0xBB9A,
    0x4A75, 0x5A54, 0x6A37, 0x7A16, 0x0AF1, 0x1AD0, 0x2AB3, 0x3A92,
    0xFD2E, 0xED0F, 0xDD6C, 0xCD4D, 0xBDAA, 0xAD8B, 0x9DE8, 0x8DC9,
    0x7C26, 0x6C07, 0x5C64, 0x4C45, 0x3CA2, 0x2C83, 0x1CE0, 0x0CC1,
    0xEF1F, 0xFF3E, 0xCF5D, 0xDF7C, 0xAF9B, 0xBFBA, 0x8FD9, 0x9FF8,
    0x6E17, 0x7E36, 0x4E55, 0x5E74, 0x2E93, 0x3EB2, 0x0ED1, 0x1EF0,
]


def calc_crc16(data: bytes) -> int:
    """Calculate CRC-16-CCITT"""
    crc = 0xFFFF
    for byte in data:
        crc = ((crc << 8) ^ CRC16_TABLE[(crc >> 8) ^ byte]) & 0xFFFF
    return crc


# ============================================================================
# Frame Data Class
# ============================================================================

@dataclass
class Frame:
    """Protocol frame"""
    cmd: int
    payload: bytes = b""

    def build(self) -> bytes:
        """Build frame bytes"""
        return build_frame(self.cmd, self.payload)


# ============================================================================
# Frame Building
# ============================================================================

def build_frame(cmd: int, payload: bytes = b"") -> bytes:
    """Build a complete protocol frame"""
    if len(payload) > PROTO_MAX_PAYLOAD:
        raise ValueError(f"Payload too large: {len(payload)} > {PROTO_MAX_PAYLOAD}")

    length = len(payload)

    # Build header + payload for CRC calculation
    crc_data = bytes([cmd, length & 0xFF, (length >> 8) & 0xFF]) + payload
    crc = calc_crc16(crc_data)

    # Build complete frame
    frame = bytes([
        PROTO_SYNC_H,
        PROTO_SYNC_L,
        cmd,
        length & 0xFF,
        (length >> 8) & 0xFF
    ]) + payload + bytes([crc & 0xFF, (crc >> 8) & 0xFF])

    return frame


# ============================================================================
# Parser State Machine
# ============================================================================

class ParseState(IntEnum):
    SYNC1 = 0
    SYNC2 = 1
    CMD = 2
    LEN_L = 3
    LEN_H = 4
    PAYLOAD = 5
    CRC_L = 6
    CRC_H = 7


class ProtocolParser:
    """Streaming protocol parser"""

    def __init__(self, max_payload: int = PROTO_MAX_PAYLOAD):
        self.max_payload = max_payload
        self.reset()

    def reset(self):
        """Reset parser state"""
        self.state = ParseState.SYNC1
        self.cmd = 0
        self.length = 0
        self.payload = bytearray()
        self.crc = 0

    def parse_byte(self, byte: int) -> Optional[Frame]:
        """
        Parse a single byte. Returns Frame if complete frame received.
        """
        if self.state == ParseState.SYNC1:
            if byte == PROTO_SYNC_H:
                self.state = ParseState.SYNC2

        elif self.state == ParseState.SYNC2:
            if byte == PROTO_SYNC_L:
                self.state = ParseState.CMD
            elif byte == PROTO_SYNC_H:
                pass  # Stay in SYNC2
            else:
                self.state = ParseState.SYNC1

        elif self.state == ParseState.CMD:
            self.cmd = byte
            self.state = ParseState.LEN_L

        elif self.state == ParseState.LEN_L:
            self.length = byte
            self.state = ParseState.LEN_H

        elif self.state == ParseState.LEN_H:
            self.length |= byte << 8

            if self.length > self.max_payload:
                self.reset()
                return None

            self.payload = bytearray()

            if self.length == 0:
                self.state = ParseState.CRC_L
            else:
                self.state = ParseState.PAYLOAD

        elif self.state == ParseState.PAYLOAD:
            self.payload.append(byte)

            if len(self.payload) >= self.length:
                self.state = ParseState.CRC_L

        elif self.state == ParseState.CRC_L:
            self.crc = byte
            self.state = ParseState.CRC_H

        elif self.state == ParseState.CRC_H:
            self.crc |= byte << 8

            # Verify CRC
            crc_data = bytes([
                self.cmd,
                self.length & 0xFF,
                (self.length >> 8) & 0xFF
            ]) + bytes(self.payload)

            calc = calc_crc16(crc_data)

            if calc == self.crc:
                frame = Frame(cmd=self.cmd, payload=bytes(self.payload))
                self.reset()
                return frame

            self.reset()

        return None

    def parse_bytes(self, data: bytes) -> List[Frame]:
        """Parse multiple bytes, return list of complete frames"""
        frames = []
        for byte in data:
            frame = self.parse_byte(byte)
            if frame:
                frames.append(frame)
        return frames


# ============================================================================
# Telemetry Header
# ============================================================================

@dataclass
class TelemHeader:
    """Telemetry header (16 bytes)"""
    seq: int = 0
    timestamp_ms: int = 0
    voltage_mv: int = 0
    mcu_temp_c10: int = 0
    sections: int = 0
    reserved: int = 0

    FORMAT = "<IIHhHH"
    SIZE = 16

    def pack(self) -> bytes:
        return struct.pack(
            self.FORMAT,
            self.seq, self.timestamp_ms, self.voltage_mv,
            self.mcu_temp_c10, self.sections, self.reserved
        )

    @classmethod
    def unpack(cls, data: bytes) -> "TelemHeader":
        values = struct.unpack(cls.FORMAT, data[:cls.SIZE])
        return cls(*values)


# ============================================================================
# Convenience Functions
# ============================================================================

def build_ping() -> bytes:
    """Build PING frame"""
    return build_frame(Cmd.PING)


def build_pong() -> bytes:
    """Build PONG frame"""
    return build_frame(Cmd.PONG)


def build_get_caps() -> bytes:
    """Build GET_CAPS frame"""
    return build_frame(Cmd.GET_CAPS)


def build_telem_start() -> bytes:
    """Build TELEM_START frame"""
    return build_frame(Cmd.TELEM_START)


def build_telem_stop() -> bytes:
    """Build TELEM_STOP frame"""
    return build_frame(Cmd.TELEM_STOP)


def build_telem_config(sections: int, rate_ms: int) -> bytes:
    """Build TELEM_CONFIG frame"""
    payload = struct.pack("<HH", sections, rate_ms)
    return build_frame(Cmd.TELEM_CONFIG, payload)


def build_channel_set(channel_id: int, value: int) -> bytes:
    """Build CH_SET_VALUE frame"""
    payload = struct.pack("<Hi", channel_id, value)
    return build_frame(Cmd.CH_SET_VALUE, payload)


def build_channel_get(channel_id: int) -> bytes:
    """Build CH_GET_VALUE frame"""
    payload = struct.pack("<H", channel_id)
    return build_frame(Cmd.CH_GET_VALUE, payload)


def parse_channel_value(payload: bytes) -> Tuple[int, int]:
    """Parse channel value response. Returns (channel_id, value)"""
    if len(payload) < 6:
        raise ValueError("Payload too small")
    channel_id, value = struct.unpack("<Hi", payload[:6])
    return channel_id, value


def parse_error(payload: bytes) -> Tuple[Error, int]:
    """Parse error response. Returns (error_code, original_cmd)"""
    if len(payload) < 2:
        raise ValueError("Payload too small")
    return Error(payload[0]), payload[1]


# ============================================================================
# Protocol Handler Base Class
# ============================================================================

class ProtocolHandler:
    """Base class for protocol handling"""

    def __init__(self):
        self.parser = ProtocolParser()
        self._handlers = {}

    def register_handler(self, cmd: int, handler: Callable[[bytes], None]):
        """Register command handler"""
        self._handlers[cmd] = handler

    def on_data_received(self, data: bytes):
        """Process received data"""
        frames = self.parser.parse_bytes(data)
        for frame in frames:
            self._dispatch(frame)

    def _dispatch(self, frame: Frame):
        """Dispatch frame to handler"""
        handler = self._handlers.get(frame.cmd)
        if handler:
            handler(frame.payload)
        else:
            self.on_unknown_command(frame.cmd, frame.payload)

    def on_unknown_command(self, cmd: int, payload: bytes):
        """Override to handle unknown commands"""
        pass
