"""
PMU-30 Protocol Helpers for Hardware Tests

Provides protocol utilities for communicating with real hardware.
Updated for protocol v2 with SeqID support.

Frame Format v2:
┌──────┬────────┬───────┬───────┬─────────────┬───────┐
│ 0xAA │ Length │ SeqID │ MsgID │   Payload   │ CRC16 │
│ 1B   │ 2B LE  │ 2B LE │ 1B    │ Variable    │ 2B LE │
└──────┴────────┴───────┴───────┴─────────────┴───────┘
"""

import struct
import time
import serial
from typing import Optional, Tuple, List
from dataclasses import dataclass
from enum import IntEnum


# ============================================================================
# Protocol Constants
# ============================================================================

FRAME_START = 0xAA
FRAME_HEADER_SIZE = 6  # START(1) + LENGTH(2) + SEQID(2) + TYPE(1)
FRAME_CRC_SIZE = 2

# SeqID special values
SEQ_ID_BROADCAST = 0x0000
_seq_id_counter = 1


class CMD(IntEnum):
    """Protocol command IDs"""
    # Basic commands
    PING = 0x01
    PONG = 0x02
    GET_INFO = 0x10
    INFO_RESP = 0x11

    # Configuration
    GET_CONFIG = 0x20
    CONFIG_DATA = 0x21
    LOAD_CONFIG = 0x22
    CONFIG_ACK = 0x23
    SAVE_CONFIG = 0x24
    FLASH_ACK = 0x25
    CLEAR_CONFIG = 0x26
    CLEAR_CONFIG_ACK = 0x27

    # Telemetry
    START_STREAM = 0x30
    STOP_STREAM = 0x31
    DATA = 0x32

    # Channel control
    SET_OUTPUT = 0x40
    OUTPUT_ACK = 0x41
    GET_CHANNEL = 0x43
    CHANNEL_DATA = 0x44
    GET_OUTPUTS = 0x46
    GET_INPUTS = 0x47

    # Binary config
    LOAD_BINARY_CONFIG = 0x68
    BINARY_CONFIG_ACK = 0x69

    # Response codes
    ACK = 0xE0
    NACK = 0xE1
    ERROR = 0x50


# ============================================================================
# Protocol Utilities
# ============================================================================

def get_next_seq_id() -> int:
    """Get next sequence ID for request-response correlation."""
    global _seq_id_counter
    seq_id = _seq_id_counter
    _seq_id_counter = (_seq_id_counter % 0xFFFE) + 1
    return seq_id


