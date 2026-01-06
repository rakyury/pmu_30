"""
PMU-30 Protocol using SerialTransfer (COBS + CRC8)

Simple, reliable serial protocol without complex transport layer.
Native Python implementation - no external dependencies except pyserial.

Packet Format:
[0x7E] [ID] [COBS] [LEN] [payload...] [CRC8] [0x81]
  |      |     |     |                  |      |
start   cmd  overhead len             check   stop
"""

import serial
import struct
import time
from typing import Optional, List, Tuple
from enum import IntEnum
from dataclasses import dataclass


class Command(IntEnum):
    """Protocol Command IDs (Packet ID in SerialTransfer terms)"""
    # Basic commands
    PING = 0x01
    PONG = 0x02
    RESET = 0x05

    # Configuration
    GET_CONFIG = 0x10
    CONFIG_DATA = 0x11
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

    # Device info
    GET_CAPABILITIES = 0x30
    CAPABILITIES = 0x31

    # CAN testing
    CAN_INJECT = 0x40
    CAN_INJECT_ACK = 0x41

    # Generic responses
    ACK = 0x3E
    NACK = 0x3F


@dataclass
class Packet:
    """Received packet"""
    cmd: int
    payload: bytes


# CRC8 lookup table (polynomial 0x9B)
CRC8_TABLE = [
    0x00, 0x9b, 0xad, 0x36, 0xc1, 0x5a, 0x6c, 0xf7,
    0x19, 0x82, 0xb4, 0x2f, 0xd8, 0x43, 0x75, 0xee,
    0x32, 0xa9, 0x9f, 0x04, 0xf3, 0x68, 0x5e, 0xc5,
    0x2b, 0xb0, 0x86, 0x1d, 0xea, 0x71, 0x47, 0xdc,
    0x64, 0xff, 0xc9, 0x52, 0xa5, 0x3e, 0x08, 0x93,
    0x7d, 0xe6, 0xd0, 0x4b, 0xbc, 0x27, 0x11, 0x8a,
    0x56, 0xcd, 0xfb, 0x60, 0x97, 0x0c, 0x3a, 0xa1,
    0x4f, 0xd4, 0xe2, 0x79, 0x8e, 0x15, 0x23, 0xb8,
    0xc8, 0x53, 0x65, 0xfe, 0x09, 0x92, 0xa4, 0x3f,
    0xd1, 0x4a, 0x7c, 0xe7, 0x10, 0x8b, 0xbd, 0x26,
    0xfa, 0x61, 0x57, 0xcc, 0x3b, 0xa0, 0x96, 0x0d,
    0xe3, 0x78, 0x4e, 0xd5, 0x22, 0xb9, 0x8f, 0x14,
    0xac, 0x37, 0x01, 0x9a, 0x6d, 0xf6, 0xc0, 0x5b,
    0xb5, 0x2e, 0x18, 0x83, 0x74, 0xef, 0xd9, 0x42,
    0x9e, 0x05, 0x33, 0xa8, 0x5f, 0xc4, 0xf2, 0x69,
    0x87, 0x1c, 0x2a, 0xb1, 0x46, 0xdd, 0xeb, 0x70,
    0x0b, 0x90, 0xa6, 0x3d, 0xca, 0x51, 0x67, 0xfc,
    0x12, 0x89, 0xbf, 0x24, 0xd3, 0x48, 0x7e, 0xe5,
    0x39, 0xa2, 0x94, 0x0f, 0xf8, 0x63, 0x55, 0xce,
    0x20, 0xbb, 0x8d, 0x16, 0xe1, 0x7a, 0x4c, 0xd7,
    0x6f, 0xf4, 0xc2, 0x59, 0xae, 0x35, 0x03, 0x98,
    0x76, 0xed, 0xdb, 0x40, 0xb7, 0x2c, 0x1a, 0x81,
    0x5d, 0xc6, 0xf0, 0x6b, 0x9c, 0x07, 0x31, 0xaa,
    0x44, 0xdf, 0xe9, 0x72, 0x85, 0x1e, 0x28, 0xb3,
    0xc3, 0x58, 0x6e, 0xf5, 0x02, 0x99, 0xaf, 0x34,
    0xda, 0x41, 0x77, 0xec, 0x1b, 0x80, 0xb6, 0x2d,
    0xf1, 0x6a, 0x5c, 0xc7, 0x30, 0xab, 0x9d, 0x06,
    0xe8, 0x73, 0x45, 0xde, 0x29, 0xb2, 0x84, 0x1f,
    0xa7, 0x3c, 0x0a, 0x91, 0x66, 0xfd, 0xcb, 0x50,
    0xbe, 0x25, 0x13, 0x88, 0x7f, 0xe4, 0xd2, 0x49,
    0x95, 0x0e, 0x38, 0xa3, 0x54, 0xcf, 0xf9, 0x62,
    0x8c, 0x17, 0x21, 0xba, 0x4d, 0xd6, 0xe0, 0x7b
]

