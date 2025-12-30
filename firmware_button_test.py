#!/usr/bin/env python3
"""
PMU-30 Digital Input (Button) Test for Nucleo-F446RE

Tests that the user button (DIN0/PC13) is correctly reported in telemetry.
Run this test and press the blue B1 button on the Nucleo board.

Usage: python firmware_button_test.py [COM_PORT]
"""

import serial
import struct
import time
import sys

# Protocol constants
FRAME_MARKER = 0xAA

# Message types
MSG_PING = 0x01
MSG_PONG = 0x02
MSG_START_STREAM = 0x30
MSG_STOP_STREAM = 0x31
MSG_DATA = 0x32
MSG_ACK = 0xE0


def crc16_ccitt(data: bytes, initial: int = 0xFFFF) -> int:
    """Calculate CRC-16-CCITT checksum."""
    crc = initial
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc


def build_frame(msg_type: int, payload: bytes = b"") -> bytes:
    """Build a protocol frame."""
    header = struct.pack("<BHB", FRAME_MARKER, len(payload), msg_type)
    crc_data = header[1:] + payload
    crc = crc16_ccitt(crc_data)
    return header + payload + struct.pack("<H", crc)


def parse_frame(data: bytes) -> dict:
    """Parse a protocol frame."""
    if len(data) < 6:
        return {"error": f"Too short: {len(data)} bytes"}

    if data[0] != FRAME_MARKER:
        return {"error": f"Bad start marker: 0x{data[0]:02X}"}

    length = struct.unpack("<H", data[1:3])[0]
    msg_type = data[3]

    if len(data) < 4 + length + 2:
        return {"error": f"Incomplete frame"}

    payload = data[4:4+length]
    received_crc = struct.unpack("<H", data[4+length:6+length])[0]
    crc_data = data[1:4+length]
    calculated_crc = crc16_ccitt(crc_data)

    return {
        "msg_type": msg_type,
        "length": length,
        "payload": payload,
        "crc_ok": received_crc == calculated_crc,
        "total_bytes": 4 + length + 2
    }


def parse_telemetry(payload: bytes) -> dict:
    """Parse telemetry DATA payload.

    Telemetry format (from pmu_protocol.c for Nucleo-F446RE):
    - counter: 4 bytes (offset 0)
    - timestamp_ms: 4 bytes (offset 4)
    - outputs: 30 bytes (offset 8) - PROFET channel states
    - analog_inputs: 40 bytes (offset 38) - 20 x 2 bytes
    - digital_inputs: 1 byte (offset 78) - 8 bits for DIN0-DIN7
    - voltages: 4 bytes (offset 79) - battery_mv + current_mA
    - temps: 4 bytes (offset 83) - mcu_temp + board_temp
    - faults: 2 bytes (offset 87) - status + fault_flags
    """
    if len(payload) < 79:
        return {"error": f"Payload too short: {len(payload)} bytes"}

    result = {
        "counter": struct.unpack("<I", payload[0:4])[0],
        "timestamp_ms": struct.unpack("<I", payload[4:8])[0],
    }

    # Output states (30 bytes) at offset 8
    result["output_states"] = list(payload[8:38])

    # Analog inputs (20 x 2 bytes = 40 bytes) at offset 38
    result["analog_inputs"] = []
    for i in range(20):
        if 38 + i*2 + 2 <= len(payload):
            val = struct.unpack("<H", payload[38 + i*2:40 + i*2])[0]
            result["analog_inputs"].append(val)

    # Digital inputs at offset 78 (1 byte = 8 bits)
    if len(payload) > 78:
        din_byte = payload[78]
        result["digital_inputs_byte"] = din_byte
        result["digital_inputs"] = [(din_byte >> i) & 1 for i in range(8)]
    else:
        result["digital_inputs_byte"] = 0
        result["digital_inputs"] = [0] * 8

    # Voltages at offset 79 (if available)
    if len(payload) >= 83:
        result["battery_mv"] = struct.unpack("<H", payload[79:81])[0]
        result["current_mA"] = struct.unpack("<H", payload[81:83])[0]

    # Temps at offset 83 (if available)
    if len(payload) >= 87:
        result["mcu_temp_c"] = struct.unpack("<h", payload[83:85])[0]
        result["board_temp_c"] = struct.unpack("<h", payload[85:87])[0]

    return result


