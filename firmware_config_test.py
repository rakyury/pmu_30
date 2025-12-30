#!/usr/bin/env python3
"""
PMU-30 Configuration Test Suite for Nucleo-F446RE

Tests configuration and control functionality:
1. GET_CONFIG - Read current configuration
2. LOAD_CONFIG - Write configuration to device
3. SAVE_TO_FLASH - Save configuration to flash
4. Re-read config to verify
5. SET_CHANNEL_CONFIG - Atomic channel update
6. RESET - Device restart

Usage: python firmware_config_test.py [COM_PORT]
"""

import serial
import struct
import time
import sys
import json

# Protocol constants
FRAME_MARKER = 0xAA

# Message types - must match firmware pmu_protocol.h
MSG_PING = 0x01
MSG_PONG = 0x02
MSG_GET_VERSION = 0x10
MSG_GET_SERIAL = 0x03
MSG_ACK = 0xE0
MSG_NACK = 0xE1

# Config commands
MSG_GET_CONFIG = 0x20
MSG_CONFIG_DATA = 0x21
MSG_LOAD_CONFIG = 0x22
MSG_CONFIG_ACK = 0x23
MSG_SAVE_CONFIG = 0x24
MSG_FLASH_ACK = 0x25

# Channel update
MSG_SET_CHANNEL_CONFIG = 0x66
MSG_CHANNEL_CONFIG_ACK = 0x67

# Device control
MSG_RESET = 0x70
MSG_RESET_ACK = 0x71


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


