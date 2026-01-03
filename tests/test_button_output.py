#!/usr/bin/env python3
"""
PMU-30 Button-to-Output Test

Tests:
1. Read button state (digital input) via telemetry
2. Control output based on button state
3. Verify output state changes in telemetry

Button: PC13 (User button on Nucleo, DIN0)
Output: Channel 0 (LED on PA5)

Usage:
    python tests/test_button_output.py [COM_PORT]
"""

import sys
import struct
import time
import serial
from dataclasses import dataclass
from typing import Optional


# Protocol constants
FRAME_START = 0xAA

class CMD:
    PING = 0x01
    PONG = 0x02
    GET_INFO = 0x10
    INFO_RESP = 0x11
    START_STREAM = 0x30
    STOP_STREAM = 0x31
    DATA = 0x32
    SET_OUTPUT = 0x40
    OUTPUT_ACK = 0x41
    LOAD_BINARY_CONFIG = 0x68
    BINARY_CONFIG_ACK = 0x69


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


def read_frame(port: serial.Serial, timeout: float = 1.0):
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


@dataclass
class TelemetryData:
    """Parsed telemetry data."""
    counter: int
    timestamp_ms: int
    outputs: list
    digital_inputs: list

    @classmethod
    def from_payload(cls, payload: bytes) -> Optional['TelemetryData']:
        if len(payload) < 8:
            return None

        counter = struct.unpack("<I", payload[0:4])[0]
        timestamp = struct.unpack("<I", payload[4:8])[0]

        # Output states (30 bytes at offset 8)
        outputs = list(payload[8:38]) if len(payload) >= 38 else []

        # Digital inputs - scan through payload to find the DIN byte
        # In Nucleo format: after outputs (30B) + analog inputs (40B) = offset 78
        digital_inputs = []
        if len(payload) > 78:
            din_byte = payload[78]
            digital_inputs = [(din_byte >> i) & 1 for i in range(8)]

        return cls(counter, timestamp, outputs, digital_inputs)


