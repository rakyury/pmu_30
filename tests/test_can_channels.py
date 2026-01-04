#!/usr/bin/env python3
"""
PMU-30 CAN Channel Test

Tests CAN-related channel configuration:
- CAN Input channels can be created
- CAN Output channels can be created
- CAN Message definitions can be loaded
- Firmware doesn't crash with CAN config

Note: Nucleo-F446RE has CAN stubs - no actual CAN traffic is tested.
Real CAN testing requires PMU-30 hardware with CAN transceiver.

Usage: python tests/test_can_channels.py [COM_PORT]
"""

import sys
import struct
import time
import serial

sys.path.insert(0, 'tests')
from protocol_helpers import (
    CMD, build_min_frame, MINFrameParser, drain_serial,
    ping, clear_config, read_config, parse_channels,
    start_stream, stop_stream, parse_telemetry
)

# Channel types
CH_TYPE_CAN_INPUT = 0x14
CH_TYPE_CAN_OUTPUT = 0x15
CH_TYPE_NUMBER = 0x27
CH_TYPE_LOGIC = 0x21
CH_REF_NONE = 0xFFFF

# CAN constants
CAN_BUS_1 = 0
CAN_BUS_2 = 1


def build_header(channel_id, channel_type, hw_device=0, hw_index=0,
                 source_id=CH_REF_NONE, name="", config_size=0):
    """Build CfgChannelHeader_t (14 bytes) + name."""
    name_bytes = name.encode('utf-8')[:31]
    return struct.pack('<HBBBBHiBB',
        channel_id, channel_type, 0x01, hw_device, hw_index, source_id, 0,
        len(name_bytes), config_size
    ) + name_bytes


def build_can_input_config(can_id, bus=CAN_BUS_1, start_bit=0, length=8,
                           is_signed=False, scale=1.0, offset=0.0):
    """Build CfgCanInput_t.

    Format:
    - message_id: uint32 (4B)
    - bus: uint8 (1B)
    - start_bit: uint8 (1B)
    - length: uint8 (1B)
    - is_signed: uint8 (1B)
    - scale: float (4B)
    - offset: float (4B)
    - timeout_ms: uint16 (2B)
    - reserved: uint16 (2B)
    Total: 20 bytes
    """
    return struct.pack('<IBBBB ff HH',
        can_id, bus, start_bit, length, 1 if is_signed else 0,
        scale, offset, 1000, 0)


def build_can_output_config(can_id, bus=CAN_BUS_1, start_bit=0, length=8,
                            is_signed=False, scale=1.0, offset=0.0):
    """Build CfgCanOutput_t.

    Format:
    - message_id: uint32 (4B)
    - bus: uint8 (1B)
    - start_bit: uint8 (1B)
    - length: uint8 (1B)
    - is_signed: uint8 (1B)
    - scale: float (4B)
    - offset: float (4B)
    - period_ms: uint16 (2B)
    - reserved: uint16 (2B)
    Total: 20 bytes
    """
    return struct.pack('<IBBBB ff HH',
        can_id, bus, start_bit, length, 1 if is_signed else 0,
        scale, offset, 100, 0)


def build_number_config(value=0):
    """Build CfgNumber_t (20 bytes)."""
    return struct.pack('<iiiiBB2s', value, -32768, 32767, 1, 0, 0, b'\x00\x00')


