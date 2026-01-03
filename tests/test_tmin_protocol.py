#!/usr/bin/env python3
"""
PMU-30 T-MIN Protocol Integration Test

Comprehensive test for T-MIN (Transport MIN) protocol operations.
Runs 10 iterations to verify 100% reliability.

Uses T-MIN transport layer with automatic ACK/retransmit for reliable
communication with firmware.

Usage:
    python tests/test_tmin_protocol.py COM11
    python tests/test_tmin_protocol.py COM11 --iterations 10
"""

import sys
import struct
import time
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "shared" / "python"))
sys.path.insert(0, 'tests')

from channel_config import ChannelType
from protocol_helpers import CMD, TMinContext, parse_telemetry


@dataclass
class TestResult:
    """Single test result."""
    name: str
    passed: bool
    duration_ms: float
    error: str = ""


@dataclass
class IterationResult:
    """Results from one test iteration."""
    iteration: int
    tests: List[TestResult]
    duration_sec: float

    @property
    def passed(self) -> bool:
        return all(t.passed for t in self.tests)


def build_minimal_config():
    """Build minimal test config: 1 DIN -> 1 Output (direct link)."""
    channels = []

    # Digital Input (ch 50) - PC13 button
    din = struct.pack('<HBBBBHiBB',
        50, ChannelType.DIGITAL_INPUT, 0x01, 0x01, 0, 0xFFFF, 0, 7, 4)
    din += b'TestDIN'
    din += struct.pack('<BBH', 0, 1, 0)  # gpio_pin=0 (PC13), active_high=1
    channels.append(din)

    # Power Output (ch 100) - LED on PA5, source=DIN
    output = struct.pack('<HBBBBHiBB',
        100, ChannelType.POWER_OUTPUT, 0x01, 0x05, 1, 50, 0, 6, 12)
    output += b'OutLED'
    output += struct.pack('<HHHBBHBB', 1000, 0, 0, 100, 1, 0, 3, 0)
    channels.append(output)

    result = struct.pack('<H', len(channels))
    for ch in channels:
        result += ch
    return result


def run_test_iteration(tmin: TMinContext, iteration: int) -> IterationResult:
    """Run one full test iteration using T-MIN transport."""
    results = []
    start_time = time.time()

    # Test 1: PING/PONG
    t_start = time.time()
    try:
        tmin.send_command(CMD.PING)
        frames = tmin.wait_for_response(CMD.PONG, timeout=2.0)
        success = any(cmd == CMD.PONG for cmd, _, _ in frames)
        results.append(TestResult(
            "PING", success, (time.time() - t_start) * 1000,
            "" if success else "No PONG response"
        ))
    except Exception as e:
        results.append(TestResult("PING", False, 0, str(e)))

    # Test 2: Clear config
    t_start = time.time()
    try:
        tmin.send_command(CMD.CLEAR_CONFIG)
        frames = tmin.wait_for_response(CMD.CLEAR_CONFIG_ACK, timeout=2.0)
        success = False
        for cmd, payload, _ in frames:
            if cmd == CMD.CLEAR_CONFIG_ACK and len(payload) >= 1:
                success = payload[0] == 1
                break
        results.append(TestResult(
            "CLEAR_CONFIG", success, (time.time() - t_start) * 1000,
            "" if success else "No ACK"
        ))
    except Exception as e:
        results.append(TestResult("CLEAR_CONFIG", False, 0, str(e)))

    # Test 3: Upload config
    t_start = time.time()
    try:
        config = build_minimal_config()
        # Add chunk header: chunk_idx=0, total_chunks=1
        chunked = struct.pack('<HH', 0, 1) + config
        tmin.send_command(CMD.LOAD_BINARY, chunked)
        frames = tmin.wait_for_response(CMD.BINARY_ACK, timeout=5.0)

        success = False
        channels_loaded = 0
        error_msg = ""
        for cmd, payload, _ in frames:
            if cmd == CMD.BINARY_ACK and len(payload) >= 2:
                success = payload[0] == 1
                if len(payload) >= 4:
                    channels_loaded = struct.unpack('<H', payload[2:4])[0]
                error_msg = f"success={success}, channels={channels_loaded}, payload={payload.hex()}"
                break
            elif cmd == CMD.NACK:
                error_msg = f"NACK received: payload={payload.hex()}"

        # Executor only counts virtual channels + power outputs, not inputs
        # Test config has 1 DIN (skipped) + 1 Power Output (counted) = 1
        results.append(TestResult(
            "UPLOAD_CONFIG", success and channels_loaded >= 1,
            (time.time() - t_start) * 1000,
            "" if (success and channels_loaded >= 1) else error_msg
        ))
    except Exception as e:
        results.append(TestResult("UPLOAD_CONFIG", False, 0, str(e)))

    # Test 4: Read config back
    t_start = time.time()
    try:
        tmin.send_command(CMD.GET_CONFIG)
        frames = tmin.wait_for_response(CMD.CONFIG_DATA, timeout=5.0)

        cfg = None
        for cmd, payload, _ in frames:
            if cmd == CMD.CONFIG_DATA and len(payload) >= 4:
                cfg = payload[4:]  # Skip chunk header
                break

        if cfg is not None:
            count = struct.unpack('<H', cfg[:2])[0] if len(cfg) >= 2 else 0
            success = count >= 2
            results.append(TestResult(
                "READ_CONFIG", success, (time.time() - t_start) * 1000,
                "" if success else f"Expected 2 channels, got {count}"
            ))
        else:
            results.append(TestResult("READ_CONFIG", False, 0, "No config data"))
    except Exception as e:
        results.append(TestResult("READ_CONFIG", False, 0, str(e)))

    # Test 5: Save to flash
    t_start = time.time()
    try:
        tmin.send_command(CMD.SAVE_CONFIG)
        frames = tmin.wait_for_response(CMD.FLASH_ACK, timeout=5.0)

        success = False
        for cmd, payload, _ in frames:
            if cmd == CMD.FLASH_ACK and len(payload) >= 1:
                success = payload[0] == 1
                break

        results.append(TestResult(
            "SAVE_FLASH", success, (time.time() - t_start) * 1000,
            "" if success else "No FLASH_ACK"
        ))
    except Exception as e:
        results.append(TestResult("SAVE_FLASH", False, 0, str(e)))

    # Test 6: Telemetry streaming
    t_start = time.time()
    try:
        # Start stream (unreliable - telemetry doesn't need ACK)
        rate_payload = struct.pack('<H', 10)  # 10 Hz
        tmin.send_unreliable(CMD.START_STREAM, rate_payload)

        # Wait for telemetry data
        telem = None
        for _ in range(50):  # Try for ~2 seconds
            frames = tmin.poll()
            for frame in frames:
                if frame.min_id == CMD.DATA:
                    telem = parse_telemetry(frame.payload)
                    break
            if telem:
                break
            time.sleep(0.04)

        # Stop stream
        tmin.send_unreliable(CMD.STOP_STREAM)
        time.sleep(0.2)
        tmin.poll()  # Drain remaining

        if telem:
            success = telem.stream_counter >= 0
            results.append(TestResult(
                "TELEMETRY", success, (time.time() - t_start) * 1000,
                "" if success else "Invalid telemetry data"
            ))
        else:
            results.append(TestResult("TELEMETRY", False, 0, "No telemetry received"))
    except Exception as e:
        results.append(TestResult("TELEMETRY", False, 0, str(e)))

    # Cleanup
    try:
        tmin.send_command(CMD.CLEAR_CONFIG)
        tmin.wait_for_response(CMD.CLEAR_CONFIG_ACK, timeout=1.0)
    except:
        pass

    duration = time.time() - start_time
    return IterationResult(iteration, results, duration)


