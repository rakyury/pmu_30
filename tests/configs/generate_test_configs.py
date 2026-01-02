#!/usr/bin/env python3
"""
Generate binary test configuration files (.emu)

These configs can be loaded in the PMU-30 Configurator and uploaded to the device.
Each config corresponds to a specific test scenario.
"""

import sys
import struct
from pathlib import Path

# Protocol constants
FRAME_START = 0xAA

# Channel types (from shared/channel_types.h)
CH_TYPE_POWER_OUTPUT = 0x10
CH_TYPE_TIMER = 0x20
CH_TYPE_LOGIC = 0x21

# Logic operations (from shared/engine/logic.h)
LOGIC_OP_AND = 0x00
LOGIC_OP_OR = 0x01
LOGIC_OP_GT = 0x03
LOGIC_OP_LT = 0x04
LOGIC_OP_IS_TRUE = 0x06
LOGIC_OP_IS_FALSE = 0x07

# Timer modes
TIMER_MODE_PULSE = 0x02
TIMER_MODE_BLINK = 0x03

# Trigger modes
TRIGGER_RISING = 0x00

# Hardware
HW_DEVICE_PROFET = 0x05
HW_DEVICE_NONE = 0x00
CH_REF_NONE = 0xFFFF

# Config sizes
CFG_MAX_INPUTS = 8


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


def build_logic_config(operation: int, inputs: list, compare_value: int = 0, invert: bool = False) -> bytes:
    """Build CfgLogic_t (26 bytes)."""
    input_count = len(inputs)
    inputs_padded = inputs + [0] * (CFG_MAX_INPUTS - len(inputs))

    return struct.pack('<BB8Hi?3s',
        operation,
        input_count,
        *inputs_padded,
        compare_value,
        invert,
        b'\x00\x00\x00'
    )


def build_timer_config(
    mode: int = TIMER_MODE_PULSE,
    trigger_mode: int = TRIGGER_RISING,
    trigger_id: int = 50,
    delay_ms: int = 5000,
    on_time_ms: int = 0,
    off_time_ms: int = 0
) -> bytes:
    """Build CfgTimer_t (16 bytes)."""
    return struct.pack('<BBHIHH?3s',
        mode,
        trigger_mode,
        trigger_id,
        delay_ms,
        on_time_ms,
        off_time_ms,
        True,  # auto_reset
        b'\x00\x00\x00'
    )


def build_power_output_config() -> bytes:
    """Build CfgPowerOutput_t (12 bytes)."""
    return struct.pack('<HHHBBHBB',
        5000, 100, 10000, 3, 5, 0, 0, 0
    )


def build_config(channels: list) -> bytes:
    """Build complete binary config."""
    config = struct.pack('<H', len(channels))
    for ch in channels:
        config += ch
    return config


def generate_logic_is_true_config() -> bytes:
    """
    Logic IS_TRUE: DIN0 -> Logic IS_TRUE -> Power Output -> LED
    Button pressed -> LED ON
    """
    channels = []

    # Logic IS_TRUE (ch 200)
    logic_config = build_logic_config(operation=LOGIC_OP_IS_TRUE, inputs=[50])
    logic_header = build_channel_header(
        channel_id=200,
        channel_type=CH_TYPE_LOGIC,
        name="IS_TRUE",
        config_size=len(logic_config)
    )
    channels.append(logic_header + logic_config)

    # Power Output (ch 100)
    output_config = build_power_output_config()
    output_header = build_channel_header(
        channel_id=100,
        channel_type=CH_TYPE_POWER_OUTPUT,
        hw_device=HW_DEVICE_PROFET,
        hw_index=1,
        source_id=200,
        name="LED",
        config_size=len(output_config)
    )
    channels.append(output_header + output_config)

    return build_config(channels)


