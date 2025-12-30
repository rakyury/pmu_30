#!/usr/bin/env python3
"""
Comprehensive PMU-30 Protocol Test Suite for Nucleo-F446RE

Tests all basic protocol functionality:
1. Serial connection
2. Echo (RX verification)
3. PING/PONG
4. GET_VERSION
5. GET_SERIAL
6. GET_CONFIG

Usage: python firmware_protocol_test.py [COM_PORT]
"""

import serial
import struct
import time
import sys

# Protocol constants
FRAME_MARKER = 0xAA

# Message types - must match firmware pmu_protocol.h
MSG_PING = 0x01
MSG_PONG = 0x02
MSG_GET_VERSION = 0x10  # GET_INFO in firmware
MSG_VERSION_DATA = 0x10  # Response uses same ID
MSG_GET_SERIAL = 0x03
MSG_SERIAL_DATA = 0x03  # Response uses same ID
MSG_ACK = 0xE0
MSG_NACK = 0xE1
MSG_GET_CONFIG = 0x20
MSG_CONFIG_DATA = 0x21

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
    crc_data = header[1:] + payload  # CRC over length + msg_type + payload
    crc = crc16_ccitt(crc_data)
    return header + payload + struct.pack("<H", crc)

def parse_frame(data: bytes) -> dict:
    """Parse a protocol frame."""
    if len(data) < 6:
        return {"error": f"Too short: {len(data)} bytes", "raw": data.hex()}

    if data[0] != FRAME_MARKER:
        return {"error": f"Bad start marker: 0x{data[0]:02X}", "raw": data.hex()}

    length = struct.unpack("<H", data[1:3])[0]
    msg_type = data[3]

    if len(data) < 4 + length + 2:
        return {"error": f"Incomplete: need {4 + length + 2}, got {len(data)}", "raw": data.hex()}

    payload = data[4:4+length]
    received_crc = struct.unpack("<H", data[4+length:6+length])[0]

    # Verify CRC
    crc_data = data[1:4+length]
    calculated_crc = crc16_ccitt(crc_data)

    return {
        "msg_type": msg_type,
        "length": length,
        "payload": payload,
        "received_crc": received_crc,
        "calculated_crc": calculated_crc,
        "crc_ok": received_crc == calculated_crc,
        "total_bytes": 4 + length + 2
    }

def test_result(name: str, passed: bool, details: str = ""):
    """Print test result."""
    status = "[PASS]" if passed else "[FAIL]"
    print(f"  {status}: {name}")
    if details:
        print(f"         {details}")
    return passed