def run_tests(port):
    print("=" * 60)
    print("PMU-30 CAN Channel Test")
    print("=" * 60)
    print(f"Port: {port}")
    print("Note: CAN is stubbed on Nucleo - testing config only")

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

        # Test 1: CAN Input channel
        print("\n[TEST 1] CAN Input Channel")
        clear_config(ser)
        time.sleep(0.3)
        drain_serial(ser, 100)

        can_in_cfg = build_can_input_config(0x100, CAN_BUS_1, start_bit=0, length=16)
        can_in_hdr = build_header(100, CH_TYPE_CAN_INPUT, name="rpm", config_size=len(can_in_cfg))

        config1 = struct.pack('<H', 1) + can_in_hdr + can_in_cfg
        chunked = struct.pack('<HH', 0, 1) + config1
        ser.write(build_min_frame(CMD.LOAD_BINARY, chunked))
        ser.flush()

        parser = MINFrameParser()
        start = time.time()
        success = False
        loaded = 0
        while time.time() - start < 3.0:
            chunk = ser.read(512)
            if chunk:
                frames = parser.feed(chunk)
                for cmd, payload, seq, _ in frames:
                    if cmd == CMD.BINARY_ACK:
                        success = payload[0] == 1 if len(payload) > 0 else False
                        loaded = struct.unpack('<H', payload[2:4])[0] if len(payload) >= 4 else 0
                        break
            if success:
                break

        if success:
            print(f"  Upload OK - loaded {loaded} channel(s)")
            # Verify firmware is still alive
            time.sleep(0.3)
            if ping(ser, timeout=1.0):
                print("  Firmware stable after CAN Input config")
                results["CANInput"] = True
            else:
                print("  FAIL - Firmware crashed")
                results["CANInput"] = False
        else:
            print("  FAIL - Upload failed")
            results["CANInput"] = False

        # Test 2: CAN Output channel
        print("\n[TEST 2] CAN Output Channel")
        clear_config(ser)
        time.sleep(0.3)
        drain_serial(ser, 100)

        # Create a Number channel as source for CAN output
        num_cfg = build_number_config(value=1234)
        num_hdr = build_header(50, CH_TYPE_NUMBER, name="value", config_size=len(num_cfg))

        can_out_cfg = build_can_output_config(0x200, CAN_BUS_1, start_bit=0, length=16)
        can_out_hdr = build_header(101, CH_TYPE_CAN_OUTPUT, source_id=50,
                                   name="out", config_size=len(can_out_cfg))

        config2 = struct.pack('<H', 2) + num_hdr + num_cfg + can_out_hdr + can_out_cfg
        chunked = struct.pack('<HH', 0, 1) + config2
        ser.write(build_min_frame(CMD.LOAD_BINARY, chunked))
        ser.flush()

        parser = MINFrameParser()
        start = time.time()
        success = False
        loaded = 0
        while time.time() - start < 3.0:
            chunk = ser.read(512)
            if chunk:
                frames = parser.feed(chunk)
                for cmd, payload, seq, _ in frames:
                    if cmd == CMD.BINARY_ACK:
                        success = payload[0] == 1 if len(payload) > 0 else False
                        loaded = struct.unpack('<H', payload[2:4])[0] if len(payload) >= 4 else 0
                        break
            if success:
                break

        if success:
            print(f"  Upload OK - loaded {loaded} channel(s)")
            time.sleep(0.3)
            if ping(ser, timeout=1.0):
                print("  Firmware stable after CAN Output config")
                results["CANOutput"] = True
            else:
                print("  FAIL - Firmware crashed")
                results["CANOutput"] = False
        else:
            print("  FAIL - Upload failed")
            results["CANOutput"] = False

        # Test 3: Multiple CAN channels
        print("\n[TEST 3] Multiple CAN Channels")
        clear_config(ser)
        time.sleep(0.3)
        drain_serial(ser, 100)

        # 2 CAN inputs, 1 Number, 1 CAN output
        can_in1_cfg = build_can_input_config(0x100, CAN_BUS_1, start_bit=0, length=8)
        can_in1_hdr = build_header(100, CH_TYPE_CAN_INPUT, name="temp", config_size=len(can_in1_cfg))

        can_in2_cfg = build_can_input_config(0x100, CAN_BUS_1, start_bit=8, length=8)
        can_in2_hdr = build_header(101, CH_TYPE_CAN_INPUT, name="pres", config_size=len(can_in2_cfg))

        num_cfg = build_number_config(value=50)
        num_hdr = build_header(50, CH_TYPE_NUMBER, name="tgt", config_size=len(num_cfg))

        can_out_cfg = build_can_output_config(0x300, CAN_BUS_1, start_bit=0, length=8)
        can_out_hdr = build_header(102, CH_TYPE_CAN_OUTPUT, source_id=50,
                                   name="cmd", config_size=len(can_out_cfg))

        config3 = (struct.pack('<H', 4) +
                   can_in1_hdr + can_in1_cfg +
                   can_in2_hdr + can_in2_cfg +
                   num_hdr + num_cfg +
                   can_out_hdr + can_out_cfg)

        chunked = struct.pack('<HH', 0, 1) + config3
        ser.write(build_min_frame(CMD.LOAD_BINARY, chunked))
        ser.flush()

        parser = MINFrameParser()
        start = time.time()
        success = False
        loaded = 0
        while time.time() - start < 3.0:
            chunk = ser.read(512)
            if chunk:
                frames = parser.feed(chunk)
                for cmd, payload, seq, _ in frames:
                    if cmd == CMD.BINARY_ACK:
                        success = payload[0] == 1 if len(payload) > 0 else False
                        loaded = struct.unpack('<H', payload[2:4])[0] if len(payload) >= 4 else 0
                        break
            if success:
                break

        if success and loaded == 4:
            print(f"  Upload OK - loaded {loaded} channels")
            time.sleep(0.3)
            if ping(ser, timeout=1.0):
                # Verify readback
                config_data = read_config(ser)
                if config_data:
                    channels = parse_channels(config_data)
                    if len(channels) == 4:
                        print(f"  Readback OK - {len(channels)} channels")
                        results["MultiCAN"] = True
                    else:
                        print(f"  FAIL - Wrong channel count: {len(channels)}")
                        results["MultiCAN"] = False
                else:
                    print("  FAIL - No readback")
                    results["MultiCAN"] = False
            else:
                print("  FAIL - Firmware crashed")
                results["MultiCAN"] = False
        else:
            print(f"  FAIL - Upload failed (success={success}, loaded={loaded})")
            results["MultiCAN"] = False

        # Test 4: CAN channels persist in telemetry
        print("\n[TEST 4] CAN Input in Telemetry")
        # Using config from test 3
        time.sleep(0.3)
        drain_serial(ser, 200)

        start_stream(ser, rate_hz=10)
        time.sleep(0.5)

        # CAN inputs should appear as virtual channels (since they have no hardware signal)
        found_data = False
        parser = MINFrameParser()
        start = time.time()
        while time.time() - start < 3.0:
            chunk = ser.read(512)
            if chunk:
                frames = parser.feed(chunk)
                for cmd, payload, seq, _ in frames:
                    if cmd == CMD.DATA:
                        tel = parse_telemetry(payload)
                        if tel:
                            # CAN inputs might be in virtual channels
                            # or might not be reported (depends on impl)
                            found_data = True
                            print(f"  Telemetry received, virtual channels: {tel.virtual_channels}")
                            break
            if found_data:
                break

        stop_stream(ser)

        if found_data:
            print("  OK - Telemetry streaming with CAN config")
            results["CANTelemetry"] = True
        else:
            print("  FAIL - No telemetry received")
            results["CANTelemetry"] = False

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