class ButtonOutputTest:
    """Test button-to-output functionality."""

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
            return True
        except serial.SerialException as e:
            print(f"ERROR: Cannot open {self.port_name}: {e}")
            return False

    def disconnect(self):
        """Close serial connection."""
        if self.port and self.port.is_open:
            self.port.close()

    def send_command(self, cmd: int, payload: bytes = b''):
        """Send command and wait for response."""
        self.port.reset_input_buffer()
        frame = build_frame(cmd, payload)
        self.port.write(frame)
        self.port.flush()
        return read_frame(self.port, timeout=2.0)

    def set_output(self, channel: int, state: int):
        """Set output channel state."""
        payload = struct.pack('<BB', channel, state)
        cmd, resp = self.send_command(CMD.SET_OUTPUT, payload)
        return cmd == CMD.OUTPUT_ACK

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

    def read_telemetry(self, timeout: float = 0.5) -> Optional[TelemetryData]:
        """Read one telemetry packet."""
        cmd, payload = read_frame(self.port, timeout)
        if cmd == CMD.DATA:
            return TelemetryData.from_payload(payload)
        return None

    def run_interactive_test(self, duration: float = 30.0):
        """
        Interactive test: mirrors button state to output.

        Press the button on the Nucleo board and watch the LED.
        The Python script reads telemetry, detects button press,
        and sends output command to turn LED on/off.
        """
        print("\n" + "=" * 60)
        print("Button-to-Output Interactive Test")
        print("=" * 60)
        print(f"\nDuration: {duration}s")
        print("Button: PC13 (User button on Nucleo)")
        print("Output: Channel 1 (LED on PA5)")
        print("\nPress the button to see the LED turn on!")
        print("Press Ctrl+C to exit early.\n")

        self.start_telemetry(rate_hz=50)  # 50Hz for responsive button

        last_button = None
        output_state = 0
        packets = 0
        button_presses = 0
        start = time.time()

        try:
            while time.time() - start < duration:
                tel = self.read_telemetry(timeout=0.1)

                if tel:
                    packets += 1

                    # Get button state (DIN0 = PC13)
                    # Note: Button is active LOW on Nucleo (pressed = 0)
                    button = tel.digital_inputs[0] if tel.digital_inputs else 0
                    button_pressed = (button == 0)  # Invert for active-low

                    # Detect state change
                    if last_button is not None and button_pressed != last_button:
                        if button_pressed:
                            button_presses += 1
                            print(f"  [{tel.timestamp_ms:8d}ms] Button PRESSED  -> Output ON")
                            output_state = 255
                            self.set_output(1, 255)  # Output 1 = LED
                        else:
                            print(f"  [{tel.timestamp_ms:8d}ms] Button RELEASED -> Output OFF")
                            output_state = 0
                            self.set_output(1, 0)

                    last_button = button_pressed

                    # Print status every 50 packets
                    if packets % 50 == 0:
                        btn_str = "PRESSED" if button_pressed else "released"
                        out_str = "ON" if output_state else "OFF"
                        print(f"  Status: Button={btn_str}, Output={out_str}, Packets={packets}")

        except KeyboardInterrupt:
            print("\n\nTest interrupted by user.")

        finally:
            self.stop_telemetry()
            self.set_output(1, 0)  # Turn off output

        print("\n" + "-" * 60)
        print(f"Test completed!")
        print(f"  Total packets: {packets}")
        print(f"  Button presses: {button_presses}")
        print("-" * 60)

    def run_automated_test(self) -> bool:
        """
        Automated test: verify telemetry contains button state.
        """
        print("\n" + "=" * 60)
        print("Automated Button/Output Test")
        print("=" * 60)

        # Test 1: Verify button state is visible in telemetry
        print("\n[1] Verifying button state in telemetry...")

        self.start_telemetry(rate_hz=20)

        telemetry_ok = False
        for _ in range(10):
            tel = self.read_telemetry(timeout=0.5)
            if tel and tel.digital_inputs:
                print(f"    [OK] Digital inputs visible: {tel.digital_inputs}")
                telemetry_ok = True
                break

        self.stop_telemetry()

        if not telemetry_ok:
            print("    [FAIL] No digital input data in telemetry")
            return False

        # Test 2: Verify output control works
        print("\n[2] Testing output control...")

        # Turn on
        if self.set_output(1, 255):
            print("    [OK] Output 1 set to ON")
        else:
            print("    [FAIL] Failed to set output")
            return False

        time.sleep(0.5)

        # Verify via telemetry
        self.start_telemetry(rate_hz=20)
        time.sleep(0.2)

        output_ok = False
        for _ in range(5):
            tel = self.read_telemetry(timeout=0.5)
            if tel and len(tel.outputs) > 1:
                if tel.outputs[1] > 0:
                    print(f"    [OK] Output 1 confirmed ON in telemetry: {tel.outputs[1]}")
                    output_ok = True
                    break

        self.stop_telemetry()
        self.set_output(1, 0)  # Turn off

        if not output_ok:
            print("    [WARN] Could not verify output state in telemetry")

        # Test 3: Verify output turns off
        print("\n[3] Testing output off...")

        time.sleep(0.2)
        self.start_telemetry(rate_hz=20)
        time.sleep(0.2)

        off_ok = False
        for _ in range(5):
            tel = self.read_telemetry(timeout=0.5)
            if tel and len(tel.outputs) > 1:
                if tel.outputs[1] == 0:
                    print(f"    [OK] Output 1 confirmed OFF: {tel.outputs[1]}")
                    off_ok = True
                    break

        self.stop_telemetry()

        # Summary
        print("\n" + "=" * 60)
        all_passed = telemetry_ok and output_ok and off_ok
        print("ALL TESTS PASSED" if all_passed else "SOME TESTS FAILED")
        print("=" * 60)

        return all_passed

    def run(self):
        """Run all tests."""
        if not self.connect():
            return 1

        try:
            # First verify connection
            cmd, _ = self.send_command(CMD.PING)
            if cmd != CMD.PONG:
                print("ERROR: Device not responding to PING")
                return 1

            print("[OK] Device connected")

            # Run automated test
            if not self.run_automated_test():
                return 1

            # Run interactive test
            print("\n\nStarting interactive test...")
            print("Press Enter to continue or Ctrl+C to skip...")
            try:
                input()
                self.run_interactive_test(duration=30.0)
            except KeyboardInterrupt:
                print("\nInteractive test skipped.")

            return 0

        finally:
            self.disconnect()


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM11"
    tester = ButtonOutputTest(port)
    return tester.run()


if __name__ == "__main__":
    sys.exit(main())
