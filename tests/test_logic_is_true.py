#!/usr/bin/env python3
"""
PMU-30 Logic IS_TRUE Test

Tests channel linking with Logic IS_TRUE function:
  DIN0 (button, ch 50) -> Logic IS_TRUE (ch 200) -> Power Output (ch 100) -> LED

IS_TRUE returns 1 when input is non-zero.

Expected behavior:
  - Button released (0) -> IS_TRUE(0) = 0 -> Output OFF -> LED OFF
  - Button pressed  (1) -> IS_TRUE(1) = 1 -> Output ON  -> LED ON

Usage:
    python tests/test_logic_is_true.py [COM_PORT]
"""

import sys
import struct
import time
import serial
from typing import Optional, Tuple


# Protocol constants
FRAME_START = 0xAA

class CMD:
    PING = 0x01
    PONG = 0x02
    START_STREAM = 0x30
    STOP_STREAM = 0x31
    DATA = 0x32
    LOAD_BINARY_CONFIG = 0x68
    BINARY_CONFIG_ACK = 0x69


# Channel types (from shared/channel_types.h)
CH_TYPE_LOGIC = 0x21
CH_TYPE_POWER_OUTPUT = 0x10

# Logic operations (from shared/engine/logic.h)
LOGIC_OP_IS_TRUE = 0x06  # Returns 1 if input != 0

# Channel IDs
CH_DIN0 = 50            # Digital input 0 (button)
CH_LOGIC_IS_TRUE = 200  # Logic IS_TRUE channel
CH_OUTPUT_0 = 100       # Power output 0

# Hardware binding
HW_DEVICE_PROFET = 0x05
HW_DEVICE_NONE = 0x00
CH_REF_NONE = 0xFFFF

# Config sizes
CFG_MAX_INPUTS = 8


def crc16_ccitt(data: bytes) -> int:
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


def build_frame(msg_type: int, payload: bytes = b'') -> bytes:
    """Build protocol frame with CRC."""
    frame_data = struct.pack('<BHB', FRAME_START, len(payload), msg_type) + payload
    crc = crc16_ccitt(frame_data[1:])
    return frame_data + struct.pack('<H', crc)


def read_frame(port: serial.Serial, timeout: float = 2.0) -> Tuple[Optional[int], Optional[bytes]]:
    """Read a complete frame from port."""
    start_time = time.time()
    buffer = b''

    while time.time() - start_time < timeout:
        if port.in_waiting > 0:
            buffer += port.read(port.in_waiting)

            start_idx = buffer.find(bytes([FRAME_START]))
            if start_idx >= 0:
                buffer = buffer[start_idx:]

                if len(buffer) >= 4:
                    length = struct.unpack('<H', buffer[1:3])[0]
                    frame_size = 4 + length + 2

                    if len(buffer) >= frame_size:
                        cmd = buffer[3]
                        payload = buffer[4:4+length]
                        return cmd, payload

        time.sleep(0.01)

    return None, None


def build_channel_header(
    channel_id: int,
    channel_type: int,
    flags: int = 0x01,
    hw_device: int = 0,
    hw_index: int = 0,
    source_id: int = CH_REF_NONE,
    default_value: int = 0,
    name: str = "",
    config_size: int = 0
) -> bytes:
    """Build CfgChannelHeader_t (14 bytes) + name."""
    name_bytes = name.encode('utf-8')[:31]
    name_len = len(name_bytes)

    header = struct.pack('<HBBBBHiBB',
        channel_id,
        channel_type,
        flags,
        hw_device,
        hw_index,
        source_id,
        default_value,
        name_len,
        config_size
    )
    return header + name_bytes


def build_logic_config(operation: int, inputs: list, compare_value: int = 0, invert: bool = False) -> bytes:
    """Build CfgLogic_t (26 bytes)."""
    input_count = len(inputs)
    inputs_padded = inputs + [0] * (CFG_MAX_INPUTS - len(inputs))

    return struct.pack('<BB8Hi?3s',
        operation,
        input_count,
        *inputs_padded,
        compare_value,
        invert,
        b'\x00\x00\x00'
    )


def build_power_output_config() -> bytes:
    """Build CfgPowerOutput_t (12 bytes)."""
    return struct.pack('<HHHBBHBB',
        5000, 100, 10000, 3, 5, 0, 0, 0
    )