START_BYTE = 0x7E
STOP_BYTE = 0x81
MAX_PAYLOAD = 254


def crc8(data: bytes) -> int:
    """Calculate CRC8 with polynomial 0x9B"""
    crc = 0
    for b in data:
        crc = CRC8_TABLE[crc ^ b]
    return crc


def find_start_byte(data: bytes, length: int) -> int:
    """Find last occurrence of START_BYTE in data"""
    for i in range(length - 1, -1, -1):
        if data[i] == START_BYTE:
            return i
    return -1


def cobs_stuff(data: bytearray) -> int:
    """Apply COBS stuffing, returns overhead byte"""
    length = len(data)
    ref_byte = find_start_byte(data, length)

    if ref_byte == -1:
        return 0xFF  # No START_BYTE in data

    # Calculate overhead (position of first START_BYTE)
    overhead = 0xFF
    for i, b in enumerate(data):
        if b == START_BYTE:
            overhead = i
            break

    # Stuff the data
    for i in range(length - 1, -1, -1):
        if data[i] == START_BYTE:
            data[i] = ref_byte - i
            ref_byte = i

    return overhead


def cobs_unstuff(data: bytearray, overhead: int):
    """Remove COBS stuffing"""
    if overhead == 0xFF or overhead >= len(data):
        return  # No stuffing needed

    test_index = overhead
    while test_index < len(data) and data[test_index] != 0:
        delta = data[test_index]
        data[test_index] = START_BYTE
        test_index += delta
        if test_index >= len(data):
            break

    if test_index < len(data):
        data[test_index] = START_BYTE


def build_packet(cmd: int, payload: bytes = b'') -> bytes:
    """
    Build SerialTransfer packet.

    Format: [0x7E] [cmd] [overhead] [len] [payload...] [crc] [0x81]
    """
    # Make mutable copy of payload
    data = bytearray(payload) if payload else bytearray([0])
    length = len(data)

    if length > MAX_PAYLOAD:
        data = data[:MAX_PAYLOAD]
        length = MAX_PAYLOAD

    # Calculate overhead before stuffing
    overhead = 0xFF
    for i, b in enumerate(data):
        if b == START_BYTE:
            overhead = i
            break

    # Apply COBS stuffing
    cobs_stuff(data)

    # Calculate CRC on stuffed data
    crc = crc8(data)

    # Build frame
    frame = bytes([START_BYTE, cmd, overhead, length]) + bytes(data) + bytes([crc, STOP_BYTE])
    return frame


