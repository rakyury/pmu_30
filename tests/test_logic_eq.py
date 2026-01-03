#!/usr/bin/env python3
"""
PMU-30 Logic EQ (Equal) Test

Tests Logic EQ function:
  - DIN0 (button 0, ch 50) == threshold

Chain:
  DIN0 (button, ch 50) -> Logic EQ (ch 200, threshold=1) -> Power Output (ch 100) -> LED

Logic EQ configuration:
  - Input: DIN0 (value 0 or 1)
  - Threshold: 1
  - Operation: input == threshold

Expected behavior:
  - Button released (0) -> 0 == 1 = FALSE -> LED OFF
  - Button pressed  (1) -> 1 == 1 = TRUE  -> LED ON

Usage:
    python tests/test_logic_eq.py [COM_PORT]
"""

import sys
import struct
import time
import serial
from typing import Optional, Tuple


# Protocol constants
FRAME_START = 0xAA

class CMD:
    PING = 0x01
    PONG = 0x02
    START_STREAM = 0x30
    STOP_STREAM = 0x31
    DATA = 0x32
    LOAD_BINARY_CONFIG = 0x68
    BINARY_CONFIG_ACK = 0x69


# Channel types
CH_TYPE_LOGIC = 0x21
CH_TYPE_POWER_OUTPUT = 0x10

# Logic operations
LOGIC_OP_EQ = 0x14

# Channel IDs
CH_DIN0 = 50
CH_LOGIC_EQ = 200
CH_OUTPUT_0 = 100

# Hardware
HW_DEVICE_PROFET = 0x05
CH_REF_NONE = 0xFFFF
CFG_MAX_INPUTS = 8


def crc16_ccitt(data: bytes) -> int:
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
    frame_data = struct.pack('<BHB', FRAME_START, len(payload), msg_type) + payload
    crc = crc16_ccitt(frame_data[1:])
    return frame_data + struct.pack('<H', crc)


def read_frame(port: serial.Serial, timeout: float = 2.0) -> Tuple[Optional[int], Optional[bytes]]:
    start_time = time.time()
    buffer = b''
    while time.time() - start_time < timeout:
        if port.in_waiting > 0:
            buffer += port.read(port.in_waiting)
            start_idx = buffer.find(bytes([FRAME_START]))
            if start_idx >= 0:
                buffer = buffer[start_idx:]
                if len(buffer) >= 4:
                    length = struct.unpack('<H', buffer[1:3])[0]
                    frame_size = 4 + length + 2
                    if len(buffer) >= frame_size:
                        cmd = buffer[3]
                        payload = buffer[4:4+length]
                        return cmd, payload
        time.sleep(0.01)
    return None, None


def build_channel_header(channel_id, channel_type, flags=0x01, hw_device=0, hw_index=0,
                          source_id=CH_REF_NONE, default_value=0, name="", config_size=0):
    name_bytes = name.encode('utf-8')[:31]
    header = struct.pack('<HBBBBHiBB', channel_id, channel_type, flags, hw_device,
                         hw_index, source_id, default_value, len(name_bytes), config_size)
    return header + name_bytes


def build_logic_config(operation: int, inputs: list, threshold: int = 0) -> bytes:
    inputs_padded = inputs + [0] * (CFG_MAX_INPUTS - len(inputs))
    return struct.pack('<BB8Hi?3s', operation, len(inputs), *inputs_padded, threshold, False, b'\x00\x00\x00')


def build_power_output_config() -> bytes:
    return struct.pack('<HHHBBHBB', 5000, 100, 10000, 3, 5, 0, 0, 0)


def build_test_config() -> bytes:
    channels = []

    # Logic EQ (ch 200) - threshold = 1
    logic_config = build_logic_config(LOGIC_OP_EQ, [CH_DIN0], threshold=1)
    logic_header = build_channel_header(CH_LOGIC_EQ, CH_TYPE_LOGIC, name="EQ",
                                         config_size=len(logic_config))
    channels.append(logic_header + logic_config)

    # Power Output (ch 100)
    output_config = build_power_output_config()
    output_header = build_channel_header(CH_OUTPUT_0, CH_TYPE_POWER_OUTPUT, hw_device=HW_DEVICE_PROFET,
                                          hw_index=1, source_id=CH_LOGIC_EQ, name="LED",
                                          config_size=len(output_config))
    channels.append(output_header + output_config)

    config = struct.pack('<H', len(channels))
    for ch in channels:
        config += ch
    return config


