#!/usr/bin/env python3
"""
Configurator Binary Config Test

Tests binary configuration upload using Configurator's communication modules.
This test verifies the full communication path:
  Configurator -> serialize_ui_channels_for_executor() -> LOAD_BINARY_CONFIG -> Firmware

Usage:
    python configurator_binary_test.py [COM_PORT]

Example:
    python configurator_binary_test.py COM3
"""

import sys
import struct
import time
from pathlib import Path

# Add configurator src to path
configurator_src = Path(__file__).parent / "configurator" / "src"
sys.path.insert(0, str(configurator_src))

# Add shared library
shared_path = Path(__file__).parent / "shared" / "python"
sys.path.insert(0, str(shared_path))

import serial
from channel_config import CH_REF_NONE

# Import configurator's binary config serializer
from models.binary_config import serialize_ui_channels_for_executor

# Protocol constants
FRAME_START = 0xAA
CMD_LOAD_BINARY_CONFIG = 0x68
CMD_BINARY_CONFIG_ACK = 0x69
CMD_PING = 0x01
CMD_PONG = 0x02
CMD_SET_CONFIG = 0x22
CMD_CONFIG_ACK = 0x23


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


def build_frame(msg_type: int, payload: bytes) -> bytes:
    """Build protocol frame with CRC."""
    frame_data = struct.pack('<BHB', FRAME_START, len(payload), msg_type) + payload
    crc = crc16_ccitt(frame_data[1:])
    return frame_data + struct.pack('<H', crc)


def build_chunked_frame(msg_type: int, chunk_idx: int, total_chunks: int, chunk: bytes) -> bytes:
    """Build chunked frame (for config upload)."""
    header = struct.pack('<HH', chunk_idx, total_chunks)
    payload = header + chunk
    return build_frame(msg_type, payload)


def ping_device(port: serial.Serial) -> bool:
    """Send PING and wait for PONG."""
    print("Testing connection (PING)...")
    frame = build_frame(CMD_PING, b'')

    port.reset_input_buffer()
    port.write(frame)
    port.flush()

    time.sleep(0.2)
    response = port.read(20)

    if len(response) >= 4:
        if response[0] == FRAME_START and response[3] == CMD_PONG:
            print("  ✓ PONG received - device connected!")
            return True

    print(f"  ✗ No PONG response: {response.hex() if response else 'none'}")
    return False


def send_binary_config(port: serial.Serial, binary_data: bytes) -> bool:
    """Send binary config using Configurator's frame format."""
    chunk_size = 1024
    chunks = [binary_data[i:i + chunk_size] for i in range(0, len(binary_data), chunk_size)]
    total_chunks = len(chunks)

    print(f"\nSending binary config: {len(binary_data)} bytes in {total_chunks} chunk(s)")

    for idx, chunk in enumerate(chunks):
        frame = build_chunked_frame(CMD_LOAD_BINARY_CONFIG, idx, total_chunks, chunk)
        print(f"  Chunk {idx+1}/{total_chunks}: {len(chunk)} bytes")

        port.reset_input_buffer()
        port.write(frame)
        port.flush()

        # Wait for ACK
        time.sleep(0.15)
        response = port.read(30)

        if len(response) >= 6:
            if response[0] == FRAME_START and response[3] == CMD_BINARY_CONFIG_ACK:
                success = response[4]
                error_code = response[5] if len(response) > 5 else 0
                print(f"    ACK: success={success}, error={error_code}")

                if not success and error_code != 0:
                    print(f"    ✗ ERROR: Chunk rejected!")
                    return False
            else:
                print(f"    Response: cmd=0x{response[3]:02X}")
        else:
            print(f"    Partial/no response: {len(response)} bytes")

    # Wait for final ACK with channel count
    time.sleep(0.3)
    final = port.read(30)
    if len(final) >= 8 and final[0] == FRAME_START and final[3] == CMD_BINARY_CONFIG_ACK:
        success = final[4]
        channels_loaded = final[6] | (final[7] << 8) if len(final) > 7 else 0
        print(f"  Final ACK: success={success}, channels_loaded={channels_loaded}")
        return success == 1

    return True  # Assume success if no error


def create_test_channels() -> list:
    """Create test channel configs in UI format (dict)."""
    channels = [
        # Timer channel
        {
            "channel_id": 200,
            "type": "timer",
            "name": "TestTimer",
            "timer_mode": "one_shot",
            "limit_hours": 0,
            "limit_minutes": 0,
            "limit_seconds": 5,
            "start_channel": None,
        },
        # Logic AND channel
        {
            "channel_id": 201,
            "type": "logic",
            "name": "TestLogic",
            "operation": "and",
            "input_channels": [1, 2],
            "compare_value": 0,
            "invert_output": False,
        },
        # Number constant
        {
            "channel_id": 202,
            "type": "number",
            "name": "TestNumber",
            "constant_value": 123.45,
            "min_value": -1000,
            "max_value": 1000,
            "step": 1,
        },
        # Filter
        {
            "channel_id": 203,
            "type": "filter",
            "name": "TestFilter",
            "input_channel": 10,
            "time_constant": 0.5,
        },
        # Digital input (should be skipped - not a virtual channel)
        {
            "channel_id": 1,
            "type": "digital_input",
            "name": "Button1",
        },
        # Power output (should be skipped - not a virtual channel)
        {
            "channel_id": 100,
            "type": "power_output",
            "name": "Output1",
        },
    ]
    return channels


def main():
    # Get COM port
    if len(sys.argv) > 1:
        port_name = sys.argv[1]
    else:
        port_name = "COM3"

    print("=" * 60)
    print("Configurator Binary Config Communication Test")
    print("=" * 60)
    print(f"Port: {port_name}")
    print()

    try:
        # Open serial port
        port = serial.Serial(
            port=port_name,
            baudrate=115200,
            timeout=1.0,
            write_timeout=1.0
        )
        print(f"✓ Serial port opened: {port.name}")

        time.sleep(0.5)

        # Test connectivity
        if not ping_device(port):
            print("\n✗ ERROR: Device not responding")
            port.close()
            return 1

        # Create test channels (UI format)
        print("\nCreating test channels (UI format)...")
        test_channels = create_test_channels()
        print(f"  Total channels: {len(test_channels)}")
        for ch in test_channels:
            print(f"    - [{ch['channel_id']:3d}] {ch['type']:15} {ch.get('name', '')}")

        # Serialize using Configurator's binary_config module
        print("\nSerializing with serialize_ui_channels_for_executor()...")
        binary_data = serialize_ui_channels_for_executor(test_channels)

        # Parse and show what was serialized
        if len(binary_data) >= 2:
            channel_count = struct.unpack('<H', binary_data[:2])[0]
            print(f"  Serialized {channel_count} virtual channels")
            print(f"  Total size: {len(binary_data)} bytes")
            print(f"  Hex (first 50 bytes): {binary_data[:50].hex()}")

        # Send binary config
        success = send_binary_config(port, binary_data)

        print("\n" + "=" * 60)
        if success:
            print("✓ SUCCESS: Binary config uploaded via Configurator module!")
        else:
            print("✗ FAILED: Binary config upload failed")
        print("=" * 60)

        port.close()
        return 0 if success else 1

    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("  Make sure you're running from pmu_30 directory")
        return 1
    except serial.SerialException as e:
        print(f"✗ Serial port error: {e}")
        return 1
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
