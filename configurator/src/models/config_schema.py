"""
JSON Schema for PMU-30 Configuration Validation
Version 2.0 - Unified Channel Architecture
"""

from typing import Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)

# JSON Schema for PMU-30 Configuration v3.0
# Updated to support two-level CAN Message/Input architecture
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


class ConfigValidator:
    """Configuration validator for PMU-30"""

    @staticmethod
    def validate_type(value: Any, expected_type: str, path: str) -> Tuple[bool, str]:
        """Validate value type"""
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict
        }

        expected_py_type = type_map.get(expected_type)
        if not isinstance(value, expected_py_type):
            return False, f"{path}: expected {expected_type}, got {type(value).__name__}"
        return True, ""

    @staticmethod
    def validate_range(value: int, minimum: int = None, maximum: int = None, path: str = "") -> Tuple[bool, str]:
        """Validate numeric value range"""
        if minimum is not None and value < minimum:
            return False, f"{path}: value {value} is less than minimum {minimum}"
        if maximum is not None and value > maximum:
            return False, f"{path}: value {value} is greater than maximum {maximum}"
        return True, ""

    @staticmethod
    def validate_enum(value: str, allowed_values: List[str], path: str) -> Tuple[bool, str]:
        """Validate enumeration value"""
        if value not in allowed_values:
            return False, f"{path}: '{value}' is not one of {allowed_values}"
        return True, ""

    @staticmethod
    def validate_channel_id(channel_id: str, path: str) -> Tuple[bool, str]:
        """Validate channel ID format"""
        import re
        if not channel_id:
            return False, f"{path}: channel ID cannot be empty"
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', channel_id):
            return False, f"{path}: channel ID must start with a letter and contain only letters, numbers, and underscores"
        return True, ""

    @staticmethod
    def validate_channel_reference(channel_ref, all_channel_ids: set, path: str) -> Tuple[bool, str]:
        """Validate that a channel reference exists.

        Channel references can be:
        - String channel ID (e.g., "Logic_4", "Timer_7")
        - Integer runtime channel ID (used by firmware, validated at runtime)
        - Empty string or None (no reference)
        """
        if not channel_ref:
            return True, ""

        # Integer references are runtime channel IDs - validated by firmware
        if isinstance(channel_ref, int):
            return True, ""

        # String references must exist in the channel list
        if channel_ref not in all_channel_ids:
            return False, f"{path}: references undefined channel '{channel_ref}'"
        return True, ""

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate full configuration

        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_errors)
        """
        errors = []

        # Check required top-level fields
        required_fields = ["version", "device", "channels"]
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: '{field}'")

        if errors:
            return False, errors

        # Validate version
        if not isinstance(config.get("version"), str):
            errors.append("Field 'version' must be a string")
        elif not config["version"]:
            errors.append("Field 'version' cannot be empty")

        # Validate device
        device = config.get("device", {})
        if not isinstance(device, dict):
            errors.append("Field 'device' must be an object")
        else:
            if "name" not in device:
                errors.append("device.name is required")
            elif not device["name"]:
                errors.append("device.name cannot be empty")

        # Validate can_messages (Level 1)
        can_messages = config.get("can_messages", [])
        all_message_ids = set()  # Message IDs for reference validation
        if isinstance(can_messages, list):
            for i, msg in enumerate(can_messages):
                if isinstance(msg, dict):
                    # Use 'id' for reference validation (message_ref uses id, not name)
                    msg_id = msg.get("id", "")
                    if msg_id:
                        if msg_id in all_message_ids:
                            errors.append(f"Duplicate CAN message ID: '{msg_id}'")
                        all_message_ids.add(msg_id)

                    # Validate required fields
                    path = f"can_messages[{i}]"
                    if not msg_id:
                        errors.append(f"{path}.id is required")
                    if "can_bus" not in msg:
                        errors.append(f"{path}.can_bus is required")
                    elif not isinstance(msg["can_bus"], int) or not (1 <= msg["can_bus"] <= 4):
                        errors.append(f"{path}.can_bus must be between 1 and 4")
                    if "base_id" not in msg:
                        errors.append(f"{path}.base_id is required")

        # Validate channels
        channels = config.get("channels", [])
        if not isinstance(channels, list):
            errors.append("Field 'channels' must be an array")
        else:
            # Collect all channel IDs for reference validation
            # Include system channels that are always available
            all_channel_ids = {'zero', 'one'}  # System constant channels
            for ch in channels:
                if isinstance(ch, dict) and "id" in ch:
                    all_channel_ids.add(ch["id"])

            # Validate each channel
            for i, channel in enumerate(channels):
                path = f"channels[{i}]"
                channel_errors = ConfigValidator._validate_channel(
                    channel, path, all_channel_ids, all_message_ids
                )
                errors.extend(channel_errors)

            # Check for duplicate IDs
            seen_ids = set()
            for ch in channels:
                if isinstance(ch, dict) and "id" in ch:
                    ch_id = ch["id"]
                    if ch_id in seen_ids:
                        errors.append(f"Duplicate channel ID: '{ch_id}'")
                    seen_ids.add(ch_id)

        is_valid = len(errors) == 0
        return is_valid, errors

    @staticmethod
    def _validate_channel(channel: Dict[str, Any], path: str, all_channel_ids: set,
                          all_message_ids: set = None) -> List[str]:
        """Validate a single channel configuration"""
        errors = []
        if all_message_ids is None:
            all_message_ids = set()

        # Required fields
        for field in ["id", "channel_type"]:
            if field not in channel:
                errors.append(f"{path}.{field} is required")

        if "id" in channel:
            valid, error = ConfigValidator.validate_channel_id(channel["id"], f"{path}.id")
            if not valid:
                errors.append(error)

        if "channel_type" in channel:
            channel_type = channel["channel_type"]
            allowed_types = [
                "digital_input", "analog_input", "power_output",
                "can_rx", "can_tx", "logic", "number",
                "table_2d", "table_3d", "switch", "timer",
                "filter", "enum", "pid", "hbridge",
                "lua_script", "handler", "blinkmarine_keypad"
            ]
            if channel_type not in allowed_types:
                errors.append(f"{path}.channel_type: '{channel_type}' is not valid")
            else:
                # Validate type-specific fields
                type_errors = ConfigValidator._validate_channel_type_fields(
                    channel, channel_type, path, all_channel_ids, all_message_ids
                )
                errors.extend(type_errors)

        return errors

    @staticmethod
    def _validate_channel_type_fields(channel: Dict[str, Any], channel_type: str,
                                       path: str, all_channel_ids: set,
                                       all_message_ids: set = None) -> List[str]:
        """Validate channel type-specific fields"""
        errors = []
        if all_message_ids is None:
            all_message_ids = set()

        if channel_type == "digital_input":
            if "input_pin" in channel:
                pin = channel["input_pin"]
                if not isinstance(pin, int) or not (0 <= pin <= 19):
                    errors.append(f"{path}.input_pin must be between 0 and 19")

        elif channel_type == "analog_input":
            if "input_pin" in channel:
                pin = channel["input_pin"]
                if not isinstance(pin, int) or not (0 <= pin <= 19):
                    errors.append(f"{path}.input_pin must be between 0 and 19")

        elif channel_type == "power_output":
            if "output_pins" in channel:
                pins = channel["output_pins"]
                if not isinstance(pins, list):
                    errors.append(f"{path}.output_pins must be an array")
                elif len(pins) > 3:
                    errors.append(f"{path}.output_pins: maximum 3 pins allowed")
            if "source_channel" in channel:
                valid, error = ConfigValidator.validate_channel_reference(
                    channel["source_channel"], all_channel_ids, f"{path}.source_channel"
                )
                if not valid:
                    errors.append(error)

        elif channel_type == "logic":
            # Validate channel references for logic operations
            channel_fields = ["channel", "channel_2", "set_channel", "reset_channel", "toggle_channel"]
            for field in channel_fields:
                if field in channel and channel[field]:
                    valid, error = ConfigValidator.validate_channel_reference(
                        channel[field], all_channel_ids, f"{path}.{field}"
                    )
                    if not valid:
                        errors.append(error)

            # Legacy support: validate inputs array
            if "inputs" in channel:
                inputs = channel["inputs"]
                if not isinstance(inputs, list):
                    errors.append(f"{path}.inputs must be an array")
                else:
                    for j, inp in enumerate(inputs):
                        valid, error = ConfigValidator.validate_channel_reference(
                            inp, all_channel_ids, f"{path}.inputs[{j}]"
                        )
                        if not valid:
                            errors.append(error)

            # Validate delay values (legacy)
            if "delay_on_ms" in channel:
                delay = channel["delay_on_ms"]
                if not isinstance(delay, int) or delay < 0 or delay > 60000:
                    errors.append(f"{path}.delay_on_ms must be between 0 and 60000")
            if "delay_off_ms" in channel:
                delay = channel["delay_off_ms"]
                if not isinstance(delay, int) or delay < 0 or delay > 60000:
                    errors.append(f"{path}.delay_off_ms must be between 0 and 60000")

        elif channel_type == "timer":
            if "start_channel" in channel:
                valid, error = ConfigValidator.validate_channel_reference(
                    channel["start_channel"], all_channel_ids, f"{path}.start_channel"
                )
                if not valid:
                    errors.append(error)
            if "stop_channel" in channel and channel["stop_channel"]:
                valid, error = ConfigValidator.validate_channel_reference(
                    channel["stop_channel"], all_channel_ids, f"{path}.stop_channel"
                )
                if not valid:
                    errors.append(error)

        elif channel_type == "filter":
            if "input_channel" in channel:
                valid, error = ConfigValidator.validate_channel_reference(
                    channel["input_channel"], all_channel_ids, f"{path}.input_channel"
                )
                if not valid:
                    errors.append(error)

        elif channel_type in ["table_2d", "table_3d"]:
            if "x_axis_channel" in channel:
                valid, error = ConfigValidator.validate_channel_reference(
                    channel["x_axis_channel"], all_channel_ids, f"{path}.x_axis_channel"
                )
                if not valid:
                    errors.append(error)
            if channel_type == "table_3d" and "y_axis_channel" in channel:
                valid, error = ConfigValidator.validate_channel_reference(
                    channel["y_axis_channel"], all_channel_ids, f"{path}.y_axis_channel"
                )
                if not valid:
                    errors.append(error)

        elif channel_type == "switch":
            for field in ["input_up_channel", "input_down_channel"]:
                if field in channel and channel[field]:
                    valid, error = ConfigValidator.validate_channel_reference(
                        channel[field], all_channel_ids, f"{path}.{field}"
                    )
                    if not valid:
                        errors.append(error)

        elif channel_type == "can_rx":
            # Validate message_ref reference (new architecture)
            if "message_ref" in channel and channel["message_ref"]:
                msg_ref = channel["message_ref"]
                if msg_ref not in all_message_ids:
                    errors.append(f"{path}.message_ref: references undefined CAN message '{msg_ref}'")

            # Validate divider is not zero
            if "divider" in channel and channel["divider"] == 0:
                errors.append(f"{path}.divider cannot be zero")

        elif channel_type == "can_tx":
            if "signals" in channel:
                signals = channel["signals"]
                if isinstance(signals, list):
                    for j, sig in enumerate(signals):
                        if isinstance(sig, dict) and "source_channel" in sig:
                            valid, error = ConfigValidator.validate_channel_reference(
                                sig["source_channel"], all_channel_ids,
                                f"{path}.signals[{j}].source_channel"
                            )
                            if not valid:
                                errors.append(error)

        return errors

    @staticmethod
    def detect_circular_dependencies(config: Dict[str, Any]) -> List[List[str]]:
        """
        Detect circular dependencies between channels.

        Returns:
            List of cycles found (each cycle is a list of channel IDs)
        """
        channels = config.get("channels", [])

        # Build adjacency list (channel -> channels it depends on)
        dependencies = {}
        for ch in channels:
            if not isinstance(ch, dict):
                continue
            # Use 'id' for dependency tracking (channel references use id, not name)
            ch_id = ch.get("id", "")
            if not ch_id:
                continue

            deps = set()
            channel_type = ch.get("channel_type", "")

            # Collect all channel references based on type
            if channel_type == "logic":
                # New format channel references
                for field in ["channel", "channel_2", "set_channel", "reset_channel", "toggle_channel"]:
                    if ch.get(field):
                        deps.add(ch[field])
                # Legacy support
                deps.update(ch.get("inputs", []))
            elif channel_type == "number":
                deps.update(ch.get("inputs", []))
            elif channel_type == "timer":
                if ch.get("start_channel"):
                    deps.add(ch["start_channel"])
                if ch.get("stop_channel"):
                    deps.add(ch["stop_channel"])
            elif channel_type == "filter":
                if ch.get("input_channel"):
                    deps.add(ch["input_channel"])
            elif channel_type == "power_output":
                if ch.get("source_channel"):
                    deps.add(ch["source_channel"])
                if ch.get("duty_channel"):
                    deps.add(ch["duty_channel"])
            elif channel_type in ["table_2d", "table_3d"]:
                if ch.get("x_axis_channel"):
                    deps.add(ch["x_axis_channel"])
                if ch.get("y_axis_channel"):
                    deps.add(ch["y_axis_channel"])
            elif channel_type == "switch":
                if ch.get("input_up_channel"):
                    deps.add(ch["input_up_channel"])
                if ch.get("input_down_channel"):
                    deps.add(ch["input_down_channel"])
            elif channel_type == "can_tx":
                for sig in ch.get("signals", []):
                    if isinstance(sig, dict) and sig.get("source_channel"):
                        deps.add(sig["source_channel"])

            dependencies[ch_id] = deps

        # Find cycles using DFS
        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in dependencies.get(node, set()):
                if neighbor not in dependencies:
                    continue  # External reference, skip
                if neighbor not in visited:
                    cycle = dfs(neighbor)
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]

            path.pop()
            rec_stack.remove(node)
            return None

        for ch_id in dependencies:
            if ch_id not in visited:
                cycle = dfs(ch_id)
                if cycle:
                    cycles.append(cycle)

        return cycles

    @staticmethod
    def format_validation_errors(errors: List[str]) -> str:
        """Format validation errors for user display"""
        if not errors:
            return ""

        error_msg = "Configuration validation failed:\n\n"
        for i, error in enumerate(errors, 1):
            error_msg += f"{i}. {error}\n"

        return error_msg


def create_default_config(include_hardware: bool = True) -> Dict[str, Any]:
    """Create a default configuration with all PMU-30 hardware channels.

    Args:
        include_hardware: If True, creates all 30 outputs, 20 analog inputs,
                         20 digital inputs, and 4 H-bridges. If False, creates
                         minimal config with just example tables.

    Returns:
        Complete PMU-30 configuration dictionary.
    """
    from datetime import datetime

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