def generate_logic_is_false_config() -> bytes:
    """
    Logic IS_FALSE: DIN0 -> Logic IS_FALSE -> Power Output -> LED
    Button released -> LED ON
    """
    channels = []

    # Logic IS_FALSE (ch 200)
    logic_config = build_logic_config(operation=LOGIC_OP_IS_FALSE, inputs=[50])
    logic_header = build_channel_header(
        channel_id=200,
        channel_type=CH_TYPE_LOGIC,
        name="IS_FALSE",
        config_size=len(logic_config)
    )
    channels.append(logic_header + logic_config)

    # Power Output (ch 100)
    output_config = build_power_output_config()
    output_header = build_channel_header(
        channel_id=100,
        channel_type=CH_TYPE_POWER_OUTPUT,
        hw_device=HW_DEVICE_PROFET,
        hw_index=1,
        source_id=200,
        name="LED",
        config_size=len(output_config)
    )
    channels.append(output_header + output_config)

    return build_config(channels)


def generate_logic_and_config() -> bytes:
    """
    Logic AND: DIN0 AND DIN1 -> Power Output -> LED
    Both buttons pressed -> LED ON
    """
    channels = []

    # Logic AND (ch 200)
    logic_config = build_logic_config(operation=LOGIC_OP_AND, inputs=[50, 51])
    logic_header = build_channel_header(
        channel_id=200,
        channel_type=CH_TYPE_LOGIC,
        name="AND",
        config_size=len(logic_config)
    )
    channels.append(logic_header + logic_config)

    # Power Output (ch 100)
    output_config = build_power_output_config()
    output_header = build_channel_header(
        channel_id=100,
        channel_type=CH_TYPE_POWER_OUTPUT,
        hw_device=HW_DEVICE_PROFET,
        hw_index=1,
        source_id=200,
        name="LED",
        config_size=len(output_config)
    )
    channels.append(output_header + output_config)

    return build_config(channels)


def generate_logic_or_config() -> bytes:
    """
    Logic OR: DIN0 OR DIN1 -> Power Output -> LED
    Any button pressed -> LED ON
    """
    channels = []

    # Logic OR (ch 200)
    logic_config = build_logic_config(operation=LOGIC_OP_OR, inputs=[50, 51])
    logic_header = build_channel_header(
        channel_id=200,
        channel_type=CH_TYPE_LOGIC,
        name="OR",
        config_size=len(logic_config)
    )
    channels.append(logic_header + logic_config)

    # Power Output (ch 100)
    output_config = build_power_output_config()
    output_header = build_channel_header(
        channel_id=100,
        channel_type=CH_TYPE_POWER_OUTPUT,
        hw_device=HW_DEVICE_PROFET,
        hw_index=1,
        source_id=200,
        name="LED",
        config_size=len(output_config)
    )
    channels.append(output_header + output_config)

    return build_config(channels)


def generate_logic_gt_config() -> bytes:
    """
    Logic GT: DIN0 > 0 -> Power Output -> LED
    Button pressed (value > 0) -> LED ON
    """
    channels = []

    # Logic GT (ch 200)
    logic_config = build_logic_config(operation=LOGIC_OP_GT, inputs=[50], compare_value=0)
    logic_header = build_channel_header(
        channel_id=200,
        channel_type=CH_TYPE_LOGIC,
        name="GT",
        config_size=len(logic_config)
    )
    channels.append(logic_header + logic_config)

    # Power Output (ch 100)
    output_config = build_power_output_config()
    output_header = build_channel_header(
        channel_id=100,
        channel_type=CH_TYPE_POWER_OUTPUT,
        hw_device=HW_DEVICE_PROFET,
        hw_index=1,
        source_id=200,
        name="LED",
        config_size=len(output_config)
    )
    channels.append(output_header + output_config)

    return build_config(channels)


def generate_logic_lt_config() -> bytes:
    """
    Logic LT: DIN0 < 1 -> Power Output -> LED
    Button released (value < 1) -> LED ON
    """
    channels = []

    # Logic LT (ch 200)
    logic_config = build_logic_config(operation=LOGIC_OP_LT, inputs=[50], compare_value=1)
    logic_header = build_channel_header(
        channel_id=200,
        channel_type=CH_TYPE_LOGIC,
        name="LT",
        config_size=len(logic_config)
    )
    channels.append(logic_header + logic_config)

    # Power Output (ch 100)
    output_config = build_power_output_config()
    output_header = build_channel_header(
        channel_id=100,
        channel_type=CH_TYPE_POWER_OUTPUT,
        hw_device=HW_DEVICE_PROFET,
        hw_index=1,
        source_id=200,
        name="LED",
        config_size=len(output_config)
    )
    channels.append(output_header + output_config)

    return build_config(channels)


