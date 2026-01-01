#!/usr/bin/env python3
"""
PMU-30 Firmware Telemetry Comprehensive Test Suite

Tests ALL telemetry functionality:
1. Basic connectivity (PING/PONG)
2. Device information (GET_INFO)
3. Telemetry streaming at different rates
4. Telemetry with different data flags
5. Channel control (GET/SET output)
6. Bulk data reading (all outputs/inputs)
7. Edge cases (rapid start/stop, long streams)

Usage:
    python tests/test_firmware_telemetry.py [COM_PORT]

Example:
    python tests/test_firmware_telemetry.py COM3
"""

import sys
import struct
import time
import serial
from dataclasses import dataclass
from typing import Optional, List, Tuple
from enum import IntEnum


# ============================================================================
# Protocol Constants
# ============================================================================

class CMD(IntEnum):
    """Protocol command IDs"""
    # Basic commands
    PING = 0x01
    PONG = 0x02
    GET_INFO = 0x10
    INFO_RESP = 0x11

    # Configuration
    GET_CONFIG = 0x20
    CONFIG_DATA = 0x21
    LOAD_CONFIG = 0x22
    CONFIG_ACK = 0x23

    # Telemetry
    START_STREAM = 0x30
    STOP_STREAM = 0x31
    DATA = 0x32

    # Channel control
    SET_OUTPUT = 0x40
    OUTPUT_ACK = 0x41
    GET_CHANNEL = 0x43
    CHANNEL_DATA = 0x44
    GET_OUTPUTS = 0x46
    GET_INPUTS = 0x47

    # Binary config
    LOAD_BINARY_CONFIG = 0x68
    BINARY_CONFIG_ACK = 0x69

    # Response codes
    ACK = 0xE0
    NACK = 0xE1
    ERROR = 0x50


FRAME_START = 0xAA


# ============================================================================
# Protocol Utilities
# ============================================================================

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
    crc = crc16_ccitt(frame_data[1:])  # CRC excludes start byte
    return frame_data + struct.pack('<H', crc)


def read_frame(port: serial.Serial, timeout: float = 1.0) -> Tuple[Optional[int], Optional[bytes]]:
    """Read a complete frame from port. Returns (cmd, payload) or (None, None)."""
    start_time = time.time()
    buffer = b''

    while time.time() - start_time < timeout:
        if port.in_waiting > 0:
            buffer += port.read(port.in_waiting)

            # Try to find frame start
            start_idx = buffer.find(bytes([FRAME_START]))
            if start_idx >= 0:
                buffer = buffer[start_idx:]

                # Check if we have enough data for header
                if len(buffer) >= 4:
                    length = struct.unpack('<H', buffer[1:3])[0]
                    frame_size = 4 + length + 2

                    if len(buffer) >= frame_size:
                        cmd = buffer[3]
                        payload = buffer[4:4+length]
                        return cmd, payload

        time.sleep(0.01)

    return None, None


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class TelemetryPacket:
    """Parsed telemetry data packet"""
    counter: int
    timestamp_ms: int
    outputs: List[int]
    currents: List[int]
    digital_inputs: List[int]
    analog_inputs: List[int]

    @classmethod
    def from_payload(cls, payload: bytes) -> 'TelemetryPacket':
        """Parse telemetry payload into structured data."""
        if len(payload) < 8:
            raise ValueError(f"Payload too short: {len(payload)} bytes")

        counter = struct.unpack("<I", payload[0:4])[0]
        timestamp_ms = struct.unpack("<I", payload[4:8])[0]

        # Output states (30 bytes at offset 8)
        outputs = list(payload[8:38]) if len(payload) >= 38 else []

        # Currents (30x uint16 = 60 bytes at offset 38)
        currents = []
        if len(payload) >= 98:
            for i in range(30):
                offset = 38 + i * 2
                currents.append(struct.unpack("<H", payload[offset:offset+2])[0])

        # Digital inputs at offset 78
        digital_inputs = []
        if len(payload) > 78:
            din_byte = payload[78]
            digital_inputs = [(din_byte >> i) & 1 for i in range(8)]

        # Analog inputs would be after currents
        analog_inputs = []

        return cls(
            counter=counter,
            timestamp_ms=timestamp_ms,
            outputs=outputs,
            currents=currents,
            digital_inputs=digital_inputs,
            analog_inputs=analog_inputs
        )


@dataclass
class TestResult:
    """Test result with details"""
    name: str
    passed: bool
    message: str = ""
    duration_ms: float = 0


