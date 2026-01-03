#!/usr/bin/env python3
"""
PMU-30 Simple Config Test (MIN Protocol)
Tests basic config operations without requiring button presses.
"""

import sys
import struct
import time
import serial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "shared" / "python"))
sys.path.insert(0, 'tests')

from channel_config import ChannelType
from protocol_helpers import (
    CMD, build_min_frame, MINFrameParser, drain_serial,
    ping, start_stream, stop_stream, clear_config, read_config,
    upload_config, save_to_flash, wait_for_telemetry, parse_telemetry
)


def build_test_config():
    """Build test config: 1 DIN, 1 Logic, 1 Output.

    Channel structure:
    - DIN (ch 50): hw_device=0x01 (GPIO), hw_index=0 (PC13 button)
    - Logic (ch 200): inputs=[50] (single input, IS_TRUE mode)
    - Output (ch 100): source=200 (Logic), hw_index=1 (LED PA5)
    """
    channels = []

    # Digital Input (ch 50) - PC13 button
    din = struct.pack('<HBBBBHiBB',
        50, ChannelType.DIGITAL_INPUT, 0x01, 0x01, 0, 0xFFFF, 0, 7, 4)
    din += b'TestDIN'
    din += struct.pack('<BBH', 0, 1, 0)  # gpio_pin=0 (PC13), active_high=1
    channels.append(din)

    # Logic IS_TRUE (ch 200) - single input, just passes through
    logic = struct.pack('<HBBBBHiBB',
        200, ChannelType.LOGIC, 0x01, 0x00, 0, 0xFFFF, 0, 8, 26)
    logic += b'LogicAND'
    logic += struct.pack('<BB', 0x06, 1)  # op=IS_TRUE(6), input_count=1
    logic += struct.pack('<H', 50)  # Input: DIN (ch 50)
    logic += b'\x00' * 14  # Remaining input slots
    logic += struct.pack('<i?3s', 0, False, b'\x00\x00\x00')  # compare_value, invert, reserved
    channels.append(logic)

    # Power Output (ch 100) - LED on PA5 (hw_index=1)
    output = struct.pack('<HBBBBHiBB',
        100, ChannelType.POWER_OUTPUT, 0x01, 0x05, 1, 200, 0, 6, 12)
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
    print("PMU-30 Simple Config Test (MIN Protocol)")
    print("=" * 60)
    print(f"Port: {port}")

    results = {}

    # Open serial once
    ser = serial.Serial(port, 115200, timeout=1.0)
    time.sleep(3.0)  # Device startup
    stop_stream(ser)  # Ensure clean state
    time.sleep(0.5)  # Extra wait for stream to fully stop

    # Test 1: PING
    print("\n[TEST] PING")
    if ping(ser, timeout=2.0):
        print("  OK - PONG received")
        results["PING"] = True
    else:
        print("  FAIL - No PONG")
        results["PING"] = False

    # Test 2: Clear config
    print("\n[TEST] CLEAR_CONFIG")
    if clear_config(ser):
        print("  OK - Config cleared")
        results["CLEAR"] = True
    else:
        print("  FAIL - Clear failed")
        results["CLEAR"] = False

    # Test 3: Upload config
    print("\n[TEST] Upload Config")
    config = build_test_config()
    success, channels_loaded = upload_config(ser, config)
    if success:
        print(f"  OK - Uploaded {len(config)} bytes, {channels_loaded} channels")
        results["UPLOAD"] = True
    else:
        print("  FAIL - Upload failed")
        results["UPLOAD"] = False

    # Test 4: Read config back
    print("\n[TEST] Read Config")
    cfg = read_config(ser)
    if cfg is not None:
        count = struct.unpack('<H', cfg[:2])[0] if len(cfg) >= 2 else 0
        print(f"  OK - Read {len(cfg)} bytes, {count} channels")
        results["READ"] = count >= 1
    else:
        print("  FAIL - No config data")
        results["READ"] = False

    # Test 5: Save to flash
    print("\n[TEST] Save to Flash")
    if save_to_flash(ser):
        print("  OK - Saved to flash")
        results["FLASH"] = True
    else:
        print("  FAIL - Flash save failed")
        results["FLASH"] = False

    # Test 6: Telemetry
    print("\n[TEST] Telemetry")
    start_stream(ser, rate_hz=10)
    telem = wait_for_telemetry(ser, timeout=2.0)
    stop_stream(ser)

    if telem:
        print(f"  OK - Received telemetry (counter={telem.stream_counter})")
        print(f"       Uptime: {telem.uptime_sec}s, Channels: {telem.channel_count}")
        print(f"       Virtual channels: {telem.virtual_channels}")
        results["TELEMETRY"] = True
    else:
        print("  FAIL - No telemetry")
        results["TELEMETRY"] = False

    # Cleanup
    print("\n[CLEANUP] Clear config")
    clear_config(ser)
    ser.close()

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