def build_test_config() -> bytes:
    """
    Build binary config for Logic IS_TRUE test.

    Config contains 2 channels:
    1. Logic IS_TRUE (ch 200): input=DIN0(50), output=1 if input!=0
    2. Power Output (ch 100): source=Logic IS_TRUE (200), hw_index=1 (LED)

    Chain: DIN0 (50) -> Logic IS_TRUE (200) -> Power Output (100) -> LED
    """
    channels = []

    # 1. Logic IS_TRUE channel (ch 200)
    logic_config = build_logic_config(
        operation=LOGIC_OP_IS_TRUE,
        inputs=[CH_DIN0],
        compare_value=0,
        invert=False
    )
    logic_header = build_channel_header(
        channel_id=CH_LOGIC_IS_TRUE,
        channel_type=CH_TYPE_LOGIC,
        flags=0x01,
        hw_device=HW_DEVICE_NONE,
        hw_index=0,
        source_id=CH_REF_NONE,
        default_value=0,
        name="IS_TRUE",
        config_size=len(logic_config)
    )
    channels.append(logic_header + logic_config)

    # 2. Power Output (ch 100)
    output_config = build_power_output_config()
    output_header = build_channel_header(
        channel_id=CH_OUTPUT_0,
        channel_type=CH_TYPE_POWER_OUTPUT,
        flags=0x01,
        hw_device=HW_DEVICE_PROFET,
        hw_index=1,
        source_id=CH_LOGIC_IS_TRUE,
        default_value=0,
        name="LED",
        config_size=len(output_config)
    )
    channels.append(output_header + output_config)

    # Build complete config
    config = struct.pack('<H', len(channels))
    for ch in channels:
        config += ch

    return config


