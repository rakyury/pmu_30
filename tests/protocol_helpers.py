"""
PMU-30 Protocol Helpers for Hardware Tests (T-MIN Protocol)

Provides protocol utilities for communicating with real hardware using T-MIN protocol.
T-MIN (Transport MIN) provides reliable framing with CRC32 and automatic retransmission.

T-MIN Frame Format:
┌────────────────┬────────────┬─────┬────────┬─────────┬───────┬─────┐
│ 0xAA 0xAA 0xAA │ ID|0x80    │ Seq │ Length │ Payload │ CRC32 │ EOF │
│    3 bytes     │   1 byte   │ 1B  │  1B    │ 0-255B  │  4B   │ 1B  │
└────────────────┴────────────┴─────┴────────┴─────────┴───────┴─────┘

Key difference from simple MIN:
- Transport frames have bit 7 set in ID byte (ID | 0x80)
- Requires ACK from receiver (firmware and host must both acknowledge)
- Automatic retransmission on timeout
"""

import struct
import time
import serial
from typing import Optional, Tuple, List
from dataclasses import dataclass
from enum import IntEnum
from binascii import crc32
from pathlib import Path
import sys

# Import T-MIN transport from shared library
sys.path.insert(0, str(Path(__file__).parent.parent / "shared" / "python"))
from min_protocol import MINTransportSerial, MINFrame, MINConnectionError


# ============================================================================
# MIN Protocol Constants
# ============================================================================

class MINCMD(IntEnum):
    """MIN Protocol Command IDs (0-63 range)"""
    # Basic commands
    PING = 0x01
    PONG = 0x02
    RESET = 0x05  # Software reset (NVIC_SystemReset)

    # Configuration
    GET_CONFIG = 0x10
    CONFIG_DATA = 0x11
    LOAD_CONFIG = 0x12
    CONFIG_ACK = 0x13
    SAVE_CONFIG = 0x14
    FLASH_ACK = 0x15
    CLEAR_CONFIG = 0x16
    CLEAR_CONFIG_ACK = 0x17
    LOAD_BINARY = 0x18
    BINARY_ACK = 0x19

    # Telemetry
    START_STREAM = 0x20
    STOP_STREAM = 0x21
    DATA = 0x22

    # Channel control
    SET_OUTPUT = 0x28
    OUTPUT_ACK = 0x29

    # Device capabilities
    GET_CAPABILITIES = 0x30
    CAPABILITIES = 0x31

    # Response codes
    ACK = 0x3E
    NACK = 0x3F


# Alias for backwards compatibility
CMD = MINCMD


# MIN Protocol Constants
HEADER_BYTE = 0xAA
STUFF_BYTE = 0x55
EOF_BYTE = 0x55


# ============================================================================
# T-MIN Transport Context
# ============================================================================

