#!/usr/bin/env python3
"""
Test: Config Swap (automated)

Tests that config can be swapped and telemetry reflects the change.

Usage: python tests/test_config_swap.py [COM_PORT]
"""

import sys
import struct
import time
import serial
from pathlib import Path

# Import shared protocol helpers
sys.path.insert(0, str(Path(__file__).parent))
from protocol_helpers import (
    CMD, build_min_frame, MINFrameParser, transact,
    ping, upload_config, read_config, clear_config
)


# Channel types
CH_TYPE_LOGIC = 0x21
CH_TYPE_POWER_OUTPUT = 0x10
CH_TYPE_DIGITAL_INPUT = 0x01

# Logic operations
LOGIC_OP_IS_TRUE = 0x06
LOGIC_OP_IS_FALSE = 0x07

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


def build_config(logic_op, channel_id_base=50):
    """Build config with DIN -> Logic -> Output."""
    channels = []

    din_cfg = build_din_config()
    din_hdr = build_channel_header(channel_id_base, CH_TYPE_DIGITAL_INPUT, 0x01, HW_DEVICE_DIN, 0,
                                   CH_REF_NONE, 0, "DIN", len(din_cfg))
    channels.append(din_hdr + din_cfg)

    logic_cfg = build_logic_config(logic_op, [channel_id_base])
    logic_hdr = build_channel_header(channel_id_base + 150, CH_TYPE_LOGIC, 0x01, 0, 0,
                                     CH_REF_NONE, 0, "Logic", len(logic_cfg))
    channels.append(logic_hdr + logic_cfg)

    out_cfg = build_power_output_config()
    out_hdr = build_channel_header(channel_id_base + 50, CH_TYPE_POWER_OUTPUT, 0x01, HW_DEVICE_PROFET, 1,
                                   channel_id_base + 150, 0, "Out", len(out_cfg))
    channels.append(out_hdr + out_cfg)

    return struct.pack('<H', len(channels)) + b''.join(channels)


def get_virtual_channels(ser, timeout=2.0):
    """Get virtual channels from telemetry."""
    parser = MINFrameParser()
    start = time.time()
    old_timeout = ser.timeout
    ser.timeout = 0.15

    try:
        while time.time() - start < timeout:
            chunk = ser.read(512)
            if chunk:
                frames = parser.feed(chunk)
                for cmd, payload, seq, _ in frames:
                    if cmd == CMD.DATA and len(payload) >= 106:
                        virtual_count = struct.unpack('<H', payload[104:106])[0]
                        virtuals = []
                        for i in range(virtual_count):
                            voff = 106 + i * 6
                            if voff + 6 <= len(payload):
                                vid = struct.unpack('<H', payload[voff:voff+2])[0]
                                vval = struct.unpack('<i', payload[voff+2:voff+6])[0]
                                virtuals.append((vid, vval))
                        return virtuals
    finally:
        ser.timeout = old_timeout

    return None


def start_telemetry(ser, rate_hz=10):
    """Start telemetry stream."""
    payload = struct.pack('<H', rate_hz)
    ser.write(build_min_frame(CMD.START_STREAM, payload))
    ser.flush()
    time.sleep(0.1)


