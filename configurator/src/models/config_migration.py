"""
Configuration Migration Module (Simplified for Binary-Only)

Handles runtime ID generation for PMU-30 configurations.
JSON migration functions removed - binary format only.
"""

import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ConfigMigration:
    """Handles channel ID generation for configurations."""

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
    def ensure_numeric_channel_ids(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure all channels have a numeric 'channel_id' field.
        Auto-generates unique IDs for channels without one.
        """
        channels = config.get("channels", [])

        # Find max existing channel_id
        max_id = 0
        for ch in channels:
            ch_id = ch.get("channel_id")
            if isinstance(ch_id, int) and ch_id > max_id:
                max_id = ch_id

        # Start from max + 1 (or 1 if none exist)
        next_id = max(max_id + 1, 1)

        # Assign channel_id to channels that don't have one (None, 0, or empty)
        for ch in channels:
            ch_id = ch.get("channel_id")
            if ch_id is None or ch_id == 0 or ch_id == "":
                ch["channel_id"] = next_id
                logger.debug(f"Assigned channel_id {next_id} to channel '{ch.get('name', ch.get('id', 'unknown'))}'")
                next_id += 1

        return config