class PMUSerialTransfer:
    """
    PMU-30 Serial Protocol using SerialTransfer.

    Simple synchronous API for sending commands and receiving responses.
    Native Python implementation using only pyserial.

    Usage:
        pmu = PMUSerialTransfer('COM11')
        pmu.connect()

        # Send command and wait for response
        response = pmu.transact(Command.PING, expected=Command.PONG)

        # Upload config
        success = pmu.upload_config(binary_data)

        pmu.disconnect()
    """

    # Parser states
    STATE_FIND_START = 0
    STATE_FIND_ID = 1
    STATE_FIND_OVERHEAD = 2
    STATE_FIND_LEN = 3
    STATE_FIND_PAYLOAD = 4
    STATE_FIND_CRC = 5
    STATE_FIND_STOP = 6

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 2.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._port: Optional[serial.Serial] = None

        # Parser state
        self._state = self.STATE_FIND_START
        self._rx_buffer = bytearray(MAX_PAYLOAD)
        self._payload_index = 0
        self._bytes_to_rec = 0
        self._id_byte = 0
        self._overhead_byte = 0

    def connect(self) -> bool:
        """Open serial connection"""
        try:
            # Extract just the port name if format is "COMx - description"
            port_name = self.port.split(" - ")[0] if " - " in self.port else self.port

            self._port = serial.Serial(
                port=port_name,
                baudrate=self.baudrate,
                timeout=0.1,
                write_timeout=1.0
            )
            time.sleep(0.5)  # Wait for port to stabilize
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def disconnect(self):
        """Close serial connection"""
        if self._port:
            try:
                self._port.close()
            except:
                pass
            self._port = None

    def is_connected(self) -> bool:
        """Check if connected"""
        return self._port is not None and self._port.is_open

    def _reset_parser(self):
        """Reset packet parser state"""
        self._state = self.STATE_FIND_START
        self._payload_index = 0
        self._bytes_to_rec = 0

    def _process_byte(self, byte: int) -> Optional[Packet]:
        """
        Process a received byte through parser state machine.
        Returns Packet if complete packet received, None otherwise.
        """
        if self._state == self.STATE_FIND_START:
            if byte == START_BYTE:
                self._state = self.STATE_FIND_ID
            return None

        elif self._state == self.STATE_FIND_ID:
            self._id_byte = byte
            self._state = self.STATE_FIND_OVERHEAD
            return None

        elif self._state == self.STATE_FIND_OVERHEAD:
            self._overhead_byte = byte
            self._state = self.STATE_FIND_LEN
            return None

        elif self._state == self.STATE_FIND_LEN:
            if byte <= MAX_PAYLOAD:
                self._bytes_to_rec = byte
                self._payload_index = 0
                if byte == 0:
                    # Zero-length payload - go straight to CRC
                    self._state = self.STATE_FIND_CRC
                else:
                    self._state = self.STATE_FIND_PAYLOAD
            else:
                self._reset_parser()
            return None

        elif self._state == self.STATE_FIND_PAYLOAD:
            if self._payload_index < self._bytes_to_rec:
                self._rx_buffer[self._payload_index] = byte
                self._payload_index += 1
                if self._payload_index >= self._bytes_to_rec:
                    self._state = self.STATE_FIND_CRC
            return None

        elif self._state == self.STATE_FIND_CRC:
            # Verify CRC
            calc_crc = crc8(self._rx_buffer[:self._bytes_to_rec])
            if calc_crc == byte:
                self._state = self.STATE_FIND_STOP
            else:
                self._reset_parser()
            return None

        elif self._state == self.STATE_FIND_STOP:
            self._state = self.STATE_FIND_START
            if byte == STOP_BYTE:
                # Valid packet - unstuff and return
                payload = bytearray(self._rx_buffer[:self._bytes_to_rec])
                cobs_unstuff(payload, self._overhead_byte)
                return Packet(cmd=self._id_byte, payload=bytes(payload))
            return None

        return None

    def send(self, cmd: int, payload: bytes = b'') -> bool:
        """
        Send a packet (fire-and-forget).

        Args:
            cmd: Command ID (0-255)
            payload: Payload bytes (0-254)

        Returns:
            True if sent successfully
        """
        if not self._port:
            return False

        try:
            frame = build_packet(cmd, payload)
            self._port.write(frame)
            self._port.flush()
            return True
        except Exception as e:
            print(f"Send error: {e}")
            return False

    def receive(self, timeout: float = None) -> Optional[Packet]:
        """
        Receive a single packet.

        Args:
            timeout: Max time to wait (uses default if None)

        Returns:
            Packet or None on timeout
        """
        if not self._port:
            return None

        timeout = timeout or self.timeout
        start = time.time()

        while time.time() - start < timeout:
            data = b''
            try:
                data = self._port.read(256)
                for byte in data:
                    pkt = self._process_byte(byte)
                    if pkt:
                        return pkt
            except Exception:
                pass

            if not data:
                time.sleep(0.001)

        return None

    def transact(self, cmd: int, payload: bytes = b'',
                 timeout: float = None, expected: int = None,
                 skip_telemetry: bool = True) -> List[Packet]:
        """
        Send command and collect response packets.

        Args:
            cmd: Command to send
            payload: Payload data
            timeout: Max time to wait for response
            expected: If set, return when this command received
            skip_telemetry: If True, skip DATA packets

        Returns:
            List of received packets
        """
        if not self.send(cmd, payload):
            return []

        timeout = timeout or self.timeout
        start = time.time()
        results = []

        while time.time() - start < timeout:
            pkt = self.receive(timeout=0.1)
            if pkt:
                if skip_telemetry and pkt.cmd == Command.DATA:
                    continue
                results.append(pkt)
                if expected is not None and pkt.cmd == expected:
                    return results

        return results

    # =========================================================================
    # High-level API
    # =========================================================================

    def ping(self, timeout: float = 1.0) -> bool:
        """Send PING and wait for PONG"""
        packets = self.transact(Command.PING, timeout=timeout, expected=Command.PONG)
        return any(p.cmd == Command.PONG for p in packets)

    def stop_stream(self):
        """Stop telemetry stream"""
        self.send(Command.STOP_STREAM)
        # Drain any remaining telemetry
        time.sleep(0.1)
        while self.receive(timeout=0.1):
            pass

    def start_stream(self, rate_hz: int = 10):
        """Start telemetry stream"""
        payload = struct.pack('<H', rate_hz)
        self.send(Command.START_STREAM, payload)

    def clear_config(self) -> bool:
        """Clear device configuration"""
        packets = self.transact(Command.CLEAR_CONFIG, timeout=3.0,
                                expected=Command.CLEAR_CONFIG_ACK)
        for p in packets:
            if p.cmd == Command.CLEAR_CONFIG_ACK and len(p.payload) >= 1:
                return p.payload[0] == 1
        return False

    def upload_config(self, binary_data: bytes) -> Tuple[bool, int]:
        """
        Upload binary configuration.

        Args:
            binary_data: Binary config data

        Returns:
            (success, channels_loaded)
        """
        # Add chunk header (single chunk)
        payload = struct.pack('<HH', 0, 1) + binary_data

        packets = self.transact(Command.LOAD_BINARY, payload, timeout=5.0,
                                expected=Command.BINARY_ACK)

        for p in packets:
            if p.cmd == Command.BINARY_ACK and len(p.payload) >= 2:
                success = p.payload[0] == 1
                channels = 0
                if len(p.payload) >= 4:
                    channels = struct.unpack('<H', p.payload[2:4])[0]
                return success, channels

        return False, 0

    def read_config(self) -> Optional[bytes]:
        """Read configuration from device"""
        packets = self.transact(Command.GET_CONFIG, timeout=5.0,
                                expected=Command.CONFIG_DATA)

        for p in packets:
            if p.cmd == Command.CONFIG_DATA and len(p.payload) >= 4:
                # Skip chunk header (4 bytes)
                return p.payload[4:]

        return None

    def save_to_flash(self) -> bool:
        """Save configuration to flash"""
        packets = self.transact(Command.SAVE_CONFIG, timeout=5.0,
                                expected=Command.FLASH_ACK)

        for p in packets:
            if p.cmd == Command.FLASH_ACK and len(p.payload) >= 1:
                return p.payload[0] == 1

        return False

    def set_output(self, index: int, state: bool) -> bool:
        """Set output state"""
        payload = struct.pack('<BB', index, 1 if state else 0)
        packets = self.transact(Command.SET_OUTPUT, payload, timeout=1.0,
                                expected=Command.OUTPUT_ACK)

        for p in packets:
            if p.cmd == Command.OUTPUT_ACK and len(p.payload) >= 2:
                return p.payload[1] == (1 if state else 0)

        return False

    def get_capabilities(self) -> Optional[dict]:
        """Get device capabilities"""
        packets = self.transact(Command.GET_CAPABILITIES, timeout=2.0,
                                expected=Command.CAPABILITIES)

        for p in packets:
            if p.cmd == Command.CAPABILITIES and len(p.payload) >= 9:
                caps = p.payload
                return {
                    'device_type': caps[0],
                    'version': f"{caps[1]}.{caps[2]}.{caps[3]}",
                    'outputs': caps[4],
                    'analog_inputs': caps[5],
                    'digital_inputs': caps[6],
                    'hbridges': caps[7],
                    'can_buses': caps[8]
                }

        return None


