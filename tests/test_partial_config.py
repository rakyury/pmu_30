#!/usr/bin/env python3
"""
PMU-30 Partial Config Changes Test

Tests create/edit/delete operations on channels:
- Create: Add new channel and verify in readback
- Edit: Modify existing channel value and verify
- Delete: Clear config and verify empty

Usage: python tests/test_partial_config.py [COM_PORT]
"""

import sys
import struct
import time
import serial

sys.path.insert(0, 'tests')
from protocol_helpers import (
    CMD, build_min_frame, MINFrameParser, drain_serial,
    ping, clear_config, upload_config, read_config, parse_channels,
    start_stream, stop_stream, parse_telemetry
)

# Channel types
CH_TYPE_NUMBER = 0x27
CH_TYPE_LOGIC = 0x21
CH_TYPE_TIMER = 0x20
CH_TYPE_POWER_OUTPUT = 0x10
CH_REF_NONE = 0xFFFF

# Logic operations
LOGIC_OP_IS_TRUE = 0x06
LOGIC_OP_GT = 0x08


def build_header(channel_id, channel_type, hw_device=0, hw_index=0,
                 source_id=CH_REF_NONE, name="", config_size=0):
    """Build CfgChannelHeader_t (14 bytes) + name."""
    name_bytes = name.encode('utf-8')[:31]
    return struct.pack('<HBBBBHiBB',
        channel_id, channel_type, 0x01, hw_device, hw_index, source_id, 0,
        len(name_bytes), config_size
    ) + name_bytes


def build_number_config(value=1, min_val=0, max_val=100, step=1):
    """Build CfgNumber_t (20 bytes)."""
    return struct.pack('<iiiiBB2s', value, min_val, max_val, step, 1, 0, b'\x00\x00')


def build_logic_config(inputs, operation=LOGIC_OP_IS_TRUE, compare_value=0):
    """Build CfgLogic_t (26 bytes)."""
    inputs_padded = inputs + [0] * (8 - len(inputs))
    return struct.pack('<BB8HiB3s', operation, len(inputs), *inputs_padded, compare_value, 0, b'\x00\x00\x00')