def generate_timer_pulse_config() -> bytes:
    """
    Timer PULSE: DIN0 triggers timer -> LED ON for 10 seconds
    Button press -> LED ON for 10s -> LED OFF
    """
    channels = []

    # Timer (ch 200)
    timer_config = build_timer_config(
        mode=TIMER_MODE_PULSE,
        trigger_mode=TRIGGER_RISING,
        trigger_id=50,
        delay_ms=10000
    )
    timer_header = build_channel_header(
        channel_id=200,
        channel_type=CH_TYPE_TIMER,
        name="Timer",
        config_size=len(timer_config)
    )
    channels.append(timer_header + timer_config)

    # Power Output (ch 100)
    output_config = build_power_output_config()
    output_header = build_channel_header(
        channel_id=100,
        channel_type=CH_TYPE_POWER_OUTPUT,
        hw_device=HW_DEVICE_PROFET,
        hw_index=1,
        source_id=200,
        name="LED",
        config_size=len(output_config)
    )
    channels.append(output_header + output_config)

    return build_config(channels)


def generate_timer_blink_config() -> bytes:
    """
    Timer BLINK: DIN0 triggers blinking -> LED blinks 500ms ON/500ms OFF
    Button press -> LED blinks until button released
    """
    channels = []

    # Timer (ch 200)
    timer_config = build_timer_config(
        mode=TIMER_MODE_BLINK,
        trigger_mode=TRIGGER_RISING,
        trigger_id=50,
        delay_ms=0,
        on_time_ms=500,
        off_time_ms=500
    )
    timer_header = build_channel_header(
        channel_id=200,
        channel_type=CH_TYPE_TIMER,
        name="Blink",
        config_size=len(timer_config)
    )
    channels.append(timer_header + timer_config)

    # Power Output (ch 100)
    output_config = build_power_output_config()
    output_header = build_channel_header(
        channel_id=100,
        channel_type=CH_TYPE_POWER_OUTPUT,
        hw_device=HW_DEVICE_PROFET,
        hw_index=1,
        source_id=200,
        name="LED",
        config_size=len(output_config)
    )
    channels.append(output_header + output_config)

    return build_config(channels)


def generate_button_output_config() -> bytes:
    """
    Direct link: DIN0 -> Power Output -> LED
    Button pressed -> LED ON (no logic processing)
    """
    channels = []

    # Power Output (ch 100) directly linked to DIN0 (ch 50)
    output_config = build_power_output_config()
    output_header = build_channel_header(
        channel_id=100,
        channel_type=CH_TYPE_POWER_OUTPUT,
        hw_device=HW_DEVICE_PROFET,
        hw_index=1,
        source_id=50,  # Direct link to DIN0
        name="LED",
        config_size=len(output_config)
    )
    channels.append(output_header + output_config)

    return build_config(channels)


def main():
    """Generate all test configuration files."""
    output_dir = Path(__file__).parent

    configs = {
        "logic_is_true.pmu30": generate_logic_is_true_config(),
        "logic_is_false.pmu30": generate_logic_is_false_config(),
        "logic_and.pmu30": generate_logic_and_config(),
        "logic_or.pmu30": generate_logic_or_config(),
        "logic_gt.pmu30": generate_logic_gt_config(),
        "logic_lt.pmu30": generate_logic_lt_config(),
        "timer_pulse.pmu30": generate_timer_pulse_config(),
        "timer_blink.pmu30": generate_timer_blink_config(),
        "button_output.pmu30": generate_button_output_config(),
    }

    for name, data in configs.items():
        filepath = output_dir / name
        with open(filepath, 'wb') as f:
            f.write(data)
        print(f"Generated: {filepath} ({len(data)} bytes)")

    print(f"\nTotal: {len(configs)} configuration files generated")


if __name__ == "__main__":
    main()
