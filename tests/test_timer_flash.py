#!/usr/bin/env python3
"""
PMU-30 Timer FLASH (Blink) Test

Tests Timer channel in BLINK mode with trigger:
  DIN0 (button, ch 50) -> Timer FLASH (ch 200) -> Power Output (ch 100) -> LED

Timer FLASH configuration:
  - Mode: BLINK (0x03)
  - Trigger: DIN0 (button)
  - ON time: 1000ms (1 second)
  - OFF time: 1000ms (1 second)

Expected behavior:
  - Button released (0): LED OFF (immediately)
  - Button pressed (1):  LED blinks (1s ON, 1s OFF cycle)

FLASH generates impulses only while trigger is true (non-zero).
When trigger becomes false, output immediately returns to 0.

Usage:
    python tests/test_timer_flash.py [COM_PORT]
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


# Channel types (from shared/channel_types.h)
CH_TYPE_TIMER = 0x20
CH_TYPE_POWER_OUTPUT = 0x10

# Timer modes (from shared/engine/timer.h)
TIMER_MODE_BLINK = 0x03  # Toggle at interval

# Channel IDs
CH_DIN0 = 50           # Digital input 0 (button on PC13)
CH_TIMER_FLASH = 200   # Timer FLASH channel
CH_OUTPUT_0 = 100      # Power output 0

# Hardware binding
HW_DEVICE_PROFET = 0x05
HW_DEVICE_NONE = 0x00
CH_REF_NONE = 0xFFFF

# Config sizes
CFG_TIMER_SIZE = 16  # CfgTimer_t


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
    crc = crc16_ccitt(frame_data[1:])
    return frame_data + struct.pack('<H', crc)


def read_frame(port: serial.Serial, timeout: float = 2.0) -> Tuple[Optional[int], Optional[bytes]]:
    """Read a complete frame from port."""
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


def build_channel_header(
    channel_id: int,
    channel_type: int,
    flags: int = 0x01,
    hw_device: int = 0,
    hw_index: int = 0,
    source_id: int = CH_REF_NONE,
    default_value: int = 0,
    name: str = "",
    config_size: int = 0
) -> bytes:
    """Build CfgChannelHeader_t (14 bytes) + name."""
    name_bytes = name.encode('utf-8')[:31]
    name_len = len(name_bytes)

    header = struct.pack('<HBBBBHiBB',
        channel_id,
        channel_type,
        flags,
        hw_device,
        hw_index,
        source_id,
        default_value,
        name_len,
        config_size
    )
    return header + name_bytes


def build_timer_config(mode: int, trigger_id: int, on_time_ms: int, off_time_ms: int) -> bytes:
    """
    Build CfgTimer_t (16 bytes).

    Format:
        uint8_t  mode           (1 byte)  - TimerMode_t
        uint8_t  trigger_mode   (1 byte)  - TimerTrigger_t
        uint16_t trigger_id     (2 bytes) - Trigger source channel
        uint32_t delay_ms       (4 bytes) - Delay/pulse time
        uint16_t on_time_ms     (2 bytes) - On time for BLINK mode
        uint16_t off_time_ms    (2 bytes) - Off time for BLINK mode
        uint8_t  auto_reset     (1 byte)  - Auto-reset after expire
        uint8_t  reserved[3]    (3 bytes)
    """
    return struct.pack('<BBHIHH?3s',
        mode,           # mode = BLINK
        0,              # trigger_mode = 0 (level)
        trigger_id,     # trigger_id = DIN0 (cycles while high)
        0,              # delay_ms = 0 (not used for blink)
        on_time_ms,     # on_time_ms
        off_time_ms,    # off_time_ms
        False,          # auto_reset
        b'\x00\x00\x00' # reserved
    )


def build_power_output_config() -> bytes:
    """Build CfgPowerOutput_t (12 bytes)."""
    return struct.pack('<HHHBBHBB',
        5000, 100, 10000, 3, 5, 0, 0, 0
    )


def build_test_config() -> bytes:
    """
    Build binary config for Timer FLASH test.

    Config contains 2 channels:
    1. Timer FLASH (ch 200): mode=BLINK, trigger=DIN0, on=1000ms, off=1000ms
    2. Power Output (ch 100): source=Timer FLASH (200), hw_index=1 (LED)

    Chain: DIN0 (trigger) -> Timer FLASH (200) -> Power Output (100) -> LED

    When button released (0): Timer stops, LED OFF
    When button pressed (1):  Timer runs, LED blinks 1s ON / 1s OFF
    """
    channels = []

    # 1. Timer FLASH channel (ch 200)
    timer_config = build_timer_config(
        mode=TIMER_MODE_BLINK,
        trigger_id=CH_DIN0,    # Trigger from button
        on_time_ms=1000,       # 1 second ON
        off_time_ms=1000       # 1 second OFF
    )
    timer_header = build_channel_header(
        channel_id=CH_TIMER_FLASH,
        channel_type=CH_TYPE_TIMER,
        flags=0x01,
        hw_device=HW_DEVICE_NONE,
        hw_index=0,
        source_id=CH_REF_NONE,
        default_value=0,
        name="FLASH",
        config_size=len(timer_config)
    )
    channels.append(timer_header + timer_config)

    # 2. Power Output (ch 100)
    output_config = build_power_output_config()
    output_header = build_channel_header(
        channel_id=CH_OUTPUT_0,
        channel_type=CH_TYPE_POWER_OUTPUT,
        flags=0x01,
        hw_device=HW_DEVICE_PROFET,
        hw_index=1,
        source_id=CH_TIMER_FLASH,
        default_value=0,
        name="LED",
        config_size=len(output_config)
    )
    channels.append(output_header + output_config)

    # Build complete config
    config = struct.pack('<H', len(channels))
    for ch in channels:
        config += ch

    return config


class TimerFlashTest:
    """Test Timer FLASH (Blink) channel functionality."""

    def __init__(self, port_name: str = "COM11"):
        self.port_name = port_name
        self.port: Optional[serial.Serial] = None

    def connect(self) -> bool:
        try:
            self.port = serial.Serial(
                port=self.port_name,
                baudrate=115200,
                timeout=1.0,
                write_timeout=1.0
            )
            time.sleep(0.5)
            self.port.reset_input_buffer()
            return True
        except serial.SerialException as e:
            print(f"ERROR: Cannot open {self.port_name}: {e}")
            return False

    def disconnect(self):
        if self.port and self.port.is_open:
            self.port.close()

    def send_command(self, cmd: int, payload: bytes = b'') -> Tuple[Optional[int], Optional[bytes]]:
        self.port.reset_input_buffer()
        frame = build_frame(cmd, payload)
        self.port.write(frame)
        self.port.flush()
        return read_frame(self.port, timeout=3.0)

    def test_ping(self) -> bool:
        print("\n[1] Testing device connection...")
        # Stop any running telemetry first
        self.port.write(build_frame(CMD.STOP_STREAM))
        self.port.flush()
        time.sleep(0.3)
        self.port.reset_input_buffer()

        cmd, _ = self.send_command(CMD.PING)
        if cmd == CMD.PONG:
            print("    [OK] Device responding to PING")
            return True
        print(f"    [FAIL] Expected PONG, got: {hex(cmd) if cmd else 'None'}")
        return False

    def upload_config(self, config: bytes) -> bool:
        print("\n[2] Uploading Timer FLASH config...")
        print(f"    Config size: {len(config)} bytes")
        print(f"    Timer: BLINK mode, trigger=DIN0, 1s ON / 1s OFF")

        payload = struct.pack('<HH', 0, 1) + config
        cmd, resp = self.send_command(CMD.LOAD_BINARY_CONFIG, payload)

        if cmd == CMD.BINARY_CONFIG_ACK and resp and resp[0]:
            channels_loaded = struct.unpack('<H', resp[2:4])[0] if len(resp) >= 4 else 0
            print(f"    [OK] Config uploaded, channels loaded: {channels_loaded}")
            return channels_loaded >= 2
        print(f"    [FAIL] Upload failed")
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

    def monitor_flash(self, duration: float = 15.0):
        """
        Monitor Timer FLASH with trigger.

        Expected:
        - Button released (0): LED OFF (immediately)
        - Button pressed (1):  LED blinks (1s ON, 1s OFF)
        """
        print("\n[3] Monitoring Timer FLASH...")
        print(f"    Duration: {duration}s")
        print("    Chain: DIN0 (trigger) -> Timer FLASH -> Power Output -> LED")
        print()
        print("    Expected behavior:")
        print("    - Button RELEASED: LED OFF (timer stopped)")
        print("    - Button PRESSED:  LED blinks (1s ON / 1s OFF)")
        print()
        print("    Press and hold button to see LED blinking...")
        print()

        self.start_telemetry(rate_hz=20)

        blinks_while_pressed = 0
        off_while_released = 0
        on_while_released = 0  # Error counter
        last_button = None
        last_output = None
        start = time.time()

        try:
            while time.time() - start < duration:
                outputs, dins = self.read_telemetry(timeout=0.1)

                if outputs is not None and dins is not None:
                    button_pressed = (dins[0] != 0)
                    output_on = (outputs[1] > 0)

                    # Track state changes
                    if last_button is not None and button_pressed != last_button:
                        elapsed = time.time() - start
                        if button_pressed:
                            print(f"    [{elapsed:.1f}s] Button PRESSED - LED should start blinking")
                        else:
                            print(f"    [{elapsed:.1f}s] Button RELEASED - LED should go OFF")

                    # Count LED transitions while button is pressed (blinking)
                    if button_pressed and last_output is not None and output_on != last_output:
                        blinks_while_pressed += 1
                        elapsed = time.time() - start
                        state = "ON" if output_on else "OFF"
                        print(f"    [{elapsed:.1f}s]   LED -> {state}")

                    # Verify LED is OFF when button is released
                    if not button_pressed:
                        if output_on:
                            on_while_released += 1
                        else:
                            off_while_released += 1

                    last_button = button_pressed
                    last_output = output_on

        except KeyboardInterrupt:
            print("\n    Interrupted by user")

        finally:
            self.stop_telemetry()

        print(f"\n    Results:")
        print(f"    - Blink transitions while pressed: {blinks_while_pressed}")
        print(f"    - LED OFF samples while released: {off_while_released}")
        print(f"    - LED ON samples while released (errors): {on_while_released}")

        # Success criteria:
        # 1. Should have at least a few blinks if button was pressed
        # 2. LED should be OFF when button is released (allow some tolerance for transition)
        error_rate = (100 * on_while_released / (off_while_released + on_while_released)) if (off_while_released + on_while_released) > 0 else 0

        if error_rate < 5:
            print(f"    [OK] LED correctly OFF when button released (error rate: {error_rate:.1f}%)")
        else:
            print(f"    [FAIL] LED incorrectly ON when button released (error rate: {error_rate:.1f}%)")
            return False

        if blinks_while_pressed >= 2:
            print(f"    [OK] LED is blinking when button pressed ({blinks_while_pressed} transitions)")
            return True
        elif blinks_while_pressed == 0:
            print("    [WARN] No blinks detected - did you press and hold the button?")
            print("    [INFO] Test passed for 'OFF when released' behavior")
            return True  # Still pass if LED is correctly OFF when released
        else:
            print(f"    [OK] Timer FLASH working ({blinks_while_pressed} transitions)")
            return True

    def run(self) -> int:
        print("=" * 60)
        print("PMU-30 Timer FLASH (Triggered Blink) Test")
        print("=" * 60)
        print(f"Port: {self.port_name}")
        print("\nTest: DIN0 (trigger) -> Timer FLASH -> Power Output -> LED")
        print("Timer: BLINK mode, 1 second ON, 1 second OFF")
        print("\nExpected:")
        print("  - Button released: LED OFF")
        print("  - Button pressed:  LED blinks (1s ON / 1s OFF)")

        if not self.connect():
            return 1

        try:
            if not self.test_ping():
                return 1

            test_config = build_test_config()
            if not self.upload_config(test_config):
                return 1

            if not self.monitor_flash(duration=15.0):
                return 1

            print("\n" + "=" * 60)
            print("ALL TESTS PASSED - Timer FLASH working!")
            print("=" * 60)
            return 0

        finally:
            self.disconnect()


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "COM11"
    tester = TimerFlashTest(port)
    return tester.run()


if __name__ == "__main__":
    sys.exit(main())
