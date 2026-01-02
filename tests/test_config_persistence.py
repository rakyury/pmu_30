#!/usr/bin/env python3
"""
PMU-30 Comprehensive Config Persistence Test

Tests:
1. Config round-trip: upload → read → verify identical
2. Config persistence: upload → flash → restart → read → verify
3. Telemetry works with empty config (system channels only)
4. CLEAR_CONFIG clears memory and flash

Usage: python tests/test_config_persistence.py [COM_PORT]
"""

import sys
import struct
import time
import serial
from pathlib import Path

# Add shared path
sys.path.insert(0, str(Path(__file__).parent.parent / "shared" / "python"))
from channel_config import ChannelType

# Protocol commands
CMD_PING = 0x01
CMD_PONG = 0x02
CMD_GET_CONFIG = 0x20
CMD_CONFIG_DATA = 0x21
CMD_SAVE_CONFIG = 0x24
CMD_FLASH_ACK = 0x25
CMD_CLEAR_CONFIG = 0x26
CMD_CLEAR_CONFIG_ACK = 0x27
CMD_START_STREAM = 0x30
CMD_STOP_STREAM = 0x31
CMD_TELEMETRY = 0x32
CMD_LOAD_BINARY_CONFIG = 0x68
CMD_BINARY_CONFIG_ACK = 0x69
CMD_RESTART = 0x70


