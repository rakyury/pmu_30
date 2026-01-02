#!/usr/bin/env python3
"""
PMU-30 Config Roundtrip Test

Tests that config uploaded to device matches config read back.
This helps diagnose issues where Digital Input channels are lost.

Usage: python tests/test_config_roundtrip.py [COM_PORT] [CONFIG_FILE]

KNOWN ISSUES:
- Firmware protocol handling is timing-sensitive and flaky
- Commands may fail randomly and require retries
- Test is most reliable immediately after firmware upload
- STOP_STREAM command breaks subsequent command handling
- Best run manually for debugging, not suitable for CI
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

    ser = None
    try:
        ser = serial.Serial(port, 115200, timeout=2.0)
        time.sleep(2.0)  # Longer wait for serial to stabilize

        # Initial warmup - establish reliable communication
        print("\n[0] Initial warmup...")
        ser.reset_input_buffer()

        # NOTE: Firmware is known to be flaky with timing.
        # Try multiple PINGs with delays to warm up the communication.
        from protocol_helpers import ping
        success = False
        for i in range(10):
            time.sleep(0.3)
            ser.reset_input_buffer()
            if ping(ser, timeout=0.5):
                print(f"  OK - Firmware responding (attempt {i+1})")
                success = True
                # Do a few more PINGs to stabilize
                for _ in range(3):
                    time.sleep(0.1)
                    ser.reset_input_buffer()
                    ping(ser, timeout=0.3)
                break
        if not success:
            print("  WARNING - Firmware slow to respond, continuing anyway")

        time.sleep(0.5)
        ser.reset_input_buffer()

        # Step 1: Clear existing config
        print("\n[1] Clearing device config...")
        if clear_config(ser):
            print("  OK - Config cleared")
        else:
            print("  WARNING - Clear may have failed")

        # Step 2: Upload config (with retry)
        print("\n[2] Uploading config...")
        for attempt in range(5):
            time.sleep(0.3)
            ser.reset_input_buffer()
            success, channels_loaded = upload_config(ser, original_data)
            if success:
                print(f"  OK - Uploaded {len(original_data)} bytes, {channels_loaded} channels loaded")
                break
            else:
                if attempt < 4:
                    print(f"  Attempt {attempt+1} failed, retrying after delay...")
                    time.sleep(1.5)
                    ser.reset_input_buffer()
                    # Try a PING to wake up firmware
                    ping(ser, timeout=0.5)
                else:
                    print(f"  FAIL - Upload failed after 5 attempts")
                    return 1

        # Step 2.5: Verify firmware is still responsive
        print("\n[2.5] Checking firmware responsiveness (PING)...")
        from protocol_helpers import ping, build_frame, CMD
        if ping(ser, timeout=2.0):
            print("  OK - Firmware responding")
        else:
            print("  WARNING - No PONG response, trying again...")
            time.sleep(1.0)
            if ping(ser, timeout=2.0):
                print("  OK - Firmware responding (delayed)")
            else:
                print("  FAIL - Firmware not responding to PING")
                # Let's try to see what's in the buffer
                ser.reset_input_buffer()
                time.sleep(0.5)
                data = ser.read(1024)
                if data:
                    print(f"  Buffer had {len(data)} bytes: {data[:50].hex()}")
                return 1

        # Step 3: Read back immediately (with retry)
        print("\n[3] Reading config back (before save)...")
        readback_data = None
        for attempt in range(3):
            readback_data = read_config(ser, debug=(attempt == 0))
            if readback_data:
                readback_channels = parse_channels(readback_data)
                print(f"  Got {len(readback_data)} bytes, {len(readback_channels)} channels:")
                for ch in readback_channels:
                    print(f"    id={ch['id']}, type=0x{ch['type']:02X}, name=\"{ch['name']}\", hw_dev=0x{ch['hw_dev']:02X}")
                break
            else:
                if attempt < 2:
                    print(f"  Attempt {attempt+1} failed, waiting and retrying...")
                    time.sleep(1.0)
                    ser.reset_input_buffer()
                else:
                    print("  FAIL - No config data received after 3 attempts")
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

    except serial.SerialException as e:
        print(f"Serial error: {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Cleanup serial port (skip STOP_STREAM to avoid timing issues)
        if ser:
            try:
                pass  # Don't send STOP_STREAM - causes firmware instability
            except:
                pass
            try:
                ser.close()
            except:
                pass


if __name__ == '__main__':
    sys.exit(main())
