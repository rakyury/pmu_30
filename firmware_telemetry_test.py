#!/usr/bin/env python3
"""
PMU-30 Telemetry Test Suite for Nucleo-F446RE

Tests telemetry streaming functionality:
1. Serial connection
2. Start telemetry stream
3. Receive telemetry data packets
4. Parse telemetry data format
5. Stop telemetry stream
6. Verify stream stopped

Usage: python firmware_telemetry_test.py [COM_PORT]
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
MSG_START_STREAM = 0x30
MSG_STOP_STREAM = 0x31
MSG_DATA = 0x32
MSG_ACK = 0xE0
MSG_NACK = 0xE1

# Telemetry stream rates
STREAM_RATE_1HZ = 1
STREAM_RATE_10HZ = 10
STREAM_RATE_50HZ = 50
STREAM_RATE_100HZ = 100

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

def parse_telemetry_data(payload: bytes) -> dict:
    """Parse telemetry data payload."""
    if len(payload) < 8:
        return {"error": "Payload too short for telemetry header"}

    result = {}
    offset = 0

    # Stream counter (4 bytes)
    result["stream_counter"] = struct.unpack("<I", payload[offset:offset+4])[0]
    offset += 4

    # Timestamp (4 bytes)
    result["timestamp_ms"] = struct.unpack("<I", payload[offset:offset+4])[0]
    offset += 4

    # Output states (30 bytes if present)
    if offset + 30 <= len(payload):
        result["outputs"] = list(payload[offset:offset+30])
        offset += 30

    # Input values (40 bytes = 20 x 2 bytes if present)
    if offset + 40 <= len(payload):
        inputs = []
        for i in range(20):
            val = struct.unpack("<H", payload[offset:offset+2])[0]
            inputs.append(val)
            offset += 2
        result["inputs"] = inputs

    # Voltages (4 bytes if present)
    if offset + 4 <= len(payload):
        result["voltage_mV"] = struct.unpack("<H", payload[offset:offset+2])[0]
        offset += 2
        result["current_mA"] = struct.unpack("<H", payload[offset:offset+2])[0]
        offset += 2

    # Temperatures (4 bytes if present)
    if offset + 4 <= len(payload):
        result["mcu_temp_C"] = struct.unpack("<h", payload[offset:offset+2])[0]
        offset += 2
        result["board_temp_C"] = struct.unpack("<h", payload[offset:offset+2])[0]
        offset += 2

    # Faults (2 bytes if present)
    if offset + 2 <= len(payload):
        result["status"] = payload[offset]
        offset += 1
        result["fault_flags"] = payload[offset]
        offset += 1

    result["bytes_parsed"] = offset
    result["total_bytes"] = len(payload)

    return result

def build_telemetry_config(rate_hz: int = 10,
                           outputs: bool = True,
                           inputs: bool = True,
                           can: bool = True,
                           temps: bool = True,
                           voltages: bool = True,
                           faults: bool = True) -> bytes:
    """Build telemetry configuration payload."""
    # PMU_TelemetryConfig_t structure (matches firmware)
    config = struct.pack("<BBBBBBH",
        1 if outputs else 0,
        1 if inputs else 0,
        1 if can else 0,
        1 if temps else 0,
        1 if voltages else 0,
        1 if faults else 0,
        rate_hz
    )
    return config

def test_result(name: str, passed: bool, details: str = ""):
    """Print test result."""
    status = "[PASS]" if passed else "[FAIL]"
    print(f"  {status}: {name}")
    if details:
        print(f"         {details}")
    return passed

class TelemetryTester:
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

    def receive_frames(self, timeout: float = 1.0, max_frames: int = 10) -> list:
        """Receive multiple frames."""
        frames = []
        buffer = b""
        start = time.time()

        while time.time() - start < timeout and len(frames) < max_frames:
            if self.ser.in_waiting:
                buffer += self.ser.read(self.ser.in_waiting)

                # Try to parse complete frames from buffer
                while len(buffer) >= 6:
                    if buffer[0] != FRAME_MARKER:
                        # Skip invalid byte
                        buffer = buffer[1:]
                        continue

                    length = struct.unpack("<H", buffer[1:3])[0]
                    expected_len = 4 + length + 2

                    if len(buffer) >= expected_len:
                        frame_data = buffer[:expected_len]
                        buffer = buffer[expected_len:]

                        parsed = parse_frame(frame_data)
                        if "error" not in parsed:
                            frames.append(parsed)
                    else:
                        break
            else:
                time.sleep(0.01)

        return frames

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

    def test_ping(self) -> bool:
        """Test 1: Verify connection with PING/PONG."""
        frame = build_frame(MSG_PING)
        response = self.send_and_receive(frame)

        if not response:
            return test_result("PING -> PONG", False, "No response")

        parsed = parse_frame(response)
        if "error" in parsed:
            return test_result("PING -> PONG", False, parsed["error"])

        if parsed["msg_type"] == MSG_PONG and parsed["crc_ok"]:
            return test_result("PING -> PONG", True, "Connection verified")
        else:
            return test_result("PING -> PONG", False, f"msg_type=0x{parsed['msg_type']:02X}")

    def test_start_stream(self) -> bool:
        """Test 2: Start telemetry stream."""
        # Build config for 10Hz stream with all data
        config = build_telemetry_config(rate_hz=10)
        frame = build_frame(MSG_START_STREAM, config)
        print(f"         TX: {frame.hex()}")

        response = self.send_and_receive(frame)
        print(f"         RX: {response.hex() if response else 'NOTHING'}")

        if not response:
            return test_result("START_STREAM", False, "No response")

        parsed = parse_frame(response)
        if "error" in parsed:
            return test_result("START_STREAM", False, parsed["error"])

        if parsed["msg_type"] == MSG_ACK and parsed["crc_ok"]:
            return test_result("START_STREAM", True, "Stream started @ 10Hz")
        else:
            return test_result("START_STREAM", False, f"msg_type=0x{parsed['msg_type']:02X}")

    def test_receive_telemetry(self) -> bool:
        """Test 3: Receive and parse telemetry data."""
        print("         Waiting for telemetry packets (2s)...")

        # Receive frames for 2 seconds
        frames = self.receive_frames(timeout=2.0, max_frames=25)

        data_frames = [f for f in frames if f["msg_type"] == MSG_DATA]

        if len(data_frames) == 0:
            return test_result("RECEIVE_TELEMETRY", False, "No DATA frames received")

        print(f"         Received {len(data_frames)} DATA frames")

        # Parse first few frames
        valid_frames = 0
        for i, frame in enumerate(data_frames[:5]):
            if frame["crc_ok"]:
                telemetry = parse_telemetry_data(frame["payload"])
                if "error" not in telemetry:
                    valid_frames += 1
                    if i == 0:
                        print(f"         Frame 0: counter={telemetry.get('stream_counter', '?')}, "
                              f"ts={telemetry.get('timestamp_ms', '?')}ms, "
                              f"voltage={telemetry.get('voltage_mV', '?')}mV")

        if valid_frames >= 3:
            return test_result("RECEIVE_TELEMETRY", True,
                f"{valid_frames}/{min(5, len(data_frames))} frames parsed successfully")
        else:
            return test_result("RECEIVE_TELEMETRY", False,
                f"Only {valid_frames} valid frames")

    def test_telemetry_rate(self) -> bool:
        """Test 4: Verify telemetry rate is approximately correct."""
        print("         Measuring telemetry rate (3s)...")

        start_time = time.time()
        frames = self.receive_frames(timeout=3.0, max_frames=50)
        elapsed = time.time() - start_time

        data_frames = [f for f in frames if f["msg_type"] == MSG_DATA and f["crc_ok"]]

        if len(data_frames) < 2:
            return test_result("TELEMETRY_RATE", False, "Not enough frames to measure rate")

        # Calculate rate
        rate = len(data_frames) / elapsed
        expected_rate = 10  # We configured 10Hz

        # Allow 50% tolerance (5-15 Hz is acceptable for 10Hz)
        rate_ok = expected_rate * 0.5 <= rate <= expected_rate * 1.5

        details = f"Received {len(data_frames)} frames in {elapsed:.2f}s = {rate:.1f} Hz (expected ~{expected_rate} Hz)"

        return test_result("TELEMETRY_RATE", rate_ok, details)

    def test_stream_counters(self) -> bool:
        """Test 5: Verify stream counters are incrementing."""
        frames = self.receive_frames(timeout=1.5, max_frames=20)

        data_frames = [f for f in frames if f["msg_type"] == MSG_DATA and f["crc_ok"]]

        if len(data_frames) < 3:
            return test_result("STREAM_COUNTERS", False, "Not enough frames")

        counters = []
        for frame in data_frames:
            telemetry = parse_telemetry_data(frame["payload"])
            if "stream_counter" in telemetry:
                counters.append(telemetry["stream_counter"])

        if len(counters) < 3:
            return test_result("STREAM_COUNTERS", False, "Could not parse counters")

        # Check counters are incrementing
        incrementing = all(counters[i] < counters[i+1] for i in range(len(counters)-1))

        details = f"Counters: {counters[:5]}{'...' if len(counters) > 5 else ''}"

        return test_result("STREAM_COUNTERS", incrementing, details)

    def test_stop_stream(self) -> bool:
        """Test 6: Stop telemetry stream."""
        frame = build_frame(MSG_STOP_STREAM)
        print(f"         TX: {frame.hex()}")

        response = self.send_and_receive(frame)
        print(f"         RX: {response.hex() if response else 'NOTHING'}")

        if not response:
            return test_result("STOP_STREAM", False, "No response")

        parsed = parse_frame(response)
        if "error" in parsed:
            return test_result("STOP_STREAM", False, parsed["error"])

        if parsed["msg_type"] == MSG_ACK and parsed["crc_ok"]:
            return test_result("STOP_STREAM", True, "Stream stopped")
        else:
            return test_result("STOP_STREAM", False, f"msg_type=0x{parsed['msg_type']:02X}")

    def test_stream_stopped(self) -> bool:
        """Test 7: Verify no more telemetry after stop."""
        print("         Waiting 1.5s to verify no DATA frames...")

        # Clear any buffered data
        time.sleep(0.2)
        if self.ser.in_waiting:
            self.ser.read(self.ser.in_waiting)

        # Wait and check for frames
        frames = self.receive_frames(timeout=1.5, max_frames=10)

        data_frames = [f for f in frames if f["msg_type"] == MSG_DATA]

        if len(data_frames) == 0:
            return test_result("STREAM_STOPPED", True, "No DATA frames after stop")
        else:
            return test_result("STREAM_STOPPED", False,
                f"Received {len(data_frames)} DATA frames after stop")

    def run_all_tests(self):
        """Run all tests."""
        print(f"\n{'='*60}")
        print(f"PMU-30 Telemetry Test Suite")
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

        # Test 1: PING
        print("Test 1: PING/PONG (connection verify)")
        self.run_test("PING", self.test_ping)
        print()

        # Test 2: START_STREAM
        print("Test 2: START_STREAM")
        self.run_test("START_STREAM", self.test_start_stream)
        print()

        # Test 3: RECEIVE_TELEMETRY
        print("Test 3: RECEIVE_TELEMETRY")
        self.run_test("RECEIVE_TELEMETRY", self.test_receive_telemetry)
        print()

        # Test 4: TELEMETRY_RATE
        print("Test 4: TELEMETRY_RATE")
        self.run_test("TELEMETRY_RATE", self.test_telemetry_rate)
        print()

        # Test 5: STREAM_COUNTERS
        print("Test 5: STREAM_COUNTERS")
        self.run_test("STREAM_COUNTERS", self.test_stream_counters)
        print()

        # Test 6: STOP_STREAM
        print("Test 6: STOP_STREAM")
        self.run_test("STOP_STREAM", self.test_stop_stream)
        print()

        # Test 7: STREAM_STOPPED
        print("Test 7: STREAM_STOPPED")
        self.run_test("STREAM_STOPPED", self.test_stream_stopped)
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

    tester = TelemetryTester(port)
    success = tester.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
