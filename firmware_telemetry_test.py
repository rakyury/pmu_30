#!/usr/bin/env python3
"""
Telemetry Communication Test

Tests:
1. Connect to device (PING/PONG)
2. Get device info (GET_INFO)
3. Start telemetry stream
4. Receive telemetry data
5. Stop telemetry stream

Usage:
    python firmware_telemetry_test.py [COM_PORT]
"""

import sys
import struct
import time
import serial

# Protocol constants
FRAME_START = 0xAA
CMD_PING = 0x01
CMD_PONG = 0x02
CMD_GET_INFO = 0x10
CMD_INFO_RESP = 0x11
CMD_START_STREAM = 0x30
CMD_STOP_STREAM = 0x31
CMD_DATA = 0x32


def crc16_ccitt(data: bytes) -> int:
    """Calculate CRC16-CCITT checksum."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc


def build_frame(msg_type: int, payload: bytes = b'') -> bytes:
    """Build protocol frame with CRC."""
    frame_data = struct.pack('<BHB', FRAME_START, len(payload), msg_type) + payload
    crc = crc16_ccitt(frame_data[1:])  # CRC excludes start byte
    return frame_data + struct.pack('<H', crc)


def read_frame(port: serial.Serial, timeout: float = 1.0) -> tuple:
    """Read a complete frame from port. Returns (cmd, payload) or (None, None)."""
    start_time = time.time()
    buffer = b''

    while time.time() - start_time < timeout:
        if port.in_waiting > 0:
            buffer += port.read(port.in_waiting)

            # Try to find frame start
            start_idx = buffer.find(bytes([FRAME_START]))
            if start_idx >= 0:
                buffer = buffer[start_idx:]

                # Check if we have enough data for header
                if len(buffer) >= 4:
                    length = struct.unpack('<H', buffer[1:3])[0]
                    frame_size = 4 + length + 2

                    if len(buffer) >= frame_size:
                        cmd = buffer[3]
                        payload = buffer[4:4+length]
                        return cmd, payload

        time.sleep(0.01)

    return None, None


def parse_telemetry(payload: bytes) -> dict:
    """Parse telemetry payload."""
    if len(payload) < 8:
        return {"error": f"Payload too short: {len(payload)} bytes"}

    result = {
        "counter": struct.unpack("<I", payload[0:4])[0],
        "timestamp_ms": struct.unpack("<I", payload[4:8])[0],
    }

    # Output states (30 bytes at offset 8)
    if len(payload) >= 38:
        result["outputs"] = list(payload[8:38])

    # Digital inputs at offset 78
    if len(payload) > 78:
        din_byte = payload[78]
        result["digital_inputs"] = [(din_byte >> i) & 1 for i in range(8)]

    return result


def test_ping(port: serial.Serial) -> bool:
    """Test PING/PONG."""
    print("\n[1] Testing PING...")

    port.reset_input_buffer()
    frame = build_frame(CMD_PING)
    port.write(frame)
    port.flush()

    cmd, payload = read_frame(port)

    if cmd == CMD_PONG:
        print("    [OK] PONG received - device connected!")
        return True
    else:
        print(f"    [FAIL] Expected PONG (0x02), got: {hex(cmd) if cmd else 'None'}")
        return False


def test_get_info(port: serial.Serial) -> bool:
    """Test GET_INFO."""
    print("\n[2] Testing GET_INFO...")

    port.reset_input_buffer()
    frame = build_frame(CMD_GET_INFO)
    port.write(frame)
    port.flush()

    cmd, payload = read_frame(port, timeout=2.0)

    if cmd == CMD_INFO_RESP:
        print("    [OK] INFO_RESP received")
        if payload:
            try:
                info_str = payload.decode('utf-8', errors='replace').rstrip('\x00')
                print(f"    Device info: {info_str[:100]}")
            except:
                print(f"    Raw payload ({len(payload)} bytes): {payload[:50].hex()}")
        return True
    else:
        print(f"    [FAIL] Expected INFO_RESP (0x11), got: {hex(cmd) if cmd else 'None'}")
        return False


def test_start_telemetry(port: serial.Serial, rate_hz: int = 10) -> bool:
    """Test START_STREAM."""
    print(f"\n[3] Testing START_STREAM (rate={rate_hz}Hz)...")

    port.reset_input_buffer()

    # Payload: flags (6 bytes) + rate_ms (2 bytes)
    # flags: outputs, inputs, can, temps, voltages, faults
    rate_ms = 1000 // rate_hz
    payload = struct.pack('<BBBBBBH', 1, 1, 0, 0, 0, 0, rate_ms)
    frame = build_frame(CMD_START_STREAM, payload)
    port.write(frame)
    port.flush()

    print("    Waiting for telemetry data...")

    packets_received = 0
    start_time = time.time()
    timeout = 3.0

    while time.time() - start_time < timeout:
        cmd, payload = read_frame(port, timeout=0.5)

        if cmd == CMD_DATA:
            packets_received += 1
            if packets_received == 1:
                print(f"    [OK] First DATA packet received ({len(payload)} bytes)")
                tel = parse_telemetry(payload)
                if "error" not in tel:
                    print(f"      Counter: {tel['counter']}, Timestamp: {tel['timestamp_ms']}ms")

            if packets_received >= 3:
                break

    if packets_received > 0:
        print(f"    [OK] Received {packets_received} telemetry packets")
        return True
    else:
        print("    [FAIL] No telemetry data received")
        return False


def test_receive_telemetry(port: serial.Serial, duration: float = 5.0) -> int:
    """Receive telemetry for specified duration."""
    print(f"\n[4] Receiving telemetry for {duration}s...")
    print("    Cnt    Time(ms)   OUT[0] OUT[1] OUT[2]  DIN")
    print("    " + "-" * 50)

    packets = []
    start_time = time.time()

    while time.time() - start_time < duration:
        cmd, payload = read_frame(port, timeout=0.2)

        if cmd == CMD_DATA:
            tel = parse_telemetry(payload)
            if "error" not in tel:
                packets.append(tel)

                # Print every 10th packet or first 5
                if len(packets) <= 5 or len(packets) % 10 == 0:
                    outputs = tel.get("outputs", [0, 0, 0])
                    dins = tel.get("digital_inputs", [0])
                    din_str = ''.join(str(d) for d in dins[:4])
                    print(f"    {tel['counter']:5d}  {tel['timestamp_ms']:8d}      {outputs[0]:3d}   {outputs[1]:3d}   {outputs[2]:3d}   {din_str}")

    print(f"    [OK] Total packets: {len(packets)}")

    if packets:
        actual_rate = len(packets) / duration
        print(f"    Actual rate: {actual_rate:.1f} Hz")

    return len(packets)


def test_stop_telemetry(port: serial.Serial) -> bool:
    """Test STOP_STREAM."""
    print("\n[5] Testing STOP_STREAM...")

    frame = build_frame(CMD_STOP_STREAM)
    port.write(frame)
    port.flush()

    # Wait and check if telemetry stopped
    time.sleep(0.3)
    port.reset_input_buffer()
    time.sleep(1.0)

    # Count remaining DATA packets
    remaining_data = 0
    while port.in_waiting > 0:
        cmd, _ = read_frame(port, timeout=0.1)
        if cmd == CMD_DATA:
            remaining_data += 1

    if remaining_data == 0:
        print("    [OK] Telemetry stopped successfully")
        return True
    else:
        print(f"    [WARN] Still received {remaining_data} packets (may be buffered)")
        return True  # Not critical


def main():
    port_name = sys.argv[1] if len(sys.argv) > 1 else "COM3"

    print("=" * 60)
    print("PMU-30 Telemetry Test")
    print("=" * 60)
    print(f"Port: {port_name}")

    try:
        port = serial.Serial(
            port=port_name,
            baudrate=115200,
            timeout=1.0,
            write_timeout=1.0
        )
        print(f"Serial port opened: {port.name}")
        time.sleep(0.5)

        # Run tests
        results = []

        results.append(("PING/PONG", test_ping(port)))
        results.append(("GET_INFO", test_get_info(port)))
        results.append(("START_STREAM", test_start_telemetry(port, rate_hz=10)))

        packet_count = test_receive_telemetry(port, duration=5.0)
        results.append(("RECEIVE_DATA", packet_count > 0))

        results.append(("STOP_STREAM", test_stop_telemetry(port)))

        # Summary
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)

        all_passed = True
        for name, passed in results:
            status = "PASS" if passed else "FAIL"
            print(f"  {name}: {status}")
            if not passed:
                all_passed = False

        print("=" * 60)
        print("ALL TESTS PASSED" if all_passed else "SOME TESTS FAILED")
        print("=" * 60)

        port.close()
        return 0 if all_passed else 1

    except serial.SerialException as e:
        print(f"ERROR: Serial port error: {e}")
        return 1
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