class TMinContext:
    """
    T-MIN transport context manager for reliable communication.

    Wraps MINTransportSerial with a simple synchronous API for tests.
    Handles ACK/NACK automatically via poll() calls.

    Usage:
        with TMinContext('COM11') as tmin:
            tmin.send_command(CMD.PING, b'')
            frames = tmin.wait_for_response(CMD.PONG, timeout=2.0)
    """

    def __init__(self, port: str, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self._transport: Optional[MINTransportSerial] = None

    def __enter__(self):
        from logging import ERROR
        self._transport = MINTransportSerial(self.port, self.baudrate, loglevel=ERROR)

        # Wait for firmware to be ready after port open
        # ST-Link VCP and firmware initialization takes ~500-1000ms
        time.sleep(1.0)

        # Drain any stale data from previous sessions
        self._transport._serial.reset_input_buffer()

        # Send RESET to sync transport state
        self._transport.transport_reset()
        time.sleep(0.3)  # Allow firmware to process reset
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._transport:
            try:
                self._transport.close()
            except:
                pass
        return False

    def send_command(self, cmd: int, payload: bytes = b''):
        """
        Send command via T-MIN transport (reliable delivery).

        Uses queue_frame() which requires ACK from firmware.
        """
        self._transport.queue_frame(cmd, payload)

    def send_unreliable(self, cmd: int, payload: bytes = b''):
        """
        Send frame without transport (unreliable, for telemetry start/stop).

        Uses send_frame() which doesn't require ACK.
        """
        self._transport.send_frame(cmd, payload)

    def poll(self) -> List[MINFrame]:
        """
        Poll for incoming frames and handle ACKs.

        Returns list of received application frames.
        """
        return self._transport.poll()

    def wait_for_response(self, expected_cmd: int, timeout: float = 3.0,
                          skip_data: bool = True) -> List[Tuple[int, bytes, int]]:
        """
        Wait for specific response command.

        Args:
            expected_cmd: Command ID to wait for
            timeout: Maximum wait time
            skip_data: If True, skip DATA (telemetry) packets

        Returns:
            List of (cmd, payload, seq) tuples
        """
        results = []
        start = time.time()

        while time.time() - start < timeout:
            frames = self.poll()
            for frame in frames:
                if skip_data and frame.min_id == CMD.DATA:
                    continue
                results.append((frame.min_id, frame.payload, frame.seq))
                if frame.min_id == expected_cmd:
                    return results
            time.sleep(0.01)

        return results

    def collect_frames(self, timeout: float = 1.0) -> List[Tuple[int, bytes, int]]:
        """
        Collect all frames for a duration.

        Returns:
            List of (cmd, payload, seq) tuples
        """
        results = []
        start = time.time()

        while time.time() - start < timeout:
            frames = self.poll()
            for frame in frames:
                results.append((frame.min_id, frame.payload, frame.seq))
            time.sleep(0.01)

        return results


# Global T-MIN context for legacy API compatibility
_tmin_context: Optional[TMinContext] = None


def get_tmin_context(ser: serial.Serial) -> TMinContext:
    """
    Get or create T-MIN context for a serial port.

    Note: This creates a new MINTransportSerial, so the original
    serial.Serial object is not used directly. The port is reopened.
    """
    global _tmin_context
    if _tmin_context is None or _tmin_context.port != ser.port:
        if _tmin_context:
            try:
                _tmin_context._transport.close()
            except:
                pass
        # Close the pyserial object since MINTransportSerial opens its own
        port = ser.port
        baudrate = ser.baudrate
        ser.close()
        _tmin_context = TMinContext(port, baudrate)
        _tmin_context.__enter__()
    return _tmin_context


# ============================================================================
# MIN Frame Building and Parsing
# ============================================================================

def _crc32_min(data: bytes) -> int:
    """Calculate CRC32 for MIN protocol (same as binascii.crc32)."""
    return crc32(data, 0) & 0xFFFFFFFF


def build_min_frame(min_id: int, payload: bytes = b'', transport: bool = False, seq: int = 0) -> bytes:
    """
    Build a MIN protocol frame.

    Args:
        min_id: Command ID (0-63)
        payload: Payload data (0-255 bytes)
        transport: If True, use transport layer (reliable delivery)
        seq: Sequence number for transport frames

    Returns:
        Complete MIN frame bytes
    """
    if min_id > 63:
        raise ValueError(f"MIN ID must be 0-63, got {min_id}")
    if len(payload) > 255:
        raise ValueError(f"Payload too large: {len(payload)}")

    # Build header
    if transport:
        # Transport frame: ID with bit 7 set, seq byte included
        id_control = min_id | 0x80
        prolog = bytes([id_control, seq, len(payload)]) + payload
    else:
        # Non-transport frame: ID without bit 7, no seq byte
        prolog = bytes([min_id, len(payload)]) + payload

    # Calculate CRC32
    crc = crc32(prolog, 0)

    # Build raw frame (before stuffing)
    raw = prolog + struct.pack(">I", crc)  # CRC is big-endian

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
        self._frames = []

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


# Global parser instance
_parser = MINFrameParser()


def parse_frames(data: bytes) -> List[Tuple[int, bytes, int]]:
    """
    Parse MIN frames from data buffer.

    Returns:
        List of (cmd, payload, seq) tuples (seq is always 0 for non-transport)
    """
    _parser.reset()
    frames = _parser.feed(data)
    # Convert to simpler format (drop is_transport flag)
    return [(cmd, payload, seq) for cmd, payload, seq, _ in frames]


# ============================================================================
# Serial Communication
# ============================================================================

def drain_serial(ser: serial.Serial, duration_ms: int = 100):
    """
    Drain serial buffer for a fixed duration.

    This is more reliable than "read until empty" because USB serial
    buffers may have asynchronous arrivals. A time-based drain ensures
    we clear all in-flight data before sending new commands.
    """
    deadline = time.time() + (duration_ms / 1000.0)
    old_timeout = ser.timeout
    ser.timeout = 0.01
    while time.time() < deadline:
        ser.read(1024)
    ser.timeout = old_timeout
    ser.reset_input_buffer()


def read_frame(ser: serial.Serial, timeout: float = 1.0) -> Tuple[Optional[int], Optional[bytes], Optional[int]]:
    """
    Read a single MIN frame from serial port.

    Returns:
        (cmd, payload, seq) or (None, None, None) on timeout
    """
    parser = MINFrameParser()
    start = time.time()

    while time.time() - start < timeout:
        chunk = ser.read(ser.in_waiting or 1)
        if chunk:
            frames = parser.feed(chunk)
            if frames:
                cmd, payload, seq, _ = frames[0]
                return cmd, payload, seq
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
        List of (cmd, payload, seq) tuples
    """
    # Time-based drain: wait 50ms to clear any in-flight data
    # This is more reliable than read-until-empty which races with async arrivals
    drain_serial(ser, 50)

    frame = build_min_frame(cmd, payload)
    if debug:
        print(f"  [MIN] Sending CMD=0x{cmd:02X}, len={len(payload)}")
        print(f"  [MIN] Frame: {frame[:20].hex()}{'...' if len(frame) > 20 else ''}")

    ser.write(frame)
    ser.flush()

    # Small delay to allow USB VCP to buffer the response
    # Without this, partial data may arrive and cause frame parsing issues
    time.sleep(0.02)  # 20ms

    parser = MINFrameParser()
    start = time.time()
    results = []

    # Use short read timeout for responsive polling
    old_timeout = ser.timeout
    ser.timeout = 0.05  # 50ms read timeout
    try:
        while time.time() - start < timeout:
            chunk = ser.read(512)
            if chunk:
                frames = parser.feed(chunk)
                for cmd_rx, payload_rx, seq_rx, _ in frames:
                    # Skip telemetry DATA packets when looking for specific command
                    if cmd_rx == CMD.DATA and expected_cmd is not None and expected_cmd != CMD.DATA:
                        continue
                    results.append((cmd_rx, payload_rx, seq_rx))
                    if debug:
                        print(f"  [MIN] Received CMD=0x{cmd_rx:02X}, len={len(payload_rx)}")
                    if expected_cmd is not None and cmd_rx == expected_cmd:
                        return results
    finally:
        ser.timeout = old_timeout

    if debug and not results:
        print(f"  [MIN] Timeout - no data received in {timeout}s")

    return results


# ============================================================================
# High-Level API
# ============================================================================

def stop_stream(ser: serial.Serial):
    """Stop telemetry stream and wait for confirmation."""
    # Send stop command
    ser.write(build_min_frame(CMD.STOP_STREAM))
    ser.flush()

    # Wait for ACK and drain any remaining telemetry
    parser = MINFrameParser()
    got_ack = False
    deadline = time.time() + 1.0  # 1 second max wait

    while time.time() < deadline:
        old_timeout = ser.timeout
        ser.timeout = 0.1
        chunk = ser.read(1024)
        ser.timeout = old_timeout

        if chunk:
            frames = parser.feed(chunk)
            for cmd, payload, seq, _ in frames:
                if cmd == CMD.ACK:
                    got_ack = True
                # Continue draining even after ACK to clear any in-flight telemetry
        elif got_ack:
            # Got ACK and no more data - done
            break

    # Wait for USB VCP buffers to flush and drain residual data
    time.sleep(0.1)
    drain_deadline = time.time() + 0.3
    old_timeout = ser.timeout
    ser.timeout = 0.05
    while time.time() < drain_deadline:
        if not ser.read(1024):
            break
    ser.timeout = old_timeout

    # Final cleanup
    ser.reset_input_buffer()


def start_stream(ser: serial.Serial, rate_hz: int = 10):
    """Start telemetry stream."""
    payload = struct.pack('<H', rate_hz)
    ser.write(build_min_frame(CMD.START_STREAM, payload))
    time.sleep(0.1)


def clear_config(ser: serial.Serial) -> bool:
    """Clear device config. Returns True on success."""
    frames = transact(ser, CMD.CLEAR_CONFIG, expected_cmd=CMD.CLEAR_CONFIG_ACK)
    for cmd, payload, seq in frames:
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
    frames = transact(ser, CMD.LOAD_BINARY, chunked, timeout=5.0,
                      expected_cmd=CMD.BINARY_ACK)

    time.sleep(0.3)

    for cmd, payload, seq in frames:
        if cmd == CMD.BINARY_ACK and len(payload) >= 2:
            success = payload[0] == 1
            channels = struct.unpack('<H', payload[2:4])[0] if len(payload) >= 4 else 0
            return success, channels

    return False, 0


def read_config(ser: serial.Serial, debug: bool = False) -> Optional[bytes]:
    """Read config from device. Returns config data or None."""
    if debug:
        print(f"  [DEBUG] Sending GET_CONFIG (0x{CMD.GET_CONFIG:02X})")

    frames = transact(ser, CMD.GET_CONFIG, timeout=5.0,
                     expected_cmd=CMD.CONFIG_DATA, debug=debug)

    for cmd, payload, seq in frames:
        if cmd == CMD.CONFIG_DATA and len(payload) >= 4:
            # Skip chunk header (4 bytes)
            return payload[4:]

    return None


def save_to_flash(ser: serial.Serial) -> bool:
    """Save config to flash. Returns True on success."""
    frames = transact(ser, CMD.SAVE_CONFIG, timeout=5.0, expected_cmd=CMD.FLASH_ACK)

    for cmd, payload, seq in frames:
        if cmd == CMD.FLASH_ACK and len(payload) >= 1:
            return payload[0] == 1

    return False


def firmware_reset(ser: serial.Serial, timeout: float = 3.0) -> bool:
    """
    Send RESET command to trigger NVIC_SystemReset().

    Returns True if firmware comes back online after reset.
    """
    # Send reset command
    ser.write(build_min_frame(CMD.RESET))
    ser.flush()

    # Close and reopen port to reset USB CDC buffers
    port = ser.port
    baudrate = ser.baudrate
    ser.close()

    # Wait for firmware to reset and reinitialize
    time.sleep(2.5)

    # Reopen port
    ser.port = port
    ser.baudrate = baudrate
    ser.timeout = 0.5
    ser.open()

    # Drain any boot messages
    drain_serial(ser, 500)

    # Verify firmware is online with ping
    return ping(ser, timeout=timeout)


def ping(ser: serial.Serial, timeout: float = 1.0) -> bool:
    """Send PING and wait for PONG. Returns True if response received."""
    # Drain any residual data first (50ms time-based drain)
    drain_serial(ser, 50)

    # Send PING
    ser.write(build_min_frame(CMD.PING))
    ser.flush()

    # Small delay to allow USB VCP to buffer the response
    time.sleep(0.02)  # 20ms

    # Wait for PONG with short read timeouts to allow quick loop iteration
    parser = MINFrameParser()
    start = time.time()
    old_timeout = ser.timeout
    ser.timeout = 0.05  # 50ms read timeout for responsive polling
    try:
        while time.time() - start < timeout:
            chunk = ser.read(256)
            if chunk:
                frames = parser.feed(chunk)
                for cmd, payload, seq, is_transport in frames:
                    if cmd == CMD.PONG:
                        return True
    finally:
        ser.timeout = old_timeout
    return False


@dataclass
class DeviceCapabilities:
    """Device capabilities from firmware GET_CAPABILITIES response."""
    device_type: int = 0        # 0=PMU-30, 1=PMU-30 Pro, 2=PMU-16 Mini
    fw_version: Tuple[int, int, int] = (0, 0, 0)  # (major, minor, patch)
    output_count: int = 30
    analog_input_count: int = 10
    digital_input_count: int = 8
    hbridge_count: int = 2
    can_bus_count: int = 2

    @property
    def fw_version_str(self) -> str:
        return f"{self.fw_version[0]}.{self.fw_version[1]}.{self.fw_version[2]}"

    @property
    def device_name(self) -> str:
        names = {0: "PMU-30", 1: "PMU-30 Pro", 2: "PMU-16 Mini", 0x10: "Nucleo-F446RE"}
        return names.get(self.device_type, f"Unknown({self.device_type})")


def get_capabilities(ser: serial.Serial, timeout: float = 1.0) -> Optional[DeviceCapabilities]:
    """
    Request device capabilities.

    Returns DeviceCapabilities or None if no response.
    """
    drain_serial(ser, 50)

    # Send GET_CAPABILITIES
    ser.write(build_min_frame(CMD.GET_CAPABILITIES))
    ser.flush()
    time.sleep(0.02)  # USB VCP delay

    # Wait for CAPABILITIES response
    parser = MINFrameParser()
    start = time.time()
    old_timeout = ser.timeout
    ser.timeout = 0.05
    try:
        while time.time() - start < timeout:
            chunk = ser.read(256)
            if chunk:
                frames = parser.feed(chunk)
                for cmd, payload, seq, is_transport in frames:
                    if cmd == CMD.CAPABILITIES and len(payload) >= 10:
                        return DeviceCapabilities(
                            device_type=payload[0],
                            fw_version=(payload[1], payload[2], payload[3]),
                            output_count=payload[4],
                            analog_input_count=payload[5],
                            digital_input_count=payload[6],
                            hbridge_count=payload[7],
                            can_bus_count=payload[8],
                        )
    finally:
        ser.timeout = old_timeout
    return None


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
    parser = MINFrameParser()
    start = time.time()

    while time.time() - start < timeout:
        chunk = ser.read(4096)
        if chunk:
            frames = parser.feed(chunk)
            for cmd, payload, seq, _ in frames:
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


# ============================================================================
# Backwards Compatibility Aliases
# ============================================================================

# These aliases allow existing tests to work without modification
build_frame = build_min_frame
get_next_seq_id = lambda: 0  # MIN doesn't use SeqID in the same way
