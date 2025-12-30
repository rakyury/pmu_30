"""
Default Configuration Generator for PMU-30
Creates default configurations with all hardware channels.
"""

from typing import Dict, Any
from datetime import datetime


def create_default_config(include_hardware: bool = True) -> Dict[str, Any]:
    """Create a default configuration with all PMU-30 hardware channels.

    Args:
        include_hardware: If True, creates all 30 outputs, 20 analog inputs,
                         20 digital inputs, and 4 H-bridges. If False, creates
                         minimal config with just example tables.

    Returns:
        Complete PMU-30 configuration dictionary.
    """
    channels = []
    channel_id = 200  # User channels start at 200

    if include_hardware:
        # Create 30 Power Outputs (O1-O30)
        # o_1...o_20 linked to digital inputs d_1...d_20
        # o_21...o_30 linked to analog inputs a_1...a_10
        for i in range(30):
            if i < 20:
                # First 20 outputs -> digital inputs
                source = f"d_{i + 1}"
            else:
                # Last 10 outputs -> analog inputs
                source = f"a_{i - 19}"  # o_21->a_1, o_22->a_2, etc.
            channels.append({
                "channel_type": "power_output",
                "channel_id": channel_id,
                "channel_name": f"o_{i + 1}",
                "output_pins": [i],
                "source_channel": source,
                "output_mode": "on_off",
                "max_current": 10000,
                "inrush_time_ms": 100,
                "retry_count": 3,
                "retry_delay_ms": 1000,
                "pwm_frequency_hz": 1000,
                "soft_start_ms": 0,
                "enabled": True
            })
            channel_id += 1

        # Create 20 Analog Inputs (A1-A20)
        for i in range(20):
            channels.append({
                "channel_type": "analog_input",
                "channel_id": channel_id,
                "channel_name": f"a_{i + 1}",
                "input_pin": i,
                "subtype": "linear",
                "pullup_option": "none",
                "min_voltage": 0.0,
                "max_voltage": 5.0,
                "min_value": 0.0,
                "max_value": 100.0,
                "decimal_places": 1,
                "enabled": False
            })
            channel_id += 1

        # Create 20 Digital Inputs (D1-D20)
        # All enabled by default for 1:1 mapping with outputs
        for i in range(20):
            channels.append({
                "channel_type": "digital_input",
                "channel_id": channel_id,
                "channel_name": f"d_{i + 1}",
                "input_pin": i,
                "subtype": "switch_active_low",
                "threshold_voltage": 2.5,
                "debounce_ms": 50,
                "enable_pullup": True,
                "enabled": True
            })
            channel_id += 1

        # Create 4 H-Bridge Motors (HB1-HB4)
        for i in range(4):
            channels.append({
                "channel_type": "hbridge",
                "channel_id": channel_id,
                "channel_name": f"hb_{i + 1}",
                "motor_index": i,
                "source_channel": "",
                "control_mode": "direction_pwm",
                "pwm_frequency_hz": 1000,
                "acceleration_ms": 100,
                "deceleration_ms": 100,
                "current_limit_a": 10.0,
                "enabled": False
            })
            channel_id += 1

        # Create example Logic channels with diverse operations
        # Base defaults for all logic channels
        logic_defaults = {
            "channel_type": "logic",
            "channel": "",
            "channel_2": "",
            "true_delay_s": 0.0,
            "false_delay_s": 0.0,
            "constant": 0.0,
            "threshold": 0.0,
            "time_on_s": 0.5,
            "time_off_s": 0.5,
            "polarity": "normal",
            "upper_value": 100.0,
            "lower_value": 0.0,
            "set_channel": "",
            "reset_channel": "",
            "toggle_channel": "",
            "default_state": "off",
            "edge": "rising",
            "pulse_count": 1,
            "retrigger": False,
            "enabled": True
        }

        # Logic channel examples with various operation types
        logic_examples = [
            # 1. AND: Both digital inputs must be active
            {"channel_name": "logic_1", "operation": "and",
             "channel": 250, "channel_2": 251},  # d_1 AND d_2

            # 2. OR: Either digital input activates
            {"channel_name": "logic_2", "operation": "or",
             "channel": 252, "channel_2": 253},  # d_3 OR d_4

            # 3. NOT: Invert digital input
            {"channel_name": "logic_3", "operation": "not",
             "channel": 254},  # NOT d_5

            # 4. GREATER: Analog threshold comparison
            {"channel_name": "logic_4", "operation": "greater",
             "channel": 230, "constant": 2.50},  # a_1 > 2.5V

            # 5. HYSTERESIS: Analog with upper/lower thresholds
            {"channel_name": "logic_5", "operation": "hysteresis",
             "channel": 231, "upper_value": 3.50, "lower_value": 1.50},  # a_2

            # 6. TOGGLE: Toggle output on rising edge
            {"channel_name": "logic_6", "operation": "toggle",
             "toggle_channel": 255, "edge": "rising"},  # toggle by d_6

            # 7. PULSE: Generate 0.5s pulse on edge
            {"channel_name": "logic_7", "operation": "pulse",
             "channel": 256, "time_on_s": 0.50, "pulse_count": 1},  # pulse on d_7

            # 8. FLASH: Blink 0.5s on/off when active
            {"channel_name": "logic_8", "operation": "flash",
             "channel": 257, "time_on_s": 0.50, "time_off_s": 0.50},  # flash when d_8

            # 9. SET_RESET_LATCH: SR flip-flop
            {"channel_name": "logic_9", "operation": "set_reset_latch",
             "set_channel": 258, "reset_channel": 259},  # set=d_9, reset=d_10

            # 10. XOR: Exclusive OR
            {"channel_name": "logic_10", "operation": "xor",
             "channel": 260, "channel_2": 261},  # d_11 XOR d_12
        ]

        for i, example in enumerate(logic_examples):
            logic_channel = logic_defaults.copy()
            logic_channel["channel_id"] = channel_id
            logic_channel.update(example)
            channels.append(logic_channel)
            channel_id += 1

        # Create example Timer channels
        for i in range(10):
            channels.append({
                "channel_type": "timer",
                "channel_id": channel_id,
                "channel_name": f"timer_{i + 1}",
                "trigger_channel": "",
                "mode": "oneshot",
                "duration_ms": 1000,
                "enabled": False
            })
            channel_id += 1

        # Create example Filter channels
        for i in range(10):
            channels.append({
                "channel_type": "filter",
                "channel_id": channel_id,
                "channel_name": f"filter_{i + 1}",
                "source_channel": "",
                "filter_type": "lowpass",
                "cutoff_hz": 10.0,
                "enabled": False
            })
            channel_id += 1

        # Create example Switch channels
        for i in range(10):
            channels.append({
                "channel_type": "switch",
                "channel_id": channel_id,
                "channel_name": f"switch_{i + 1}",
                "trigger_channel": "",
                "mode": "toggle",
                "initial_state": False,
                "enabled": False
            })
            channel_id += 1

        # Create example Number channels
        for i in range(10):
            channels.append({
                "channel_type": "number",
                "channel_id": channel_id,
                "channel_name": f"num_{i + 1}",
                "operation": "constant",
                "value": 0.0,
                "enabled": False
            })
            channel_id += 1

        # Create example PID channels
        for i in range(4):
            channels.append({
                "channel_type": "pid",
                "channel_id": channel_id,
                "channel_name": f"pid_{i + 1}",
                "input_channel": "",
                "setpoint_channel": "",
                "output_channel": "",
                "kp": 1.0,
                "ki": 0.0,
                "kd": 0.0,
                "min_output": 0.0,
                "max_output": 100.0,
                "enabled": False
            })
            channel_id += 1

    # Add example tables
    channels.extend([
        {
            "channel_type": "table_2d",
            "channel_id": channel_id,
            "channel_name": "t2d_example",
            "x_axis_channel": "",
            "x_min": 0.0,
            "x_max": 100.0,
            "x_step": 10.0,
            "x_values": [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
            "output_values": [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
            "decimal_places": 0,
            "enabled": False
        },
        {
            "channel_type": "table_3d",
            "channel_id": channel_id + 1,
            "channel_name": "t3d_example",
            "x_axis_channel": "",
            "y_axis_channel": "",
            "x_min": 0.0,
            "x_max": 100.0,
            "x_step": 25.0,
            "x_values": [0, 25, 50, 75, 100],
            "y_min": 0.0,
            "y_max": 100.0,
            "y_step": 25.0,
            "y_values": [0, 25, 50, 75, 100],
            "data": [
                [0, 25, 50, 75, 100],
                [25, 50, 75, 100, 125],
                [50, 75, 100, 125, 150],
                [75, 100, 125, 150, 175],
                [100, 125, 150, 175, 200]
            ],
            "decimal_places": 0,
            "enabled": False
        }
    ])

    return {
        "version": "3.0",
        "device": {
            "name": "PMU-30",
            "serial_number": "",
            "firmware_version": "",
            "hardware_revision": "",
            "created": datetime.now().isoformat(),
            "modified": datetime.now().isoformat()
        },
        "can_messages": [],
        "channels": channels,
        "system": {
            "control_frequency_hz": 1000,
            "logic_frequency_hz": 500,
            "can1_baudrate": 500000,
            "can2_baudrate": 500000
        }
    }
