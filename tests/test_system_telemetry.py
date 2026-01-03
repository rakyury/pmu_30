#!/usr/bin/env python3
"""
PMU-30 System Telemetry Test

Tests that system channels in telemetry are working and updating:
- uptime_sec: Should increment over time
- ram_used: Should be reasonable (< 128KB for F446RE)
- flash_used: Should be reasonable (< 512KB for F446RE)
- channel_count: Should be present and consistent

Usage: python tests/test_system_telemetry.py [COM_PORT]
"""

import sys
import struct
import time
import serial

# Protocol commands
CMD_START_STREAM = 0x30
CMD_TELEMETRY = 0x32

# Memory limits for STM32F446RE
RAM_SIZE = 128 * 1024   # 128 KB
FLASH_SIZE = 512 * 1024  # 512 KB


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


def parse_system_info(pkt: bytes) -> dict:
    """Parse system info from telemetry packet (offset 79-93)."""
    if len(pkt) < 94:
        return None
    return {
        'uptime_sec': struct.unpack('<I', pkt[79:83])[0],
        'ram_used': struct.unpack('<I', pkt[83:87])[0],
        'flash_used': struct.unpack('<I', pkt[87:91])[0],
        'channel_count': struct.unpack('<H', pkt[91:93])[0],
    }