def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = (crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1
        crc &= 0xFFFF
    return crc


def build_frame(cmd: int, payload: bytes = b'') -> bytes:
    header = struct.pack('<BHB', 0xAA, len(payload), cmd)
    crc = crc16(struct.pack('<HB', len(payload), cmd) + payload)
    return header + payload + struct.pack('<H', crc)


def parse_frames(data: bytes) -> list:
    frames = []
    while len(data) >= 6:
        if data[0] != 0xAA:
            data = data[1:]
            continue
        length = struct.unpack('<H', data[1:3])[0]
        total_len = 4 + length + 2
        if len(data) < total_len:
            break
        cmd = data[3]
        payload = data[4:4+length]
        frames.append((cmd, payload))
        data = data[total_len:]
    return frames


def send_recv(ser, cmd, payload=b'', timeout=2.0, expect_cmd=None):
    """Send command and receive response."""
    ser.reset_input_buffer()
    ser.write(build_frame(cmd, payload))

    start = time.time()
    data = b''
    while time.time() - start < timeout:
        chunk = ser.read(4096)
        if chunk:
            data += chunk
            if expect_cmd:
                frames = parse_frames(data)
                for c, _ in frames:
                    if c == expect_cmd:
                        return frames
        time.sleep(0.05)
    return parse_frames(data)


def build_test_config():
    """Build test config: 1 DIN, 1 Logic, 1 Output."""
    channels = []

    # Digital Input (user-created)
    din = struct.pack('<HBBBBHiBB',
        100, ChannelType.DIGITAL_INPUT, 0x01, 0x01, 0, 0xFFFF, 0, 7, 4)
    din += b'TestDIN'  # name
    din += struct.pack('<BBH', 50, 1, 0)  # debounce, active_high, pullup
    channels.append(din)

    # Logic AND
    logic = struct.pack('<HBBBBHiBB',
        200, ChannelType.LOGIC, 0x01, 0x00, 0, 0xFFFF, 0, 8, 26)
    logic += b'LogicAND'
    logic += struct.pack('<BB', 0x00, 2)  # AND, 2 inputs
    for inp in [50, 51]:  # DIN0, DIN1
        logic += struct.pack('<H', inp)
    logic += b'\x00' * 12  # padding
    logic += struct.pack('<ii', 0, 0)  # threshold, hyst
    channels.append(logic)

    # Power Output linked to Logic
    output = struct.pack('<HBBBBHiBB',
        300, ChannelType.POWER_OUTPUT, 0x01, 0x05, 1, 200, 0, 6, 12)
    output += b'OutLED'
    output += struct.pack('<HHHBBHBB', 1000, 0, 0, 100, 1, 0, 3, 0)
    channels.append(output)

    # Build binary
    result = struct.pack('<H', len(channels))
    for ch in channels:
        result += ch
    return result


def parse_config(data: bytes) -> dict:
    """Parse binary config into readable format."""
    if len(data) < 2:
        return {"channels": [], "raw": data.hex()}

    count = struct.unpack('<H', data[:2])[0]
    offset = 2
    channels = []

    for _ in range(count):
        if offset + 14 > len(data):
            break
        ch_id = struct.unpack('<H', data[offset:offset+2])[0]
        ch_type = data[offset+2]
        name_len = data[offset+12]
        cfg_size = data[offset+13]
        offset += 14

        name = data[offset:offset+name_len].decode('utf-8', errors='replace')
        offset += name_len + cfg_size

        channels.append({"id": ch_id, "type": ch_type, "name": name})

    return {"channels": channels, "raw": data.hex()}


def test_ping(ser):
    print("\n[TEST] PING")
    frames = send_recv(ser, CMD_PING, expect_cmd=CMD_PONG)
    if any(c == CMD_PONG for c, _ in frames):
        print("  [OK] PONG received")
        return True
    print("  [FAIL] No PONG")
    return False


def test_clear_config(ser):
    """Test CLEAR_CONFIG command."""
    print("\n[TEST] CLEAR_CONFIG")

    # Send clear command
    frames = send_recv(ser, CMD_CLEAR_CONFIG, expect_cmd=CMD_CLEAR_CONFIG_ACK, timeout=3.0)

    ack_ok = False
    for cmd, payload in frames:
        if cmd == CMD_CLEAR_CONFIG_ACK:
            success = payload[0] if len(payload) > 0 else 0
            print(f"  ACK received: success={success}")
            ack_ok = success == 1

    if not ack_ok:
        print("  [FAIL] Clear failed or no ACK")
        return False

    time.sleep(0.3)

    # Verify config is empty
    frames = send_recv(ser, CMD_GET_CONFIG, expect_cmd=CMD_CONFIG_DATA)
    for cmd, payload in frames:
        if cmd == CMD_CONFIG_DATA:
            data = payload[4:]  # skip chunk header
            if len(data) >= 2:
                count = struct.unpack('<H', data[:2])[0]
                print(f"  Channel count after clear: {count}")
                if count == 0:
                    print("  [OK] Config cleared!")
                    return True

    print("  [FAIL] Config not empty")
    return False


def test_round_trip(ser):
    """Test config upload and read-back."""
    print("\n[TEST] Config Round-Trip")

    config = build_test_config()
    print(f"  Config: {len(config)} bytes, 3 channels")

    # Upload
    chunked = struct.pack('<HH', 0, 1) + config
    frames = send_recv(ser, CMD_LOAD_BINARY_CONFIG, chunked, expect_cmd=CMD_BINARY_CONFIG_ACK, timeout=3.0)

    ack_ok = False
    for cmd, payload in frames:
        if cmd == CMD_BINARY_CONFIG_ACK:
            success = payload[0] if len(payload) > 0 else 0
            print(f"  Upload ACK: success={success}")
            ack_ok = success == 1

    if not ack_ok:
        print("  [FAIL] Upload failed")
        return False

    time.sleep(0.5)
    ser.reset_input_buffer()  # Clear any pending data

    # Read back
    frames = send_recv(ser, CMD_GET_CONFIG, expect_cmd=CMD_CONFIG_DATA, timeout=3.0)
    received = None
    for cmd, payload in frames:
        if cmd == CMD_CONFIG_DATA:
            received = payload[4:]  # skip chunk header

    if received is None:
        print("  [FAIL] No CONFIG_DATA")
        return False

    # Compare
    original = parse_config(config)
    readback = parse_config(received)

    print(f"  Original: {len(original['channels'])} channels")
    print(f"  Readback: {len(readback['channels'])} channels")

    if len(original['channels']) != len(readback['channels']):
        print("  [FAIL] Channel count mismatch")
        return False

    for o, r in zip(original['channels'], readback['channels']):
        if o['id'] != r['id'] or o['name'] != r['name']:
            print(f"  [FAIL] Channel mismatch: {o} vs {r}")
            return False
        print(f"    - {r['name']} (id={r['id']}, type={r['type']:#x}) OK")

    print("  [OK] Config round-trip successful!")
    return True


def test_persistence(ser):
    """Test config persistence across restart."""
    print("\n[TEST] Config Persistence")

    # Reset serial state
    time.sleep(1.0)  # Wait for device to settle after round-trip
    ser.timeout = 2.0
    ser.reset_input_buffer()

    # First verify device is responsive
    test_frames = send_recv(ser, CMD_PING, expect_cmd=CMD_PONG, timeout=2.0)
    if not any(c == CMD_PONG for c, _ in test_frames):
        print("  [DEBUG] Device not responding to PING, retrying...")
        time.sleep(0.5)
        test_frames = send_recv(ser, CMD_PING, expect_cmd=CMD_PONG, timeout=2.0)
        if not any(c == CMD_PONG for c, _ in test_frames):
            print("  [DEBUG] Device still not responding")
            return False
    print("  Device responsive")

    # Clear existing config first
    send_recv(ser, CMD_CLEAR_CONFIG, expect_cmd=CMD_CLEAR_CONFIG_ACK, timeout=3.0)
    time.sleep(0.5)
    print("  Cleared existing config")

    # Clear any pending data
    ser.reset_input_buffer()

    # Upload config
    config = build_test_config()
    chunked = struct.pack('<HH', 0, 1) + config
    print(f"  Sending config upload ({len(chunked)} bytes)...")

    # Ensure proper serial timeout
    ser.timeout = 2.0
    ser.reset_input_buffer()

    # Direct send/receive for debugging
    ser.write(build_frame(CMD_LOAD_BINARY_CONFIG, chunked))
    time.sleep(0.5)
    data = ser.read(4096)
    print(f"  [DEBUG] Raw response: {len(data)} bytes")
    frames = parse_frames(data)

    upload_ok = any(c == CMD_BINARY_CONFIG_ACK and p[0] == 1 for c, p in frames if len(p) > 0)
    if not upload_ok:
        print(f"  [DEBUG] Frames received: {[(hex(c), p.hex() if p else '') for c, p in frames]}")
        print("  [FAIL] Upload failed")
        return False
    print("  Uploaded config")

    time.sleep(0.3)

    # Save to flash
    frames = send_recv(ser, CMD_SAVE_CONFIG, expect_cmd=CMD_FLASH_ACK, timeout=5.0)
    if not any(c == CMD_FLASH_ACK and p[0] == 1 for c, p in frames if len(p) > 0):
        print("  [FAIL] Flash save failed")
        return False
    print("  Saved to flash")

    # Get config before restart
    time.sleep(0.3)
    ser.reset_input_buffer()
    frames = send_recv(ser, CMD_GET_CONFIG, expect_cmd=CMD_CONFIG_DATA, timeout=3.0)
    before = None
    for cmd, payload in frames:
        print(f"  [DEBUG] Got frame: cmd=0x{cmd:02X}, len={len(payload)}")
        if cmd == CMD_CONFIG_DATA:
            before = payload[4:]

    if before is None:
        print(f"  [DEBUG] Total frames: {len(frames)}")
        print("  [FAIL] Could not read config before restart")
        return False

    before_parsed = parse_config(before)
    print(f"  Before restart: {len(before_parsed['channels'])} channels")

    # Restart device
    print("  Restarting device...")
    ser.write(build_frame(CMD_RESTART))
    time.sleep(3.0)
    ser.reset_input_buffer()

    # Verify device is back
    if not test_ping(ser):
        print("  [FAIL] Device not responding after restart")
        return False

    time.sleep(0.5)

    # Read config after restart
    frames = send_recv(ser, CMD_GET_CONFIG, expect_cmd=CMD_CONFIG_DATA)
    after = None
    for cmd, payload in frames:
        if cmd == CMD_CONFIG_DATA:
            after = payload[4:]

    if after is None:
        print("  [FAIL] Could not read config after restart")
        return False

    after_parsed = parse_config(after)
    print(f"  After restart: {len(after_parsed['channels'])} channels")

    # Compare
    if len(before_parsed['channels']) != len(after_parsed['channels']):
        print("  [FAIL] Channel count mismatch after restart")
        return False

    for b, a in zip(before_parsed['channels'], after_parsed['channels']):
        if b['id'] != a['id'] or b['name'] != a['name']:
            print(f"  [FAIL] Channel mismatch: {b} vs {a}")
            return False

    print("  [OK] Config persisted across restart!")
    return True


def test_telemetry_empty_config(ser):
    """Test telemetry works even with empty config."""
    print("\n[TEST] Telemetry with Empty Config")

    # First clear config
    frames = send_recv(ser, CMD_CLEAR_CONFIG, expect_cmd=CMD_CLEAR_CONFIG_ACK, timeout=3.0)
    time.sleep(0.3)

    # Start telemetry
    ser.write(build_frame(CMD_START_STREAM))
    time.sleep(0.3)

    # Collect packets
    packets = []
    start = time.time()
    while time.time() - start < 2.0:
        data = ser.read(4096)
        if data:
            for cmd, payload in parse_frames(data):
                if cmd == CMD_TELEMETRY:
                    packets.append(payload)
        time.sleep(0.05)

    # Stop telemetry and clean up buffer
    ser.write(build_frame(CMD_STOP_STREAM))
    time.sleep(0.5)  # Wait for stream to fully stop
    ser.reset_input_buffer()
    # Flush any remaining data (non-blocking)
    old_timeout = ser.timeout
    ser.timeout = 0.1
    while ser.read(4096):
        pass
    ser.timeout = old_timeout

    if len(packets) == 0:
        print("  [FAIL] No telemetry packets")
        return False

    print(f"  Received {len(packets)} telemetry packets")

    # Parse first packet
    pkt = packets[0]
    if len(pkt) >= 104:
        counter = struct.unpack('<I', pkt[0:4])[0]
        timestamp = struct.unpack('<I', pkt[4:8])[0]
        din_mask = pkt[78]
        voltage = struct.unpack('<H', pkt[94:96])[0]
        virtual_count = struct.unpack('<H', pkt[104:106])[0] if len(pkt) >= 106 else 0

        print(f"  Counter: {counter}")
        print(f"  Timestamp: {timestamp}ms (uptime)")
        print(f"  Digital inputs: {din_mask:08b}")
        print(f"  Virtual channels: {virtual_count}")

        print("  [OK] System telemetry works with empty config!")
        return True

    print("  [FAIL] Invalid telemetry packet")
    return False


def reset_device_state(ser):
    """Reset device to known state between tests."""
    time.sleep(0.3)
    ser.reset_input_buffer()
    # Brief flush with short timeout
    old_timeout = ser.timeout
    ser.timeout = 0.1
    while ser.read(4096):
        pass
    ser.timeout = old_timeout


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM11"
    print("=" * 60)
    print("PMU-30 Config Persistence Test Suite")
    print("=" * 60)
    print(f"Port: {port}")

    try:
        ser = serial.Serial(port, 115200, timeout=2.0)
        time.sleep(1.0)  # Give device time to initialize
        ser.reset_input_buffer()

        results = {}

        # Test 1: PING
        results["PING"] = test_ping(ser)
        reset_device_state(ser)

        # Test 2: Clear config
        results["CLEAR_CONFIG"] = test_clear_config(ser)
        reset_device_state(ser)

        # Test 3: Telemetry with empty config
        results["Telemetry (empty)"] = test_telemetry_empty_config(ser)
        reset_device_state(ser)

        # Test 4: Round-trip
        results["Round-trip"] = test_round_trip(ser)
        reset_device_state(ser)

        # Test 5: Persistence
        results["Persistence"] = test_persistence(ser)
        reset_device_state(ser)

        # Final clear
        test_clear_config(ser)

        ser.close()

        print("\n" + "=" * 60)
        print("RESULTS:")
        print("=" * 60)
        for name, passed in results.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {status} {name}")

        all_passed = all(results.values())
        print("=" * 60)
        print("ALL TESTS PASSED!" if all_passed else "SOME TESTS FAILED")

        return 0 if all_passed else 1

    except serial.SerialException as e:
        print(f"Serial error: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