def run_tests(port):
    print("=" * 60)
    print("PMU-30 Partial Config Changes Test")
    print("=" * 60)
    print(f"Port: {port}")

    results = {}

    try:
        ser = serial.Serial(port, 115200, timeout=1.0, write_timeout=1.0)
        time.sleep(1.5)

        stop_stream(ser)
        drain_serial(ser, 200)

        # Test 0: Connection
        print("\n[TEST 0] Connection")
        if not ping(ser, timeout=2.0):
            print("  FAIL - Device not responding")
            return 1
        print("  OK - Device responding")
        results["Connection"] = True

        # Test 1: Create single Number channel
        print("\n[TEST 1] Create Single Number Channel")
        if clear_config(ser):
            print("  Config cleared")
        else:
            print("  Warning: Clear config failed")

        time.sleep(0.3)
        drain_serial(ser, 100)

        number_cfg = build_number_config(value=42)
        number_hdr = build_header(100, CH_TYPE_NUMBER, name="test_num", config_size=len(number_cfg))
        config1 = struct.pack('<H', 1) + number_hdr + number_cfg

        chunked = struct.pack('<HH', 0, 1) + config1
        frame = build_min_frame(CMD.LOAD_BINARY, chunked)
        ser.write(frame)
        ser.flush()

        parser = MINFrameParser()
        start = time.time()
        success = False
        while time.time() - start < 3.0:
            chunk = ser.read(512)
            if chunk:
                frames = parser.feed(chunk)
                for cmd, payload, seq, _ in frames:
                    if cmd == CMD.BINARY_ACK:
                        status = payload[0] if len(payload) > 0 else 0
                        loaded = struct.unpack('<H', payload[2:4])[0] if len(payload) >= 4 else 0
                        if status == 1 and loaded == 1:
                            success = True
                            print(f"  Upload OK - loaded {loaded} channel")
                        break
            if success:
                break

        if success:
            # Verify via readback
            time.sleep(0.3)
            drain_serial(ser, 100)
            config_data = read_config(ser)
            if config_data:
                channels = parse_channels(config_data)
                if len(channels) == 1 and channels[0]['id'] == 100:
                    print(f"  Readback OK - channel ID={channels[0]['id']}, name='{channels[0]['name']}'")
                    results["CreateNumber"] = True
                else:
                    print(f"  FAIL - Wrong readback: {channels}")
                    results["CreateNumber"] = False
            else:
                print("  FAIL - No config readback")
                results["CreateNumber"] = False
        else:
            print("  FAIL - Upload failed")
            results["CreateNumber"] = False

        # Test 2: Create multiple channels
        print("\n[TEST 2] Create Multiple Channels")
        clear_config(ser)
        time.sleep(0.5)  # Wait for clear to complete
        drain_serial(ser, 200)

        num1_cfg = build_number_config(value=10)
        num1_hdr = build_header(50, CH_TYPE_NUMBER, name="num1", config_size=len(num1_cfg))

        num2_cfg = build_number_config(value=20)
        num2_hdr = build_header(51, CH_TYPE_NUMBER, name="num2", config_size=len(num2_cfg))

        logic_cfg = build_logic_config([50], LOGIC_OP_IS_TRUE)
        logic_hdr = build_header(200, CH_TYPE_LOGIC, name="logic1", config_size=len(logic_cfg))

        config2 = (struct.pack('<H', 3) +
                   num1_hdr + num1_cfg +
                   num2_hdr + num2_cfg +
                   logic_hdr + logic_cfg)

        chunked = struct.pack('<HH', 0, 1) + config2
        ser.write(build_min_frame(CMD.LOAD_BINARY, chunked))
        ser.flush()

        parser = MINFrameParser()
        start = time.time()
        success = False
        loaded_count = 0
        while time.time() - start < 3.0:
            chunk = ser.read(512)
            if chunk:
                frames = parser.feed(chunk)
                for cmd, payload, seq, _ in frames:
                    if cmd == CMD.BINARY_ACK:
                        status = payload[0] if len(payload) > 0 else 0
                        loaded_count = struct.unpack('<H', payload[2:4])[0] if len(payload) >= 4 else 0
                        success = status == 1
                        break
            if success:
                break

        if success and loaded_count == 3:
            print(f"  Upload OK - loaded {loaded_count} channels")
            time.sleep(0.5)  # Wait for config to settle
            drain_serial(ser, 200)
            config_data = read_config(ser)
            if config_data:
                channels = parse_channels(config_data)
                if len(channels) == 3:
                    ids = [ch['id'] for ch in channels]
                    if set(ids) == {50, 51, 200}:
                        print(f"  Readback OK - channels: {ids}")
                        results["CreateMultiple"] = True
                    else:
                        print(f"  FAIL - Wrong IDs: {ids}")
                        results["CreateMultiple"] = False
                else:
                    print(f"  FAIL - Wrong count: {len(channels)}")
                    results["CreateMultiple"] = False
            else:
                print("  FAIL - No readback")
                results["CreateMultiple"] = False
        else:
            print(f"  FAIL - Upload failed (success={success}, loaded={loaded_count})")
            results["CreateMultiple"] = False

        # Test 3: Replace config (simulates edit)
        print("\n[TEST 3] Replace Config (Edit Simulation)")
        # Wait for previous test to fully complete
        time.sleep(1.0)
        stop_stream(ser)  # Make sure no streaming
        drain_serial(ser, 300)

        # Re-use config1 from Test 1 - upload and verify it replaces the 3-channel config
        success, loaded = upload_config(ser, config1)
        if success and loaded == 1:
            print(f"  Replace OK - now {loaded} channel (was 3)")
            results["ReplaceConfig"] = True
        else:
            print(f"  FAIL - Replace failed (success={success}, loaded={loaded})")
            results["ReplaceConfig"] = False

        # Test 4: Delete config (clear)
        print("\n[TEST 4] Delete Config (Clear)")
        time.sleep(0.5)
        drain_serial(ser, 200)
        if clear_config(ser):
            time.sleep(0.3)
            drain_serial(ser, 100)
            config_data = read_config(ser)
            if config_data:
                channels = parse_channels(config_data)
                if len(channels) == 0:
                    print("  Clear OK - config empty")
                    results["DeleteConfig"] = True
                else:
                    print(f"  FAIL - Still has {len(channels)} channels")
                    results["DeleteConfig"] = False
            else:
                print("  Clear OK - no config data")
                results["DeleteConfig"] = True
        else:
            print("  FAIL - Clear command failed")
            results["DeleteConfig"] = False

        # Test 5: Verify virtual channel in telemetry after config
        print("\n[TEST 5] Virtual Channel in Telemetry")
        drain_serial(ser, 100)

        num_cfg = build_number_config(value=1)
        num_hdr = build_header(100, CH_TYPE_NUMBER, name="src", config_size=len(num_cfg))
        logic_cfg = build_logic_config([100], LOGIC_OP_IS_TRUE)
        logic_hdr = build_header(200, CH_TYPE_LOGIC, name="virt", config_size=len(logic_cfg))

        config5 = struct.pack('<H', 2) + num_hdr + num_cfg + logic_hdr + logic_cfg
        chunked = struct.pack('<HH', 0, 1) + config5
        ser.write(build_min_frame(CMD.LOAD_BINARY, chunked))
        ser.flush()

        parser = MINFrameParser()
        start = time.time()
        while time.time() - start < 3.0:
            chunk = ser.read(512)
            if chunk:
                frames = parser.feed(chunk)
                for cmd, payload, seq, _ in frames:
                    if cmd == CMD.BINARY_ACK:
                        break

        time.sleep(0.5)
        drain_serial(ser, 200)

        start_stream(ser, rate_hz=10)
        time.sleep(0.5)

        found_virtual = False
        parser = MINFrameParser()
        start = time.time()
        while time.time() - start < 3.0:
            chunk = ser.read(512)
            if chunk:
                frames = parser.feed(chunk)
                for cmd, payload, seq, _ in frames:
                    if cmd == CMD.DATA:
                        tel = parse_telemetry(payload)
                        if tel and tel.virtual_channels:
                            if 200 in tel.virtual_channels:
                                print(f"  Found virtual channel 200 = {tel.virtual_channels[200]}")
                                found_virtual = True
                                break
            if found_virtual:
                break

        stop_stream(ser)

        if found_virtual:
            print("  OK - Virtual channel appears in telemetry")
            results["VirtualInTelemetry"] = True
        else:
            print("  FAIL - Virtual channel not found in telemetry")
            results["VirtualInTelemetry"] = False

        ser.close()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print("\n" + "=" * 60)
    print("RESULTS:")
    print("=" * 60)
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")

    failed = sum(1 for v in results.values() if not v)
    print("=" * 60)
    print(f"PASSED: {len(results) - failed}/{len(results)}")

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    port = sys.argv[1] if len(sys.argv) > 1 else "COM11"
    sys.exit(run_tests(port))
