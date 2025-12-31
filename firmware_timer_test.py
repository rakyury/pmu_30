#!/usr/bin/env python3
"""Test timer channel: LED turns off 5 seconds after button press."""

import serial
import struct
import time
import json
import sys

FRAME_MARKER = 0xAA
MSG_PING = 0x01
MSG_PONG = 0x02
MSG_SET_CONFIG = 0x22
MSG_START_STREAM = 0x30
MSG_STOP_STREAM = 0x31
MSG_DATA = 0x32

def crc16(data: bytes) -> int:
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
    frame = struct.pack('<BHB', FRAME_MARKER, len(payload), msg_type) + payload
    return frame + struct.pack('<H', crc16(frame[1:]))

def parse_telemetry(payload: bytes) -> dict:
    if len(payload) < 79:
        return None
    result = {
        "counter": struct.unpack("<I", payload[0:4])[0],
        "timestamp_ms": struct.unpack("<I", payload[4:8])[0],
        "output_states": list(payload[8:38]),
    }
    if len(payload) > 78:
        din_byte = payload[78]
        result["digital_inputs"] = [(din_byte >> i) & 1 for i in range(8)]
    # Debug byte at offset 79: bit7=ch50_exists, bit4=ch50_val, bit3=ch30_exists, bit0=ch30_val
    if len(payload) > 79:
        debug_byte = payload[79]
        result["ch50_exists"] = (debug_byte >> 7) & 1
        result["ch50_val"] = (debug_byte >> 4) & 1
        result["ch30_exists"] = (debug_byte >> 3) & 1
        result["ch30_val"] = debug_byte & 1
    # Extended timer debug: bytes 80-89
    if len(payload) > 89:
        result["timer_count"] = payload[80]
        result["start_channel_id"] = struct.unpack("<H", payload[81:83])[0]
        result["start_val"] = payload[83]
        result["prev_start_val"] = payload[84]
        result["timer_running"] = payload[85]
        result["update_calls"] = struct.unpack("<I", payload[86:90])[0]
    return result

