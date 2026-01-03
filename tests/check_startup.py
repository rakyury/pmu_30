#!/usr/bin/env python3
"""Check if firmware sends startup message."""

import sys
import time
import serial

port = sys.argv[1] if len(sys.argv) > 1 else "COM11"
print(f"Opening {port} and waiting for startup message...")

ser = serial.Serial(port, 115200, timeout=5.0)
print("Port opened. Reading for 5 seconds...")

data = ser.read(1024)
if data:
    print(f"Received {len(data)} bytes:")
    print(f"  Hex: {data.hex()}")
    try:
        print(f"  Text: {data.decode('utf-8', errors='replace')}")
    except:
        pass
else:
    print("No data received in 5 seconds!")

ser.close()
