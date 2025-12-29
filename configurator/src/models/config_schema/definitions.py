"""
JSON Schema Definitions for PMU-30 Configuration
Version 3.0 - Two-level CAN Message/Input architecture
"""

# JSON Schema for PMU-30 Configuration v3.0
PMU_CONFIG_SCHEMA = {
    "type": "object",
    "required": ["version", "device", "channels"],
    "properties": {
        "version": {
            "type": "string",
            "pattern": "^\\d+\\.\\d+$"
        },
        "device": {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "serial_number": {"type": "string"},
                "firmware_version": {"type": "string"},
                "hardware_revision": {"type": "string"},
                "created": {"type": "string"},
                "modified": {"type": "string"}
            }
        },
        # CAN Messages (Level 1 - Message Objects)
        "can_messages": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "can_bus", "base_id"],
                "properties": {
                    "id": {"type": "string", "minLength": 1, "pattern": "^[a-zA-Z][a-zA-Z0-9_]*$"},
                    "name": {"type": "string"},
                    "can_bus": {"type": "integer", "minimum": 1, "maximum": 4},
                    "base_id": {"type": "integer", "minimum": 0},
                    "is_extended": {"type": "boolean"},
                    "message_type": {
                        "type": "string",
                        "enum": ["normal", "compound", "pmu1_rx", "pmu2_rx", "pmu3_rx"]
                    },
                    "frame_count": {"type": "integer", "minimum": 1, "maximum": 8},
                    "dlc": {"type": "integer", "minimum": 0, "maximum": 64},
                    "timeout_ms": {"type": "integer", "minimum": 0, "maximum": 65535},
                    "description": {"type": "string"}
                }
            }
        },
        "channels": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "channel_type"],
                "properties": {
                    "id": {"type": "string", "minLength": 1, "pattern": "^[a-zA-Z][a-zA-Z0-9_]*$"},
                    "channel_type": {
                        "type": "string",
                        "enum": [
                            "digital_input", "analog_input", "power_output",
                            "can_rx", "can_tx", "logic", "number",
                            "table_2d", "table_3d", "switch", "timer",
                            "filter", "enum", "pid", "hbridge",
                            "lua_script", "handler", "blinkmarine_keypad"
                        ]
                    },
                    "description": {"type": "string"}
                }
            }
        },
        "system": {
            "type": "object",
            "properties": {
                "control_frequency_hz": {"type": "integer", "minimum": 100, "maximum": 10000},
                "logic_frequency_hz": {"type": "integer", "minimum": 100, "maximum": 10000},
                "can1_baudrate": {"type": "integer"},
                "can2_baudrate": {"type": "integer"}
            }
        },
        # Standard CAN Stream configuration
        "standard_can_stream": {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean"},
                "can_bus": {"type": "integer", "enum": [1, 2]},
                "base_id": {"type": "integer", "minimum": 0, "maximum": 2047},
                "is_extended": {"type": "boolean"},
                "include_extended_frames": {"type": "boolean"}
            }
        }
    }
}

