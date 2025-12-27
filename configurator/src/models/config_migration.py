"""
Configuration Migration Module

Handles version migration and ID generation for PMU-30 configurations.
"""

import re
import copy
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ConfigMigration:
    """Handles configuration migration between versions."""

    # Virtual channel types that get runtime IDs from firmware
    VIRTUAL_CHANNEL_TYPES = {'logic', 'number', 'timer', 'filter', 'switch'}
    VIRTUAL_CHANNEL_START_ID = 200

    # Channel type prefixes for ID generation
    CHANNEL_TYPE_PREFIXES = {
        "digital_input": "di_",
        "analog_input": "ai_",
        "power_output": "out_",
        "logic": "l_",
        "number": "n_",
        "timer": "tm_",
        "filter": "flt_",
        "enum": "e_",
        "table_2d": "t2d_",
        "table_3d": "t3d_",
        "switch": "sw_",
        "can_rx": "crx_",
        "can_tx": "ctx_",
        "lua_script": "lua_",
        "pid": "pid_",
        "hbridge": "hb_",
        "handler": "hdl_",
        "blinkmarine_keypad": "kp_",
    }

    # Fields that contain channel references (for ID conversion)
    REFERENCE_FIELDS = [
        # Power output
        "source_channel", "duty_channel",
        # Timer
        "start_channel", "stop_channel",
        # Filter
        "input_channel",
        # Table
        "x_axis_channel", "y_axis_channel",
        # Switch
        "input_up_channel", "input_down_channel",
        # Logic
        "channel", "channel_2", "set_channel", "reset_channel", "toggle_channel",
        # H-Bridge
        "direction_source_channel", "pwm_source_channel",
        "position_source_channel", "target_source_channel",
        # Handler
        "trigger_channel", "output_channel",
        # Digital input (button modes)
        "long_press_output", "double_click_output",
        # PID
        "setpoint_channel", "process_channel",
    ]

    @classmethod
    def compute_runtime_channel_ids(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute runtime_channel_id for virtual channels.

        Firmware allocates runtime IDs starting from 200 in the order
        channels appear in the config.
        """
        next_id = cls.VIRTUAL_CHANNEL_START_ID
        channels = config.get("channels", [])

        for ch in channels:
            ch_type = ch.get("channel_type", "")
            if ch_type in cls.VIRTUAL_CHANNEL_TYPES:
                ch["runtime_channel_id"] = next_id
                next_id += 1

        return config

    @classmethod
    def ensure_channel_ids(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure all channels have a valid 'id' field.
        Auto-generates id from 'name' if missing.
        Sanitizes invalid IDs.
        """

        def sanitize_id(raw_id: str) -> str:
            """Sanitize an ID to contain only valid characters."""
            sanitized = raw_id.replace(".", "_").replace("-", "_").replace(" ", "_")
            sanitized = ''.join(c if c.isalnum() or c == '_' else '_' for c in sanitized)
            if sanitized and not sanitized[0].isalpha():
                sanitized = "ch_" + sanitized
            sanitized = re.sub(r'_+', '_', sanitized)
            sanitized = sanitized.strip("_")
            return sanitized

        def is_valid_id(channel_id: str) -> bool:
            """Check if ID matches the required pattern."""
            return bool(re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', channel_id))

        channels = config.get("channels", [])
        existing_ids = set()

        # First pass - collect existing valid IDs and sanitize invalid ones
        for ch in channels:
            if "id" in ch and ch["id"]:
                if is_valid_id(ch["id"]):
                    existing_ids.add(ch["id"])
                else:
                    old_id = ch["id"]
                    new_id = sanitize_id(old_id)
                    base_id = new_id
                    counter = 1
                    while new_id in existing_ids:
                        new_id = f"{base_id}_{counter}"
                        counter += 1
                    ch["id"] = new_id
                    existing_ids.add(new_id)
                    logger.warning(f"Sanitized invalid channel ID: '{old_id}' -> '{new_id}'")

        # Second pass - generate missing IDs
        for ch in channels:
            if "id" not in ch or not ch["id"]:
                name = ch.get("channel_name", "") or ch.get("name", "")
                channel_type = ch.get("channel_type", "channel")
                prefix = cls.CHANNEL_TYPE_PREFIXES.get(channel_type, "ch_")

                if name:
                    base_id = re.sub(r'[^a-z0-9_]', '_', name.lower())
                    base_id = re.sub(r'_+', '_', base_id).strip('_')
                else:
                    base_id = "unnamed"

                new_id = f"{prefix}{base_id}"
                counter = 1
                while new_id in existing_ids:
                    new_id = f"{prefix}{base_id}_{counter}"
                    counter += 1

                ch["id"] = new_id
                existing_ids.add(new_id)
                logger.debug(f"Generated channel ID: {new_id} from name: {name}")

        return config

    @classmethod
    def migrate_v2_to_v3(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate v2.0 configuration to v3.0 (two-level CAN architecture).

        Creates CAN message objects from existing can_rx channels and
        updates can_rx channels to reference the new messages.
        """
        if "can_messages" not in config:
            config["can_messages"] = []

        message_map = {}
        channels = config.get("channels", [])

        # First pass: collect unique CAN message combinations
        for ch in channels:
            if ch.get("channel_type") == "can_rx" and not ch.get("message_ref"):
                can_bus = ch.get("can_bus", 1)
                old_msg_id = ch.get("message_id", 0)
                is_extended = ch.get("is_extended", False)

                key = (can_bus, old_msg_id, is_extended)

                if key not in message_map:
                    new_msg_name = f"msg_can{can_bus}_{old_msg_id:03X}"

                    base_name = new_msg_name
                    counter = 1
                    while any((m.get("name", "") or m.get("id", "")) == new_msg_name
                              for m in config["can_messages"]):
                        new_msg_name = f"{base_name}_{counter}"
                        counter += 1

                    message_map[key] = new_msg_name

                    can_message = {
                        "name": new_msg_name,
                        "can_bus": can_bus,
                        "base_id": old_msg_id,
                        "is_extended": is_extended,
                        "message_type": "normal",
                        "frame_count": 1,
                        "dlc": 8,
                        "timeout_ms": ch.get("timeout_ms", 500),
                        "enabled": True,
                        "description": "Auto-migrated from v2.0"
                    }
                    config["can_messages"].append(can_message)

        # Second pass: update can_rx channels to reference messages
        for ch in channels:
            if ch.get("channel_type") == "can_rx" and not ch.get("message_ref"):
                can_bus = ch.get("can_bus", 1)
                old_msg_id = ch.get("message_id", 0)
                is_extended = ch.get("is_extended", False)

                key = (can_bus, old_msg_id, is_extended)

                if key in message_map:
                    ch["message_ref"] = message_map[key]
                    ch["frame_offset"] = 0

                    if "value_type" in ch:
                        ch["data_type"] = ch["value_type"]

                    if "factor" in ch and "multiplier" not in ch:
                        ch["multiplier"] = ch["factor"]
                        ch["divider"] = 1.0

                    length = ch.get("length", 16)
                    if length == 8:
                        ch["data_format"] = "8bit"
                    elif length == 16:
                        ch["data_format"] = "16bit"
                    elif length == 32:
                        ch["data_format"] = "32bit"
                    else:
                        ch["data_format"] = "custom"
                        ch["bit_length"] = length

                    start_bit = ch.get("start_bit", 0)
                    ch["byte_offset"] = start_bit // 8

                    if "timeout_behavior" not in ch:
                        ch["timeout_behavior"] = "use_default"

        config["version"] = "3.0"
        return config

    @classmethod
    def convert_references_to_ids(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert channel references from string names to numeric channel_ids.

        This creates a clean export where firmware only sees numeric IDs.
        """
        export_config = copy.deepcopy(config)

        # Build name -> channel_id mapping with system channels
        name_to_id = {
            'zero': 1012,  # PMU_CHANNEL_CONST_ZERO
            'one': 1013,   # PMU_CHANNEL_CONST_ONE
        }

        for ch in export_config.get("channels", []):
            ch_name = ch.get("channel_name", "") or ch.get("name", "") or ch.get("id", "")
            ch_id = ch.get("channel_id", 0)
            if ch_name and ch_id:
                name_to_id[ch_name] = ch_id

        def convert_reference(value):
            """Convert a single reference value."""
            if value is None or value == "":
                return value
            if isinstance(value, int):
                return value
            if isinstance(value, str):
                if value in name_to_id:
                    return name_to_id[value]
                try:
                    return int(value)
                except ValueError:
                    logger.warning(f"Unknown channel reference: '{value}'")
                    return value
            return value

        # Convert references in all channels
        for ch in export_config.get("channels", []):
            for field in cls.REFERENCE_FIELDS:
                if field in ch:
                    ch[field] = convert_reference(ch[field])

            if "inputs" in ch and isinstance(ch["inputs"], list):
                ch["inputs"] = [convert_reference(inp) for inp in ch["inputs"]]

            if ch.get("channel_type") == "can_tx" and "signals" in ch:
                for sig in ch.get("signals", []):
                    if isinstance(sig, dict) and "source_channel" in sig:
                        sig["source_channel"] = convert_reference(sig["source_channel"])

        return export_config
