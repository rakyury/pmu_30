#!/usr/bin/env python3
"""
PMU-30 Config Roundtrip Test

Tests that config uploaded to device matches config read back.
This helps diagnose issues where Digital Input channels are lost.

Usage: python tests/test_config_roundtrip.py [COM_PORT] [CONFIG_FILE]
"""

import sys
import time
import serial
from pathlib import Path

# Import shared protocol helpers (uses protocol v2 with SeqID)
from protocol_helpers import (
    CMD, build_frame, parse_frames, transact,
    stop_stream, clear_config, upload_config, read_config,
    save_to_flash, parse_channels
)


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM11"
    config_file = sys.argv[2] if len(sys.argv) > 2 else "tests/configs/logic_and.pmu30"

    print("=" * 60)
    print("PMU-30 Config Roundtrip Test")
    print("=" * 60)
    print(f"Port: {port}")
    print(f"Config: {config_file}")

    # Load config file
    config_path = Path(config_file)
    if not config_path.exists():
        config_path = Path(__file__).parent.parent / config_file

    with open(config_path, 'rb') as f:
        original_data = f.read()

    original_channels = parse_channels(original_data)
    print(f"\n[ORIGINAL FILE] {len(original_data)} bytes, {len(original_channels)} channels:")
    for ch in original_channels:
        print(f"  id={ch['id']}, type=0x{ch['type']:02X}, name=\"{ch['name']}\", hw_dev=0x{ch['hw_dev']:02X}")

    try:
        ser = serial.Serial(port, 115200, timeout=2.0)
        time.sleep(0.5)

        # Initial stop stream
        print("\n[0] Stopping telemetry stream...")
        stop_stream(ser)
        print("  OK - Stream stopped")

        # Step 1: Clear existing config
        print("\n[1] Clearing device config...")
        if clear_config(ser):
            print("  OK - Config cleared")
        else:
            print("  WARNING - Clear may have failed")

        # Step 2: Upload config
        print("\n[2] Uploading config...")
        success, channels_loaded = upload_config(ser, original_data)
        if success:
            print(f"  OK - Uploaded {len(original_data)} bytes, {channels_loaded} channels loaded")
        else:
            print(f"  FAIL - Upload failed")
            return 1

        # Step 3: Read back immediately
        print("\n[3] Reading config back (before save)...")
        readback_data = read_config(ser)
        if readback_data:
            readback_channels = parse_channels(readback_data)
            print(f"  Got {len(readback_data)} bytes, {len(readback_channels)} channels:")
            for ch in readback_channels:
                print(f"    id={ch['id']}, type=0x{ch['type']:02X}, name=\"{ch['name']}\", hw_dev=0x{ch['hw_dev']:02X}")
        else:
            print("  FAIL - No config data received")
            return 1

        # Step 4: Save to flash
        print("\n[4] Saving to flash...")
        if save_to_flash(ser):
            print("  OK - Saved to flash")
        else:
            print("  WARNING - Flash save may have failed")

        # Step 5: Read back after save (simulates restart)
        print("\n[5] Reading config back (after save)...")
        time.sleep(0.5)
        final_data = read_config(ser)
        if final_data:
            final_channels = parse_channels(final_data)
            print(f"  Got {len(final_data)} bytes, {len(final_channels)} channels:")
            for ch in final_channels:
                print(f"    id={ch['id']}, type=0x{ch['type']:02X}, name=\"{ch['name']}\", hw_dev=0x{ch['hw_dev']:02X}")
        else:
            print("  FAIL - No config data received")
            return 1

        # Compare
        print("\n" + "=" * 60)
        print("COMPARISON:")
        print("=" * 60)

        orig_ids = {ch['id'] for ch in original_channels}
        final_ids = {ch['id'] for ch in final_channels}

        missing = orig_ids - final_ids
        added = final_ids - orig_ids

        if missing:
            print(f"  MISSING from device: {missing}")
        if added:
            print(f"  ADDED on device: {added}")

        if orig_ids == final_ids:
            print("  All channels preserved!")

            # Compare contents
            for orig in original_channels:
                final = next((ch for ch in final_channels if ch['id'] == orig['id']), None)
                if final:
                    if orig['config'] != final['config']:
                        print(f"  WARNING: Channel {orig['id']} config differs!")
                        print(f"    Original: {orig['config']}")
                        print(f"    Final:    {final['config']}")

            print("\n  PASS - Roundtrip successful!")
            return 0
        else:
            print("\n  FAIL - Channel count mismatch!")
            return 1

        ser.close()

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