def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM11"

    ser = serial.Serial(port, 115200, timeout=0.5)
    time.sleep(0.5)
    if ser.in_waiting:
        ser.read(ser.in_waiting)

    # Stop any existing stream
    ser.write(build_frame(MSG_STOP_STREAM))
    time.sleep(0.2)
    if ser.in_waiting:
        ser.read(ser.in_waiting)

    # PING
    ser.write(build_frame(MSG_PING))
    time.sleep(0.2)
    if ser.in_waiting:
        data = ser.read(ser.in_waiting)
        if len(data) >= 4 and data[0] == FRAME_MARKER and data[3] == MSG_PONG:
            print("[OK] PONG received")

    # Config:
    # 1. Digital input (DIN0 at pin 0) - button input, channel_id 50
    # 2. Timer (5 sec countdown) - starts on button press (DIN0 rising)
    # 3. Power output - controlled by timer main channel (outputs 1000 when running, 0 when stopped)
    #
    # Timer allocates 2 channels from shared pool (30-63 for F446RE):
    #   - channel 30: running state (0/1000)
    #   - channel 31: elapsed time in ms
    #
    # We want LED ON while timer running, OFF when expired

    print("\nSending config: DIN0 + Timer 5sec + power output...")
    config = {
        "version": "3.0",
        "device": {"name": "PMU30-TimerTest"},
        "channels": [
            {
                "channel_type": "digital_input",
                "channel_id": 50,
                "channel_name": "Button",
                "input_pin": 0,
                "subtype": "switch_active_high",
                "threshold_mv": 2500,
                "debounce_ms": 20
            },
            {
                "channel_type": "timer",
                "channel_id": 300,
                "channel_name": "Timer5s",
                "start_channel": 50,  # DIN0 - button (runtime channel_id)
                "start_edge": "rising",
                "mode": "count_down",
                "limit_seconds": 5
            },
            {
                "channel_type": "power_output",
                "channel_id": 100,
                "channel_name": "TimerLED",
                "pins": [1],
                "source_channel": 300,  # Timer JSON channel_id (maps to runtime ID 30)
                "current_limit_a": 10.0
            }
        ]
    }
    config_bytes = json.dumps(config, separators=(',', ':')).encode('utf-8')
    print(f"Config: {config_bytes.decode()}")
    header = struct.pack('<HH', 0, 1)
    ser.write(build_frame(MSG_SET_CONFIG, header + config_bytes))
    time.sleep(0.5)
    if ser.in_waiting:
        acks = ser.read(ser.in_waiting)
        print(f"ACKs: {acks.hex()}")

    # Start telemetry
    ser.write(build_frame(MSG_START_STREAM, struct.pack("<BBBBBBH", 1, 1, 1, 1, 1, 1, 100)))
    time.sleep(0.2)

    print("\n" + "=" * 100)
    print("TEST: Timer 5 seconds")
    print("  1. Press button to START timer (LED turns ON)")
    print("  2. Wait 5 seconds (LED turns OFF)")
    print("=" * 100)
    print("\nMonitoring 20 seconds...")
    print("Time    DIN0 OUT1 CH50 CH30 | TmrCnt StartCh SVal PVal Run  UpdCalls | Status")
    print("-" * 110)

    start = time.time()
    buffer = b""
    count = 0
    prev_din0 = None
    prev_out1 = None
    timer_started_at = None

    while time.time() - start < 20:
        if ser.in_waiting:
            buffer += ser.read(ser.in_waiting)
            while len(buffer) >= 4:
                idx = buffer.find(bytes([FRAME_MARKER]))
                if idx < 0:
                    buffer = b""
                    break
                if idx > 0:
                    buffer = buffer[idx:]
                if len(buffer) < 4:
                    break
                length = struct.unpack("<H", buffer[1:3])[0]
                msg_type = buffer[3]
                total_len = 4 + length + 2
                if len(buffer) < total_len:
                    break
                if msg_type == MSG_DATA:
                    tel = parse_telemetry(buffer[4:4+length])
                    if tel:
                        count += 1
                        din0 = tel.get("digital_inputs", [0])[0]
                        out1 = tel["output_states"][1]
                        elapsed = time.time() - start

                        # Get channel debug info
                        ch50_e = tel.get("ch50_exists", 0)
                        ch50_v = tel.get("ch50_val", 0)
                        ch30_e = tel.get("ch30_exists", 0)
                        ch30_v = tel.get("ch30_val", 0)
                        ch50_str = f"{ch50_v}" if ch50_e else "X"
                        ch30_str = f"{ch30_v}" if ch30_e else "X"

                        # Get extended timer debug
                        tmr_cnt = tel.get("timer_count", "?")
                        start_ch = tel.get("start_channel_id", 0xFFFF)
                        start_val = tel.get("start_val", "?")
                        prev_val = tel.get("prev_start_val", "?")
                        running = tel.get("timer_running", "?")
                        upd_calls = tel.get("update_calls", 0)

                        # Track timer start
                        if prev_out1 == 0 and out1 == 1:
                            timer_started_at = elapsed

                        # Show on state change or every 10th packet
                        if din0 != prev_din0 or out1 != prev_out1 or count % 10 == 1:
                            status = ""
                            if upd_calls == 0:
                                status = "TMR_UPDATE NOT CALLED!"
                            elif tmr_cnt == 0:
                                status = "NO TIMERS!"
                            elif start_ch == 0xFFFF:
                                status = "TIMER NOT CFG!"
                            elif ch50_e == 0:
                                status = "CH50 NOT REG!"
                            elif ch30_e == 0:
                                status = "CH30 NOT REG!"
                            elif din0 == 1:
                                status = "BTN PRESSED"
                            if out1 == 1:
                                if timer_started_at:
                                    remaining = 5.0 - (elapsed - timer_started_at)
                                    status = f"RUNNING ({remaining:.1f}s)"
                                else:
                                    status = "LED ON"
                            elif prev_out1 == 1 and out1 == 0:
                                status = ">>> EXPIRED <<<"

                            print(f"{elapsed:5.1f}s   {din0}    {out1}    {ch50_str}    {ch30_str}   |   {tmr_cnt}      {start_ch:5}   {start_val:3}  {prev_val:3}   {running}   {upd_calls:7} | {status}")
                            prev_din0 = din0
                            prev_out1 = out1

                buffer = buffer[total_len:]
        time.sleep(0.05)

    print(f"\nReceived {count} packets")
    ser.write(build_frame(MSG_STOP_STREAM))
    ser.close()

if __name__ == "__main__":
    main()
