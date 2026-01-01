#!/usr/bin/env python3
"""
PMU-30 Logic NOT Test

Tests channel linking with Logic NOT function:
  DIN0 (button, ch 50) -> Logic NOT (ch 200) -> Power Output (ch 100) -> LED

Expected behavior:
  - Button released (0) -> NOT(0) = 1 -> Output ON  -> LED ON
  - Button pressed  (1) -> NOT(1) = 0 -> Output OFF -> LED OFF

This is the INVERSE of test_channel_linking.py.

Usage:
    python tests/test_logic_not.py [COM_PORT]
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
LOGIC_OP_NOT = 0x05

# Channel IDs
CH_DIN0 = 50        # Digital input 0 (button)
CH_LOGIC_NOT = 200  # Logic NOT channel
CH_OUTPUT_0 = 100   # Power output 0

# Hardware binding
HW_DEVICE_PROFET = 0x05
HW_DEVICE_NONE = 0x00
CH_REF_NONE = 0xFFFF

# Config sizes
CFG_MAX_INPUTS = 8
CFG_LOGIC_SIZE = 26      # CfgLogic_t
CFG_POWER_OUTPUT_SIZE = 12  # CfgPowerOutput_t


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
    flags: int = 0x01,  # ENABLED
    hw_device: int = 0,
    hw_index: int = 0,
    source_id: int = CH_REF_NONE,
    default_value: int = 0,
    name: str = "",
    config_size: int = 0
) -> bytes:
    """
    Build CfgChannelHeader_t (14 bytes) + name.

    Format:
        uint16_t id
        uint8_t  type
        uint8_t  flags
        uint8_t  hw_device
        uint8_t  hw_index
        uint16_t source_id
        int32_t  default_value
        uint8_t  name_len
        uint8_t  config_size
        [name bytes]
    """
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

    # Pad inputs to 8 elements
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
    """
    Build CfgPowerOutput_t (12 bytes).

    Format:
        uint16_t current_limit_ma
        uint16_t inrush_time_ms
        uint16_t inrush_limit_ma
        uint8_t  retry_count
        uint8_t  retry_delay_s
        uint16_t pwm_frequency
        uint8_t  soft_start_ms
        uint8_t  flags
    """
    return struct.pack('<HHHBBHBB',
        5000,   # current_limit_ma = 5A
        100,    # inrush_time_ms
        10000,  # inrush_limit_ma = 10A
        3,      # retry_count
        5,      # retry_delay_s
        0,      # pwm_frequency = 0 (DC)
        0,      # soft_start_ms
        0       # flags
    )


def build_test_config() -> bytes:
    """
    Build binary config for Logic NOT test.

    Config contains 2 channels:
    1. Logic NOT (ch 200): input=DIN0(50), output=NOT(input)
    2. Power Output (ch 100): source=Logic NOT (200), hw_index=1 (LED)

    Chain: DIN0 (50) -> Logic NOT (200) -> Power Output (100) -> LED
    """
    channels = []

    # 1. Logic NOT channel (ch 200)
    #    Input: DIN0 (ch 50)
    #    Output: NOT(input) - 1 when button released, 0 when pressed
    logic_config = build_logic_config(
        operation=LOGIC_OP_NOT,
        inputs=[CH_DIN0],  # Input from button
        compare_value=0,
        invert=False
    )
    logic_header = build_channel_header(
        channel_id=CH_LOGIC_NOT,
        channel_type=CH_TYPE_LOGIC,
        flags=0x01,  # ENABLED
        hw_device=HW_DEVICE_NONE,
        hw_index=0,
        source_id=CH_REF_NONE,  # Logic reads inputs[] array, not source_id
        default_value=0,
        name="NOT",
        config_size=len(logic_config)
    )
    channels.append(logic_header + logic_config)

    # 2. Power Output (ch 100)
    #    Source: Logic NOT (ch 200)
    #    Hardware: output 1 (LED on PA5)
    output_config = build_power_output_config()
    output_header = build_channel_header(
        channel_id=CH_OUTPUT_0,
        channel_type=CH_TYPE_POWER_OUTPUT,
        flags=0x01,  # ENABLED
        hw_device=HW_DEVICE_PROFET,
        hw_index=1,  # Output 1 (LED on PA5)
        source_id=CH_LOGIC_NOT,  # Linked to Logic NOT output
        default_value=0,
        name="LED",
        config_size=len(output_config)
    )
    channels.append(output_header + output_config)

    # Build complete config
    channel_count = len(channels)
    config = struct.pack('<H', channel_count)
    for ch in channels:
        config += ch

    return config


class LogicNotTest:
    """Test Logic NOT channel functionality."""

    def __init__(self, port_name: str = "COM11"):
        self.port_name = port_name
        self.port: Optional[serial.Serial] = None

    def connect(self) -> bool:
        """Open serial connection."""
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
        """Close serial connection."""
        if self.port and self.port.is_open:
            self.port.close()

    def send_command(self, cmd: int, payload: bytes = b'') -> Tuple[Optional[int], Optional[bytes]]:
        """Send command and wait for response."""
        self.port.reset_input_buffer()
        frame = build_frame(cmd, payload)
        self.port.write(frame)
        self.port.flush()
        return read_frame(self.port, timeout=3.0)

    def test_ping(self) -> bool:
        """Test device connection."""
        print("\n[1] Testing device connection...")
        cmd, _ = self.send_command(CMD.PING)
        if cmd == CMD.PONG:
            print("    [OK] Device responding to PING")
            return True
        else:
            print(f"    [FAIL] Expected PONG, got: {hex(cmd) if cmd else 'None'}")
            return False

    def upload_config(self, config: bytes) -> bool:
        """Upload binary config to device."""
        print("\n[2] Uploading Logic NOT config...")
        print(f"    Config size: {len(config)} bytes")
        print(f"    Config hex: {config.hex()}")

        # Single chunk upload
        payload = struct.pack('<HH', 0, 1) + config

        cmd, resp = self.send_command(CMD.LOAD_BINARY_CONFIG, payload)

        if cmd == CMD.BINARY_CONFIG_ACK and resp:
            success = resp[0] if len(resp) > 0 else 0
            if success:
                channels_loaded = struct.unpack('<H', resp[2:4])[0] if len(resp) >= 4 else 0
                print(f"    [OK] Config uploaded, channels loaded: {channels_loaded}")
                return channels_loaded >= 2  # Need both Logic and Output
            else:
                error_code = resp[1] if len(resp) > 1 else 0
                print(f"    [FAIL] Upload failed, error code: {error_code}")
                return False
        else:
            print(f"    [FAIL] Unexpected response: cmd={hex(cmd) if cmd else 'None'}")
            return False

    def start_telemetry(self, rate_hz: int = 20):
        """Start telemetry stream."""
        payload = struct.pack('<BBBBBBH', 1, 1, 0, 0, 0, 0, rate_hz)
        self.port.reset_input_buffer()
        self.port.write(build_frame(CMD.START_STREAM, payload))
        self.port.flush()

    def stop_telemetry(self):
        """Stop telemetry stream."""
        self.port.write(build_frame(CMD.STOP_STREAM))
        self.port.flush()
        time.sleep(0.2)
        self.port.reset_input_buffer()

    def read_telemetry(self, timeout: float = 0.5):
        """Read one telemetry packet and return (outputs, digital_inputs)."""
        cmd, payload = read_frame(self.port, timeout)
        if cmd == CMD.DATA and payload and len(payload) >= 78:
            # Output states at offset 8 (30 bytes)
            outputs = list(payload[8:38])
            # Digital inputs at offset 78
            din_byte = payload[78]
            digital_inputs = [(din_byte >> i) & 1 for i in range(8)]
            return outputs, digital_inputs
        return None, None

    def monitor_logic_not(self, duration: float = 20.0):
        """
        Monitor Logic NOT: verify output is INVERTED from button state.

        Expected:
        - Button released (0) -> Logic NOT = 1 -> LED ON
        - Button pressed  (1) -> Logic NOT = 0 -> LED OFF
        """
        print("\n[3] Monitoring Logic NOT chain...")
        print(f"    Duration: {duration}s")
        print("    Chain: DIN0 (button) -> Logic NOT -> Power Output -> LED")
        print()
        print("    Expected behavior (INVERTED):")
        print("    - Button RELEASED -> LED ON")
        print("    - Button PRESSED  -> LED OFF")
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

                    # Button pressed = 1 (firmware already inverts active-low)
                    button_pressed = (dins[0] != 0)

                    # Output 1 should be INVERTED from button
                    # Button released (0) -> LED ON
                    # Button pressed  (1) -> LED OFF
                    output_on = (outputs[1] > 0)
                    expected_output = not button_pressed  # INVERTED!

                    if output_on == expected_output:
                        matches += 1
                    else:
                        mismatches += 1

                    # Log state changes
                    if last_button is not None and button_pressed != last_button:
                        state = "PRESSED" if button_pressed else "released"
                        out_state = "ON" if output_on else "OFF"
                        expected = "OFF" if button_pressed else "ON"
                        match = "OK" if output_on == expected_output else f"MISMATCH (expected {expected})"
                        print(f"    Button {state}, LED {out_state} [{match}]")

                    last_button = button_pressed

                    # Progress
                    if packets % 100 == 0:
                        elapsed = time.time() - start
                        print(f"    [{elapsed:.1f}s] Packets: {packets}, Match rate: {100*matches/packets:.1f}%")

        except KeyboardInterrupt:
            print("\n    Interrupted by user")

        finally:
            self.stop_telemetry()

        # Results
        print(f"\n    Results:")
        print(f"    - Total packets: {packets}")
        print(f"    - Matches: {matches}")
        print(f"    - Mismatches: {mismatches}")

        match_rate = (100 * matches / packets) if packets > 0 else 0
        print(f"    - Match rate: {match_rate:.1f}%")

        # Pass if > 95% match rate (allow some latency)
        if match_rate >= 95:
            print("    [OK] Logic NOT chain working correctly!")
            return True
        else:
            print("    [FAIL] Logic NOT chain not working as expected")
            return False

    def run(self) -> int:
        """Run all tests."""
        print("=" * 60)
        print("PMU-30 Logic NOT Test")
        print("=" * 60)
        print(f"Port: {self.port_name}")
        print("\nTest: DIN0 -> Logic NOT -> Power Output -> LED")
        print("Chain: Button (ch 50) -> NOT (ch 200) -> Output (ch 100)")
        print("\nExpected: LED ON when button released, LED OFF when pressed")

        if not self.connect():
            return 1

        try:
            # Step 1: Verify connection
            if not self.test_ping():
                return 1

            # Step 2: Build and upload config
            test_config = build_test_config()
            if not self.upload_config(test_config):
                return 1

            # Step 3: Monitor and verify Logic NOT chain
            if not self.monitor_logic_not(duration=15.0):
                return 1

            # Summary
            print("\n" + "=" * 60)
            print("ALL TESTS PASSED - Logic NOT chain working!")
            print("=" * 60)
            return 0

        finally:
            self.disconnect()


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM11"
    tester = LogicNotTest(port)
    return tester.run()


if __name__ == "__main__":
    sys.exit(main())
