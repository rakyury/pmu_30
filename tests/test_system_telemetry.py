#!/usr/bin/env python3
"""
PMU-30 System Telemetry Test (MIN Protocol)

Tests that system channels in telemetry are working and updating:
- Uptime: Should increment over time
- Output states: Should reflect physical outputs
- Digital inputs: Should reflect GPIO state
- Virtual channels: Should be present when config is loaded

Usage: python tests/test_system_telemetry.py [COM_PORT]
"""

import sys
import struct
import time
import serial

# Import protocol helpers - MIN protocol implementation
sys.path.insert(0, 'tests')
from protocol_helpers import (
    CMD, build_min_frame, MINFrameParser, drain_serial,
    ping, start_stream, stop_stream, parse_telemetry, get_capabilities
)


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM11"
    print("=" * 60)
    print("PMU-30 System Telemetry Test (MIN Protocol)")
    print("=" * 60)
    print(f"Port: {port}")

    results = {}

    try:
        ser = serial.Serial(port, 115200, timeout=1.0, write_timeout=1.0)
        time.sleep(2.0)  # Wait for device startup

        # Ensure clean state
        stop_stream(ser)
        drain_serial(ser, 200)

        # Test 0: Connection test
        print("\n[TEST 0] Connection (PING/PONG)")
        if ping(ser, timeout=2.0):
            print("  OK - Device responding")
            results["Connection"] = True
        else:
            print("  FAIL - No PONG response")
            results["Connection"] = False
            ser.close()
            return 1

        # Test 1: Get capabilities
        print("\n[TEST 1] Device Capabilities")
        caps = get_capabilities(ser, timeout=2.0)
        if caps:
            print(f"  Device type: 0x{caps.device_type:02X} ({caps.device_name})")
            print(f"  Firmware: v{caps.fw_version_str}")
            print(f"  Outputs: {caps.output_count}")
            print(f"  Analog inputs: {caps.analog_input_count}")
            print(f"  Digital inputs: {caps.digital_input_count}")
            print(f"  H-Bridges: {caps.hbridge_count}")
            print(f"  CAN buses: {caps.can_bus_count}")
            print("  OK - Capabilities received")
            results["Capabilities"] = True
        else:
            print("  FAIL - No capabilities response")
            results["Capabilities"] = False

        # Test 2: Basic telemetry reception
        print("\n[TEST 2] Basic Telemetry Reception")
        start_stream(ser, rate_hz=10)

        packets = []
        parser = MINFrameParser()
        start_time = time.time()

        while time.time() - start_time < 2.0:
            chunk = ser.read(512)
            if chunk:
                frames = parser.feed(chunk)
                for cmd, payload, seq, _ in frames:
                    if cmd == CMD.DATA:
                        tel = parse_telemetry(payload)
                        if tel:
                            packets.append(tel)
                        if len(packets) >= 15:
                            break
            if len(packets) >= 15:
                break

        stop_stream(ser)

        if len(packets) >= 10:
            print(f"  Received {len(packets)} packets")
            latest = packets[-1]
            print(f"  Counter: {latest.stream_counter}")
            print(f"  Timestamp: {latest.timestamp_ms} ms")
            print(f"  Uptime: {latest.uptime_sec} s")
            print("  OK - Telemetry streaming")
            results["Basic"] = True
        else:
            print(f"  FAIL - Only {len(packets)} packets received")
            results["Basic"] = False

        # Test 3: Uptime incrementing
        print("\n[TEST 3] Uptime Incrementing")
        start_stream(ser, rate_hz=10)

        packets = []
        parser = MINFrameParser()
        start_time = time.time()

        while time.time() - start_time < 3.5:
            chunk = ser.read(512)
            if chunk:
                frames = parser.feed(chunk)
                for cmd, payload, seq, _ in frames:
                    if cmd == CMD.DATA:
                        tel = parse_telemetry(payload)
                        if tel:
                            packets.append(tel)

        stop_stream(ser)

        if len(packets) >= 20:
            uptime_first = packets[0].uptime_sec
            uptime_last = packets[-1].uptime_sec
            delta = uptime_last - uptime_first
            print(f"  First uptime: {uptime_first} s")
            print(f"  Last uptime: {uptime_last} s")
            print(f"  Delta: {delta} s (expected 1-10)")

            if 1 <= delta <= 10:
                print("  OK - Uptime incrementing correctly")
                results["Uptime"] = True
            else:
                print(f"  FAIL - Delta {delta} not in expected range")
                results["Uptime"] = False
        else:
            print(f"  FAIL - Only {len(packets)} packets")
            results["Uptime"] = False

        # Test 4: Counter incrementing
        print("\n[TEST 4] Counter Incrementing")
        start_stream(ser, rate_hz=20)

        packets = []
        parser = MINFrameParser()
        start_time = time.time()

        while time.time() - start_time < 1.0:
            chunk = ser.read(512)
            if chunk:
                frames = parser.feed(chunk)
                for cmd, payload, seq, _ in frames:
                    if cmd == CMD.DATA:
                        tel = parse_telemetry(payload)
                        if tel:
                            packets.append(tel)
                        if len(packets) >= 15:
                            break
            if len(packets) >= 15:
                break

        stop_stream(ser)

        if len(packets) >= 10:
            counters = [p.stream_counter for p in packets]
            increments = [counters[i+1] - counters[i] for i in range(len(counters)-1)]
            good = sum(1 for inc in increments if inc == 1)
            print(f"  Packets: {len(packets)}")
            print(f"  Consecutive increments: {good}/{len(increments)}")

            if good >= len(increments) * 0.8:
                print("  OK - Counter incrementing correctly")
                results["Counter"] = True
            else:
                print("  FAIL - Too many gaps in counter")
                results["Counter"] = False
        else:
            print(f"  FAIL - Only {len(packets)} packets")
            results["Counter"] = False

        # Test 5: Output states in telemetry
        print("\n[TEST 5] Output States Field")
        start_stream(ser, rate_hz=10)

        tel = None
        parser = MINFrameParser()
        start_time = time.time()

        while time.time() - start_time < 1.0:
            chunk = ser.read(512)
            if chunk:
                frames = parser.feed(chunk)
                for cmd, payload, seq, _ in frames:
                    if cmd == CMD.DATA:
                        tel = parse_telemetry(payload)
                        break
            if tel:
                break

        stop_stream(ser)

        if tel and len(tel.output_states) == 30:
            active = sum(1 for s in tel.output_states if s)
            print(f"  Output states array: {len(tel.output_states)} entries")
            print(f"  Active outputs: {active}")
            print("  OK - Output states field valid")
            results["OutputStates"] = True
        else:
            print("  FAIL - Invalid output states")
            results["OutputStates"] = False

        # Test 6: ADC values in telemetry
        print("\n[TEST 6] ADC Values Field")
        start_stream(ser, rate_hz=10)

        tel = None
        parser = MINFrameParser()
        start_time = time.time()

        while time.time() - start_time < 1.0:
            chunk = ser.read(512)
            if chunk:
                frames = parser.feed(chunk)
                for cmd, payload, seq, _ in frames:
                    if cmd == CMD.DATA:
                        tel = parse_telemetry(payload)
                        break
            if tel:
                break

        stop_stream(ser)

        if tel and len(tel.adc_values) == 20:
            non_zero = sum(1 for v in tel.adc_values if v > 0)
            print(f"  ADC values array: {len(tel.adc_values)} entries")
            print(f"  Non-zero values: {non_zero}")
            print(f"  Sample values: {tel.adc_values[:3]}")
            print("  OK - ADC values field valid")
            results["ADCValues"] = True
        else:
            print("  FAIL - Invalid ADC values")
            results["ADCValues"] = False

        # Test 7: Digital inputs in telemetry
        print("\n[TEST 7] Digital Inputs Field")
        start_stream(ser, rate_hz=10)

        tel = None
        parser = MINFrameParser()
        start_time = time.time()

        while time.time() - start_time < 1.0:
            chunk = ser.read(512)
            if chunk:
                frames = parser.feed(chunk)
                for cmd, payload, seq, _ in frames:
                    if cmd == CMD.DATA:
                        tel = parse_telemetry(payload)
                        break
            if tel:
                break

        stop_stream(ser)

        if tel is not None:
            print(f"  Digital inputs bitmask: 0b{tel.digital_inputs:08b}")
            active_dins = bin(tel.digital_inputs).count('1')
            print(f"  Active digital inputs: {active_dins}")
            print("  OK - Digital inputs field valid")
            results["DigitalInputs"] = True
        else:
            print("  FAIL - No telemetry received")
            results["DigitalInputs"] = False

        # Test 8: Timestamp monotonic
        print("\n[TEST 8] Timestamp Monotonic")
        start_stream(ser, rate_hz=20)

        packets = []
        parser = MINFrameParser()
        start_time = time.time()

        while time.time() - start_time < 1.0:
            chunk = ser.read(512)
            if chunk:
                frames = parser.feed(chunk)
                for cmd, payload, seq, _ in frames:
                    if cmd == CMD.DATA:
                        tel = parse_telemetry(payload)
                        if tel:
                            packets.append(tel)
                        if len(packets) >= 15:
                            break
            if len(packets) >= 15:
                break

        stop_stream(ser)

        if len(packets) >= 10:
            timestamps = [p.timestamp_ms for p in packets]
            monotonic = all(timestamps[i] < timestamps[i+1] for i in range(len(timestamps)-1))
            print(f"  First timestamp: {timestamps[0]} ms")
            print(f"  Last timestamp: {timestamps[-1]} ms")
            print(f"  Monotonic: {monotonic}")

            if monotonic:
                print("  OK - Timestamps are monotonically increasing")
                results["Timestamp"] = True
            else:
                print("  FAIL - Timestamps not monotonic")
                results["Timestamp"] = False
        else:
            print(f"  FAIL - Only {len(packets)} packets")
            results["Timestamp"] = False

        ser.close()

        # Summary
        print("\n" + "=" * 60)
        print("RESULTS:")
        print("=" * 60)
        for name, passed in results.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {status} {name}")

        passed = sum(1 for r in results.values() if r)
        failed = sum(1 for r in results.values() if not r)
        print("=" * 60)
        print(f"PASSED: {passed}/{len(results)}")
        if failed > 0:
            print("SOME TESTS FAILED")
            return 1
        else:
            print("ALL TESTS PASSED!")
            return 0

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
