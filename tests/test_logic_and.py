#!/usr/bin/env python3
"""
PMU-30 Logic AND Test (MIN Protocol)

Tests Logic AND function with two inputs:
  - DIN0 (button, ch 50)
  - Number "one" (constant 1, ch 201)

Chain:
  Number "one" (ch 201) ─┬─> Logic AND (ch 200) -> Power Output (ch 100) -> LED
  DIN0 (button, ch 50) ──┘

Logic AND configuration:
  - Inputs: [DIN0 (51), Number "one" (201)]
  - Operation: input0 AND input1 = DIN0 AND 1 = DIN0

Expected behavior:
  - Button released (0) -> 0 AND 1 = 0 -> LED OFF
  - Button pressed  (1) -> 1 AND 1 = 1 -> LED ON

Same as direct linking, but demonstrates AND with multiple inputs.

Usage:
    python tests/test_logic_and.py [COM_PORT]
"""

import sys
import struct
import time
import serial
from typing import Optional, Tuple

# Use MIN protocol helpers
sys.path.insert(0, 'tests')
from protocol_helpers import (
    CMD, build_min_frame, MINFrameParser, drain_serial,
    ping, start_stream, stop_stream, upload_config, parse_telemetry
)


# Channel types (from shared/channel_types.h)
CH_TYPE_LOGIC = 0x21
CH_TYPE_NUMBER = 0x27
CH_TYPE_POWER_OUTPUT = 0x10

# Logic operations (from shared/engine/logic.h)
LOGIC_OP_AND = 0x00  # All inputs must be true

# Channel IDs
CH_DIN0 = 50         # Digital input 0 (button on PC13)
CH_NUMBER_ONE = 201  # Number channel "one" (always 1)
CH_LOGIC_AND = 200   # Logic AND channel
CH_OUTPUT_0 = 100    # Power output 0

# Hardware binding
HW_DEVICE_PROFET = 0x05
HW_DEVICE_NONE = 0x00
CH_REF_NONE = 0xFFFF