class ButtonTester:
    def __init__(self, port: str, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None

    def connect(self) -> bool:
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=2)
            time.sleep(0.5)
            if self.ser.in_waiting:
                self.ser.read(self.ser.in_waiting)
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def disconnect(self):
        if self.ser:
            self.ser.close()
            self.ser = None

    def send_and_receive(self, frame: bytes, timeout: float = 1.0) -> bytes:
        self.ser.timeout = timeout
        self.ser.write(frame)
        self.ser.flush()
        time.sleep(0.1)

        response = b""
        start = time.time()
        while time.time() - start < timeout:
            if self.ser.in_waiting:
                response += self.ser.read(self.ser.in_waiting)
                if len(response) >= 6:
                    length = struct.unpack("<H", response[1:3])[0] if response[0] == FRAME_MARKER else 0
                    if len(response) >= 4 + length + 2:
                        break
            time.sleep(0.02)

        return response

    def start_stream(self) -> bool:
        """Start telemetry stream at 10Hz."""
        # Payload: outputs, inputs, can, temps, voltages, faults (all enabled), rate=10Hz
        payload = struct.pack("<BBBBBBH", 1, 1, 1, 1, 1, 1, 10)
        frame = build_frame(MSG_START_STREAM, payload)

        response = self.send_and_receive(frame)
        if response:
            parsed = parse_frame(response)
            return "error" not in parsed and parsed.get("msg_type") == MSG_ACK
        return False

    def stop_stream(self) -> bool:
        """Stop telemetry stream."""
        frame = build_frame(MSG_STOP_STREAM)
        response = self.send_and_receive(frame)
        return bool(response)

    def receive_telemetry(self, timeout: float = 0.5) -> dict:
        """Receive one telemetry frame."""
        self.ser.timeout = timeout

        response = b""
        start = time.time()
        while time.time() - start < timeout:
            if self.ser.in_waiting:
                response += self.ser.read(self.ser.in_waiting)

                # Find frame start
                while response and response[0] != FRAME_MARKER:
                    response = response[1:]

                if len(response) >= 6:
                    length = struct.unpack("<H", response[1:3])[0]
                    if len(response) >= 4 + length + 2:
                        parsed = parse_frame(response)
                        if "error" not in parsed and parsed["msg_type"] == MSG_DATA:
                            return parse_telemetry(parsed["payload"])
                        break
            time.sleep(0.02)

        return {}

    def run_button_test(self):
        """Run the button test."""
        print(f"\n{'='*60}")
        print("PMU-30 Digital Input (Button) Test")
        print(f"Port: {self.port} @ {self.baudrate} baud")
        print(f"{'='*60}\n")

        # Connect
        print("Connecting...")
        if not self.connect():
            print("[FAIL] Cannot connect to device")
            return False

        print("[OK] Connected\n")

        # Verify with PING
        print("Verifying connection with PING...")
        frame = build_frame(MSG_PING)
        response = self.send_and_receive(frame)
        if not response:
            print("[FAIL] No PONG response")
            self.disconnect()
            return False

        parsed = parse_frame(response)
        if "error" in parsed or parsed.get("msg_type") != MSG_PONG:
            print("[FAIL] Invalid PONG response")
            self.disconnect()
            return False

        print("[OK] PING/PONG verified\n")

        # Start telemetry
        print("Starting telemetry stream...")
        if not self.start_stream():
            print("[FAIL] Could not start stream")
            self.disconnect()
            return False

        print("[OK] Telemetry streaming at 10Hz\n")
        time.sleep(0.2)

        # Monitor button
        print("="*60)
        print("BUTTON TEST - Press the blue B1 button on the Nucleo board!")
        print("="*60)
        print("\nMonitoring DIN[0] (User Button)...")
        print("Press Ctrl+C to exit\n")

        button_was_pressed = False
        button_was_released = False
        last_state = None
        press_count = 0

        try:
            start_time = time.time()
            timeout = 30.0  # 30 second timeout

            while time.time() - start_time < timeout:
                telemetry = self.receive_telemetry(timeout=0.2)

                if telemetry and "digital_inputs" in telemetry:
                    din = telemetry["digital_inputs"]
                    button_state = din[0]  # DIN0 = User Button

                    # Print state
                    din_str = "".join(str(d) for d in din)
                    timestamp = time.time() - start_time

                    if button_state != last_state:
                        if button_state == 1:
                            press_count += 1
                            button_was_pressed = True
                            print(f"[{timestamp:6.2f}s] DIN: {din_str} <- BUTTON PRESSED! (#{press_count})")
                        else:
                            button_was_released = True
                            print(f"[{timestamp:6.2f}s] DIN: {din_str} <- button released")
                        last_state = button_state
                    else:
                        # Periodic update
                        if int(timestamp * 2) % 2 == 0:  # Every 0.5s
                            state_str = "PRESSED" if button_state else "released"
                            print(f"[{timestamp:6.2f}s] DIN: {din_str} (button {state_str})", end="\r")

                    # Success condition: button was pressed and released
                    if button_was_pressed and button_was_released and press_count >= 1:
                        print(f"\n\n[PASS] Button test successful!")
                        print(f"       Detected {press_count} button press(es)")
                        break

        except KeyboardInterrupt:
            print("\n\nTest interrupted by user")

        # Stop stream
        print("\nStopping telemetry...")
        self.stop_stream()
        time.sleep(0.2)

        # Clear any remaining data
        if self.ser.in_waiting:
            self.ser.read(self.ser.in_waiting)

        self.disconnect()

        # Summary
        print(f"\n{'='*60}")
        if button_was_pressed:
            print(f"[PASS] Digital input DIN[0] correctly detected button press")
            print(f"       Total presses detected: {press_count}")
            return True
        else:
            print(f"[FAIL] No button press detected within {timeout}s")
            print("       Make sure to press the blue B1 button on the Nucleo board")
            return False


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM11"

    tester = ButtonTester(port)
    success = tester.run_button_test()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