class ProtocolTester:
    def __init__(self, port: str, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.passed = 0
        self.failed = 0

    def connect(self) -> bool:
        """Connect to serial port."""
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=2)
            time.sleep(0.5)  # Wait for connection
            # Flush any startup data
            if self.ser.in_waiting:
                startup = self.ser.read(self.ser.in_waiting)
                print(f"  Startup data: {startup}")
            return True
        except Exception as e:
            print(f"  Connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from serial port."""
        if self.ser:
            self.ser.close()
            self.ser = None

    def send_and_receive(self, frame: bytes, timeout: float = 1.0) -> bytes:
        """Send frame and receive response."""
        self.ser.timeout = timeout
        self.ser.write(frame)
        self.ser.flush()
        time.sleep(0.1)

        # Read response
        response = b""
        start = time.time()
        while time.time() - start < timeout:
            if self.ser.in_waiting:
                response += self.ser.read(self.ser.in_waiting)
                # Check if we have a complete frame
                if len(response) >= 6:
                    length = struct.unpack("<H", response[1:3])[0] if response[0] == FRAME_MARKER else 0
                    expected_len = 4 + length + 2
                    if len(response) >= expected_len:
                        break
            time.sleep(0.05)

        return response

    def run_test(self, name: str, test_func) -> bool:
        """Run a single test."""
        try:
            result = test_func()
            if result:
                self.passed += 1
            else:
                self.failed += 1
            return result
        except Exception as e:
            test_result(name, False, f"Exception: {e}")
            self.failed += 1
            return False

    def test_echo(self) -> bool:
        """Test 1: Verify RX by checking echo."""
        test_data = b"TEST"
        self.ser.write(test_data)
        self.ser.flush()
        time.sleep(0.2)

        response = self.ser.read(100)

        if test_data in response:
            return test_result("Echo (RX verification)", True, f"Sent: {test_data}, Got: {response}")
        else:
            return test_result("Echo (RX verification)", False, f"Sent: {test_data}, Got: {response if response else 'NOTHING'}")

    def test_ping(self) -> bool:
        """Test 2: PING/PONG."""
        frame = build_frame(MSG_PING)
        print(f"         TX: {frame.hex()}")

        response = self.send_and_receive(frame)
        print(f"         RX: {response.hex() if response else 'NOTHING'}")

        if not response:
            return test_result("PING -> PONG", False, "No response")

        parsed = parse_frame(response)
        if "error" in parsed:
            return test_result("PING -> PONG", False, parsed["error"])

        if parsed["msg_type"] == MSG_PONG and parsed["crc_ok"]:
            return test_result("PING -> PONG", True, f"Got PONG, CRC OK")
        else:
            return test_result("PING -> PONG", False, f"msg_type=0x{parsed['msg_type']:02X}, crc_ok={parsed['crc_ok']}")

    def test_get_version(self) -> bool:
        """Test 3: GET_VERSION."""
        frame = build_frame(MSG_GET_VERSION)
        print(f"         TX: {frame.hex()}")

        response = self.send_and_receive(frame)
        print(f"         RX: {response.hex() if response else 'NOTHING'}")

        if not response:
            return test_result("GET_VERSION", False, "No response")

        parsed = parse_frame(response)
        if "error" in parsed:
            return test_result("GET_VERSION", False, parsed["error"])

        if parsed["msg_type"] == MSG_VERSION_DATA and parsed["crc_ok"]:
            version_str = parsed["payload"].decode('utf-8', errors='replace')
            return test_result("GET_VERSION", True, f"Version: {version_str}")
        else:
            return test_result("GET_VERSION", False, f"msg_type=0x{parsed['msg_type']:02X}")

    def test_get_serial(self) -> bool:
        """Test 4: GET_SERIAL."""
        frame = build_frame(MSG_GET_SERIAL)
        print(f"         TX: {frame.hex()}")

        response = self.send_and_receive(frame)
        print(f"         RX: {response.hex() if response else 'NOTHING'}")

        if not response:
            return test_result("GET_SERIAL", False, "No response")

        parsed = parse_frame(response)
        if "error" in parsed:
            return test_result("GET_SERIAL", False, parsed["error"])

        if parsed["msg_type"] == MSG_SERIAL_DATA and parsed["crc_ok"]:
            serial_str = parsed["payload"].decode('utf-8', errors='replace')
            return test_result("GET_SERIAL", True, f"Serial: {serial_str}")
        else:
            return test_result("GET_SERIAL", False, f"msg_type=0x{parsed['msg_type']:02X}")

    def test_get_config(self) -> bool:
        """Test 5: GET_CONFIG."""
        frame = build_frame(MSG_GET_CONFIG)
        print(f"         TX: {frame.hex()}")

        response = self.send_and_receive(frame, timeout=2.0)
        print(f"         RX: {response[:50].hex() if response else 'NOTHING'}{'...' if len(response) > 50 else ''}")

        if not response:
            return test_result("GET_CONFIG", False, "No response")

        parsed = parse_frame(response)
        if "error" in parsed:
            return test_result("GET_CONFIG", False, parsed["error"])

        if parsed["msg_type"] == MSG_CONFIG_DATA and parsed["crc_ok"]:
            # Parse chunk header
            if len(parsed["payload"]) >= 4:
                chunk_idx = struct.unpack("<H", parsed["payload"][0:2])[0]
                total_chunks = struct.unpack("<H", parsed["payload"][2:4])[0]
                config_data = parsed["payload"][4:]
                config_str = config_data.decode('utf-8', errors='replace')
                return test_result("GET_CONFIG", True,
                    f"Chunk {chunk_idx+1}/{total_chunks}, Config: {config_str[:60]}...")
            else:
                return test_result("GET_CONFIG", False, "Payload too short for chunk header")
        else:
            return test_result("GET_CONFIG", False, f"msg_type=0x{parsed['msg_type']:02X}")

    def run_all_tests(self):
        """Run all tests."""
        print(f"\n{'='*60}")
        print(f"PMU-30 Protocol Test Suite")
        print(f"Port: {self.port} @ {self.baudrate} baud")
        print(f"{'='*60}\n")

        # Test 0: Connection
        print("Test 0: Serial Connection")
        if not self.connect():
            print("\n[FAIL]ED: Cannot connect to device\n")
            return False

        test_result("Serial connection", True, f"Connected to {self.port}")
        self.passed += 1
        print()

        # Test 1: PING (echo removed - protocol sends proper responses)
        print("Test 2: PING/PONG")
        self.run_test("PING", self.test_ping)
        print()

        # Test 3: GET_VERSION
        print("Test 3: GET_VERSION")
        self.run_test("GET_VERSION", self.test_get_version)
        print()

        # Test 4: GET_SERIAL
        print("Test 4: GET_SERIAL")
        self.run_test("GET_SERIAL", self.test_get_serial)
        print()

        # Test 5: GET_CONFIG
        print("Test 5: GET_CONFIG")
        self.run_test("GET_CONFIG", self.test_get_config)
        print()

        # Summary
        print(f"{'='*60}")
        total = self.passed + self.failed
        print(f"Results: {self.passed}/{total} passed, {self.failed}/{total} failed")
        print(f"{'='*60}\n")

        self.disconnect()
        return self.failed == 0


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM11"

    tester = ProtocolTester(port)
    success = tester.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