def print_iteration_result(result: IterationResult):
    """Print results from one iteration."""
    status = "PASS" if result.passed else "FAIL"
    print(f"\n[Iteration {result.iteration}] {status} ({result.duration_sec:.2f}s)")

    for test in result.tests:
        test_status = "OK" if test.passed else "FAIL"
        print(f"  [{test_status}] {test.name}: {test.duration_ms:.1f}ms", end="")
        if test.error:
            print(f" - {test.error}")
        else:
            print()


def main():
    parser = argparse.ArgumentParser(description="T-MIN Protocol Integration Test")
    parser.add_argument("port", nargs="?", default="COM11", help="Serial port")
    parser.add_argument("--iterations", "-n", type=int, default=10,
                        help="Number of test iterations (default: 10)")
    args = parser.parse_args()

    print("=" * 70)
    print("PMU-30 T-MIN Protocol Integration Test")
    print("=" * 70)
    print(f"Port: {args.port}")
    print(f"Iterations: {args.iterations}")
    print(f"Transport: T-MIN with automatic ACK/retransmit")
    print("=" * 70)

    # Connect with T-MIN transport
    try:
        tmin = TMinContext(args.port, 115200)
        tmin.__enter__()
        print("T-MIN transport initialized, RESET sent")
        time.sleep(1.0)  # Wait for firmware to process RESET
    except Exception as e:
        print(f"ERROR: Cannot open {args.port}: {e}")
        return 1

    # Run iterations
    all_results: List[IterationResult] = []
    start_total = time.time()

    try:
        for i in range(1, args.iterations + 1):
            result = run_test_iteration(tmin, i)
            all_results.append(result)
            print_iteration_result(result)

            # Small pause between iterations
            if i < args.iterations:
                time.sleep(0.3)
    finally:
        # Cleanup
        tmin.__exit__(None, None, None)

    # Summary
    total_duration = time.time() - start_total
    passed_iterations = sum(1 for r in all_results if r.passed)
    failed_iterations = args.iterations - passed_iterations

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total iterations: {args.iterations}")
    print(f"Passed:           {passed_iterations}")
    print(f"Failed:           {failed_iterations}")
    print(f"Success rate:     {100 * passed_iterations / args.iterations:.1f}%")
    print(f"Total time:       {total_duration:.2f}s")
    print("=" * 70)

    if failed_iterations > 0:
        print("\nFAILED TESTS:")
        for result in all_results:
            if not result.passed:
                for test in result.tests:
                    if not test.passed:
                        print(f"  Iteration {result.iteration}: {test.name} - {test.error}")

    print("\n" + "=" * 70)
    if passed_iterations == args.iterations:
        print("ALL ITERATIONS PASSED!")
        return 0
    else:
        print(f"FAILED: {failed_iterations}/{args.iterations} iterations failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
