#!/usr/bin/env python3
"""
Test button -> power output linking on Nucleo-F446RE

Tests that:
1. Digital input DIN0 (button on PC13) is read correctly
2. Power output on pin 1 responds to DIN0 via source_channel linking
"""

import serial
import struct
import time
import json
import sys

# Protocol constants
FRAME_MARKER = 0xAA
MSG_PING = 0x01
MSG_PONG = 0x02
MSG_SET_CONFIG = 0x22
MSG_CONFIG_ACK = 0x23
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
    """Parse telemetry payload."""
    if len(payload) < 79:
        return {"error": f"Payload too short: {len(payload)} bytes"}

    result = {
        "counter": struct.unpack("<I", payload[0:4])[0],
        "timestamp_ms": struct.unpack("<I", payload[4:8])[0],
        "output_states": list(payload[8:38]),  # 30 outputs
    }

    # Digital inputs at offset 78 (1 byte = 8 bits)
    if len(payload) > 78:
        din_byte = payload[78]
        result["digital_inputs"] = [(din_byte >> i) & 1 for i in range(8)]
    else:
        result["digital_inputs"] = [0] * 8

    return result


class OutputLinkTester:
    def __init__(self, port: str, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None

    def connect(self) -> bool:
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=2)
            time.sleep(0.5)
            if self.ser.in_waiting:
                self.ser.read(self.ser.in_waiting)
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False

    def disconnect(self):
        if self.ser:
            self.ser.close()

    def send_and_receive(self, frame: bytes, timeout: float = 1.0) -> bytes:
        self.ser.timeout = timeout
        self.ser.write(frame)
        self.ser.flush()
        time.sleep(0.1)

        response = b""
        start = time.time()
        while time.time() - start < timeout:
            if self.ser.in_waiting:
                response += self.ser.read(self.ser.in_waiting)
                if len(response) >= 6:
                    length = struct.unpack("<H", response[1:3])[0] if response[0] == FRAME_MARKER else 0
                    if len(response) >= 4 + length + 2:
                        break
            time.sleep(0.02)
        return response

    def send_config(self, config: dict) -> bool:
        """Send configuration with chunking."""
        config_bytes = json.dumps(config, separators=(',', ':')).encode('utf-8')

        chunk_size = 1024
        chunks = [config_bytes[i:i+chunk_size] for i in range(0, len(config_bytes), chunk_size)]
        if not chunks:
            chunks = [b'']

        for i, chunk in enumerate(chunks):
            header = struct.pack('<HH', i, len(chunks))
            payload = header + chunk
            frame = build_frame(MSG_SET_CONFIG, payload)

            self.ser.write(frame)
            self.ser.flush()
            time.sleep(0.1)

            response = self.ser.read(64)
            if response:
                # Check for ACK
                idx = response.find(bytes([FRAME_MARKER]))
                if idx >= 0 and len(response) > idx + 4:
                    msg_type = response[idx + 3]
                    if msg_type == MSG_CONFIG_ACK:
                        continue
            return False
        return True

    def start_stream(self) -> bool:
        payload = struct.pack("<BBBBBBH", 1, 1, 1, 1, 1, 1, 10)  # All enabled, 10Hz
        frame = build_frame(MSG_START_STREAM, payload)
        response = self.send_and_receive(frame)
        return bool(response)

    def stop_stream(self):
        frame = build_frame(MSG_STOP_STREAM)
        self.send_and_receive(frame)

    def receive_telemetry(self, timeout: float = 0.5) -> dict:
        self.ser.timeout = timeout
        response = b""
        start = time.time()

        while time.time() - start < timeout:
            if self.ser.in_waiting:
                response += self.ser.read(self.ser.in_waiting)

                while response and response[0] != FRAME_MARKER:
                    response = response[1:]

                if len(response) >= 6:
                    length = struct.unpack("<H", response[1:3])[0]
                    if len(response) >= 4 + length + 2:
                        msg_type = response[3]
                        if msg_type == MSG_DATA:
                            payload = response[4:4+length]
                            return parse_telemetry(payload)
                        break
            time.sleep(0.02)
        return {}

    def run_test(self):
        print(f"\n{'='*60}")
        print("PMU-30 Button -> Output Link Test")
        print(f"Port: {self.port}")
        print(f"{'='*60}\n")

        # Connect
        print("Connecting...")
        if not self.connect():
            print("[FAIL] Cannot connect")
            return False
        print("[OK] Connected\n")

        # Verify PING
        print("Verifying connection...")
        frame = build_frame(MSG_PING)
        response = self.send_and_receive(frame)
        if not response or len(response) < 4 or response[3] != MSG_PONG:
            print("[FAIL] No PONG")
            self.disconnect()
            return False
        print("[OK] PING/PONG verified\n")

        # Send config: power output on pin 1, source_channel_id = 50 (DIN0)
        # Per documentation schema - must use version 3.0 for "channels" array
        print("Sending power output config (pin 1 <- DIN0)...")
        config = {
            "version": "3.0",
            "device": {"name": "PMU30-Test"},
            "channels": [{
                "channel_type": "power_output",  # Must be "channel_type" per parser
                "channel_id": 100,
                "channel_name": "ButtonLED",
                "pins": [1],
                "source_channel_id": 50,  # DIN0 channel_id
                "current_limit_a": 10
            }]
        }
        if not self.send_config(config):
            print("[WARN] Config ACK not received (may still work)")
        else:
            print("[OK] Config sent\n")

        # Start telemetry
        print("Starting telemetry...")
        self.start_stream()
        time.sleep(0.3)
        print("[OK] Telemetry streaming\n")

        # Monitor
        print("="*60)
        print("TEST: Press button (PC13) - Output 1 (PA8) should follow")
        print("="*60)
        print("\nMonitoring... (30s timeout, Ctrl+C to exit)")
        print("DIN0  OUT1  Status")
        print("-" * 30)

        button_pressed = False
        output_followed = False
        last_din = None
        last_out = None

        try:
            start = time.time()
            while time.time() - start < 30:
                tel = self.receive_telemetry(0.2)
                if tel and "digital_inputs" in tel:
                    din0 = tel["digital_inputs"][0]
                    out1 = tel["output_states"][1] if len(tel["output_states"]) > 1 else 0

                    if din0 != last_din or out1 != last_out:
                        status = ""
                        if din0 == 1:
                            button_pressed = True
                            status = "<- BUTTON PRESSED"
                        elif last_din == 1 and din0 == 0:
                            status = "<- button released"

                        if din0 == out1:
                            if din0 == 1:
                                output_followed = True
                                status += " | OUTPUT ON!"
                            else:
                                status += " | output off"

                        print(f"  {din0}     {out1}    {status}")
                        last_din = din0
                        last_out = out1

                    # Success: button was pressed and output followed
                    if button_pressed and output_followed:
                        print("\n" + "="*60)
                        print("[PASS] Button -> Output linking works!")
                        print("       DIN0 pressed -> OUT1 turned ON")
                        print("="*60)
                        break

        except KeyboardInterrupt:
            print("\n\nInterrupted by user")

        # Stop
        self.stop_stream()
        self.disconnect()

        if button_pressed and output_followed:
            return True
        else:
            print("\n[FAIL] Test incomplete")
            if not button_pressed:
                print("       Button was not pressed")
            if not output_followed:
                print("       Output did not follow button state")
            return False


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM11"
    tester = OutputLinkTester(port)
    success = tester.run_test()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
