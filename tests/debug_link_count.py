#!/usr/bin/env python3
"""
Debug script: Upload config and check link_count in telemetry

Telemetry format (Nucleo):
- Offset 79-82: uptime_sec (4 bytes)
- Offset 83-86: ram_used (4 bytes)
- Offset 87-90: flash_used (4 bytes)
- Offset 91-92: channel_count (2 bytes)
- Offset 93: link_count DEBUG (1 byte) - was reserved
"""

import sys
import struct
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "shared" / "python"))
sys.path.insert(0, str(Path(__file__).parent))

from min_protocol import MINTransportSerial

# Channel types
CH_TYPE_POWER_OUTPUT = 0x10


def build_power_output_config(channel_id: int, hw_index: int, source_id: int, name: str) -> bytes:
    """Build binary config for a Power Output channel linked to source_id"""
    name_bytes = name.encode('utf-8')[:15]
    name_len = len(name_bytes)

    # Power Output config (12 bytes)
    config = struct.pack('<BHHH5s',
        0,          # source_mode: 0 = direct
        5000,       # current_limit_ma
        5000,       # inrush_limit_ma
        100,        # inrush_time_ms
        b'\x00' * 5 # reserved
    )
    config_size = len(config)

    # CfgChannelHeader_t (14 bytes)
    header = struct.pack('<HBBBBHIBB',
        channel_id,             # [0-1] channel_id
        CH_TYPE_POWER_OUTPUT,   # [2] type
        0x01,                   # [3] flags: enabled
        0,                      # [4] hw_device
        hw_index,               # [5] hw_index
        source_id,              # [6-7] source_id
        0,                      # [8-11] default_value
        name_len,               # [12] name_len
        config_size,            # [13] config_size
    )

    return header + name_bytes + config


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else 'COM11'

    print(f"=== Link Count Debug on {port} ===")
    print()

    min_ctx = MINTransportSerial(port, 115200)

    try:
        # 1. Stop any telemetry
        print("1. Stopping telemetry...")
        min_ctx.queue_frame(0x21, b'')  # STOP_STREAM
        time.sleep(0.3)
        min_ctx.poll()

        # 2. Check telemetry BEFORE config upload
        print("2. Starting telemetry to check link_count BEFORE upload...")
        min_ctx.queue_frame(0x20, struct.pack('<H', 10))  # START_STREAM
        time.sleep(0.5)
        print("   Waiting for telemetry...")

        got_telemetry = False
        for _ in range(10):
            frames = min_ctx.poll()
            for frame in frames:
                print(f"   Got frame: id=0x{frame.min_id:02x}, len={len(frame.payload)}")
                if frame.min_id == 0x22:  # DATA
                    if len(frame.payload) >= 94:
                        link_count = frame.payload[93]
                        channel_count = struct.unpack('<H', frame.payload[91:93])[0]
                        print(f"   channel_count={channel_count}, link_count={link_count}")
                        got_telemetry = True
                    break
            if got_telemetry:
                break
            time.sleep(0.1)

        if not got_telemetry:
            print("   No telemetry received!")

        # 3. Stop telemetry for config upload and drain pending frames
        print()
        print("Stopping telemetry stream...")
        min_ctx.queue_frame(0x21, b'')  # STOP_STREAM
        time.sleep(0.3)
        # Drain all pending telemetry frames
        for _ in range(20):
            frames = min_ctx.poll()
            if not frames:
                break
            time.sleep(0.05)
        print("   Stream stopped, buffer drained")

        # 4. Upload config: Power Output 100 linked to DIN 50 (Button B1)
        print()
        print("3. Uploading config: Power Output 100 -> DIN 50 (Button B1)...")
        power_output = build_power_output_config(
            channel_id=100,
            hw_index=1,       # Output 1 (PA9 on Nucleo)
            source_id=50,     # Link to Digital Input 50 (Button B1)
            name="LED"
        )
        config_data = struct.pack('<H', 1) + power_output
        chunk_header = struct.pack('<HH', 0, 1)
        payload = chunk_header + config_data

        print(f"   Payload size: {len(payload)} bytes")
        print(f"   Config data: {config_data.hex()}")
        min_ctx.queue_frame(0x18, payload)  # LOAD_BINARY

        # Wait for ACK
        print("   Waiting for BINARY_ACK...")
        start = time.time()
        ack_received = False
        while time.time() - start < 3.0:
            frames = min_ctx.poll()
            for frame in frames:
                print(f"      RX frame: id=0x{frame.min_id:02x}, len={len(frame.payload)}")
                if frame.min_id == 0x19:  # BINARY_ACK
                    success = frame.payload[0] if len(frame.payload) > 0 else 0
                    error = frame.payload[1] if len(frame.payload) > 1 else 0
                    channels = struct.unpack('<H', frame.payload[2:4])[0] if len(frame.payload) >= 4 else 0
                    print(f"   BINARY_ACK: success={success}, error={error}, channels={channels}")
                    ack_received = True
                    break
            if ack_received:
                break
            time.sleep(0.05)

        if not ack_received:
            print("   ERROR: No BINARY_ACK received!")
            return

        # 5. Start telemetry and check link_count AFTER upload
        print()
        print("4. Checking link_count AFTER upload...")
        time.sleep(0.3)
        min_ctx.queue_frame(0x20, struct.pack('<H', 10))  # START_STREAM
        time.sleep(0.5)

        for _ in range(5):
            frames = min_ctx.poll()
            for frame in frames:
                if frame.min_id == 0x22:  # DATA
                    if len(frame.payload) >= 101:
                        link_count = frame.payload[93]
                        channel_count = struct.unpack('<H', frame.payload[91:93])[0]
                        din = frame.payload[78]
                        # New debug fields
                        parsed_type = frame.payload[94]
                        parsed_source = struct.unpack('<H', frame.payload[95:97])[0]
                        addlink_called = frame.payload[97]
                        addlink_result = frame.payload[98]
                        load_count = frame.payload[99]
                        clear_count = frame.payload[100]

                        print(f"   channel_count={channel_count}, link_count={link_count}, DIN=0x{din:02x}")
                        print(f"   parsed: type=0x{parsed_type:02x}, source={parsed_source}")
                        print(f"   addlink: called={addlink_called}, result={addlink_result}")
                        print(f"   counts: load={load_count}, clear={clear_count}")

                        if link_count == 0:
                            print("   >>> link_count is 0! AddOutputLink didn't work!")
                        elif link_count == 1:
                            print("   >>> link_count is 1! Config loaded correctly!")
                    break
            else:
                time.sleep(0.1)
                continue
            break

        # 6. Monitor for button press
        print()
        print("5. Press button B1 - watching for 10 seconds...")

        start = time.time()
        last_din = None
        while time.time() - start < 10.0:
            frames = min_ctx.poll()
            for frame in frames:
                if frame.min_id == 0x22:  # DATA
                    if len(frame.payload) >= 103:
                        din = frame.payload[78]
                        output1 = frame.payload[8 + 1]  # output_states[1]
                        link_count = frame.payload[93]
                        source_value = frame.payload[101]
                        output_state = frame.payload[102]

                        # Decode flags: bit4=in_exec, bit5=ch_found
                        in_exec = (output_state >> 4) & 1
                        ch_found = (output_state >> 5) & 1
                        out_st = output_state & 0x0F

                        if din != last_din:
                            last_din = din
                            btn = "PRESSED" if din & 1 else "released"
                            print(f"   BTN={btn}, src={source_value}, out={out_st}, in_exec={in_exec}, ch_found={ch_found}, OUT1={output1}")
            time.sleep(0.05)

        # Stop
        min_ctx.queue_frame(0x21, b'')
        time.sleep(0.2)
        min_ctx.poll()

    finally:
        min_ctx.close()

    print()
    print("=== Done ===")


if __name__ == '__main__':
    main()
