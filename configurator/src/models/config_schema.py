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
                    "enabled": {"type": "boolean"},
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
                            "filter", "enum"
                        ]
                    },
                    "enabled": {"type": "boolean"},
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
            "enum": ["switch_active_low", "switch_active_high", "frequency", "rpm", "flex_fuel", "beacon", "puls_oil_sensor"]
        },
        "input_pin": {"type": "integer", "minimum": 0, "maximum": 7},
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
        "can_bus": {"type": "integer", "enum": [1, 2]},
        "message_id": {"type": "integer", "minimum": 0},
        "is_extended": {"type": "boolean"},
        "cycle_time_ms": {"type": "integer", "minimum": 1},
        "signals": {"type": "array"}
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
        all_message_ids = set()
        if isinstance(can_messages, list):
            for i, msg in enumerate(can_messages):
                if isinstance(msg, dict):
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
                "filter", "enum"
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
                if not isinstance(pin, int) or not (0 <= pin <= 7):
                    errors.append(f"{path}.input_pin must be between 0 and 7")

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


def create_default_config() -> Dict[str, Any]:
    """Create a default empty configuration"""
    from datetime import datetime

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
        "can_messages": [],  # Level 1 - CAN Message Objects
        "channels": [],
        "system": {
            "control_frequency_hz": 1000,
            "logic_frequency_hz": 500,
            "can1_baudrate": 500000,
            "can2_baudrate": 500000
        }
    }
