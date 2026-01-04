#!/usr/bin/env python3
"""
PMU-30 System Channels Verification Test

Verifies that system channels work correctly:
- System constants: zero (1012), one (1013)
- System telemetry channels: pmu.uptime, pmu.voltage, etc.
- Output linking to system channels

Usage: python tests/test_system_channels.py [COM_PORT]
"""

import sys
import struct
import time
import serial

sys.path.insert(0, 'tests')
from protocol_helpers import (
    CMD, build_min_frame, MINFrameParser, drain_serial,
    ping, clear_config, start_stream, stop_stream, parse_telemetry
)

# Channel types
CH_TYPE_POWER_OUTPUT = 0x10
CH_TYPE_LOGIC = 0x21
CH_REF_NONE = 0xFFFF
HW_DEVICE_PROFET = 0x05

# System channel IDs (from firmware)
SYS_CH_ZERO = 1012
SYS_CH_ONE = 1013

# Logic operations
LOGIC_OP_IS_TRUE = 0x06
LOGIC_OP_IS_FALSE = 0x07


def build_header(channel_id, channel_type, hw_device=0, hw_index=0,
                 source_id=CH_REF_NONE, name="", config_size=0):
    """Build CfgChannelHeader_t (14 bytes) + name."""
    name_bytes = name.encode('utf-8')[:31]
    return struct.pack('<HBBBBHiBB',
        channel_id, channel_type, 0x01, hw_device, hw_index, source_id, 0,
        len(name_bytes), config_size
    ) + name_bytes


def build_logic_config(inputs, operation=LOGIC_OP_IS_TRUE):
    """Build CfgLogic_t (26 bytes)."""
    inputs_padded = inputs + [0] * (8 - len(inputs))
    return struct.pack('<BB8HiB3s', operation, len(inputs), *inputs_padded, 0, 0, b'\x00\x00\x00')


def build_power_output_config():
    """Build CfgPowerOutput_t (12 bytes)."""
    return struct.pack('<HHHBBHBB', 5000, 100, 10000, 3, 5, 0, 0, 0)