# ============================================================================
# Test Framework
# ============================================================================

class TelemetryTester:
    """Comprehensive telemetry test suite"""

    def __init__(self, port_name: str = "COM3"):
        self.port_name = port_name
        self.port: Optional[serial.Serial] = None
        self.results: List[TestResult] = []

    def connect(self) -> bool:
        """Open serial connection"""
        try:
            self.port = serial.Serial(
                port=self.port_name,
                baudrate=115200,
                timeout=1.0,
                write_timeout=1.0
            )
            time.sleep(0.5)  # Wait for device
            return True
        except serial.SerialException as e:
            print(f"ERROR: Cannot open {self.port_name}: {e}")
            return False

    def disconnect(self):
        """Close serial connection"""
        if self.port and self.port.is_open:
            self.port.close()

    def send_command(self, cmd: int, payload: bytes = b'') -> Tuple[Optional[int], Optional[bytes]]:
        """Send command and wait for response"""
        self.port.reset_input_buffer()
        frame = build_frame(cmd, payload)
        self.port.write(frame)
        self.port.flush()
        return read_frame(self.port, timeout=2.0)

    def add_result(self, name: str, passed: bool, message: str = "", duration_ms: float = 0):
        """Record test result"""
        self.results.append(TestResult(name, passed, message, duration_ms))
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} {name}: {message}")

    # ========================================================================
    # Basic Tests
    # ========================================================================

    def test_ping(self) -> bool:
        """Test PING/PONG connectivity"""
        start = time.time()
        cmd, _ = self.send_command(CMD.PING)
        duration = (time.time() - start) * 1000

        passed = cmd == CMD.PONG
        self.add_result(
            "PING/PONG",
            passed,
            f"Response in {duration:.1f}ms" if passed else f"Expected PONG(0x02), got {hex(cmd) if cmd else 'None'}",
            duration
        )
        return passed

    def test_get_info(self) -> bool:
        """Test GET_INFO command"""
        start = time.time()
        cmd, payload = self.send_command(CMD.GET_INFO)
        duration = (time.time() - start) * 1000

        passed = cmd == CMD.INFO_RESP
        message = ""
        if passed and payload:
            try:
                info_str = payload.decode('utf-8', errors='replace').rstrip('\x00')
                message = f"Device: {info_str[:50]}"
            except:
                message = f"Got {len(payload)} bytes"
        elif not passed:
            message = f"Expected INFO_RESP(0x11), got {hex(cmd) if cmd else 'None'}"

        self.add_result("GET_INFO", passed, message, duration)
        return passed

    # ========================================================================
    # Telemetry Stream Tests
    # ========================================================================

    def test_telemetry_basic(self, rate_hz: int = 10) -> bool:
        """Test basic telemetry streaming"""
        # Build START_STREAM payload: flags (6 bytes) + rate_hz (2 bytes)
        # Firmware expects rate in Hz, not period in ms!
        payload = struct.pack('<BBBBBBH', 1, 1, 0, 0, 0, 0, rate_hz)

        self.port.reset_input_buffer()
        frame = build_frame(CMD.START_STREAM, payload)
        self.port.write(frame)
        self.port.flush()

        # Collect telemetry packets
        packets = []
        start_time = time.time()
        timeout = 3.0

        while time.time() - start_time < timeout:
            cmd, payload = read_frame(self.port, timeout=0.5)
            if cmd == CMD.DATA:
                try:
                    tel = TelemetryPacket.from_payload(payload)
                    packets.append(tel)
                    if len(packets) >= 5:
                        break
                except ValueError:
                    pass

        # Stop stream
        self.port.write(build_frame(CMD.STOP_STREAM))
        self.port.flush()
        time.sleep(0.2)
        self.port.reset_input_buffer()

        passed = len(packets) >= 3
        if passed:
            actual_rate = len(packets) / (time.time() - start_time)
            message = f"Received {len(packets)} packets at ~{actual_rate:.1f}Hz (requested {rate_hz}Hz)"
        else:
            message = f"Only received {len(packets)} packets"

        self.add_result(f"Telemetry@{rate_hz}Hz", passed, message)
        return passed

    def test_telemetry_rates(self) -> bool:
        """Test multiple telemetry rates"""
        rates = [1, 10, 50]
        all_passed = True

        for rate in rates:
            # Firmware expects rate in Hz directly
            payload = struct.pack('<BBBBBBH', 1, 1, 0, 0, 0, 0, rate)

            self.port.reset_input_buffer()
            self.port.write(build_frame(CMD.START_STREAM, payload))
            self.port.flush()

            # Measure actual rate
            packets = []
            start = time.time()
            duration = min(3.0, max(1.5, 10.0 / rate))  # Collect ~10 packets

            while time.time() - start < duration:
                cmd, data = read_frame(self.port, timeout=0.5)
                if cmd == CMD.DATA:
                    packets.append(time.time())

            # Stop stream
            self.port.write(build_frame(CMD.STOP_STREAM))
            self.port.flush()
            time.sleep(0.2)
            self.port.reset_input_buffer()

            if len(packets) >= 2:
                actual_rate = (len(packets) - 1) / (packets[-1] - packets[0]) if len(packets) > 1 else 0
                # Higher tolerance for bare-metal timing (no calibrated SysTick)
                # Loop timing varies with clock, temperature, etc.
                # Base 60% tolerance + extra for low rates
                tolerance = 0.6 + (1.0 / rate if rate < 20 else 0)
                rate_ok = abs(actual_rate - rate) / rate <= tolerance
            else:
                actual_rate = 0
                rate_ok = False

            passed = len(packets) >= 2 and rate_ok
            all_passed = all_passed and passed

            self.add_result(
                f"Rate {rate}Hz",
                passed,
                f"Actual: {actual_rate:.1f}Hz ({len(packets)} packets)"
            )

        return all_passed

    def test_telemetry_flags(self) -> bool:
        """Test different telemetry flag combinations"""
        test_cases = [
            ("outputs_only", (1, 0, 0, 0, 0, 0)),
            ("inputs_only", (0, 1, 0, 0, 0, 0)),
            ("outputs+inputs", (1, 1, 0, 0, 0, 0)),
        ]

        all_passed = True

        for name, flags in test_cases:
            payload = struct.pack('<BBBBBBH', *flags, 10)  # 10Hz

            self.port.reset_input_buffer()
            self.port.write(build_frame(CMD.START_STREAM, payload))
            self.port.flush()

            # Get one packet
            packets = []
            start = time.time()
            while time.time() - start < 2.0:
                cmd, data = read_frame(self.port, timeout=0.5)
                if cmd == CMD.DATA:
                    packets.append(data)
                    break

            # Stop
            self.port.write(build_frame(CMD.STOP_STREAM))
            self.port.flush()
            time.sleep(0.2)
            self.port.reset_input_buffer()

            passed = len(packets) > 0
            all_passed = all_passed and passed

            msg = f"Got {len(packets[0])} bytes" if packets else "No data"
            self.add_result(f"Flags:{name}", passed, msg)

        return all_passed

    def test_telemetry_stop(self) -> bool:
        """Test that telemetry stops properly"""
        # Start streaming
        payload = struct.pack('<BBBBBBH', 1, 1, 0, 0, 0, 0, 10)  # 10Hz
        self.port.reset_input_buffer()
        self.port.write(build_frame(CMD.START_STREAM, payload))
        self.port.flush()

        # Wait for some data
        time.sleep(0.5)

        # Stop
        self.port.write(build_frame(CMD.STOP_STREAM))
        self.port.flush()
        time.sleep(0.3)
        self.port.reset_input_buffer()

        # Count packets after stop
        time.sleep(1.0)
        remaining = 0
        while self.port.in_waiting > 0:
            cmd, _ = read_frame(self.port, timeout=0.1)
            if cmd == CMD.DATA:
                remaining += 1

        passed = remaining == 0
        self.add_result(
            "Stop Stream",
            passed,
            "Stream stopped" if passed else f"Still receiving {remaining} packets"
        )
        return passed

    def test_rapid_start_stop(self) -> bool:
        """Test rapid start/stop cycles (stress test)"""
        cycles = 5
        successful = 0

        for i in range(cycles):
            # Start
            payload = struct.pack('<BBBBBBH', 1, 1, 0, 0, 0, 0, 20)  # 20Hz
            self.port.reset_input_buffer()
            self.port.write(build_frame(CMD.START_STREAM, payload))
            self.port.flush()

            # Wait briefly
            time.sleep(0.1)

            # Check for data
            got_data = False
            start = time.time()
            while time.time() - start < 0.3:
                cmd, _ = read_frame(self.port, timeout=0.1)
                if cmd == CMD.DATA:
                    got_data = True
                    break

            # Stop
            self.port.write(build_frame(CMD.STOP_STREAM))
            self.port.flush()
            time.sleep(0.1)
            self.port.reset_input_buffer()

            if got_data:
                successful += 1

        passed = successful >= cycles - 1  # Allow 1 failure
        self.add_result(
            "Rapid Start/Stop",
            passed,
            f"{successful}/{cycles} cycles successful"
        )
        return passed

    # ========================================================================
    # Channel Control Tests
    # ========================================================================

    def test_get_outputs(self) -> bool:
        """Test GET_OUTPUTS command"""
        cmd, payload = self.send_command(CMD.GET_OUTPUTS)

        # Accept either ACK or direct response
        passed = cmd is not None and payload is not None
        if passed:
            self.add_result("GET_OUTPUTS", True, f"Response: {len(payload)} bytes")
        else:
            # Command might not be implemented yet
            self.add_result("GET_OUTPUTS", False, "No response (may not be implemented)")
        return passed

    def test_get_inputs(self) -> bool:
        """Test GET_INPUTS command"""
        cmd, payload = self.send_command(CMD.GET_INPUTS)

        passed = cmd is not None and payload is not None
        if passed:
            self.add_result("GET_INPUTS", True, f"Response: {len(payload)} bytes")
        else:
            self.add_result("GET_INPUTS", False, "No response (may not be implemented)")
        return passed

    def test_set_output(self) -> bool:
        """Test SET_OUTPUT command"""
        # Set output 0 to value 50%
        channel = 0
        value = 127  # 50% of 255
        payload = struct.pack('<BB', channel, value)

        cmd, resp = self.send_command(CMD.SET_OUTPUT, payload)

        passed = cmd in (CMD.OUTPUT_ACK, CMD.ACK)
        self.add_result(
            "SET_OUTPUT",
            passed,
            f"ACK received" if passed else f"Got {hex(cmd) if cmd else 'None'}"
        )
        return passed

    def test_get_channel(self) -> bool:
        """Test GET_CHANNEL command"""
        channel = 0
        payload = struct.pack('<B', channel)

        cmd, resp = self.send_command(CMD.GET_CHANNEL, payload)

        passed = cmd in (CMD.CHANNEL_DATA, CMD.ACK) or resp is not None
        if passed and resp:
            if len(resp) >= 2:
                ch, val = resp[0], resp[1]
                self.add_result("GET_CHANNEL", True, f"Channel {ch} = {val}")
            else:
                self.add_result("GET_CHANNEL", True, f"Response: {len(resp)} bytes")
        else:
            self.add_result("GET_CHANNEL", False, "No response")
        return passed

    # ========================================================================
    # Data Integrity Tests
    # ========================================================================

    def test_telemetry_counter(self) -> bool:
        """Test that telemetry counter increments correctly"""
        # Start stream at 50Hz for good sampling
        payload = struct.pack('<BBBBBBH', 1, 1, 0, 0, 0, 0, 50)  # 50Hz

        self.port.reset_input_buffer()
        self.port.write(build_frame(CMD.START_STREAM, payload))
        self.port.flush()

        counters = []
        start = time.time()

        while time.time() - start < 1.0:
            cmd, data = read_frame(self.port, timeout=0.1)
            if cmd == CMD.DATA and len(data) >= 4:
                counter = struct.unpack("<I", data[0:4])[0]
                counters.append(counter)
                if len(counters) >= 20:
                    break

        # Stop
        self.port.write(build_frame(CMD.STOP_STREAM))
        self.port.flush()
        time.sleep(0.2)
        self.port.reset_input_buffer()

        # Check counters are incrementing
        good_increments = 0
        if len(counters) >= 3:
            increments = [counters[i+1] - counters[i] for i in range(len(counters)-1)]
            # Most increments should be 1 (allow some dropped packets)
            good_increments = sum(1 for inc in increments if inc == 1)
            passed = good_increments >= len(increments) * 0.8
        else:
            passed = False

        self.add_result(
            "Counter Increment",
            passed,
            f"{len(counters)} packets, {good_increments} consecutive"
        )
        return passed

    def test_timestamp_monotonic(self) -> bool:
        """Test that timestamps are monotonically increasing"""
        payload = struct.pack('<BBBBBBH', 1, 1, 0, 0, 0, 0, 50)  # 50Hz

        self.port.reset_input_buffer()
        self.port.write(build_frame(CMD.START_STREAM, payload))
        self.port.flush()

        timestamps = []
        start = time.time()

        while time.time() - start < 1.0:
            cmd, data = read_frame(self.port, timeout=0.1)
            if cmd == CMD.DATA and len(data) >= 8:
                ts = struct.unpack("<I", data[4:8])[0]
                timestamps.append(ts)
                if len(timestamps) >= 20:
                    break

        # Stop
        self.port.write(build_frame(CMD.STOP_STREAM))
        self.port.flush()
        time.sleep(0.2)
        self.port.reset_input_buffer()

        # Check timestamps are increasing
        if len(timestamps) >= 3:
            monotonic = all(timestamps[i] < timestamps[i+1] for i in range(len(timestamps)-1))
            passed = monotonic
        else:
            passed = False

        self.add_result(
            "Timestamp Monotonic",
            passed,
            f"{len(timestamps)} samples, {'all increasing' if passed else 'NOT monotonic!'}"
        )
        return passed

    # ========================================================================
    # Long Duration Test
    # ========================================================================

    def test_long_stream(self, duration: float = 10.0) -> bool:
        """Test long-running telemetry stream"""
        payload = struct.pack('<BBBBBBH', 1, 1, 0, 0, 0, 0, 10)  # 10Hz

        self.port.reset_input_buffer()
        self.port.write(build_frame(CMD.START_STREAM, payload))
        self.port.flush()

        packets = 0
        errors = 0
        start = time.time()
        last_counter = None

        while time.time() - start < duration:
            cmd, data = read_frame(self.port, timeout=0.5)
            if cmd == CMD.DATA:
                packets += 1
                if len(data) >= 4:
                    counter = struct.unpack("<I", data[0:4])[0]
                    if last_counter is not None and counter != last_counter + 1:
                        errors += 1
                    last_counter = counter

        # Stop
        self.port.write(build_frame(CMD.STOP_STREAM))
        self.port.flush()
        time.sleep(0.2)
        self.port.reset_input_buffer()

        expected = int(duration * 10)  # 10Hz
        passed = packets >= expected * 0.8 and errors <= packets * 0.05

        self.add_result(
            f"Long Stream ({duration}s)",
            passed,
            f"{packets} packets, {errors} dropped ({100*errors/packets:.1f}%)" if packets > 0 else "No packets"
        )
        return passed

    # ========================================================================
    # Run All Tests
    # ========================================================================

    def run_all(self) -> bool:
        """Run complete test suite"""
        print("=" * 70)
        print("PMU-30 Firmware Telemetry Test Suite")
        print("=" * 70)
        print(f"Port: {self.port_name}")
        print()

        if not self.connect():
            return False

        try:
            # Basic connectivity
            print("\n[1] Basic Connectivity Tests")
            print("-" * 40)
            self.test_ping()
            self.test_get_info()

            # Telemetry streaming
            print("\n[2] Telemetry Streaming Tests")
            print("-" * 40)
            self.test_telemetry_basic(rate_hz=10)
            self.test_telemetry_stop()

            # Multiple rates
            print("\n[3] Telemetry Rate Tests")
            print("-" * 40)
            self.test_telemetry_rates()

            # Telemetry flags
            print("\n[4] Telemetry Flag Tests")
            print("-" * 40)
            self.test_telemetry_flags()

            # Channel control
            print("\n[5] Channel Control Tests")
            print("-" * 40)
            self.test_set_output()
            self.test_get_channel()
            self.test_get_outputs()
            self.test_get_inputs()

            # Data integrity
            print("\n[6] Data Integrity Tests")
            print("-" * 40)
            self.test_telemetry_counter()
            self.test_timestamp_monotonic()

            # Stress tests
            print("\n[7] Stress Tests")
            print("-" * 40)
            self.test_rapid_start_stop()
            self.test_long_stream(duration=10.0)

            # Summary
            print("\n" + "=" * 70)
            print("TEST RESULTS SUMMARY")
            print("=" * 70)

            passed = sum(1 for r in self.results if r.passed)
            failed = sum(1 for r in self.results if not r.passed)
            total = len(self.results)

            print(f"\n  PASSED: {passed}/{total}")
            print(f"  FAILED: {failed}/{total}")

            if failed > 0:
                print("\n  Failed tests:")
                for r in self.results:
                    if not r.passed:
                        print(f"    - {r.name}: {r.message}")

            print("\n" + "=" * 70)
            print("ALL TESTS PASSED" if failed == 0 else "SOME TESTS FAILED")
            print("=" * 70)

            return failed == 0

        finally:
            self.disconnect()


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    port_name = sys.argv[1] if len(sys.argv) > 1 else "COM3"

    tester = TelemetryTester(port_name)
    success = tester.run_all()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