# Channel Type specific schemas
CHANNEL_TYPE_SCHEMAS = {
    "digital_input": {
        "subtype": {
            "type": "string",
            "enum": ["switch_active_low", "switch_active_high", "frequency", "rpm", "flex_fuel", "beacon", "puls_oil_sensor", "keypad_button"]
        },
        "input_pin": {"type": "integer", "minimum": 0, "maximum": 19},
        "enable_pullup": {"type": "boolean"},
        "threshold_voltage": {"type": "number", "minimum": 0, "maximum": 30},
        "debounce_ms": {"type": "integer", "minimum": 0, "maximum": 10000},
        "trigger_edge": {"type": "string", "enum": ["rising", "falling", "both"]},
        "multiplier": {"type": "number"},
        "divider": {"type": "number"},
        "timeout_ms": {"type": "integer"},
        "number_of_teeth": {"type": "integer", "minimum": 1}
    },
    "analog_input": {
        "subtype": {"type": "string", "enum": ["switch_active_low", "switch_active_high", "rotary_switch", "linear", "calibrated"]},
        "input_pin": {"type": "integer", "minimum": 0, "maximum": 19},
        "pullup_option": {"type": "string", "enum": ["none", "1m_down", "10k_up", "10k_down", "100k_up", "100k_down"]},
        "decimal_places": {"type": "integer", "minimum": 0, "maximum": 6},
        "threshold_high": {"type": "number"},
        "threshold_high_time_ms": {"type": "integer"},
        "threshold_low": {"type": "number"},
        "threshold_low_time_ms": {"type": "integer"},
        "positions": {"type": "integer", "minimum": 2, "maximum": 12},
        "debounce_ms": {"type": "integer"},
        "min_voltage": {"type": "number"},
        "max_voltage": {"type": "number"},
        "min_value": {"type": "number"},
        "max_value": {"type": "number"},
        "calibration_points": {"type": "array"}
    },
    "power_output": {
        "output_pins": {"type": "array", "items": {"type": "integer"}, "maxItems": 3},
        "source_channel": {"type": "string"},
        "pwm_enabled": {"type": "boolean"},
        "pwm_frequency_hz": {"type": "integer", "minimum": 1, "maximum": 20000},
        "duty_channel": {"type": "string"},
        "duty_fixed": {"type": "number", "minimum": 0, "maximum": 100},
        "soft_start_ms": {"type": "integer"},
        "current_limit_a": {"type": "number"},
        "inrush_current_a": {"type": "number"},
        "inrush_time_ms": {"type": "integer"},
        "retry_count": {"type": "integer"},
        "retry_forever": {"type": "boolean"}
    },
    "logic": {
        "operation": {
            "type": "string",
            "enum": [
                # Basic logic
                "is_true", "is_false",
                # Comparison
                "equal", "not_equal", "less", "greater", "less_equal", "greater_equal", "in_range",
                # Multi-input logic
                "and", "or", "xor", "not", "nand", "nor",
                # Edge detection
                "edge_rising", "edge_falling",
                # Advanced
                "changed", "hysteresis", "set_reset_latch", "toggle", "pulse", "flash"
            ]
        },
        # Single input operations
        "channel": {"type": "string"},
        # Two-input operations
        "channel_2": {"type": "string"},
        # Delays (seconds)
        "true_delay_s": {"type": "number", "minimum": 0},
        "false_delay_s": {"type": "number", "minimum": 0},
        # Comparison constant
        "constant": {"type": "number"},
        # Changed operation
        "threshold": {"type": "number"},
        "time_on_s": {"type": "number", "minimum": 0},
        # Hysteresis/IN_RANGE
        "polarity": {"type": "string", "enum": ["normal", "inverted"]},
        "upper_value": {"type": "number"},
        "lower_value": {"type": "number"},
        # Set/Reset latch
        "set_channel": {"type": "string"},
        "reset_channel": {"type": "string"},
        "default_state": {"type": "string", "enum": ["off", "on"]},
        # Toggle/Pulse
        "edge": {"type": "string", "enum": ["rising", "falling", "both"]},
        "toggle_channel": {"type": "string"},
        "pulse_count": {"type": "integer", "minimum": 1},
        "retrigger": {"type": "boolean"},
        # Flash
        "time_off_s": {"type": "number", "minimum": 0},
        # Legacy support
        "inputs": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
        "delay_on_ms": {"type": "integer", "minimum": 0, "maximum": 60000},
        "delay_off_ms": {"type": "integer", "minimum": 0, "maximum": 60000},
        "range_min": {"type": "number"},
        "range_max": {"type": "number"}
    },
    "number": {
        "operation": {
            "type": "string",
            "enum": ["constant", "add", "subtract", "multiply", "divide",
                    "min", "max", "average", "abs", "scale", "clamp", "conditional"]
        },
        "inputs": {"type": "array", "items": {"type": "string"}},
        "constant_value": {"type": "number"},
        "unit": {"type": "string"},
        "multiplier": {"type": "number"},
        "offset": {"type": "number"},
        "clamp_min": {"type": "number"},
        "clamp_max": {"type": "number"}
    },
    "timer": {
        "start_channel": {"type": "string"},
        "start_edge": {"type": "string", "enum": ["rising", "falling"]},
        "stop_channel": {"type": "string"},
        "stop_edge": {"type": "string", "enum": ["rising", "falling"]},
        "mode": {"type": "string", "enum": ["count_up", "count_down"]},
        "limit_hours": {"type": "integer", "minimum": 0},
        "limit_minutes": {"type": "integer", "minimum": 0, "maximum": 59},
        "limit_seconds": {"type": "integer", "minimum": 0, "maximum": 59}
    },
    "filter": {
        "filter_type": {"type": "string", "enum": ["moving_avg", "low_pass", "min_window", "max_window", "median"]},
        "input_channel": {"type": "string"},
        "window_size": {"type": "integer", "minimum": 2, "maximum": 100},
        "time_constant": {"type": "number", "minimum": 0.001}
    },
    "enum": {
        "is_bitfield": {"type": "boolean"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "value": {"type": "integer"},
                    "text": {"type": "string"},
                    "color": {"type": "string", "pattern": "^#[0-9A-Fa-f]{6}$"}
                }
            }
        }
    },
    "table_2d": {
        "x_axis_channel": {"type": "string"},
        "x_axis_type": {"type": "string", "enum": ["channel", "enum"]},
        "interpolation": {"type": "string", "enum": ["linear", "step_previous", "step_next"]},
        "clamp_output": {"type": "boolean"},
        "data": {"type": "array"}
    },
    "table_3d": {
        "x_axis_channel": {"type": "string"},
        "x_axis_type": {"type": "string", "enum": ["channel", "enum"]},
        "x_values": {"type": "array", "items": {"type": "number"}},
        "y_axis_channel": {"type": "string"},
        "y_axis_type": {"type": "string", "enum": ["channel", "enum"]},
        "y_values": {"type": "array", "items": {"type": "number"}},
        "interpolation": {"type": "string", "enum": ["linear", "step"]},
        "data": {"type": "array"}
    },
    "switch": {
        "switch_type": {"type": "string", "enum": ["latching", "press_hold"]},
        "input_up_channel": {"type": "string"},
        "input_up_edge": {"type": "string", "enum": ["rising", "falling", "both"]},
        "input_down_channel": {"type": "string"},
        "input_down_edge": {"type": "string", "enum": ["rising", "falling", "both"]},
        "state_first": {"type": "integer"},
        "state_last": {"type": "integer"},
        "state_default": {"type": "integer"}
    },
    "can_rx": {
        # New architecture fields (v3.0)
        "message_ref": {"type": "string"},  # Reference to can_messages[].id
        "frame_offset": {"type": "integer", "minimum": 0, "maximum": 7},
        "data_type": {"type": "string", "enum": ["unsigned", "signed", "float"]},
        "data_format": {"type": "string", "enum": ["8bit", "16bit", "32bit", "custom"]},
        "byte_order": {"type": "string", "enum": ["little_endian", "big_endian"]},
        "byte_offset": {"type": "integer", "minimum": 0, "maximum": 7},
        "start_bit": {"type": "integer", "minimum": 0, "maximum": 63},
        "bit_length": {"type": "integer", "minimum": 1, "maximum": 64},
        "multiplier": {"type": "number"},
        "divider": {"type": "number"},
        "offset": {"type": "number"},
        "decimal_places": {"type": "integer", "minimum": 0, "maximum": 6},
        "default_value": {"type": "number"},
        "timeout_behavior": {"type": "string", "enum": ["use_default", "hold_last", "set_zero"]},
        # Legacy fields (v2.0 backwards compatibility)
        "can_bus": {"type": "integer", "enum": [1, 2, 3, 4]},
        "message_id": {"type": "integer", "minimum": 0},
        "is_extended": {"type": "boolean"},
        "length": {"type": "integer", "minimum": 1, "maximum": 64},
        "value_type": {"type": "string", "enum": ["unsigned", "signed", "float"]},
        "factor": {"type": "number"},
        "timeout_ms": {"type": "integer"}
    },
    "can_tx": {
        "enabled": {"type": "boolean"},
        "can_bus": {"type": "integer", "enum": [1, 2]},
        "message_id": {"type": "integer", "minimum": 0},
        "is_extended": {"type": "boolean"},
        "cycle_time_ms": {"type": "integer", "minimum": 1},
        "signals": {"type": "array"}
    },
    "pid": {
        "setpoint_channel": {"type": "string"},
        "process_channel": {"type": "string"},
        "kp": {"type": "number"},
        "ki": {"type": "number"},
        "kd": {"type": "number"},
        "output_min": {"type": "number"},
        "output_max": {"type": "number"},
        "sample_time_ms": {"type": "integer", "minimum": 1}
    },
    "hbridge": {
        "bridge_number": {"type": "integer", "minimum": 0, "maximum": 3},
        "source_channel": {"type": "string"},
        "duty_channel": {"type": "string"},
        "direction_channel": {"type": "string"},
        "mode": {"type": "string", "enum": ["direct", "pid"]},
        "pwm_frequency_hz": {"type": "integer", "minimum": 1, "maximum": 20000},
        "current_limit_a": {"type": "number"},
        "pid_setpoint_channel": {"type": "string"}
    },
    "lua_script": {
        "script": {"type": "string"},
        "input_channels": {"type": "array", "items": {"type": "string"}},
        "output_channels": {"type": "array", "items": {"type": "string"}}
    },
    "handler": {
        "handler_type": {"type": "string"},
        "trigger_channel": {"type": "string"},
        "actions": {"type": "array"}
    },
    "blinkmarine_keypad": {
        "keypad_type": {"type": "string", "enum": ["2x6", "4x4"]},
        "can_bus": {"type": "integer", "enum": [1, 2, 3, 4]},
        "node_id": {"type": "integer", "minimum": 1, "maximum": 127},
        "buttons": {"type": "object"}
    }
}