class ConfigTester:
    def __init__(self, port: str, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.passed = 0
        self.failed = 0
        self.last_config = None

    def connect(self) -> bool:
        """Connect to serial port."""
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=2)
            time.sleep(0.5)
            if self.ser.in_waiting:
                self.ser.read(self.ser.in_waiting)
            return True
        except Exception as e:
            print(f"  Connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from serial port."""
        if self.ser:
            self.ser.close()
            self.ser = None

    def send_and_receive(self, frame: bytes, timeout: float = 2.0) -> bytes:
        """Send frame and receive response."""
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
                    expected_len = 4 + length + 2
                    if len(response) >= expected_len:
                        break
            time.sleep(0.05)

        return response

    def receive_all_chunks(self, timeout: float = 5.0) -> bytes:
        """Receive all config chunks and assemble."""
        chunks = {}
        total_chunks = None
        start = time.time()
        buffer = b""

        while time.time() - start < timeout:
            if self.ser.in_waiting:
                buffer += self.ser.read(self.ser.in_waiting)

            # Try to parse frames from buffer
            while len(buffer) >= 6:
                if buffer[0] != FRAME_MARKER:
                    buffer = buffer[1:]
                    continue

                length = struct.unpack("<H", buffer[1:3])[0]
                expected_len = 4 + length + 2

                if len(buffer) < expected_len:
                    break

                frame_data = buffer[:expected_len]
                buffer = buffer[expected_len:]

                parsed = parse_frame(frame_data)
                if "error" not in parsed and parsed["crc_ok"]:
                    if parsed["msg_type"] == MSG_CONFIG_DATA:
                        payload = parsed["payload"]
                        if len(payload) >= 4:
                            chunk_idx = struct.unpack("<H", payload[0:2])[0]
                            total = struct.unpack("<H", payload[2:4])[0]
                            data = payload[4:]
                            chunks[chunk_idx] = data
                            total_chunks = total

                            if len(chunks) == total_chunks:
                                # All chunks received
                                result = b""
                                for i in range(total_chunks):
                                    if i in chunks:
                                        result += chunks[i]
                                return result

            time.sleep(0.05)

        # Return partial if timeout
        if chunks:
            result = b""
            for i in sorted(chunks.keys()):
                result += chunks[i]
            return result
        return b""

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
        """Test 0: Verify connection."""
        frame = build_frame(MSG_PING)
        response = self.send_and_receive(frame)

        if not response:
            return test_result("PING", False, "No response")

        parsed = parse_frame(response)
        if "error" in parsed:
            return test_result("PING", False, parsed["error"])

        if parsed["msg_type"] == MSG_PONG and parsed["crc_ok"]:
            return test_result("PING", True, "Connection verified")
        return test_result("PING", False, f"Unexpected response: 0x{parsed['msg_type']:02X}")

    def test_get_config(self) -> bool:
        """Test 1: Read configuration from device."""
        frame = build_frame(MSG_GET_CONFIG)
        print(f"         TX: {frame.hex()}")

        self.ser.write(frame)
        self.ser.flush()
        time.sleep(0.1)

        config_data = self.receive_all_chunks(timeout=5.0)

        if not config_data:
            return test_result("GET_CONFIG", False, "No config data received")

        try:
            config_str = config_data.decode('utf-8')
            config_json = json.loads(config_str)
            self.last_config = config_json

            # Show summary
            version = config_json.get("version", "?")
            device_name = config_json.get("device", {}).get("name", "?")
            outputs_count = len(config_json.get("outputs", []))
            inputs_count = len(config_json.get("inputs", []))

            details = f"v{version}, {device_name}, {outputs_count} outputs, {inputs_count} inputs"
            return test_result("GET_CONFIG", True, details)

        except json.JSONDecodeError as e:
            return test_result("GET_CONFIG", False, f"Invalid JSON: {e}")
        except UnicodeDecodeError as e:
            return test_result("GET_CONFIG", False, f"Decode error: {e}")

    def test_load_config(self) -> bool:
        """Test 2: Write configuration to device."""
        # Create a minimal test config (must be under 256 bytes)
        test_config = {
            "version": "1.0",
            "device": {"name": "PMU-30-TEST", "serial": "TEST-001"},
            "outputs": [],
            "inputs": [],
            "hbridges": [],
            "logic": []
        }

        config_bytes = json.dumps(test_config, separators=(',', ':')).encode('utf-8')
        print(f"         Config size: {len(config_bytes)} bytes (max 256)")

        if len(config_bytes) > 256:
            return test_result("LOAD_CONFIG", False, f"Config too large: {len(config_bytes)} > 256")

        frame = build_frame(MSG_LOAD_CONFIG, config_bytes)
        print(f"         TX: {len(config_bytes)} bytes config")

        response = self.send_and_receive(frame, timeout=3.0)

        if not response:
            return test_result("LOAD_CONFIG", False, "No response")

        parsed = parse_frame(response)
        if "error" in parsed:
            return test_result("LOAD_CONFIG", False, parsed["error"])

        if parsed["msg_type"] == MSG_CONFIG_ACK and parsed["crc_ok"]:
            if len(parsed["payload"]) >= 1 and parsed["payload"][0] == 1:
                return test_result("LOAD_CONFIG", True, "Config loaded successfully")
            else:
                error_code = struct.unpack("<H", parsed["payload"][1:3])[0] if len(parsed["payload"]) >= 3 else 0
                return test_result("LOAD_CONFIG", False, f"Device rejected config, error={error_code}")

        return test_result("LOAD_CONFIG", False, f"Unexpected response: 0x{parsed['msg_type']:02X}")

    def test_save_to_flash(self) -> bool:
        """Test 3: Save configuration to flash."""
        frame = build_frame(MSG_SAVE_CONFIG)
        print(f"         TX: {frame.hex()}")

        response = self.send_and_receive(frame, timeout=3.0)

        if not response:
            return test_result("SAVE_TO_FLASH", False, "No response")

        parsed = parse_frame(response)
        if "error" in parsed:
            return test_result("SAVE_TO_FLASH", False, parsed["error"])

        if parsed["msg_type"] == MSG_FLASH_ACK and parsed["crc_ok"]:
            if len(parsed["payload"]) >= 1 and parsed["payload"][0] == 1:
                return test_result("SAVE_TO_FLASH", True, "Saved to flash")
            else:
                return test_result("SAVE_TO_FLASH", False, "Flash write failed")

        return test_result("SAVE_TO_FLASH", False, f"Unexpected response: 0x{parsed['msg_type']:02X}")

    def test_reread_config(self) -> bool:
        """Test 4: Re-read configuration and verify changes."""
        frame = build_frame(MSG_GET_CONFIG)

        self.ser.write(frame)
        self.ser.flush()
        time.sleep(0.1)

        config_data = self.receive_all_chunks(timeout=5.0)

        if not config_data:
            return test_result("REREAD_CONFIG", False, "No config data received")

        try:
            config_str = config_data.decode('utf-8')
            config_json = json.loads(config_str)

            # Verify the loaded config is present
            device_name = config_json.get("device", {}).get("name", "")

            if "PMU-30" in device_name or "TEST" in device_name:
                return test_result("REREAD_CONFIG", True, f"Config verified: {device_name}")
            else:
                return test_result("REREAD_CONFIG", False, f"Unexpected config: {device_name}")

        except Exception as e:
            return test_result("REREAD_CONFIG", False, f"Error: {e}")

    def test_set_channel_config(self) -> bool:
        """Test 5: Atomic channel configuration update."""
        # Build SET_CHANNEL_CONFIG payload:
        # [channel_type:1B][channel_id:2B LE][json_len:2B LE][json_config:NB]
        channel_type = 0x01  # power_output
        channel_id = 0
        # Note: firmware expects "channel_name" not "name"
        channel_config = json.dumps({
            "channel_name": "Updated_Output",
            "enabled": True,
            "output_pins": [1]
        }, separators=(',', ':')).encode('utf-8')

        payload = struct.pack("<BHH", channel_type, channel_id, len(channel_config))
        payload += channel_config

        frame = build_frame(MSG_SET_CHANNEL_CONFIG, payload)
        print(f"         TX: channel_type={channel_type}, id={channel_id}, config_len={len(channel_config)}")

        response = self.send_and_receive(frame, timeout=2.0)

        if not response:
            return test_result("SET_CHANNEL_CONFIG", False, "No response")

        parsed = parse_frame(response)
        if "error" in parsed:
            return test_result("SET_CHANNEL_CONFIG", False, parsed["error"])

        if parsed["msg_type"] == MSG_CHANNEL_CONFIG_ACK and parsed["crc_ok"]:
            payload = parsed["payload"]
            if len(payload) >= 3:
                resp_ch_id = struct.unpack("<H", payload[0:2])[0]
                success = payload[2] == 1

                if success:
                    return test_result("SET_CHANNEL_CONFIG", True, f"Channel {resp_ch_id} updated")
                else:
                    error_code = struct.unpack("<H", payload[3:5])[0] if len(payload) >= 5 else 0
                    error_msg = payload[5:].decode('utf-8', errors='replace') if len(payload) > 5 else ""
                    return test_result("SET_CHANNEL_CONFIG", False, f"Error {error_code}: {error_msg}")

        return test_result("SET_CHANNEL_CONFIG", False, f"Unexpected response: 0x{parsed['msg_type']:02X}")

    def test_device_reset(self) -> bool:
        """Test 6: Device reset/restart."""
        frame = build_frame(MSG_RESET)
        print(f"         TX: {frame.hex()}")

        # Send reset command
        self.ser.write(frame)
        self.ser.flush()

        # Wait for device to reset
        print("         Waiting for device to reset...")
        time.sleep(2.0)

        # Try to reconnect (device reset may have affected serial port)
        try:
            self.ser.close()
        except:
            pass

        # Wait a bit more for USB enumeration
        time.sleep(1.0)

        # Reconnect
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=2)
            time.sleep(0.5)  # Wait for connection stabilization
            if self.ser.in_waiting:
                self.ser.read(self.ser.in_waiting)  # Clear any startup data
        except Exception as e:
            return test_result("DEVICE_RESET", False, f"Failed to reconnect: {e}")

        # Check if device is back online with PING (multiple attempts)
        ping_frame = build_frame(MSG_PING)
        for attempt in range(3):
            try:
                ping_response = self.send_and_receive(ping_frame, timeout=1.0)
                if ping_response:
                    parsed = parse_frame(ping_response)
                    if "error" not in parsed and parsed["msg_type"] == MSG_PONG:
                        return test_result("DEVICE_RESET", True,
                            f"Device rebooted and responding (attempt {attempt+1})")
            except:
                pass
            time.sleep(0.3)

        return test_result("DEVICE_RESET", False, "Device not responding after reset")

    def test_multiple_channel_updates(self) -> bool:
        """Test 7: Multiple channel updates without full config reload."""
        success_count = 0
        total_updates = 3

        for i in range(total_updates):
            channel_type = 0x01  # power_output
            channel_id = i
            # Note: firmware expects "channel_name" not "name"
            channel_config = json.dumps({
                "channel_name": f"Channel_{i}",
                "enabled": i % 2 == 0,
                "output_pins": [i + 1]
            }, separators=(',', ':')).encode('utf-8')

            payload = struct.pack("<BHH", channel_type, channel_id, len(channel_config))
            payload += channel_config

            frame = build_frame(MSG_SET_CHANNEL_CONFIG, payload)
            response = self.send_and_receive(frame, timeout=1.0)

            if response:
                parsed = parse_frame(response)
                if "error" not in parsed and parsed["msg_type"] == MSG_CHANNEL_CONFIG_ACK:
                    if len(parsed["payload"]) >= 3 and parsed["payload"][2] == 1:
                        success_count += 1

            time.sleep(0.05)

        if success_count == total_updates:
            return test_result("MULTI_CHANNEL_UPDATE", True, f"{success_count}/{total_updates} channels updated")
        elif success_count > 0:
            return test_result("MULTI_CHANNEL_UPDATE", False, f"Only {success_count}/{total_updates} succeeded")
        else:
            return test_result("MULTI_CHANNEL_UPDATE", False, "No updates succeeded")

    def run_all_tests(self):
        """Run all tests."""
        print(f"\n{'='*60}")
        print(f"PMU-30 Configuration Test Suite")
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
        print("Test 1: PING (connection verify)")
        self.run_test("PING", self.test_ping)
        print()

        # Test 2: GET_CONFIG
        print("Test 2: GET_CONFIG (read current config)")
        self.run_test("GET_CONFIG", self.test_get_config)
        print()

        # Test 3: LOAD_CONFIG
        print("Test 3: LOAD_CONFIG (write config to device)")
        self.run_test("LOAD_CONFIG", self.test_load_config)
        print()

        # Test 4: SAVE_TO_FLASH
        print("Test 4: SAVE_TO_FLASH (persist config)")
        self.run_test("SAVE_TO_FLASH", self.test_save_to_flash)
        print()

        # Test 5: REREAD_CONFIG
        print("Test 5: REREAD_CONFIG (verify saved config)")
        self.run_test("REREAD_CONFIG", self.test_reread_config)
        print()

        # Test 6: SET_CHANNEL_CONFIG
        print("Test 6: SET_CHANNEL_CONFIG (atomic channel update)")
        self.run_test("SET_CHANNEL_CONFIG", self.test_set_channel_config)
        print()

        # Test 7: MULTI_CHANNEL_UPDATE
        print("Test 7: MULTI_CHANNEL_UPDATE (batch updates)")
        self.run_test("MULTI_CHANNEL_UPDATE", self.test_multiple_channel_updates)
        print()

        # Test 8: DEVICE_RESET (run last as it reboots device)
        print("Test 8: DEVICE_RESET (restart device)")
        self.run_test("DEVICE_RESET", self.test_device_reset)
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

    tester = ConfigTester(port)
    success = tester.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