# Context manager for clean usage
class PMUConnection:
    """Context manager for PMU serial connection"""

    def __init__(self, port: str, baudrate: int = 115200):
        self.pmu = PMUSerialTransfer(port, baudrate)

    def __enter__(self) -> PMUSerialTransfer:
        if not self.pmu.connect():
            raise ConnectionError(f"Cannot connect to {self.pmu.port}")
        return self.pmu

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.pmu.disconnect()
        return False


# ============================================================================
# Standalone test
# ============================================================================

if __name__ == '__main__':
    import sys

    port = sys.argv[1] if len(sys.argv) > 1 else 'COM11'

    print(f"Testing PMU SerialTransfer protocol on {port}")

    with PMUConnection(port) as pmu:
        # Test PING
        print("\n1. PING test...")
        if pmu.ping():
            print("   OK - PONG received")
        else:
            print("   FAIL - no PONG")

        # Get capabilities
        print("\n2. Get capabilities...")
        caps = pmu.get_capabilities()
        if caps:
            print(f"   Device type: 0x{caps['device_type']:02X}")
            print(f"   Version: {caps['version']}")
            print(f"   Outputs: {caps['outputs']}, Analog: {caps['analog_inputs']}, Digital: {caps['digital_inputs']}")
        else:
            print("   Failed to get capabilities")

        # Read config
        print("\n3. Read config...")
        config = pmu.read_config()
        if config:
            if len(config) >= 2:
                count = struct.unpack('<H', config[0:2])[0]
                print(f"   OK - {count} channels on device ({len(config)} bytes)")
            else:
                print(f"   OK - {len(config)} bytes config data")
        else:
            print("   No config on device")

    print("\nDone!")
