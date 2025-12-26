"""
PMU-30 Configuration Manager
Version 3.0 - Unified Channel Architecture with CAN Message/Input Two-Level

Owner: R2 m-sport
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime

from .config_schema import ConfigValidator, create_default_config
from .channel import ChannelBase, ChannelType, ChannelFactory, CanMessage

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages PMU-30 configuration files (JSON format) with unified channels"""

    def __init__(self):
        self.config: Dict[str, Any] = create_default_config()
        self.current_file: Optional[Path] = None
        self.modified: bool = False

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return self.config

    def new_config(self) -> None:
        """Create new empty configuration"""
        self.config = create_default_config()
        self.current_file = None
        self.modified = False
        logger.info("Created new configuration")

    def load_from_file(self, filepath: str) -> Tuple[bool, Optional[str]]:
        """
        Load configuration from JSON file with validation

        Args:
            filepath: Path to JSON configuration file

        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            path = Path(filepath)

            if not path.exists():
                error_msg = f"Configuration file not found: {filepath}"
                logger.error(error_msg)
                return False, error_msg

            # Load JSON
            with open(path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)

            # Check version and migrate if needed
            version = loaded_config.get("version", "1.0")
            if version.startswith("1."):
                # Old format - don't support migration
                error_msg = (
                    "Configuration file uses old format (v1.x).\n"
                    "Please create a new configuration.\n"
                    "Migration from v1.x is not supported."
                )
                logger.error(error_msg)
                return False, error_msg

            # Migrate from v2.0 to v3.0 if needed
            if version.startswith("2."):
                loaded_config = self._migrate_v2_to_v3(loaded_config)
                logger.info(f"Migrated configuration from v{version} to v3.0")

            # Auto-generate missing IDs from name field
            loaded_config = self._ensure_channel_ids(loaded_config)

            # Validate configuration
            is_valid, validation_errors = ConfigValidator.validate_config(loaded_config)

            if not is_valid:
                error_msg = ConfigValidator.format_validation_errors(validation_errors)
                logger.error(f"Configuration validation failed:\n{error_msg}")
                return False, error_msg

            # Check for circular dependencies
            cycles = ConfigValidator.detect_circular_dependencies(loaded_config)
            if cycles:
                cycle_str = " -> ".join(cycles[0])
                error_msg = f"Circular dependency detected: {cycle_str}"
                logger.warning(error_msg)
                # Just warn, don't fail

            # Configuration is valid, apply it
            self.config = loaded_config

            # Update modified timestamp
            if "device" in self.config:
                self.config["device"]["modified"] = datetime.now().isoformat()

            self.current_file = path
            self.modified = False

            logger.info(f"Loaded and validated configuration from: {filepath}")
            return True, None

        except json.JSONDecodeError as e:
            error_msg = (
                f"Invalid JSON format in configuration file:\n\n"
                f"Line {e.lineno}, Column {e.colno}:\n{e.msg}\n\n"
                f"Please check the file syntax."
            )
            logger.error(f"JSON decode error: {e}")
            return False, error_msg

        except Exception as e:
            error_msg = f"Failed to load configuration:\n\n{str(e)}"
            logger.error(f"Failed to load configuration: {e}")
            return False, error_msg

    def load_from_dict(self, config_dict: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Load configuration from dictionary (e.g., from device).

        Args:
            config_dict: Configuration dictionary

        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            # Auto-generate missing IDs from name field
            config_dict = self._ensure_channel_ids(config_dict)

            # Validate configuration
            is_valid, validation_errors = ConfigValidator.validate_config(config_dict)

            if not is_valid:
                error_msg = ConfigValidator.format_validation_errors(validation_errors)
                logger.warning(f"Config validation warnings:\n{error_msg}")
                # Don't fail on validation, just warn

            # Compute runtime_channel_id for virtual channels
            # Firmware allocates IDs starting from 200 in order of channel parsing
            config_dict = self._compute_runtime_channel_ids(config_dict)

            # Apply configuration
            self.config = config_dict
            self.current_file = None
            self.modified = False

            logger.info("Loaded configuration from device")
            return True, None

        except Exception as e:
            error_msg = f"Failed to load configuration: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def save_to_file(self, filepath: Optional[str] = None) -> bool:
        """
        Save configuration to JSON file

        Args:
            filepath: Path to save to (uses current_file if None)

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            if filepath:
                path = Path(filepath)
            elif self.current_file:
                path = self.current_file
            else:
                logger.error("No filepath specified")
                return False

            # Update modified timestamp
            self.config["device"]["modified"] = datetime.now().isoformat()

            # Convert channel references from names to numeric IDs
            export_config = self._convert_references_to_ids(self.config)

            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)

            # Save with pretty formatting
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(export_config, f, indent=2, ensure_ascii=False)

            self.current_file = path
            self.modified = False

            logger.info(f"Saved configuration to: {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False

    # ========== Channel Methods ==========

    def get_all_channels(self) -> List[Dict[str, Any]]:
        """Get all channels"""
        return self.config.get("channels", [])

    def get_channels_by_type(self, channel_type: ChannelType) -> List[Dict[str, Any]]:
        """Get channels of specific type"""
        channels = self.config.get("channels", [])
        return [ch for ch in channels if ch.get("channel_type") == channel_type.value]

    def get_channel_by_name(self, channel_name: str) -> Optional[Dict[str, Any]]:
        """Get channel by name (with backwards compatibility for 'id' field)"""
        for ch in self.config.get("channels", []):
            # Try 'name' first, fall back to 'id' for backwards compatibility
            name = ch.get("name", "") or ch.get("id", "")
            if name == channel_name:
                return ch
        return None

    # Backwards compatibility alias
    def get_channel_by_id(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Deprecated: Use get_channel_by_name instead"""
        return self.get_channel_by_name(channel_id)

    def get_channel_index(self, channel_name: str) -> int:
        """Get channel index by name, returns -1 if not found"""
        for i, ch in enumerate(self.config.get("channels", [])):
            # Try 'name' first, fall back to 'id' for backwards compatibility
            name = ch.get("name", "") or ch.get("id", "")
            if name == channel_name:
                return i
        return -1

    def add_channel(self, channel_config: Dict[str, Any]) -> bool:
        """
        Add new channel

        Args:
            channel_config: Channel configuration dict

        Returns:
            True if added successfully
        """
        if "channels" not in self.config:
            self.config["channels"] = []

        # Check for duplicate name (try 'name' first, fall back to 'id')
        channel_name = channel_config.get("name", "") or channel_config.get("id", "")
        if self.get_channel_by_name(channel_name):
            logger.error(f"Channel with name '{channel_name}' already exists")
            return False

        self.config["channels"].append(channel_config)
        self.modified = True
        logger.info(f"Added channel: {channel_name}")
        return True

    def update_channel(self, channel_id: str, channel_config: Dict[str, Any]) -> bool:
        """
        Update existing channel

        Args:
            channel_id: ID of channel to update
            channel_config: New configuration

        Returns:
            True if updated successfully
        """
        index = self.get_channel_index(channel_id)
        if index < 0:
            logger.error(f"Channel '{channel_id}' not found")
            return False

        # Update the channel
        self.config["channels"][index] = channel_config
        self.modified = True
        logger.info(f"Updated channel: {channel_id}")
        return True

    def remove_channel(self, channel_id: str) -> bool:
        """
        Remove channel

        Args:
            channel_id: ID of channel to remove

        Returns:
            True if removed successfully
        """
        index = self.get_channel_index(channel_id)
        if index < 0:
            logger.error(f"Channel '{channel_id}' not found")
            return False

        self.config["channels"].pop(index)
        self.modified = True
        logger.info(f"Removed channel: {channel_id}")
        return True

    def get_available_channels_for_input(
        self,
        exclude_id: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """
        Get all channels available for selection as input

        Args:
            exclude_id: Channel ID to exclude (prevent self-reference)

        Returns:
            Dict mapping category names to lists of channel IDs
        """
        available = {
            "Digital Inputs": [],
            "Analog Inputs": [],
            "Power Outputs": [],
            "Logic Functions": [],
            "Math/Numbers": [],
            "Timers": [],
            "Filters": [],
            "Switches": [],
            "2D Tables": [],
            "3D Tables": [],
            "Enumerations": [],
            "CAN RX": [],
            "CAN TX": [],
        }

        type_to_category = {
            "digital_input": "Digital Inputs",
            "analog_input": "Analog Inputs",
            "power_output": "Power Outputs",
            "logic": "Logic Functions",
            "number": "Math/Numbers",
            "timer": "Timers",
            "filter": "Filters",
            "switch": "Switches",
            "table_2d": "2D Tables",
            "table_3d": "3D Tables",
            "enum": "Enumerations",
            "can_rx": "CAN RX",
            "can_tx": "CAN TX",
        }

        for ch in self.config.get("channels", []):
            # Try 'name' first, fall back to 'id' for backwards compatibility
            ch_name = ch.get("name", "") or ch.get("id", "")
            if ch_name and ch_name != exclude_id:
                channel_type = ch.get("channel_type", "")
                category = type_to_category.get(channel_type)
                if category:
                    available[category].append(ch_name)

        # Remove empty categories
        return {k: v for k, v in available.items() if v}

    def get_channel_names_of_type(self, channel_type: ChannelType) -> List[str]:
        """Get list of channel names of specific type"""
        result = []
        for ch in self.config.get("channels", []):
            if ch.get("channel_type") == channel_type.value:
                # Try 'name' first, fall back to 'id' for backwards compatibility
                name = ch.get("name", "") or ch.get("id", "")
                if name:
                    result.append(name)
        return result

    # Backwards compatibility alias
    def get_channel_ids_of_type(self, channel_type: ChannelType) -> List[str]:
        """Deprecated: Use get_channel_names_of_type instead"""
        return self.get_channel_names_of_type(channel_type)

    def channel_exists(self, channel_name: str) -> bool:
        """Check if channel with given name exists"""
        return self.get_channel_by_name(channel_name) is not None

    def get_channel_count(self, channel_type: Optional[ChannelType] = None) -> int:
        """Get count of channels, optionally filtered by type"""
        channels = self.config.get("channels", [])
        if channel_type:
            return sum(1 for ch in channels if ch.get("channel_type") == channel_type.value)
        return len(channels)

    # ========== Convenience Methods for Specific Channel Types ==========

    def get_can_inputs(self) -> List[Dict[str, Any]]:
        """Get all CAN RX channels"""
        return self.get_channels_by_type(ChannelType.CAN_RX)

    def get_outputs(self) -> List[Dict[str, Any]]:
        """Get all power output channels"""
        return self.get_channels_by_type(ChannelType.POWER_OUTPUT)

    def get_inputs(self) -> List[Dict[str, Any]]:
        """Get all analog input channels"""
        return self.get_channels_by_type(ChannelType.ANALOG_INPUT)

    def get_digital_inputs(self) -> List[Dict[str, Any]]:
        """Get all digital input channels"""
        return self.get_channels_by_type(ChannelType.DIGITAL_INPUT)

    def get_logic_channels(self) -> List[Dict[str, Any]]:
        """Get all logic channels"""
        return self.get_channels_by_type(ChannelType.LOGIC)

    def get_number_channels(self) -> List[Dict[str, Any]]:
        """Get all number/math channels"""
        return self.get_channels_by_type(ChannelType.NUMBER)

    def get_switch_channels(self) -> List[Dict[str, Any]]:
        """Get all switch channels"""
        return self.get_channels_by_type(ChannelType.SWITCH)

    def get_timers(self) -> List[Dict[str, Any]]:
        """Get all timer channels"""
        return self.get_channels_by_type(ChannelType.TIMER)

    def get_keypads(self) -> List[Dict[str, Any]]:
        """Get all keypad configurations from system settings (legacy)"""
        return self.config.get("system", {}).get("keypads", [])

    def get_blinkmarine_keypads(self) -> List[Dict[str, Any]]:
        """Get all BlinkMarine keypad channels"""
        return self.get_channels_by_type(ChannelType.BLINKMARINE_KEYPAD)

    # ========== System Settings ==========

    def get_system_settings(self) -> Dict[str, Any]:
        """Get system settings"""
        return self.config.get("system", {})

    def update_system_settings(self, settings: Dict[str, Any]) -> None:
        """Update system settings"""
        self.config["system"] = settings
        self.modified = True

    # ========== Device Info ==========

    def get_device_info(self) -> Dict[str, Any]:
        """Get device information"""
        return self.config.get("device", {})

    def update_device_info(self, info: Dict[str, Any]) -> None:
        """Update device information"""
        self.config["device"] = info
        self.modified = True

    # ========== State ==========

    def is_modified(self) -> bool:
        """Check if configuration has been modified"""
        return self.modified

    def set_modified(self, modified: bool = True) -> None:
        """Set modified flag"""
        self.modified = modified

    def get_current_file(self) -> Optional[Path]:
        """Get current configuration file path"""
        return self.current_file

    # ========== Validation ==========

    def validate_config(self) -> Tuple[bool, List[str]]:
        """
        Validate current configuration

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        return ConfigValidator.validate_config(self.config)

    def validate_channel_references(self) -> List[str]:
        """
        Check that all channel references are valid

        Returns:
            List of error messages
        """
        errors = []
        # Include system channels that are always available
        all_channel_names = {'zero', 'one'}  # System constant channels
        for ch in self.config.get("channels", []):
            # Try 'name' first, fall back to 'id' for backwards compatibility
            ch_name = ch.get("name", "") or ch.get("id", "")
            if ch_name:
                all_channel_names.add(ch_name)

        for ch in self.config.get("channels", []):
            # Try 'name' first, fall back to 'id' for backwards compatibility
            ch_name = ch.get("name", "") or ch.get("id", "unknown")
            channel_type = ch.get("channel_type", "")

            # Check references based on type
            refs_to_check = []

            if channel_type == "logic":
                refs_to_check = ch.get("inputs", [])
            elif channel_type == "number":
                refs_to_check = ch.get("inputs", [])
            elif channel_type == "timer":
                if ch.get("start_channel"):
                    refs_to_check.append(ch["start_channel"])
                if ch.get("stop_channel"):
                    refs_to_check.append(ch["stop_channel"])
            elif channel_type == "filter":
                if ch.get("input_channel"):
                    refs_to_check.append(ch["input_channel"])
            elif channel_type == "power_output":
                if ch.get("source_channel"):
                    refs_to_check.append(ch["source_channel"])
                if ch.get("duty_channel"):
                    refs_to_check.append(ch["duty_channel"])
            elif channel_type in ["table_2d", "table_3d"]:
                if ch.get("x_axis_channel"):
                    refs_to_check.append(ch["x_axis_channel"])
                if ch.get("y_axis_channel"):
                    refs_to_check.append(ch["y_axis_channel"])
            elif channel_type == "switch":
                if ch.get("input_up_channel"):
                    refs_to_check.append(ch["input_up_channel"])
                if ch.get("input_down_channel"):
                    refs_to_check.append(ch["input_down_channel"])
            elif channel_type == "can_tx":
                for sig in ch.get("signals", []):
                    if sig.get("source_channel"):
                        refs_to_check.append(sig["source_channel"])

            for ref in refs_to_check:
                # Skip empty, None, and integer references (runtime channel IDs)
                if not ref or isinstance(ref, int):
                    continue
                if ref not in all_channel_names:
                    errors.append(f"Channel '{ch_name}' references undefined channel '{ref}'")

        return errors

    def detect_circular_dependencies(self) -> List[List[str]]:
        """
        Detect circular dependencies

        Returns:
            List of cycles (each cycle is a list of channel IDs)
        """
        return ConfigValidator.detect_circular_dependencies(self.config)

    # ========== Export ==========

    def export_to_yaml(self, filepath: str) -> bool:
        """Export configuration to YAML format"""
        try:
            import yaml

            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)

            logger.info(f"Exported configuration to YAML: {filepath}")
            return True

        except ImportError:
            logger.error("PyYAML not installed. Cannot export to YAML.")
            return False
        except Exception as e:
            logger.error(f"Failed to export to YAML: {e}")
            return False

    def export_channel_summary(self) -> str:
        """
        Export summary of all channels

        Returns:
            Formatted string summary
        """
        lines = ["PMU-30 Configuration Summary", "=" * 40, ""]

        type_counts = {}
        for ch in self.config.get("channels", []):
            channel_type = ch.get("channel_type", "unknown")
            type_counts[channel_type] = type_counts.get(channel_type, 0) + 1

        lines.append(f"Total channels: {len(self.config.get('channels', []))}")
        lines.append("")
        lines.append("By type:")
        for channel_type, count in sorted(type_counts.items()):
            lines.append(f"  {channel_type}: {count}")

        lines.append("")
        lines.append("Channel list:")
        for ch in self.config.get("channels", []):
            # Try 'name' first, fall back to 'id' for backwards compatibility
            ch_name = ch.get("name", "") or ch.get("id", "?")
            ch_type = ch.get("channel_type", "?")
            ch_id = ch.get("channel_id", 0)
            enabled = "enabled" if ch.get("enabled", True) else "disabled"
            lines.append(f"  [{ch_type}] #{ch_id}: {ch_name} ({enabled})")

        return "\n".join(lines)

    # ========== CAN Message Methods (Level 1) ==========

    def get_all_can_messages(self) -> List[Dict[str, Any]]:
        """Get all CAN messages"""
        return self.config.get("can_messages", [])

    def get_can_message_by_name(self, message_name: str) -> Optional[Dict[str, Any]]:
        """Get CAN message by name (with backwards compatibility for 'id' field)"""
        for msg in self.config.get("can_messages", []):
            # Try 'name' first, fall back to 'id' for backwards compatibility
            name = msg.get("name", "") or msg.get("id", "")
            if name == message_name:
                return msg
        return None

    # Backwards compatibility alias
    def get_can_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Deprecated: Use get_can_message_by_name instead"""
        return self.get_can_message_by_name(message_id)

    def get_can_message_index(self, message_name: str) -> int:
        """Get CAN message index by name, returns -1 if not found"""
        for i, msg in enumerate(self.config.get("can_messages", [])):
            # Try 'name' first, fall back to 'id' for backwards compatibility
            name = msg.get("name", "") or msg.get("id", "")
            if name == message_name:
                return i
        return -1

    def add_can_message(self, message_config: Dict[str, Any]) -> bool:
        """Add new CAN message"""
        if "can_messages" not in self.config:
            self.config["can_messages"] = []

        # Try 'name' first, fall back to 'id' for backwards compatibility
        message_name = message_config.get("name", "") or message_config.get("id", "")
        if self.get_can_message_by_name(message_name):
            logger.error(f"CAN message with name '{message_name}' already exists")
            return False

        self.config["can_messages"].append(message_config)
        self.modified = True
        logger.info(f"Added CAN message: {message_name}")
        return True

    def update_can_message(self, message_name: str, message_config: Dict[str, Any]) -> bool:
        """Update existing CAN message"""
        index = self.get_can_message_index(message_name)
        if index < 0:
            logger.error(f"CAN message '{message_name}' not found")
            return False

        self.config["can_messages"][index] = message_config
        self.modified = True
        logger.info(f"Updated CAN message: {message_name}")
        return True

    def remove_can_message(self, message_name: str) -> bool:
        """Remove CAN message"""
        index = self.get_can_message_index(message_name)
        if index < 0:
            logger.error(f"CAN message '{message_name}' not found")
            return False

        self.config["can_messages"].pop(index)
        self.modified = True
        logger.info(f"Removed CAN message: {message_name}")
        return True

    def get_can_inputs_for_message(self, message_name: str) -> List[Dict[str, Any]]:
        """Get all CAN RX channels that reference a specific message"""
        can_inputs = []
        for ch in self.config.get("channels", []):
            if ch.get("channel_type") == "can_rx" and ch.get("message_ref") == message_name:
                can_inputs.append(ch)
        return can_inputs

    def get_can_message_names(self) -> List[str]:
        """Get list of all CAN message names"""
        result = []
        for msg in self.config.get("can_messages", []):
            # Try 'name' first, fall back to 'id' for backwards compatibility
            name = msg.get("name", "") or msg.get("id", "")
            if name:
                result.append(name)
        return result

    # Backwards compatibility alias
    def get_can_message_ids(self) -> List[str]:
        """Deprecated: Use get_can_message_names instead"""
        return self.get_can_message_names()

    def can_message_exists(self, message_name: str) -> bool:
        """Check if CAN message with given name exists"""
        return self.get_can_message_by_name(message_name) is not None

    # ========== Runtime ID Computation ==========

    def _compute_runtime_channel_ids(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute runtime_channel_id for virtual channels.

        Firmware allocates runtime IDs starting from 200 in the order
        channels appear in the config. Virtual channel types:
        - logic, number, timer, filter, switch, enum

        This allows the configurator to match telemetry data (which uses
        runtime IDs) with the correct channels.
        """
        VIRTUAL_CHANNEL_START_ID = 200
        # Note: enum is excluded because firmware doesn't allocate IDs for enum channels yet
        VIRTUAL_CHANNEL_TYPES = {'logic', 'number', 'timer', 'filter', 'switch'}

        next_id = VIRTUAL_CHANNEL_START_ID
        channels = config.get("channels", [])

        for ch in channels:
            ch_type = ch.get("channel_type", "")
            if ch_type in VIRTUAL_CHANNEL_TYPES:
                ch["runtime_channel_id"] = next_id
                next_id += 1

        return config

    # ========== Migration ==========

    def _ensure_channel_ids(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure all channels have a valid 'id' field.
        Auto-generates id from 'name' if missing.
        Sanitizes invalid IDs (containing invalid characters).
        """
        import re

        def sanitize_id(raw_id: str) -> str:
            """Sanitize an ID to contain only valid characters."""
            # Replace common separators with underscores
            sanitized = raw_id.replace(".", "_").replace("-", "_").replace(" ", "_")
            # Remove any remaining invalid characters
            sanitized = ''.join(c if c.isalnum() or c == '_' else '_' for c in sanitized)
            # Ensure it starts with a letter
            if sanitized and not sanitized[0].isalpha():
                sanitized = "ch_" + sanitized
            # Collapse multiple underscores
            sanitized = re.sub(r'_+', '_', sanitized)
            # Remove trailing underscores
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
                    # Sanitize invalid ID
                    old_id = ch["id"]
                    new_id = sanitize_id(old_id)
                    # Ensure uniqueness
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
                name = ch.get("name", "")
                channel_type = ch.get("channel_type", "channel")

                # Get prefix based on channel type
                prefix_map = {
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
                }
                prefix = prefix_map.get(channel_type, "ch_")

                # Generate base id from name
                if name:
                    base_id = re.sub(r'[^a-z0-9_]', '_', name.lower())
                    base_id = re.sub(r'_+', '_', base_id).strip('_')
                else:
                    base_id = "unnamed"

                # Ensure uniqueness
                new_id = f"{prefix}{base_id}"
                counter = 1
                while new_id in existing_ids:
                    new_id = f"{prefix}{base_id}_{counter}"
                    counter += 1

                ch["id"] = new_id
                existing_ids.add(new_id)
                logger.debug(f"Generated channel ID: {new_id} from name: {name}")

        return config

    def _migrate_v2_to_v3(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate v2.0 configuration to v3.0 (two-level CAN architecture)

        Creates CAN message objects from existing can_rx channels and
        updates can_rx channels to reference the new messages.
        """
        # Create can_messages array if not exists
        if "can_messages" not in config:
            config["can_messages"] = []

        # Track unique messages (can_bus, message_id, is_extended) -> new_message_id
        message_map = {}

        channels = config.get("channels", [])

        # First pass: collect unique CAN message combinations from can_rx channels
        for ch in channels:
            if ch.get("channel_type") == "can_rx" and not ch.get("message_ref"):
                can_bus = ch.get("can_bus", 1)
                old_msg_id = ch.get("message_id", 0)
                is_extended = ch.get("is_extended", False)

                key = (can_bus, old_msg_id, is_extended)

                if key not in message_map:
                    # Create new message name
                    new_msg_name = f"msg_can{can_bus}_{old_msg_id:03X}"

                    # Ensure unique name
                    base_name = new_msg_name
                    counter = 1
                    while any((m.get("name", "") or m.get("id", "")) == new_msg_name for m in config["can_messages"]):
                        new_msg_name = f"{base_name}_{counter}"
                        counter += 1

                    message_map[key] = new_msg_name

                    # Create CAN message object
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
                        "description": f"Auto-migrated from v2.0"
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
                    # Add new fields
                    ch["message_ref"] = message_map[key]
                    ch["frame_offset"] = 0

                    # Convert value_type to data_type if present
                    if "value_type" in ch:
                        ch["data_type"] = ch["value_type"]

                    # Convert factor to multiplier if present
                    if "factor" in ch and "multiplier" not in ch:
                        ch["multiplier"] = ch["factor"]
                        ch["divider"] = 1.0

                    # Guess data_format from length
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

                    # Calculate byte_offset from start_bit
                    start_bit = ch.get("start_bit", 0)
                    ch["byte_offset"] = start_bit // 8

                    # Set default timeout behavior
                    if "timeout_behavior" not in ch:
                        ch["timeout_behavior"] = "use_default"

        # Update version
        config["version"] = "3.0"

        return config

    def _convert_references_to_ids(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert channel references from string names to numeric channel_ids.

        This creates a clean export where the firmware only sees numeric IDs,
        while the configurator still works with names internally.

        Architecture:
        - Firmware processes channels by channel_id only
        - Names are stored separately for Lua script lookups and UI display
        - This conversion happens only during export (save)
        """
        import copy
        export_config = copy.deepcopy(config)

        # Build name -> channel_id mapping
        # Include system channels that are always available
        name_to_id = {
            'zero': 1012,  # PMU_CHANNEL_CONST_ZERO
            'one': 1013,   # PMU_CHANNEL_CONST_ONE
        }

        for ch in export_config.get("channels", []):
            ch_name = ch.get("channel_name", "") or ch.get("name", "") or ch.get("id", "")
            ch_id = ch.get("channel_id", 0)
            if ch_name and ch_id:
                name_to_id[ch_name] = ch_id

        # Fields that contain channel references
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
        ]

        def convert_reference(value):
            """Convert a single reference value."""
            if value is None or value == "":
                return value
            if isinstance(value, int):
                return value  # Already numeric
            if isinstance(value, str):
                if value in name_to_id:
                    return name_to_id[value]
                # Try to parse as numeric string
                try:
                    return int(value)
                except ValueError:
                    # Unknown channel name - keep as string for backward compatibility
                    logger.warning(f"Unknown channel reference: '{value}'")
                    return value
            return value

        # Convert references in all channels
        for ch in export_config.get("channels", []):
            # Convert direct reference fields
            for field in REFERENCE_FIELDS:
                if field in ch:
                    ch[field] = convert_reference(ch[field])

            # Handle 'inputs' array (used by logic and number channels)
            if "inputs" in ch and isinstance(ch["inputs"], list):
                ch["inputs"] = [convert_reference(inp) for inp in ch["inputs"]]

            # Handle CAN TX signals
            if ch.get("channel_type") == "can_tx" and "signals" in ch:
                for sig in ch.get("signals", []):
                    if isinstance(sig, dict) and "source_channel" in sig:
                        sig["source_channel"] = convert_reference(sig["source_channel"])

        return export_config