def crc16(data: bytes) -> int:
    """Calculate CRC16-CCITT checksum."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc


def build_frame(cmd: int, payload: bytes = b'', seq_id: int = None) -> bytes:
    """
    Build protocol frame v2 with SeqID.

    Frame format: [0xAA][Length:2B][SeqID:2B][MsgID:1B][Payload][CRC16:2B]

    Args:
        cmd: Command/message type
        payload: Payload data
        seq_id: Optional SeqID (auto-assigned if None)

    Returns:
        Complete frame bytes
    """
    if seq_id is None:
        seq_id = get_next_seq_id()

    # Header: START(1) + LENGTH(2) + SEQID(2) + TYPE(1)
    header = struct.pack('<BHHB', FRAME_START, len(payload), seq_id, cmd)
    # CRC over LENGTH+SEQID+TYPE+PAYLOAD (excludes start byte)
    crc = crc16(header[1:] + payload)
    return header + payload + struct.pack('<H', crc)


def parse_frames(data: bytes) -> List[Tuple[int, bytes, int]]:
    """
    Parse frames from data buffer.

    Returns:
        List of (cmd, payload, seq_id) tuples
    """
    frames = []
    while len(data) >= FRAME_HEADER_SIZE:
        # Find start byte
        if data[0] != FRAME_START:
            data = data[1:]
            continue

        # Parse header
        if len(data) < FRAME_HEADER_SIZE:
            break

        length = struct.unpack('<H', data[1:3])[0]
        seq_id = struct.unpack('<H', data[3:5])[0]
        cmd = data[5]

        # Check if we have complete frame
        total_len = FRAME_HEADER_SIZE + length + FRAME_CRC_SIZE
        if len(data) < total_len:
            break

        # Extract payload
        payload = data[FRAME_HEADER_SIZE:FRAME_HEADER_SIZE + length]
        frames.append((cmd, payload, seq_id))
        data = data[total_len:]

    return frames


def read_frame(ser: serial.Serial, timeout: float = 1.0) -> Tuple[Optional[int], Optional[bytes], Optional[int]]:
    """
    Read a single frame from serial port.

    Returns:
        (cmd, payload, seq_id) or (None, None, None) on timeout
    """
    data = b''
    start = time.time()

    while time.time() - start < timeout:
        chunk = ser.read(ser.in_waiting or 1)
        if chunk:
            data += chunk
            frames = parse_frames(data)
            if frames:
                return frames[0]
        time.sleep(0.01)

    return None, None, None


def transact(ser: serial.Serial, cmd: int, payload: bytes = b'',
             timeout: float = 3.0, expected_cmd: int = None,
             debug: bool = False) -> List[Tuple[int, bytes, int]]:
    """
    Send command and collect response frames.

    Args:
        ser: Serial port
        cmd: Command to send
        payload: Payload data
        timeout: Read timeout
        expected_cmd: If specified, wait for this response command
        debug: If True, print debug info

    Returns:
        List of (cmd, payload, seq_id) tuples
    """
    ser.reset_input_buffer()
    frame = build_frame(cmd, payload)
    if debug:
        print(f"  [TRANSACT] Sending CMD=0x{cmd:02X}, len={len(payload)}")
        print(f"  [TRANSACT] Frame: {frame[:20].hex()}{'...' if len(frame) > 20 else ''}")
    ser.write(frame)
    time.sleep(0.2)  # Give device time to process and respond

    data = b''
    start = time.time()
    no_data_count = 0
    while time.time() - start < timeout:
        chunk = ser.read(4096)
        if chunk:
            data += chunk
            no_data_count = 0
            if debug:
                print(f"  [TRANSACT] Read {len(chunk)} bytes, total {len(data)}")
        else:
            no_data_count += 1
            # Wait for 3 consecutive empty reads before parsing
            if no_data_count >= 3 and data:
                frames = parse_frames(data)
                if expected_cmd is None:
                    return frames
                if any(c == expected_cmd for c, p, s in frames):
                    return frames
        time.sleep(0.05)

    if debug and not data:
        print(f"  [TRANSACT] Timeout - no data received in {timeout}s")
    elif debug:
        print(f"  [TRANSACT] Timeout with {len(data)} bytes")

    return parse_frames(data)


def stop_stream(ser: serial.Serial):
    """Stop telemetry stream and wait for dead period."""
    ser.write(build_frame(CMD.STOP_STREAM))
    time.sleep(3.0)  # Dead period after STOP_STREAM (firmware needs ~2.5s)
    ser.reset_input_buffer()
    time.sleep(0.1)  # Small delay before next command


def start_stream(ser: serial.Serial, rate_hz: int = 10):
    """Start telemetry stream."""
    # Stream config: rate_hz as uint16
    payload = struct.pack('<H', rate_hz)
    ser.write(build_frame(CMD.START_STREAM, payload))
    time.sleep(0.1)


def clear_config(ser: serial.Serial) -> bool:
    """Clear device config. Returns True on success.

    Note: Assumes stream is already stopped.
    """
    frames = transact(ser, CMD.CLEAR_CONFIG, expected_cmd=CMD.CLEAR_CONFIG_ACK)
    for cmd, payload, seq_id in frames:
        if cmd == CMD.CLEAR_CONFIG_ACK and len(payload) >= 1:
            return payload[0] == 1
    return False


def upload_config(ser: serial.Serial, config_data: bytes) -> Tuple[bool, int]:
    """
    Upload binary config to device.

    Args:
        ser: Serial port
        config_data: Binary config data (.pmu30 file contents)

    Returns:
        (success, channels_loaded)
    """
    # Add chunk header: chunk_idx=0, total_chunks=1
    chunked = struct.pack('<HH', 0, 1) + config_data
    frames = transact(ser, CMD.LOAD_BINARY_CONFIG, chunked, timeout=5.0,
                      expected_cmd=CMD.BINARY_CONFIG_ACK)

    # Give device time to process config after upload
    time.sleep(0.5)

    for cmd, payload, seq_id in frames:
        if cmd == CMD.BINARY_CONFIG_ACK and len(payload) >= 2:
            success = payload[0] == 1
            channels = struct.unpack('<H', payload[2:4])[0] if len(payload) >= 4 else 0
            return success, channels

    return False, 0


def read_config(ser: serial.Serial, debug: bool = False) -> Optional[bytes]:
    """Read config from device. Returns config data or None.

    Args:
        ser: Serial port
        debug: If True, print debug info
    """
    if debug:
        print(f"  [DEBUG] Sending GET_CONFIG (0x{CMD.GET_CONFIG:02X})")

    frames = transact(ser, CMD.GET_CONFIG, timeout=5.0,
                     expected_cmd=CMD.CONFIG_DATA, debug=debug)

    if debug:
        print(f"  [DEBUG] Received {len(frames)} frames")
        for cmd, payload, seq_id in frames:
            print(f"    CMD=0x{cmd:02X}, len={len(payload)}, seq={seq_id}")

    for cmd, payload, seq_id in frames:
        if cmd == CMD.CONFIG_DATA and len(payload) >= 4:
            # Skip chunk header (4 bytes)
            return payload[4:]

    return None


def save_to_flash(ser: serial.Serial) -> bool:
    """Save config to flash. Returns True on success.

    Note: Assumes stream is already stopped.
    """
    frames = transact(ser, CMD.SAVE_CONFIG, timeout=5.0, expected_cmd=CMD.FLASH_ACK)

    for cmd, payload, seq_id in frames:
        if cmd == CMD.FLASH_ACK and len(payload) >= 1:
            return payload[0] == 1

    return False


def ping(ser: serial.Serial, timeout: float = 1.0) -> bool:
    """Send PING and wait for PONG. Returns True if response received."""
    ser.reset_input_buffer()
    ser.write(build_frame(CMD.PING))

    cmd, payload, seq_id = read_frame(ser, timeout)
    return cmd == CMD.PONG


# ============================================================================
# Telemetry Parsing
# ============================================================================

@dataclass
class TelemetryPacket:
    """Parsed telemetry packet for Nucleo-F446RE."""
    stream_counter: int = 0
    timestamp_ms: int = 0
    output_states: List[int] = None  # 30 outputs
    adc_values: List[int] = None     # 20 ADC values
    digital_inputs: int = 0          # Bitmask
    uptime_sec: int = 0
    ram_used: int = 0
    flash_used: int = 0
    channel_count: int = 0
    voltage_mv: int = 0
    current_ma: int = 0
    mcu_temp_c: int = 0
    board_temp_c: int = 0
    fault_status: int = 0
    fault_flags: int = 0
    virtual_channels: dict = None  # {channel_id: value}

    def __post_init__(self):
        if self.output_states is None:
            self.output_states = [0] * 30
        if self.adc_values is None:
            self.adc_values = [0] * 20
        if self.virtual_channels is None:
            self.virtual_channels = {}


def parse_telemetry(payload: bytes) -> TelemetryPacket:
    """
    Parse Nucleo-F446RE telemetry packet.

    Format (see CLAUDE.md):
    - 0-3: stream_counter (4B)
    - 4-7: timestamp_ms (4B)
    - 8-37: output_states (30B)
    - 38-77: adc_values (40B = 20 x 2B)
    - 78: digital_inputs (1B bitmask)
    - 79-93: system info
    - 94-103: voltage, current, temps, faults
    - 104+: virtual channels
    """
    if len(payload) < 104:
        return TelemetryPacket()

    pkt = TelemetryPacket()
    pkt.stream_counter = struct.unpack('<I', payload[0:4])[0]
    pkt.timestamp_ms = struct.unpack('<I', payload[4:8])[0]
    pkt.output_states = list(payload[8:38])
    pkt.adc_values = list(struct.unpack('<20H', payload[38:78]))
    pkt.digital_inputs = payload[78]

    # System info
    pkt.uptime_sec = struct.unpack('<I', payload[79:83])[0]
    pkt.ram_used = struct.unpack('<I', payload[83:87])[0]
    pkt.flash_used = struct.unpack('<I', payload[87:91])[0]
    pkt.channel_count = struct.unpack('<H', payload[91:93])[0]

    # Status
    pkt.voltage_mv = struct.unpack('<H', payload[94:96])[0]
    pkt.current_ma = struct.unpack('<H', payload[96:98])[0]
    pkt.mcu_temp_c = struct.unpack('<h', payload[98:100])[0]
    pkt.board_temp_c = struct.unpack('<h', payload[100:102])[0]
    pkt.fault_status = payload[102]
    pkt.fault_flags = payload[103]

    # Virtual channels
    if len(payload) >= 106:
        virtual_count = struct.unpack('<H', payload[104:106])[0]
        offset = 106
        for _ in range(virtual_count):
            if offset + 6 > len(payload):
                break
            ch_id = struct.unpack('<H', payload[offset:offset+2])[0]
            value = struct.unpack('<i', payload[offset+2:offset+6])[0]
            pkt.virtual_channels[ch_id] = value
            offset += 6

    return pkt


def wait_for_telemetry(ser: serial.Serial, timeout: float = 3.0) -> Optional[TelemetryPacket]:
    """Wait for and return a telemetry packet."""
    data = b''
    start = time.time()

    while time.time() - start < timeout:
        chunk = ser.read(4096)
        if chunk:
            data += chunk
            frames = parse_frames(data)
            for cmd, payload, seq_id in frames:
                if cmd == CMD.DATA:
                    return parse_telemetry(payload)
        time.sleep(0.05)

    return None


# ============================================================================
# Config Parsing
# ============================================================================

def parse_channels(config_data: bytes) -> List[dict]:
    """Parse channels from binary config data."""
    channels = []
    if len(config_data) < 2:
        return channels

    count = struct.unpack('<H', config_data[0:2])[0]
    pos = 2

    for i in range(count):
        if pos + 14 > len(config_data):
            break

        ch_id = struct.unpack('<H', config_data[pos:pos+2])[0]
        ch_type = config_data[pos+2]
        flags = config_data[pos+3]
        hw_dev = config_data[pos+4]
        hw_idx = config_data[pos+5]
        src = struct.unpack('<H', config_data[pos+6:pos+8])[0]
        default = struct.unpack('<i', config_data[pos+8:pos+12])[0]
        name_len = config_data[pos+12]
        cfg_size = config_data[pos+13]
        name = config_data[pos+14:pos+14+name_len].decode('utf-8', errors='replace')
        cfg_bytes = config_data[pos+14+name_len:pos+14+name_len+cfg_size]

        channels.append({
            'id': ch_id,
            'type': ch_type,
            'flags': flags,
            'hw_dev': hw_dev,
            'hw_idx': hw_idx,
            'source': src,
            'default': default,
            'name': name,
            'config': cfg_bytes.hex()
        })

        pos += 14 + name_len + cfg_size

    return channels