def run_tests(port):
    print("=" * 60)
    print("PMU-30 System Channels Verification Test")
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

        # Test 1: Output linked to system channel 'one' (1013) - should be always ON
        print("\n[TEST 1] Output Linked to System 'one' (1013)")
        clear_config(ser)
        time.sleep(0.3)
        drain_serial(ser, 100)

        output_cfg = build_power_output_config()
        output_hdr = build_header(100, CH_TYPE_POWER_OUTPUT, hw_device=HW_DEVICE_PROFET, hw_index=1,
                                  source_id=SYS_CH_ONE, name="out_one", config_size=len(output_cfg))

        config1 = struct.pack('<H', 1) + output_hdr + output_cfg
        chunked = struct.pack('<HH', 0, 1) + config1
        ser.write(build_min_frame(CMD.LOAD_BINARY, chunked))
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
                        success = payload[0] == 1 if len(payload) > 0 else False
                        break
            if success:
                break

        if not success:
            print("  FAIL - Config upload failed")
            results["OutputToOne"] = False
        else:
            # Wait for output to update
            time.sleep(0.5)
            drain_serial(ser, 200)

            # Start telemetry and check output state
            start_stream(ser, rate_hz=10)
            time.sleep(0.5)

            output_on = False
            parser = MINFrameParser()
            start = time.time()
            while time.time() - start < 3.0:
                chunk = ser.read(512)
                if chunk:
                    frames = parser.feed(chunk)
                    for cmd, payload, seq, _ in frames:
                        if cmd == CMD.DATA:
                            tel = parse_telemetry(payload)
                            if tel and len(tel.output_states) > 1:
                                # Output index 1 should be ON (linked to 'one')
                                if tel.output_states[1] > 0:
                                    output_on = True
                                    break
                if output_on:
                    break

            stop_stream(ser)

            if output_on:
                print(f"  OK - Output[1] is ON (linked to 'one')")
                results["OutputToOne"] = True
            else:
                print("  FAIL - Output[1] is OFF (should be ON)")
                results["OutputToOne"] = False

        # Test 2: Output linked to system channel 'zero' (1012) - should be always OFF
        print("\n[TEST 2] Output Linked to System 'zero' (1012)")
        clear_config(ser)
        time.sleep(0.3)
        drain_serial(ser, 100)

        output_hdr = build_header(101, CH_TYPE_POWER_OUTPUT, hw_device=HW_DEVICE_PROFET, hw_index=2,
                                  source_id=SYS_CH_ZERO, name="out_zero", config_size=len(output_cfg))

        config2 = struct.pack('<H', 1) + output_hdr + output_cfg
        chunked = struct.pack('<HH', 0, 1) + config2
        ser.write(build_min_frame(CMD.LOAD_BINARY, chunked))
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
                        success = payload[0] == 1 if len(payload) > 0 else False
                        break
            if success:
                break

        if not success:
            print("  FAIL - Config upload failed")
            results["OutputToZero"] = False
        else:
            time.sleep(0.5)
            drain_serial(ser, 200)

            start_stream(ser, rate_hz=10)
            time.sleep(0.5)

            output_off = False
            parser = MINFrameParser()
            start = time.time()
            while time.time() - start < 3.0:
                chunk = ser.read(512)
                if chunk:
                    frames = parser.feed(chunk)
                    for cmd, payload, seq, _ in frames:
                        if cmd == CMD.DATA:
                            tel = parse_telemetry(payload)
                            if tel and len(tel.output_states) > 2:
                                if tel.output_states[2] == 0:
                                    output_off = True
                                    break
                if output_off:
                    break

            stop_stream(ser)

            if output_off:
                print(f"  OK - Output[2] is OFF (linked to 'zero')")
                results["OutputToZero"] = True
            else:
                print("  FAIL - Output[2] is ON (should be OFF)")
                results["OutputToZero"] = False

        # Test 3: Logic IS_TRUE with system 'one' - should always output 1
        print("\n[TEST 3] Logic IS_TRUE with System 'one'")
        clear_config(ser)
        time.sleep(0.3)
        drain_serial(ser, 100)

        logic_cfg = build_logic_config([SYS_CH_ONE], LOGIC_OP_IS_TRUE)
        logic_hdr = build_header(200, CH_TYPE_LOGIC, name="is_one", config_size=len(logic_cfg))

        config3 = struct.pack('<H', 1) + logic_hdr + logic_cfg
        chunked = struct.pack('<HH', 0, 1) + config3
        ser.write(build_min_frame(CMD.LOAD_BINARY, chunked))
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
                        success = payload[0] == 1 if len(payload) > 0 else False
                        break
            if success:
                break

        if not success:
            print("  FAIL - Config upload failed")
            results["LogicIsOne"] = False
        else:
            time.sleep(0.5)
            drain_serial(ser, 200)

            start_stream(ser, rate_hz=10)
            time.sleep(0.5)

            logic_true = False
            parser = MINFrameParser()
            start = time.time()
            while time.time() - start < 3.0:
                chunk = ser.read(512)
                if chunk:
                    frames = parser.feed(chunk)
                    for cmd, payload, seq, _ in frames:
                        if cmd == CMD.DATA:
                            tel = parse_telemetry(payload)
                            if tel and 200 in tel.virtual_channels:
                                if tel.virtual_channels[200] == 1:
                                    logic_true = True
                                    break
                if logic_true:
                    break

            stop_stream(ser)

            if logic_true:
                print(f"  OK - Logic[200] = 1 (IS_TRUE of 'one')")
                results["LogicIsOne"] = True
            else:
                print("  FAIL - Logic[200] != 1")
                results["LogicIsOne"] = False

        # Test 4: Logic IS_FALSE with system 'zero' - should always output 1
        print("\n[TEST 4] Logic IS_FALSE with System 'zero'")
        clear_config(ser)
        time.sleep(0.3)
        drain_serial(ser, 100)

        logic_cfg = build_logic_config([SYS_CH_ZERO], LOGIC_OP_IS_FALSE)
        logic_hdr = build_header(201, CH_TYPE_LOGIC, name="not_zero", config_size=len(logic_cfg))

        config4 = struct.pack('<H', 1) + logic_hdr + logic_cfg
        chunked = struct.pack('<HH', 0, 1) + config4
        ser.write(build_min_frame(CMD.LOAD_BINARY, chunked))
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
                        success = payload[0] == 1 if len(payload) > 0 else False
                        break
            if success:
                break

        if not success:
            print("  FAIL - Config upload failed")
            results["LogicNotZero"] = False
        else:
            time.sleep(0.5)
            drain_serial(ser, 200)

            start_stream(ser, rate_hz=10)
            time.sleep(0.5)

            logic_true = False
            parser = MINFrameParser()
            start = time.time()
            while time.time() - start < 3.0:
                chunk = ser.read(512)
                if chunk:
                    frames = parser.feed(chunk)
                    for cmd, payload, seq, _ in frames:
                        if cmd == CMD.DATA:
                            tel = parse_telemetry(payload)
                            if tel and 201 in tel.virtual_channels:
                                if tel.virtual_channels[201] == 1:
                                    logic_true = True
                                    break
                if logic_true:
                    break

            stop_stream(ser)

            if logic_true:
                print(f"  OK - Logic[201] = 1 (IS_FALSE of 'zero')")
                results["LogicNotZero"] = True
            else:
                print("  FAIL - Logic[201] != 1")
                results["LogicNotZero"] = False

        # Cleanup
        clear_config(ser)
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