# Config sizes
CFG_MAX_INPUTS = 8
CFG_LOGIC_SIZE = 26   # CfgLogic_t
CFG_NUMBER_SIZE = 20  # CfgNumber_t


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
    Build binary config for Logic AND test.

    Config contains 3 channels:
    1. Number "one" (ch 201): value = 1, readonly = true
    2. Logic AND (ch 200): inputs = [DIN0 (51), Number (201)]
    3. Power Output (ch 100): source = Logic AND (200), hw_index = 1 (LED)

    Chain: DIN0 (51) + Number(201) -> Logic AND (200) -> Power Output (100) -> LED

    When button pressed:  1 AND 1 = 1 -> LED ON
    When button released: 0 AND 1 = 0 -> LED OFF
    """
    channels = []

    # 1. Number channel "one" (ch 201) - constant value 1
    number_config = build_number_config(value=1, readonly=True)
    number_header = build_channel_header(
        channel_id=CH_NUMBER_ONE,
        channel_type=CH_TYPE_NUMBER,
        flags=0x01,
        hw_device=HW_DEVICE_NONE,
        hw_index=0,
        source_id=CH_REF_NONE,
        default_value=1,
        name="one",
        config_size=len(number_config)
    )
    channels.append(number_header + number_config)

    # 2. Logic AND channel (ch 200)
    #    Inputs: DIN0 (ch 50), Number "one" (ch 201)
    #    Result: DIN0 AND 1 = DIN0
    logic_config = build_logic_config(
        operation=LOGIC_OP_AND,
        inputs=[CH_DIN0, CH_NUMBER_ONE],  # Two inputs
        compare_value=0,
        invert=False
    )
    logic_header = build_channel_header(
        channel_id=CH_LOGIC_AND,
        channel_type=CH_TYPE_LOGIC,
        flags=0x01,
        hw_device=HW_DEVICE_NONE,
        hw_index=0,
        source_id=CH_REF_NONE,
        default_value=0,
        name="AND",
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
        source_id=CH_LOGIC_AND,
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


class LogicAndTest:
    """Test Logic AND channel functionality."""

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
            time.sleep(3.0)  # Wait for device startup
            stop_stream(self.port)  # Ensure clean state
            return True
        except serial.SerialException as e:
            print(f"ERROR: Cannot open {self.port_name}: {e}")
            return False

    def disconnect(self):
        if self.port and self.port.is_open:
            stop_stream(self.port)
            self.port.close()

    def test_ping(self) -> bool:
        print("\n[1] Testing device connection...")
        result = ping(self.port, timeout=2.0)
        if result:
            print("    [OK] Device responding to PING")
            return True
        print("    [FAIL] No response")
        return False

    def upload_test_config(self, config: bytes) -> bool:
        print("\n[2] Uploading Logic AND config...")
        print(f"    Config size: {len(config)} bytes")
        print(f"    Channels: Number(one=1), Logic AND, Power Output")
        print(f"    Logic: DIN0 AND one = DIN0 AND 1")

        success, channels_loaded = upload_config(self.port, config)

        if success:
            print(f"    [OK] Config uploaded, channels loaded: {channels_loaded}")
            return channels_loaded >= 3  # Number + Logic + Output
        print(f"    [FAIL] Upload failed")
        return False

    def read_telemetry_packet(self, timeout: float = 0.5):
        """Read a single telemetry packet."""
        parser = MINFrameParser()
        start = time.time()

        while time.time() - start < timeout:
            chunk = self.port.read(256)
            if chunk:
                frames = parser.feed(chunk)
                for cmd, payload, seq, _ in frames:
                    if cmd == CMD.DATA:
                        pkt = parse_telemetry(payload)
                        return pkt.output_states, pkt.digital_inputs
        return None, None

    def monitor_logic_and(self, duration: float = 15.0):
        """
        Monitor Logic AND: DIN0 AND 1

        Expected:
        - Button released (0) -> 0 AND 1 = 0 -> LED OFF
        - Button pressed  (1) -> 1 AND 1 = 1 -> LED ON
        """
        print("\n[3] Monitoring Logic AND chain...")
        print(f"    Duration: {duration}s")
        print("    Chain: DIN0 + Number(1) -> Logic AND -> Power Output -> LED")
        print()
        print("    Logic: DIN0 AND 1 = DIN0")
        print("    - Button RELEASED (0 AND 1 = 0) -> LED OFF")
        print("    - Button PRESSED  (1 AND 1 = 1) -> LED ON")
        print()

        start_stream(self.port, rate_hz=50)

        packets = 0
        matches = 0
        mismatches = 0
        last_button = None
        start = time.time()

        try:
            while time.time() - start < duration:
                outputs, din_mask = self.read_telemetry_packet(timeout=0.1)

                if outputs is not None:
                    packets += 1

                    # DIN0 is bit 0
                    button_pressed = (din_mask & 1) != 0
                    output_on = (outputs[1] > 0)

                    # Logic: DIN0 AND 1 = DIN0
                    expected_output = button_pressed

                    if output_on == expected_output:
                        matches += 1
                    else:
                        mismatches += 1

                    if last_button is not None and button_pressed != last_button:
                        state = "PRESSED" if button_pressed else "released"
                        out_state = "ON" if output_on else "OFF"
                        logic_result = "1 AND 1=1" if button_pressed else "0 AND 1=0"
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
            stop_stream(self.port)

        print(f"\n    Results:")
        print(f"    - Total packets: {packets}")
        print(f"    - Matches: {matches}")
        print(f"    - Mismatches: {mismatches}")

        match_rate = (100 * matches / packets) if packets > 0 else 0
        print(f"    - Match rate: {match_rate:.1f}%")

        if match_rate >= 95:
            print("    [OK] Logic AND (DIN0 AND 1) working correctly!")
            return True
        print("    [FAIL] Logic AND not working as expected")
        return False

    def run(self) -> int:
        print("=" * 60)
        print("PMU-30 Logic AND Test (MIN Protocol)")
        print("=" * 60)
        print(f"Port: {self.port_name}")
        print("\nTest: DIN0 + Number(1) -> Logic AND -> Power Output -> LED")
        print("Logic: DIN0 AND 1 = DIN0")
        print("\nExpected: LED ON when pressed, LED OFF when released")

        if not self.connect():
            return 1

        try:
            if not self.test_ping():
                return 1

            test_config = build_test_config()
            if not self.upload_test_config(test_config):
                return 1

            if not self.monitor_logic_and(duration=12.0):
                return 1

            print("\n" + "=" * 60)
            print("ALL TESTS PASSED - Logic AND (DIN0 AND 1) working!")
            print("=" * 60)
            return 0

        finally:
            self.disconnect()


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM11"
    tester = LogicAndTest(port)
    return tester.run()


if __name__ == "__main__":
    sys.exit(main())
