#!/usr/bin/env python3
"""
PMU-30 Logic OR Test

Tests Logic OR function with two inputs:
  - DIN0 (button, ch 50)
  - Number "zero" (constant 0, ch 201)

Chain:
  Number "zero" (ch 201) ─┬─> Logic OR (ch 200) -> Power Output (ch 100) -> LED
  DIN0 (button, ch 50) ──┘

Logic OR configuration:
  - Inputs: [DIN0 (50), Number "zero" (201)]
  - Operation: input0 OR input1 = DIN0 OR 0 = DIN0

Expected behavior:
  - Button released (0) -> 0 OR 0 = 0 -> LED OFF
  - Button pressed  (1) -> 1 OR 0 = 1 -> LED ON

Same as direct linking, but demonstrates OR with multiple inputs.

Usage:
    python tests/test_logic_or.py [COM_PORT]
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
CH_TYPE_NUMBER = 0x27
CH_TYPE_POWER_OUTPUT = 0x10

# Logic operations (from shared/engine/logic.h)
LOGIC_OP_OR = 0x01  # All inputs must be true

# Channel IDs
CH_DIN0 = 50         # Digital input 0 (button on PC13)
CH_NUMBER_ZERO = 201  # Number channel "zero" (always 1)
CH_LOGIC_OR = 200   # Logic OR channel
CH_OUTPUT_0 = 100    # Power output 0

# Hardware binding
HW_DEVICE_PROFET = 0x05
HW_DEVICE_NONE = 0x00
CH_REF_NONE = 0xFFFF

# Config sizes
CFG_MAX_INPUTS = 8
CFG_LOGIC_SIZE = 26   # CfgLogic_t
CFG_NUMBER_SIZE = 20  # CfgNumber_t


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


def build_number_config(value: int, readonly: bool = True) -> bytes:
    """
    Build CfgNumber_t (20 bytes).

    Format:
        int32_t  value           (4 bytes)
        int32_t  min_value       (4 bytes)
        int32_t  max_value       (4 bytes)
        int32_t  step            (4 bytes)
        uint8_t  readonly        (1 byte)
        uint8_t  save_to_flash   (1 byte)
        uint8_t  reserved[2]     (2 bytes)
    """
    return struct.pack('<iiii??2s',
        value,           # value
        0,               # min_value
        value,           # max_value
        1,               # step
        readonly,        # readonly
        False,           # save_to_flash
        b'\x00\x00'      # reserved
    )


def build_logic_config(operation: int, inputs: list, compare_value: int = 0, invert: bool = False) -> bytes:
    """
    Build CfgLogic_t (26 bytes).

    Format:
        uint8_t  operation       (1 byte)
        uint8_t  input_count     (1 byte)
        uint16_t inputs[8]       (16 bytes)
        int32_t  compare_value   (4 bytes)
        uint8_t  invert_output   (1 byte)
        uint8_t  reserved[3]     (3 bytes)
    """
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
    Build binary config for Logic OR test.

    Config contains 3 channels:
    1. Number "zero" (ch 201): value = 1, readonly = true
    2. Logic OR (ch 200): inputs = [DIN0 (50), Number (201)]
    3. Power Output (ch 100): source = Logic OR (200), hw_index = 1 (LED)

    Chain: DIN0 (50) + Number(201) -> Logic OR (200) -> Power Output (100) -> LED

    When button pressed:  1 OR 0 = 1 -> LED ON
    When button released: 0 OR 0 = 0 -> LED OFF
    """
    channels = []

    # 1. Number channel "zero" (ch 201) - constant value 1
    number_config = build_number_config(value=0, readonly=True)
    number_header = build_channel_header(
        channel_id=CH_NUMBER_ZERO,
        channel_type=CH_TYPE_NUMBER,
        flags=0x01,
        hw_device=HW_DEVICE_NONE,
        hw_index=0,
        source_id=CH_REF_NONE,
        default_value=0,
        name="zero",
        config_size=len(number_config)
    )
    channels.append(number_header + number_config)

    # 2. Logic OR channel (ch 200)
    #    Inputs: DIN0 (ch 50), Number "zero" (ch 201)
    #    Result: DIN0 OR 0 = DIN0
    logic_config = build_logic_config(
        operation=LOGIC_OP_OR,
        inputs=[CH_DIN0, CH_NUMBER_ZERO],  # Two inputs
        compare_value=0,
        invert=False
    )
    logic_header = build_channel_header(
        channel_id=CH_LOGIC_OR,
        channel_type=CH_TYPE_LOGIC,
        flags=0x01,
        hw_device=HW_DEVICE_NONE,
        hw_index=0,
        source_id=CH_REF_NONE,
        default_value=0,
        name="OR",
        config_size=len(logic_config)
    )
    channels.append(logic_header + logic_config)

    # 3. Power Output (ch 100)
    output_config = build_power_output_config()
    output_header = build_channel_header(
        channel_id=CH_OUTPUT_0,
        channel_type=CH_TYPE_POWER_OUTPUT,
        flags=0x01,
        hw_device=HW_DEVICE_PROFET,
        hw_index=1,
        source_id=CH_LOGIC_OR,
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


class LogicOrTest:
    """Test Logic OR channel functionality."""

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
        print("\n[2] Uploading Logic OR config...")
        print(f"    Config size: {len(config)} bytes")
        print(f"    Channels: Number(zero=0), Logic OR, Power Output")
        print(f"    Logic: DIN0 AND zero = DIN0 OR 0")

        payload = struct.pack('<HH', 0, 1) + config
        cmd, resp = self.send_command(CMD.LOAD_BINARY_CONFIG, payload)

        print(f"    Response: cmd={hex(cmd) if cmd else 'None'}, resp={resp.hex() if resp else 'None'}")
        if cmd == CMD.BINARY_CONFIG_ACK and resp and resp[0]:
            channels_loaded = struct.unpack('<H', resp[2:4])[0] if len(resp) >= 4 else 0
            print(f"    [OK] Config uploaded, channels loaded: {channels_loaded}")
            return channels_loaded >= 3  # Number + Logic + Output
        print(f"    [FAIL] Upload failed")
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
        cmd, payload = read_frame(self.port, timeout)
        if cmd == CMD.DATA and payload and len(payload) >= 78:
            outputs = list(payload[8:38])
            din_byte = payload[78]
            digital_inputs = [(din_byte >> i) & 1 for i in range(8)]
            return outputs, digital_inputs
        return None, None

    def monitor_logic_or(self, duration: float = 15.0):
        """
        Monitor Logic OR: DIN0 OR 0

        Expected:
        - Button released (0) -> 0 OR 0 = 0 -> LED OFF
        - Button pressed  (1) -> 1 OR 0 = 1 -> LED ON
        """
        print("\n[3] Monitoring Logic OR chain...")
        print(f"    Duration: {duration}s")
        print("    Chain: DIN0 + Number(0) -> Logic OR -> Power Output -> LED")
        print()
        print("    Logic: DIN0 OR 0 = DIN0")
        print("    - Button RELEASED (0 OR 0 = 0) -> LED OFF")
        print("    - Button PRESSED  (1 OR 0 = 1) -> LED ON")
        print()

        self.start_telemetry(rate_hz=50)

        packets = 0
        matches = 0
        mismatches = 0
        last_button = None
        start = time.time()

        try:
            while time.time() - start < duration:
                outputs, dins = self.read_telemetry(timeout=0.1)

                if outputs is not None and dins is not None:
                    packets += 1

                    # DIN0 is bit 0 (index 0)
                    button_pressed = (dins[0] != 0)
                    output_on = (outputs[1] > 0)

                    # Logic: DIN0 OR 0 = DIN0
                    # button=1 -> 1 OR 0 = 1 -> LED ON
                    # button=0 -> 0 OR 0 = 0 -> LED OFF
                    expected_output = button_pressed

                    if output_on == expected_output:
                        matches += 1
                    else:
                        mismatches += 1

                    if last_button is not None and button_pressed != last_button:
                        state = "PRESSED" if button_pressed else "released"
                        out_state = "ON" if output_on else "OFF"
                        logic_result = "1 OR 0=1" if button_pressed else "0 OR 0=0"
                        match = "OK" if output_on == expected_output else "MISMATCH"
                        print(f"    Button {state} ({logic_result}), LED {out_state} [{match}]")

                    last_button = button_pressed

                    if packets % 100 == 0:
                        elapsed = time.time() - start
                        rate = 100 * matches / packets if packets > 0 else 0
                        print(f"    [{elapsed:.1f}s] Packets: {packets}, Match rate: {rate:.1f}%")

        except KeyboardInterrupt:
            print("\n    Interrupted by user")

        finally:
            self.stop_telemetry()

        print(f"\n    Results:")
        print(f"    - Total packets: {packets}")
        print(f"    - Matches: {matches}")
        print(f"    - Mismatches: {mismatches}")

        match_rate = (100 * matches / packets) if packets > 0 else 0
        print(f"    - Match rate: {match_rate:.1f}%")

        if match_rate >= 95:
            print("    [OK] Logic OR (DIN0 OR 0) working correctly!")
            return True
        print("    [FAIL] Logic OR not working as expected")
        return False

    def run(self) -> int:
        print("=" * 60)
        print("PMU-30 Logic OR Test")
        print("=" * 60)
        print(f"Port: {self.port_name}")
        print("\nTest: DIN0 + Number(0) -> Logic OR -> Power Output -> LED")
        print("Logic: DIN0 OR 0 = DIN0")
        print("\nExpected: LED ON when pressed, LED OFF when released")

        if not self.connect():
            return 1

        try:
            if not self.test_ping():
                return 1

            test_config = build_test_config()
            if not self.upload_config(test_config):
                return 1

            if not self.monitor_logic_or(duration=12.0):
                return 1

            print("\n" + "=" * 60)
            print("ALL TESTS PASSED - Logic OR (DIN0 OR 0) working!")
            print("=" * 60)
            return 0

        finally:
            self.disconnect()


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM11"
    tester = LogicOrTest(port)
    return tester.run()


if __name__ == "__main__":
    sys.exit(main())
