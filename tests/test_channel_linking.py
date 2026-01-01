#!/usr/bin/env python3
"""
PMU-30 Channel Linking Test

Tests firmware channel executor linking functionality:
1. Upload binary config with Power Output linked to Digital Input
2. Firmware should automatically set output based on input channel
3. Verify via telemetry that output follows button state

Config:
  - Digital Input DIN0 (channel 50) - button on PC13
  - Power Output (channel 100) with source_id=50, hw_index=1 (LED on PA5)

The firmware Channel Executor should automatically link:
  DIN0 (50) -> Output 1

Usage:
    python tests/test_channel_linking.py [COM_PORT]
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
CH_TYPE_DIGITAL_INPUT = 0x01
CH_TYPE_POWER_OUTPUT = 0x10

# Channel IDs
CH_DIN0 = 50        # Digital input 0 (button)
CH_OUTPUT_0 = 100   # Power output 0

# Hardware binding
HW_DEVICE_PROFET = 0x05
CH_REF_NONE = 0xFFFF


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
    Build binary config for button-to-output test.

    Config contains 1 channel:
    - Power Output (ch 100) linked to DIN0 (ch 50), hw_index=1

    Note: Digital inputs are handled by firmware automatically
    and registered in channel system at startup.
    """
    channels = []

    # Power Output: channel 100, source=50 (DIN0), hw_index=1 (LED)
    config_data = build_power_output_config()
    header = build_channel_header(
        channel_id=CH_OUTPUT_0,
        channel_type=CH_TYPE_POWER_OUTPUT,
        flags=0x01,  # ENABLED
        hw_device=HW_DEVICE_PROFET,
        hw_index=1,  # Output 1 (LED on PA5)
        source_id=CH_DIN0,  # Linked to DIN0 (button)
        default_value=0,
        name="LED",
        config_size=len(config_data)
    )
    channels.append(header + config_data)

    # Build complete config
    channel_count = len(channels)
    config = struct.pack('<H', channel_count)
    for ch in channels:
        config += ch

    return config


class ChannelLinkingTest:
    """Test channel linking functionality."""

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
        print("\n[2] Uploading channel linking config...")
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
                return True
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

    def monitor_linking(self, duration: float = 30.0):
        """
        Monitor channel linking: verify output follows button state.
        """
        print("\n[3] Monitoring channel linking...")
        print(f"    Duration: {duration}s")
        print("    Press button (PC13) to toggle LED (PA5)")
        print("    The firmware should automatically link DIN0 -> Output 1")
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

                    # Output 1 should follow button
                    output_on = (outputs[1] > 0)

                    if button_pressed == output_on:
                        matches += 1
                    else:
                        mismatches += 1

                    # Log state changes
                    if last_button is not None and button_pressed != last_button:
                        state = "PRESSED" if button_pressed else "released"
                        out_state = "ON" if output_on else "OFF"
                        match = "OK" if button_pressed == output_on else "MISMATCH!"
                        print(f"    Button {state}, Output {out_state} [{match}]")

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
            print("    [OK] Channel linking working correctly!")
            return True
        else:
            print("    [FAIL] Channel linking not working as expected")
            return False

    def run(self) -> int:
        """Run all tests."""
        print("=" * 60)
        print("PMU-30 Channel Linking Test")
        print("=" * 60)
        print(f"Port: {self.port_name}")
        print("\nTest: Digital Input (button) -> Power Output (LED)")
        print("Config: DIN0 (ch 50) -> Output 1 (ch 100, hw_index=1)")

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

            # Step 3: Monitor and verify linking
            if not self.monitor_linking(duration=20.0):
                return 1

            # Summary
            print("\n" + "=" * 60)
            print("ALL TESTS PASSED - Channel linking working!")
            print("=" * 60)
            return 0

        finally:
            self.disconnect()


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM11"
    tester = ChannelLinkingTest(port)
    return tester.run()


if __name__ == "__main__":
    sys.exit(main())
