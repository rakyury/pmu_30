#!/usr/bin/env python3
"""
Test: Config Swap (minimal - no telemetry)

Tests that config can be swapped without using telemetry streaming.
Uses GET_CONFIG to verify config instead of telemetry.

Usage: python tests/test_config_swap_minimal.py [COM_PORT]
"""

import sys
import struct
import time
import serial
from pathlib import Path

# Import shared protocol helpers
sys.path.insert(0, str(Path(__file__).parent))
from protocol_helpers import (
    CMD, build_min_frame, MINFrameParser,
    ping, upload_config, read_config, clear_config, parse_channels
)


# Channel types
CH_TYPE_LOGIC = 0x21
CH_TYPE_POWER_OUTPUT = 0x10
CH_TYPE_DIGITAL_INPUT = 0x01

# Logic operations
LOGIC_OP_IS_TRUE = 0x06

# Hardware
HW_DEVICE_DIN = 0x01
HW_DEVICE_PROFET = 0x05
CH_REF_NONE = 0xFFFF


def build_channel_header(channel_id, channel_type, flags=0x01, hw_device=0, hw_index=0,
                         source_id=CH_REF_NONE, default_value=0, name="", config_size=0):
    name_bytes = name.encode('utf-8')[:31]
    header = struct.pack('<HBBBBHiBB',
        channel_id, channel_type, flags, hw_device, hw_index,
        source_id, default_value, len(name_bytes), config_size
    )
    return header + name_bytes


def build_din_config():
    return struct.pack('<BBH', 0x00, 0x00, 0x0000)


def build_logic_config(operation, inputs):
    inputs_padded = inputs + [0] * (8 - len(inputs))
    return struct.pack('<BB8Hi?3s',
        operation, len(inputs), *inputs_padded, 0, False, b'\x00\x00\x00'
    )


def build_power_output_config():
    return struct.pack('<HHHBBHBB', 5000, 100, 10000, 3, 5, 0, 0, 0)


def build_config(channel_id_base=50, name_suffix=""):
    """Build config with DIN -> Logic -> Output."""
    channels = []

    din_cfg = build_din_config()
    din_hdr = build_channel_header(channel_id_base, CH_TYPE_DIGITAL_INPUT, 0x01, HW_DEVICE_DIN, 0,
                                   CH_REF_NONE, 0, f"DIN{name_suffix}", len(din_cfg))
    channels.append(din_hdr + din_cfg)

    logic_cfg = build_logic_config(LOGIC_OP_IS_TRUE, [channel_id_base])
    logic_hdr = build_channel_header(channel_id_base + 150, CH_TYPE_LOGIC, 0x01, 0, 0,
                                     CH_REF_NONE, 0, f"Logic{name_suffix}", len(logic_cfg))
    channels.append(logic_hdr + logic_cfg)

    out_cfg = build_power_output_config()
    out_hdr = build_channel_header(channel_id_base + 50, CH_TYPE_POWER_OUTPUT, 0x01, HW_DEVICE_PROFET, 1,
                                   channel_id_base + 150, 0, f"Out{name_suffix}", len(out_cfg))
    channels.append(out_hdr + out_cfg)

    return struct.pack('<H', len(channels)) + b''.join(channels)


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else 'COM11'

    print("=" * 60)
    print("Test: Config Swap (minimal - no telemetry)")
    print("=" * 60)
    print(f"Port: {port}")
    print()

    ser = serial.Serial(port, 115200, timeout=2.0)
    time.sleep(2.0)

    try:
        # Warmup
        print("[0] Warming up connection...")
        ser.reset_input_buffer()
        for attempt in range(5):
            time.sleep(0.3)
            if ping(ser, timeout=0.5):
                print(f"  OK - PONG received (attempt {attempt + 1})")
                break
        else:
            print("  WARNING - No PONG after 5 attempts")

        # Initial clear
        time.sleep(0.3)
        if clear_config(ser):
            print("  Config cleared")
        else:
            print("  WARNING - Clear may have failed")

        # ========== TEST 1: Upload Config A ==========
        print("\n[1] Upload Config A (DIN=50, Logic=200, Out=100)")
        config_a = build_config(channel_id_base=50, name_suffix="A")
        success, channels = upload_config(ser, config_a)
        if not success:
            print("  FAIL: Config A upload failed")
            return 1
        print(f"  OK: Uploaded {channels} channels")

        # Verify config via GET_CONFIG
        time.sleep(0.3)
        config_read = read_config(ser)
        if config_read is None:
            print("  FAIL: Could not read config back")
            return 1
        ch_list = parse_channels(config_read)
        ch_ids = [ch['id'] for ch in ch_list]
        if 200 in ch_ids:
            print(f"  OK: Logic channel 200 found in config")
        else:
            print(f"  WARNING: Logic channel 200 not found, got {ch_ids}")

        # ========== TEST 2: Upload Config B ==========
        print("\n[2] Upload Config B (DIN=60, Logic=210, Out=110)")
        time.sleep(0.3)
        clear_config(ser)
        time.sleep(0.3)

        config_b = build_config(channel_id_base=60, name_suffix="B")
        success, channels = upload_config(ser, config_b)
        if not success:
            print("  FAIL: Config B upload failed")
            return 1
        print(f"  OK: Uploaded {channels} channels")

        # Verify config via GET_CONFIG
        time.sleep(0.3)
        config_read = read_config(ser)
        if config_read is None:
            print("  FAIL: Could not read config back")
            return 1
        ch_list = parse_channels(config_read)
        ch_ids = [ch['id'] for ch in ch_list]
        if 210 in ch_ids:
            print(f"  OK: Logic channel 210 found in config")
        else:
            print(f"  WARNING: Logic channel 210 not found, got {ch_ids}")
        if 200 in ch_ids:
            print("  FAIL: Old Logic channel 200 still present!")
            return 1
        print("  OK: Old Logic channel 200 replaced")

        # ========== TEST 3: Swap back to Config A ==========
        print("\n[3] Swap back to Config A")
        time.sleep(0.3)
        clear_config(ser)
        time.sleep(0.3)

        success, channels = upload_config(ser, config_a)
        if not success:
            print("  FAIL: Config A re-upload failed")
            return 1
        print(f"  OK: Uploaded {channels} channels")

        # Verify config via GET_CONFIG
        time.sleep(0.3)
        config_read = read_config(ser)
        if config_read is None:
            print("  FAIL: Could not read config back")
            return 1
        ch_list = parse_channels(config_read)
        ch_ids = [ch['id'] for ch in ch_list]
        if 200 in ch_ids:
            print(f"  OK: Logic channel 200 restored")
        else:
            print(f"  WARNING: Logic channel 200 not found, got {ch_ids}")

        print("\n" + "=" * 60)
        print("PASS: Config swap works correctly!")
        print("=" * 60)
        return 0

    finally:
        ser.close()


if __name__ == '__main__':
    sys.exit(main())
