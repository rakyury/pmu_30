#!/usr/bin/env python3
"""
PMU-30 Simple Config Test - Reliable serial communication.
Reopens serial port between tests for clean state.
"""

import sys
import struct
import time
import serial
from pathlib import Path

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


def transact(port: str, cmd: int, payload: bytes = b'', timeout: float = 2.0) -> list:
    """Open serial, send command, get response, close serial."""
    ser = serial.Serial(port, 115200, timeout=timeout)
    time.sleep(0.1)
    ser.reset_input_buffer()
    ser.write(build_frame(cmd, payload))
    time.sleep(0.3)
    data = ser.read(4096)
    ser.close()
    return parse_frames(data)


def build_test_config():
    """Build test config: 1 DIN, 1 Logic, 1 Output."""
    channels = []

    din = struct.pack('<HBBBBHiBB',
        100, ChannelType.DIGITAL_INPUT, 0x01, 0x01, 0, 0xFFFF, 0, 7, 4)
    din += b'TestDIN'
    din += struct.pack('<BBH', 50, 1, 0)
    channels.append(din)

    logic = struct.pack('<HBBBBHiBB',
        200, ChannelType.LOGIC, 0x01, 0x00, 0, 0xFFFF, 0, 8, 26)
    logic += b'LogicAND'
    logic += struct.pack('<BB', 0x00, 2)
    for inp in [50, 51]:
        logic += struct.pack('<H', inp)
    logic += b'\x00' * 12
    logic += struct.pack('<ii', 0, 0)
    channels.append(logic)

    output = struct.pack('<HBBBBHiBB',
        300, ChannelType.POWER_OUTPUT, 0x01, 0x05, 1, 200, 0, 6, 12)
    output += b'OutLED'
    output += struct.pack('<HHHBBHBB', 1000, 0, 0, 100, 1, 0, 3, 0)
    channels.append(output)

    result = struct.pack('<H', len(channels))
    for ch in channels:
        result += ch
    return result


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM11"
    print("=" * 60)
    print("PMU-30 Simple Config Test")
    print("=" * 60)
    print(f"Port: {port}")

    results = {}

    # Test 1: PING
    print("\n[TEST] PING")
    frames = transact(port, CMD_PING)
    if any(c == CMD_PONG for c, _ in frames):
        print("  OK - PONG received")
        results["PING"] = True
    else:
        print("  FAIL - No PONG")
        results["PING"] = False

    # Test 2: Clear config
    print("\n[TEST] CLEAR_CONFIG")
    frames = transact(port, CMD_CLEAR_CONFIG, timeout=3.0)
    ack = next((p for c, p in frames if c == CMD_CLEAR_CONFIG_ACK), None)
    if ack and ack[0] == 1:
        print("  OK - Config cleared")
        results["CLEAR"] = True
    else:
        print("  FAIL - Clear failed")
        results["CLEAR"] = False

    # Test 3: Upload config
    print("\n[TEST] Upload Config")
    config = build_test_config()
    chunked = struct.pack('<HH', 0, 1) + config
    frames = transact(port, CMD_LOAD_BINARY_CONFIG, chunked, timeout=3.0)
    ack = next((p for c, p in frames if c == CMD_BINARY_CONFIG_ACK), None)
    if ack and ack[0] == 1:
        print(f"  OK - Uploaded {len(config)} bytes")
        results["UPLOAD"] = True
    else:
        print("  FAIL - Upload failed")
        results["UPLOAD"] = False

    # Test 4: Read config back
    print("\n[TEST] Read Config")
    time.sleep(0.3)
    frames = transact(port, CMD_GET_CONFIG, timeout=3.0)
    cfg = next((p for c, p in frames if c == CMD_CONFIG_DATA), None)
    if cfg:
        data = cfg[4:]  # skip chunk header
        count = struct.unpack('<H', data[:2])[0] if len(data) >= 2 else 0
        print(f"  OK - Read {len(data)} bytes, {count} channels")
        results["READ"] = count == 3
    else:
        print("  FAIL - No config data")
        results["READ"] = False

    # Test 5: Save to flash (needs longer connection)
    print("\n[TEST] Save to Flash")
    ser = serial.Serial(port, 115200, timeout=5.0)
    time.sleep(0.2)
    ser.reset_input_buffer()
    ser.write(build_frame(CMD_SAVE_CONFIG))
    time.sleep(2.0)  # Flash erase/write takes time
    data = ser.read(4096)
    ser.close()
    frames = parse_frames(data)
    ack = next((p for c, p in frames if c == CMD_FLASH_ACK), None)
    if ack and ack[0] == 1:
        print("  OK - Saved to flash")
        results["FLASH"] = True
    else:
        print(f"  FAIL - Flash save failed (got {len(frames)} frames)")
        results["FLASH"] = False

    # Test 6: Telemetry with system info
    print("\n[TEST] Telemetry")
    time.sleep(0.5)  # Wait after flash operation
    ser = serial.Serial(port, 115200, timeout=2.0)
    time.sleep(0.2)
    ser.reset_input_buffer()
    ser.write(build_frame(CMD_START_STREAM))
    time.sleep(2.0)  # Collect telemetry for 2 seconds
    data = ser.read(4096)
    ser.write(build_frame(CMD_STOP_STREAM))
    time.sleep(0.2)
    ser.close()

    packets = [p for c, p in parse_frames(data) if c == CMD_TELEMETRY]
    if packets:
        pkt = packets[-1]
        if len(pkt) >= 94:
            uptime = struct.unpack('<I', pkt[79:83])[0]
            ram = struct.unpack('<I', pkt[83:87])[0]
            flash = struct.unpack('<I', pkt[87:91])[0]
            ch_count = struct.unpack('<H', pkt[91:93])[0]
            print(f"  OK - {len(packets)} packets")
            print(f"       Uptime: {uptime}s, RAM: {ram}B, Flash: {flash}B, Channels: {ch_count}")
            results["TELEMETRY"] = True
        else:
            print("  FAIL - Packet too short")
            results["TELEMETRY"] = False
    else:
        print("  FAIL - No telemetry")
        results["TELEMETRY"] = False

    # Final cleanup
    print("\n[CLEANUP] Clear config")
    transact(port, CMD_CLEAR_CONFIG, timeout=3.0)

    # Summary
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


if __name__ == '__main__':
    sys.exit(main())