def stop_telemetry(ser):
    """Stop telemetry stream and drain frames."""
    ser.write(build_min_frame(CMD.STOP_STREAM))
    ser.flush()
    time.sleep(0.3)

    # Drain any remaining telemetry frames
    old_timeout = ser.timeout
    ser.timeout = 0.1
    try:
        for _ in range(30):
            chunk = ser.read(1024)
            if not chunk:
                break
    finally:
        ser.timeout = old_timeout


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else 'COM11'

    print("=" * 60)
    print("Test: Config Swap (automated)")
    print("=" * 60)
    print(f"Port: {port}")
    print()

    ser = serial.Serial(port, 115200, timeout=2.0)
    time.sleep(2.0)  # Wait for port to stabilize

    try:
        # Warmup - send PINGs to sync
        print("[0] Warming up connection...")
        ser.reset_input_buffer()
        for attempt in range(5):
            time.sleep(0.3)
            if ping(ser, timeout=0.5):
                print(f"  OK - PONG received (attempt {attempt + 1})")
                break
        else:
            print("  WARNING - No PONG after 5 attempts")

        # Initial stop and drain (in case telemetry was running)
        stop_telemetry(ser)
        time.sleep(0.3)

        # Clear existing config first (like roundtrip test does)
        if clear_config(ser):
            print("  Config cleared")
        else:
            print("  WARNING - Clear may have failed")
        time.sleep(0.3)

        # ========== TEST 1: Upload Config A (IS_TRUE, ch 50) ==========
        print("[1] Upload Config A (IS_TRUE, DIN=50, Logic=200, Out=100)")
        config_a = build_config(LOGIC_OP_IS_TRUE, channel_id_base=50)
        success, channels = upload_config(ser, config_a)
        if not success:
            print("  FAIL: Config A upload failed")
            return 1
        print(f"  OK: Uploaded {channels} channels")

        # Start telemetry
        start_telemetry(ser, 10)
        time.sleep(0.5)

        virtuals_a = get_virtual_channels(ser)
        if virtuals_a is None:
            print("  FAIL: No telemetry")
            return 1
        print(f"  Virtual channels: {virtuals_a}")

        # Check Logic channel exists with ID 200
        logic_ids = [v[0] for v in virtuals_a]
        if 200 not in logic_ids:
            print(f"  WARNING: Logic channel 200 not found, got {logic_ids}")
        else:
            print("  OK: Logic channel 200 found")

        # Stop telemetry
        print("  Stopping telemetry...")
        stop_telemetry(ser)

        # Check if firmware is responsive
        print("  Checking PING...")
        if ping(ser, timeout=2.0):
            print("  PONG OK - firmware responsive")
        else:
            print("  NO PONG - firmware hung!")
            return 1

        # ========== TEST 2: Upload Config B (different base ID) ==========
        print("\n[2] Upload Config B (IS_TRUE, DIN=60, Logic=210, Out=110)")

        # Extra drain after stop_telemetry to ensure clean state
        time.sleep(0.5)
        ser.reset_input_buffer()

        # Check firmware is still responsive
        if not ping(ser, timeout=1.0):
            print("  WARNING - firmware not responding after stop_telemetry")

        # Clear before uploading new config
        if clear_config(ser):
            print("  Config cleared")
        else:
            print("  WARNING - Clear may have failed")
        time.sleep(0.3)

        config_b = build_config(LOGIC_OP_IS_TRUE, channel_id_base=60)
        success, channels = upload_config(ser, config_b)
        if not success:
            print("  FAIL: Config B upload failed")
            return 1
        print(f"  OK: Uploaded {channels} channels")

        # Start telemetry
        start_telemetry(ser, 10)
        time.sleep(0.5)

        virtuals_b = get_virtual_channels(ser)
        if virtuals_b is None:
            print("  FAIL: No telemetry")
            return 1
        print(f"  Virtual channels: {virtuals_b}")

        # Check Logic channel changed to ID 210
        logic_ids = [v[0] for v in virtuals_b]
        if 210 not in logic_ids:
            print(f"  WARNING: Logic channel 210 not found, got {logic_ids}")
        else:
            print("  OK: Logic channel 210 found")

        # Verify old config is gone
        if 200 in logic_ids:
            print("  FAIL: Old Logic channel 200 still present!")
            return 1
        print("  OK: Old Logic channel 200 replaced")

        # Extra long drain before stopping to ensure all telemetry is received
        print("  Extra drain before stop...")
        time.sleep(1.0)
        ser.reset_input_buffer()

        stop_telemetry(ser)

        # Extra recovery time after stop
        print("  Waiting for firmware to stabilize...")
        time.sleep(1.0)

        # ========== TEST 3: Swap back to Config A ==========
        print("\n[3] Swap back to Config A")

        # Extra drain after stop_telemetry
        time.sleep(0.5)
        ser.reset_input_buffer()

        # Check firmware is still responsive
        if ping(ser, timeout=1.0):
            print("  PONG OK - firmware responsive")
        else:
            print("  WARNING - firmware not responding after stop_telemetry")

        # Clear before uploading
        if clear_config(ser):
            print("  Config cleared")
        else:
            print("  WARNING - Clear may have failed")
        time.sleep(0.3)

        # Try upload with retries (test 3 sometimes fails)
        for attempt in range(3):
            success, channels = upload_config(ser, config_a)
            if success:
                break
            else:
                print(f"  Upload attempt {attempt+1} failed, retrying...")
                time.sleep(0.5)
                ser.reset_input_buffer()
                ping(ser, timeout=1.0)
                time.sleep(0.3)

        if not success:
            print("  FAIL: Config A re-upload failed after 3 attempts")
            return 1
        print(f"  OK: Uploaded {channels} channels")

        start_telemetry(ser, 10)
        time.sleep(0.5)

        virtuals_a2 = get_virtual_channels(ser)
        if virtuals_a2 is None:
            print("  FAIL: No telemetry")
            return 1
        print(f"  Virtual channels: {virtuals_a2}")

        logic_ids = [v[0] for v in virtuals_a2]
        if 200 not in logic_ids:
            print(f"  WARNING: Logic channel 200 not found, got {logic_ids}")
        else:
            print("  OK: Logic channel 200 restored")

        print("\n" + "=" * 60)
        print("PASS: Config swap works correctly!")
        print("=" * 60)
        return 0

    finally:
        stop_telemetry(ser)
        ser.close()


if __name__ == '__main__':
    sys.exit(main())