class LogicEqTest:
    def __init__(self, port_name: str = "COM11"):
        self.port_name = port_name
        self.port: Optional[serial.Serial] = None

    def connect(self) -> bool:
        try:
            self.port = serial.Serial(port=self.port_name, baudrate=115200, timeout=1.0)
            time.sleep(0.5)
            self.port.reset_input_buffer()
            return True
        except serial.SerialException as e:
            print(f"ERROR: Cannot open {self.port_name}: {e}")
            return False

    def disconnect(self):
        if self.port and self.port.is_open:
            self.port.close()

    def send_command(self, cmd: int, payload: bytes = b''):
        self.port.reset_input_buffer()
        self.port.write(build_frame(cmd, payload))
        self.port.flush()
        return read_frame(self.port, timeout=3.0)

    def test_ping(self) -> bool:
        print("\n[1] Testing device connection...")
        self.port.write(build_frame(CMD.STOP_STREAM))
        self.port.flush()
        time.sleep(0.3)
        self.port.reset_input_buffer()
        cmd, _ = self.send_command(CMD.PING)
        if cmd == CMD.PONG:
            print("    [OK] Device responding")
            return True
        print(f"    [FAIL] Expected PONG, got: {hex(cmd) if cmd else 'None'}")
        return False

    def upload_config(self, config: bytes) -> bool:
        print("\n[2] Uploading Logic EQ config (threshold=1)...")
        payload = struct.pack('<HH', 0, 1) + config
        cmd, resp = self.send_command(CMD.LOAD_BINARY_CONFIG, payload)
        if cmd == CMD.BINARY_CONFIG_ACK and resp and resp[0]:
            channels = struct.unpack('<H', resp[2:4])[0] if len(resp) >= 4 else 0
            print(f"    [OK] Channels loaded: {channels}")
            return channels >= 2
        print("    [FAIL] Upload failed")
        return False

    def start_telemetry(self, rate_hz: int = 50):
        payload = struct.pack('<BBBBBBH', 1, 1, 0, 0, 0, 0, rate_hz)
        self.port.reset_input_buffer()
        self.port.write(build_frame(CMD.START_STREAM, payload))
        self.port.flush()

    def stop_telemetry(self):
        self.port.write(build_frame(CMD.STOP_STREAM))
        self.port.flush()
        time.sleep(0.2)
        self.port.reset_input_buffer()

    def read_telemetry(self, timeout: float = 0.5):
        cmd, payload = read_frame(self.port, timeout)
        if cmd == CMD.DATA and payload and len(payload) >= 78:
            outputs = list(payload[8:38])
            din_byte = payload[78]
            digital_inputs = [(din_byte >> i) & 1 for i in range(8)]
            return outputs, digital_inputs
        return None, None

    def monitor(self, duration: float = 12.0):
        print("\n[3] Monitoring Logic EQ chain...")
        print("    Logic: DIN0 == 1")
        print("    - Button RELEASED (0) -> 0 == 1 = FALSE -> LED OFF")
        print("    - Button PRESSED  (1) -> 1 == 1 = TRUE  -> LED ON")
        print()

        self.start_telemetry(rate_hz=50)
        packets = 0
        matches = 0
        last_btn = None
        start = time.time()

        try:
            while time.time() - start < duration:
                outputs, dins = self.read_telemetry(timeout=0.1)
                if outputs is not None and dins is not None:
                    packets += 1
                    btn0 = dins[0]
                    output_on = (outputs[1] > 0)
                    # EQ: input == 1
                    expected_output = (btn0 == 1)
                    if output_on == expected_output:
                        matches += 1
                    if last_btn is not None and btn0 != last_btn:
                        state = "PRESSED" if btn0 else "released"
                        out_state = "ON" if output_on else "OFF"
                        print(f"    DIN0={state} ({btn0}), LED {out_state}")
                    last_btn = btn0
                    if packets % 100 == 0:
                        print(f"    [{time.time()-start:.1f}s] Packets: {packets}, Match: {100*matches/packets:.1f}%")
        except KeyboardInterrupt:
            print("\n    Interrupted")
        finally:
            self.stop_telemetry()

        match_rate = (100 * matches / packets) if packets > 0 else 0
        print(f"\n    Match rate: {match_rate:.1f}%")
        if match_rate >= 95:
            print("    [OK] Logic EQ working!")
            return True
        print("    [FAIL] Logic EQ not working")
        return False

    def run(self) -> int:
        print("=" * 60)
        print("PMU-30 Logic EQ (==) Test")
        print("=" * 60)
        print(f"Port: {self.port_name}")
        print("\nExpected: LED ON when button pressed (1 == 1)")

        if not self.connect():
            return 1
        try:
            if not self.test_ping():
                return 1
            if not self.upload_config(build_test_config()):
                return 1
            if not self.monitor():
                return 1
            print("\n" + "=" * 60)
            print("ALL TESTS PASSED!")
            print("=" * 60)
            return 0
        finally:
            self.disconnect()


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM11"
    return LogicEqTest(port).run()


if __name__ == "__main__":
    sys.exit(main())
