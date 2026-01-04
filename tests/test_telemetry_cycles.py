#!/usr/bin/env python3
"""Test multiple START/STOP telemetry cycles."""

import sys
import struct
import time
import serial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from protocol_helpers import CMD, build_min_frame, MINFrameParser, ping


def start_telemetry(ser, rate_hz=10):
    ser.write(build_min_frame(CMD.START_STREAM, struct.pack('<H', rate_hz)))
    ser.flush()


def stop_telemetry(ser):
    ser.write(build_min_frame(CMD.STOP_STREAM))
    ser.flush()
    time.sleep(0.3)
    # Drain
    old_timeout = ser.timeout
    ser.timeout = 0.1
    try:
        while ser.read(1024):
            pass
    finally:
        ser.timeout = old_timeout


def count_telemetry_frames(ser, duration=1.0):
    """Count telemetry frames received in duration seconds."""
    parser = MINFrameParser()
    start = time.time()
    count = 0
    old_timeout = ser.timeout
    ser.timeout = 0.15
    try:
        while time.time() - start < duration:
            chunk = ser.read(512)
            if chunk:
                for cmd, _, _, _ in parser.feed(chunk):
                    if cmd == CMD.DATA:
                        count += 1
    finally:
        ser.timeout = old_timeout
    return count


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else 'COM11'
    cycles = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    print(f"=== Telemetry Cycles Test ({cycles} cycles) on {port} ===\n")
    
    ser = serial.Serial(port, 115200, timeout=2.0)
    time.sleep(2.0)
    
    try:
        # Initial ping
        print("[0] Initial PING...")
        ser.reset_input_buffer()
        if ping(ser, timeout=1.0):
            print("    OK")
        else:
            print("    FAIL - no response")
            return 1
        
        # Run cycles
        for i in range(cycles):
            print(f"\n[Cycle {i+1}/{cycles}]")
            
            # Start telemetry
            start_telemetry(ser, 10)
            time.sleep(0.2)  # Let telemetry start
            
            # Count frames for 0.5 seconds
            frames = count_telemetry_frames(ser, 0.5)
            print(f"    Telemetry frames: {frames}")
            
            # Stop telemetry
            stop_telemetry(ser)
            
            # Verify PING works
            time.sleep(0.2)
            if ping(ser, timeout=1.0):
                print("    PING: OK")
            else:
                print("    PING: FAIL - firmware hung!")
                return 1
        
        print(f"\n=== PASS ({cycles} cycles completed) ===")
        return 0
        
    finally:
        stop_telemetry(ser)
        ser.close()


if __name__ == '__main__':
    sys.exit(main())