def collect_telemetry(ser, duration: float = 2.0) -> list:
    """Collect telemetry packets for specified duration.

    Assumes stream is already running from initialization.
    """
    ser.reset_input_buffer()
    time.sleep(0.1)

    packets = []
    all_data = b''
    start = time.time()
    while time.time() - start < duration:
        data = ser.read(4096)
        if data:
            all_data += data
        time.sleep(0.05)

    # Parse all collected data at once
    frames = parse_frames(all_data)
    for cmd, payload in frames:
        if cmd == CMD_TELEMETRY:
            info = parse_system_info(payload)
            if info:
                packets.append(info)

    return packets


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM11"
    print("=" * 60)
    print("PMU-30 System Telemetry Test")
    print("=" * 60)
    print(f"Port: {port}")

    results = {}

    try:
        # Open connection and start stream
        ser = serial.Serial(port, 115200, timeout=2.0)
        time.sleep(1.5)

        # Initialize connection with robust startup
        print("Initializing connection...")
        ser.reset_input_buffer()

        # Send START_STREAM multiple times to ensure firmware starts
        for i in range(5):
            ser.write(build_frame(CMD_START_STREAM))
            time.sleep(0.3)

        # Wait for stream to stabilize
        time.sleep(1.0)

        if ser.in_waiting > 0:
            print(f"  Connection ready ({ser.in_waiting} bytes buffered)")
        else:
            print("  Connection ready (waiting for data...)")
            time.sleep(1.0)

        # Test 1: Basic telemetry reception
        print("\n[TEST 1] Basic System Telemetry")
        packets = collect_telemetry(ser, 2.0)

        if len(packets) < 10:
            print(f"  FAIL - Only {len(packets)} packets received")
            results["Basic"] = False
        else:
            info = packets[-1]
            print(f"  Received {len(packets)} packets")
            print(f"  Uptime: {info['uptime_sec']} sec")
            print(f"  RAM used: {info['ram_used']} bytes ({info['ram_used']/1024:.1f} KB)")
            print(f"  Flash used: {info['flash_used']} bytes ({info['flash_used']/1024:.1f} KB)")
            print(f"  Channels: {info['channel_count']}")
            print("  OK - System telemetry received")
            results["Basic"] = True

        time.sleep(0.5)

        # Test 2: Uptime incrementing
        print("\n[TEST 2] Uptime Incrementing")
        packets = collect_telemetry(ser, 3.0)

        if len(packets) >= 20:
            uptime_first = packets[0]['uptime_sec']
            uptime_last = packets[-1]['uptime_sec']
            delta = uptime_last - uptime_first
            print(f"  First packet: {uptime_first} sec")
            print(f"  Last packet: {uptime_last} sec")
            print(f"  Delta: {delta} sec (expected 1-10)")

            # Key test: uptime should be incrementing, not stuck
            if 1 <= delta <= 10:
                print("  OK - Uptime incrementing correctly")
                results["Uptime"] = True
            else:
                print(f"  FAIL - Delta {delta} not in expected range")
                results["Uptime"] = False
        else:
            print(f"  FAIL - Only {len(packets)} packets")
            results["Uptime"] = False

        time.sleep(0.5)

        # Test 3: RAM usage reasonable
        print("\n[TEST 3] RAM Usage Reasonable")
        packets = collect_telemetry(ser, 1.0)

        if packets:
            ram = packets[-1]['ram_used']
            print(f"  RAM used: {ram} bytes ({ram/1024:.2f} KB)")
            print(f"  RAM total: {RAM_SIZE} bytes ({RAM_SIZE/1024:.0f} KB)")
            print(f"  Usage: {ram*100/RAM_SIZE:.2f}%")

            if 0 < ram < RAM_SIZE:
                print("  OK - RAM usage within bounds")
                results["RAM"] = True
            else:
                print(f"  FAIL - RAM {ram} out of bounds")
                results["RAM"] = False
        else:
            print("  FAIL - No packets")
            results["RAM"] = False

        time.sleep(0.5)

        # Test 4: Flash usage reasonable
        print("\n[TEST 4] Flash Usage Reasonable")
        packets = collect_telemetry(ser, 1.0)

        if packets:
            flash = packets[-1]['flash_used']
            print(f"  Flash used: {flash} bytes ({flash/1024:.2f} KB)")
            print(f"  Flash total: {FLASH_SIZE} bytes ({FLASH_SIZE/1024:.0f} KB)")
            print(f"  Usage: {flash*100/FLASH_SIZE:.2f}%")

            if 10000 < flash < FLASH_SIZE:
                print("  OK - Flash usage within bounds")
                results["Flash"] = True
            else:
                print(f"  FAIL - Flash {flash} out of bounds")
                results["Flash"] = False
        else:
            print("  FAIL - No packets")
            results["Flash"] = False

        time.sleep(0.5)

        # Test 5: Channel count in telemetry
        print("\n[TEST 5] Channel Count Field Valid")
        packets = collect_telemetry(ser, 2.0)

        if packets:
            channel_counts = [p['channel_count'] for p in packets]
            latest_count = channel_counts[-1]
            all_same = len(set(channel_counts)) == 1

            print(f"  Channel count: {latest_count}")
            print(f"  Consistent across {len(packets)} packets: {all_same}")

            if 0 <= latest_count < 1000 and all_same:
                print("  OK - Channel count field is valid")
                results["ChannelCount"] = True
            else:
                print(f"  FAIL - Invalid channel count or inconsistent")
                results["ChannelCount"] = False
        else:
            print("  FAIL - No packets")
            results["ChannelCount"] = False

        time.sleep(0.5)

        # Test 6: Consistency across packets
        print("\n[TEST 6] Value Consistency")
        packets = collect_telemetry(ser, 2.0)

        if len(packets) >= 10:
            ram_values = [p['ram_used'] for p in packets]
            flash_values = [p['flash_used'] for p in packets]

            ram_variance = max(ram_values) - min(ram_values)
            flash_variance = max(flash_values) - min(flash_values)

            print(f"  RAM variance: {ram_variance} bytes (max-min)")
            print(f"  Flash variance: {flash_variance} bytes (should be 0)")

            if flash_variance == 0 and ram_variance < 1000:
                print("  OK - Values are stable")
                results["Consistency"] = True
            else:
                print("  FAIL - Values too variable")
                results["Consistency"] = False
        else:
            print(f"  FAIL - Only {len(packets)} packets")
            results["Consistency"] = False

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