class LogicIsTrueTest:
    """Test Logic IS_TRUE channel functionality."""

    def __init__(self, port_name: str = "COM11"):
        self.port_name = port_name
        self.port: Optional[serial.Serial] = None

    def connect(self) -> bool:
        try:
            self.port = serial.Serial(
                port=self.port_name,
                baudrate=115200,
                timeout=1.0,
                write_timeout=1.0
            )
            time.sleep(0.5)
            self.port.reset_input_buffer()
            return True
        except serial.SerialException as e:
            print(f"ERROR: Cannot open {self.port_name}: {e}")
            return False

    def disconnect(self):
        if self.port and self.port.is_open:
            self.port.close()

    def send_command(self, cmd: int, payload: bytes = b'') -> Tuple[Optional[int], Optional[bytes]]:
        self.port.reset_input_buffer()
        frame = build_frame(cmd, payload)
        self.port.write(frame)
        self.port.flush()
        return read_frame(self.port, timeout=3.0)

    def test_ping(self) -> bool:
        print("\n[1] Testing device connection...")
        # Stop any running telemetry first
        self.port.write(build_frame(CMD.STOP_STREAM))
        self.port.flush()
        time.sleep(0.3)
        self.port.reset_input_buffer()

        cmd, _ = self.send_command(CMD.PING)
        if cmd == CMD.PONG:
            print("    [OK] Device responding to PING")
            return True
        print(f"    [FAIL] Expected PONG, got: {hex(cmd) if cmd else 'None'}")
        return False

    def upload_config(self, config: bytes) -> bool:
        print("\n[2] Uploading Logic IS_TRUE config...")
        print(f"    Config size: {len(config)} bytes")

        payload = struct.pack('<HH', 0, 1) + config
        cmd, resp = self.send_command(CMD.LOAD_BINARY_CONFIG, payload)

        if cmd == CMD.BINARY_CONFIG_ACK and resp and resp[0]:
            channels_loaded = struct.unpack('<H', resp[2:4])[0] if len(resp) >= 4 else 0
            print(f"    [OK] Config uploaded, channels loaded: {channels_loaded}")
            return channels_loaded >= 2
        print("    [FAIL] Upload failed")
        return False

    def start_telemetry(self, rate_hz: int = 50):
        payload = struct.pack('<BBBBBBH', 1, 1, 0, 0, 0, 0, rate_hz)
        self.port.reset_input_buffer()
        self.port.write(build_frame(CMD.START_STREAM, payload))
        self.port.flush()

    def stop_telemetry(self):
        self.port.write(build_frame(CMD.STOP_STREAM))
        self.port.flush()
        time.sleep(0.2)
        self.port.reset_input_buffer()

    def read_telemetry(self, timeout: float = 0.5):
        """
        Parse telemetry packet.

        Telemetry structure:
          0-3:   stream_counter (4 bytes)
          4-7:   timestamp (4 bytes)
          8-37:  outputs (30 bytes)
          38-77: analog inputs (40 bytes)
          78:    digital inputs (1 byte)
          79-93: reserved (15 bytes)
          94-97: voltages (4 bytes)
          98-101: temperatures (4 bytes)
          102-103: faults (2 bytes)
          104-105: virtual_count (2 bytes)
          106+:  virtual channels (6 bytes each: id + value)
        """
        cmd, payload = read_frame(self.port, timeout)
        if cmd == CMD.DATA and payload and len(payload) >= 78:
            outputs = list(payload[8:38])
            din_byte = payload[78]
            digital_inputs = [(din_byte >> i) & 1 for i in range(8)]

            # Parse virtual channels (after fixed data at offset 104)
            virtual_channels = {}
            if len(payload) >= 106:
                virtual_count = struct.unpack('<H', payload[104:106])[0]
                offset = 106
                for _ in range(virtual_count):
                    if offset + 6 <= len(payload):
                        ch_id = struct.unpack('<H', payload[offset:offset+2])[0]
                        ch_val = struct.unpack('<i', payload[offset+2:offset+6])[0]
                        virtual_channels[ch_id] = ch_val
                        offset += 6

            return outputs, digital_inputs, virtual_channels
        return None, None, None

    def monitor_is_true(self, duration: float = 15.0):
        """
        Monitor Logic IS_TRUE: output = 1 when input != 0.

        Expected:
        - Button released (0) -> IS_TRUE(0) = 0 -> LED OFF
        - Button pressed  (1) -> IS_TRUE(1) = 1 -> LED ON
        """
        print("\n[3] Monitoring Logic IS_TRUE chain...")
        print(f"    Duration: {duration}s")
        print("    Chain: DIN0 (button) -> Logic IS_TRUE -> Power Output -> LED")
        print()
        print("    Expected behavior:")
        print("    - Button RELEASED (0) -> IS_TRUE = 0 -> LED OFF")
        print("    - Button PRESSED  (1) -> IS_TRUE = 1 -> LED ON")
        print()

        self.start_telemetry(rate_hz=50)

        packets = 0
        matches = 0
        channel_matches = 0
        channel_found = 0
        last_button = None
        start = time.time()

        try:
            while time.time() - start < duration:
                outputs, dins, channels = self.read_telemetry(timeout=0.1)

                if outputs is not None and dins is not None:
                    packets += 1
                    button_pressed = (dins[0] != 0)
                    output_on = (outputs[1] > 0)
                    # IS_TRUE: returns 1 when input != 0
                    expected_output = button_pressed

                    if output_on == expected_output:
                        matches += 1

                    # Check virtual channel value in telemetry
                    if channels and CH_LOGIC_IS_TRUE in channels:
                        channel_found += 1
                        logic_value = channels[CH_LOGIC_IS_TRUE]
                        expected_logic = 1 if button_pressed else 0
                        if logic_value == expected_logic:
                            channel_matches += 1

                    if last_button is not None and button_pressed != last_button:
                        state = "PRESSED" if button_pressed else "released"
                        out_state = "ON" if output_on else "OFF"
                        logic_val = channels.get(CH_LOGIC_IS_TRUE, "N/A") if channels else "N/A"
                        print(f"    Button {state}, LED {out_state}, Logic ch={logic_val}")

                    last_button = button_pressed

                    if packets % 100 == 0:
                        elapsed = time.time() - start
                        ch_rate = (100 * channel_found / packets) if packets > 0 else 0
                        print(f"    [{elapsed:.1f}s] Packets: {packets}, Channel in telem: {ch_rate:.0f}%")

        except KeyboardInterrupt:
            print("\n    Interrupted by user")

        finally:
            self.stop_telemetry()

        print(f"\n    Results:")
        print(f"    - Total packets: {packets}")
        print(f"    - Output matches: {matches}")
        print(f"    - Channel in telemetry: {channel_found}/{packets}")
        print(f"    - Channel value matches: {channel_matches}")

        match_rate = (100 * matches / packets) if packets > 0 else 0
        channel_rate = (100 * channel_found / packets) if packets > 0 else 0
        print(f"    - Output match rate: {match_rate:.1f}%")
        print(f"    - Channel telemetry rate: {channel_rate:.1f}%")

        if match_rate >= 95 and channel_rate >= 90:
            print("    [OK] Logic IS_TRUE chain working correctly!")
            print("    [OK] Virtual channel present in telemetry!")
            return True
        elif match_rate >= 95:
            print("    [OK] Logic IS_TRUE chain working correctly!")
            print("    [WARN] Virtual channel missing from telemetry")
            return True  # Still pass, but warn
        else:
            print("    [FAIL] Logic IS_TRUE chain not working as expected")
            return False

    def run(self) -> int:
        print("=" * 60)
        print("PMU-30 Logic IS_TRUE Test")
        print("=" * 60)
        print(f"Port: {self.port_name}")
        print("\nTest: DIN0 -> Logic IS_TRUE -> Power Output -> LED")
        print("IS_TRUE returns 1 when input != 0")
        print("\nExpected: LED OFF when button released, LED ON when pressed")

        if not self.connect():
            return 1

        try:
            if not self.test_ping():
                return 1

            test_config = build_test_config()
            if not self.upload_config(test_config):
                return 1

            if not self.monitor_is_true(duration=15.0):
                return 1

            print("\n" + "=" * 60)
            print("ALL TESTS PASSED - Logic IS_TRUE working!")
            print("=" * 60)
            return 0

        finally:
            self.disconnect()


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM11"
    tester = LogicIsTrueTest(port)
    return tester.run()


if __name__ == "__main__":
    sys.exit(main())
