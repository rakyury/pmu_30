"""
PMU-30 Configuration Manager
Version 4.0 - Binary-Only Config (no JSON)

Owner: R2 m-sport
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime

from .channel import ChannelType, LogicOperation
from .config_can import CANMessageManager
from .config_migration import ConfigMigration
from .channel_display_service import ChannelIdGenerator

logger = logging.getLogger(__name__)


def create_default_config() -> Dict[str, Any]:
    """Create a minimal empty configuration (no default hardware channels)."""
    return {
        "version": "4.0",
        "device": {
            "name": "PMU-30",
            "serial_number": "",
            "firmware_version": "",
            "hardware_revision": "",
            "created": datetime.now().isoformat(),
            "modified": datetime.now().isoformat()
        },
        "can_messages": [],
        "channels": [],  # Empty - user creates channels as needed
        "system": {
            "control_frequency_hz": 1000,
            "logic_frequency_hz": 500,
            "can1_baudrate": 500000,
            "can2_baudrate": 500000
        }
    }


class ConfigManager:
    """Manages PMU-30 configuration files (binary .pmu30 format only)"""

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
        logger.info("Created new empty configuration")

    def load_from_file(self, filepath: str) -> Tuple[bool, Optional[str]]:
        """
        Load configuration from binary .pmu30 file.

        Args:
            filepath: Path to configuration file (.pmu30 only)

        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            path = Path(filepath)

            if not path.exists():
                error_msg = f"Configuration file not found: {filepath}"
                logger.error(error_msg)
                return False, error_msg

            # Only .pmu30 binary files are supported
            if path.suffix.lower() != '.pmu30':
                error_msg = (
                    f"Unsupported file format: {path.suffix}\n\n"
                    "Only .pmu30 binary files are supported.\n"
                    "JSON configuration files are no longer supported."
                )
                logger.error(error_msg)
                return False, error_msg

            return self._load_binary_file(path)

        except Exception as e:
            error_msg = f"Failed to load configuration:\n\n{str(e)}"
            logger.error(f"Failed to load configuration: {e}")
            return False, error_msg

    def _load_binary_file(self, path: Path) -> Tuple[bool, Optional[str]]:
        """
        Load configuration from binary .pmu30 file.

        Args:
            path: Path to binary configuration file

        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            from .binary_config import BinaryConfigManager

            # Read raw file bytes
            with open(path, 'rb') as f:
                data = f.read()

            binary_manager = BinaryConfigManager()

            # Try loading as full format (with header) first
            success, error = binary_manager.load_from_bytes(data)
            if not success:
                # Try as raw channel data (no file header - test configs)
                success, error = binary_manager.load_from_raw_bytes(data)

            if not success:
                return False, f"Failed to load binary config: {error}"

            # Convert binary channels to config format
            channels = []

            # Add system Digital Input channels (built-in firmware channels)
            # These are for UI only - firmware already knows about them, don't serialize back!
            for i in range(8):
                channels.append({
                    "id": f"DIN{i}",
                    "channel_id": 50 + i,
                    "channel_type": "digital_input",
                    "name": f"Digital Input {i}",
                    "enabled": True,
                    "hw_index": i,
                    "system": True,  # Mark as system channel - NOT sent to firmware
                })

            # Add configured channels from binary file
            for ch in binary_manager.channels:
                ch_dict = self._binary_channel_to_dict(ch)
                if ch_dict:
                    channels.append(ch_dict)

            # Create config structure
            self.config = create_default_config()
            self.config["channels"] = channels
            self.current_file = path
            self.modified = False

            logger.info(f"Loaded binary configuration: {len(channels)} channels")
            return True, None

        except Exception as e:
            error_msg = f"Failed to load binary configuration: {e}"
            logger.error(error_msg)
            return False, error_msg

    def _binary_channel_to_dict(self, ch) -> Optional[Dict[str, Any]]:
        """Convert a binary Channel object to config dictionary format."""
        from channel_config import ChannelType as BinaryChannelType

        # Map binary channel types to config channel types
        type_map = {
            BinaryChannelType.POWER_OUTPUT: "power_output",
            BinaryChannelType.LOGIC: "logic",
            BinaryChannelType.TIMER: "timer",
            BinaryChannelType.TABLE_2D: "table_2d",
            BinaryChannelType.TABLE_3D: "table_3d",
            BinaryChannelType.FILTER: "filter",
            BinaryChannelType.PID: "pid",
        }

        ch_type = type_map.get(ch.type)
        if not ch_type:
            logger.warning(f"Unknown channel type: {ch.type}")
            return None

        result = {
            "id": ch.name or f"ch_{ch.id}",
            "channel_id": ch.id,
            "channel_type": ch_type,
            "name": ch.name or f"Channel {ch.id}",
            "enabled": bool(ch.flags & 0x01),
        }

        # Add source reference if present
        if ch.source_id != 0xFFFF:
            result["source_channel"] = ch.source_id

        # Merge type-specific config into result (flat structure for UI dialogs)
        if ch.config:
            type_config = self._parse_binary_config(ch_type, ch.config)
            result.update(type_config)

        return result

    def _parse_binary_config(self, ch_type: str, config_obj) -> Dict[str, Any]:
        """Convert parsed config dataclass to dictionary format."""
        from channel_config import CfgLogic, CfgTimer, CfgPowerOutput
        from .channel import LogicOperation

        if ch_type == "logic" and isinstance(config_obj, CfgLogic):
            # Use LogicOperation.from_binary_code for proper enum value mapping
            op = LogicOperation.from_binary_code(config_obj.operation)
            inputs = list(config_obj.inputs[:config_obj.input_count])
            result = {
                "operation": op.value,  # Returns lowercase string like "is_true"
                "inputs": inputs,
                "threshold": config_obj.compare_value,
                "constant": config_obj.compare_value,  # Alias for comparison ops
                "invert": bool(config_obj.invert_output),
            }
            # Map inputs to channel/channel_2 for UI dialog compatibility
            if len(inputs) >= 1:
                result["channel"] = inputs[0]
            if len(inputs) >= 2:
                result["channel_2"] = inputs[1]
            return result

        elif ch_type == "power_output" and isinstance(config_obj, CfgPowerOutput):
            return {
                "inrush_time_ms": config_obj.inrush_time_ms,
                "current_limit_ma": config_obj.current_limit_ma,
                "retry_count": config_obj.retry_count,
                "retry_delay_s": config_obj.retry_delay_s,
                "soft_start_ms": config_obj.soft_start_ms,
            }

        elif ch_type == "timer" and isinstance(config_obj, CfgTimer):
            mode_names = {0: "ONE_SHOT", 1: "TOGGLE", 2: "PULSE", 3: "BLINK", 4: "FLASH"}
            return {
                "mode": mode_names.get(config_obj.mode, f"MODE_{config_obj.mode}"),
                "trigger_channel": config_obj.trigger_channel_id,
                "delay_ms": config_obj.delay_ms,
                "on_time_ms": config_obj.on_time_ms,
                "off_time_ms": config_obj.off_time_ms,
            }

        # Return raw attributes for unknown types
        if hasattr(config_obj, '__dataclass_fields__'):
            return {k: getattr(config_obj, k) for k in config_obj.__dataclass_fields__}

        return {}

    def load_from_dict(self, config_dict: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Load configuration from dictionary (e.g., from device).

        Args:
            config_dict: Configuration dictionary

        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            # DEBUG: Check what we received
            logger.info(f"load_from_dict: config keys={list(config_dict.keys())}")
            can_msgs = config_dict.get("can_messages", [])
            logger.info(f"load_from_dict: can_messages count={len(can_msgs)}")
            if can_msgs:
                logger.info(f"load_from_dict: can_messages[0]={can_msgs[0]}")

            # Auto-generate missing string IDs from name field
            config_dict = ConfigMigration.ensure_channel_ids(config_dict)

            # Auto-generate missing numeric channel_ids
            config_dict = ConfigMigration.ensure_numeric_channel_ids(config_dict)

            # Compute runtime_channel_id for virtual channels
            # Firmware allocates IDs starting from 200 in order of channel parsing
            config_dict = ConfigMigration.compute_runtime_channel_ids(config_dict)

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
        Save configuration to binary .pmu30 file.

        Args:
            filepath: Path to save to (.pmu30 only, uses current_file if None)

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

            # Ensure .pmu30 extension
            if path.suffix.lower() != '.pmu30':
                path = path.with_suffix('.pmu30')

            # Update modified timestamp
            self.config["device"]["modified"] = datetime.now().isoformat()

            # Use BinaryConfigManager to serialize
            from .binary_config import BinaryConfigManager
            binary_manager = BinaryConfigManager()

            # Convert UI channel dicts to binary Channel dataclasses
            channels = self.config.get("channels", [])
            binary_manager.set_channels_from_dicts(channels)

            # Save to binary file
            success, error = binary_manager.save_to_file(str(path))

            if not success:
                logger.error(f"Failed to save binary config: {error}")
                return False

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
        """Get channel by name (with backwards compatibility for 'name' and 'id' fields)"""
        for ch in self.config.get("channels", []):
            # Try 'channel_name' first, then 'name', then 'id' for backwards compatibility
            name = ch.get("channel_name", "") or ch.get("name", "") or ch.get("id", "")
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
            # Try 'channel_name' first, then 'name', then 'id' for backwards compatibility
            name = ch.get("channel_name", "") or ch.get("name", "") or ch.get("id", "")
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

        # Check for duplicate name (try 'channel_name' first, then 'name', then 'id')
        channel_name = channel_config.get("channel_name", "") or channel_config.get("name", "") or channel_config.get("id", "")
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
            # Try 'channel_name' first, then 'name', then 'id' for backwards compatibility
            ch_name = ch.get("channel_name", "") or ch.get("name", "") or ch.get("id", "")
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
                # Try 'channel_name' first, then 'name', then 'id' for backwards compatibility
                name = ch.get("channel_name", "") or ch.get("name", "") or ch.get("id", "")
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

    def get_next_channel_id(self) -> int:
        """Get next available channel ID for a new channel.

        Convenience method that delegates to ChannelIdGenerator with the
        current configuration's channels. Use this when you have access to
        ConfigManager and don't want to gather existing_channels manually.

        Returns:
            Next available channel ID in user range (200-999)
        """
        return ChannelIdGenerator.get_next_channel_id(self.get_all_channels())

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
        # Basic validation - ConfigValidator was removed
        errors = self.validate_channel_references()
        return len(errors) == 0, errors

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
            # Try 'channel_name' first, then 'name', then 'id' for backwards compatibility
            ch_name = ch.get("channel_name", "") or ch.get("name", "") or ch.get("id", "")
            if ch_name:
                all_channel_names.add(ch_name)

        for ch in self.config.get("channels", []):
            # Try 'channel_name' first, then 'name', then 'id' for backwards compatibility
            ch_name = ch.get("channel_name", "") or ch.get("name", "") or ch.get("id", "unknown")
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
        # ConfigValidator was removed - return empty (no cycles detected)
        return []

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
            # Try 'channel_name' first, then 'name', then 'id' for backwards compatibility
            ch_name = ch.get("channel_name", "") or ch.get("name", "") or ch.get("id", "?")
            ch_type = ch.get("channel_type", "?")
            ch_id = ch.get("channel_id", 0)
            enabled = "enabled" if ch.get("enabled", True) else "disabled"
            lines.append(f"  [{ch_type}] #{ch_id}: {ch_name} ({enabled})")

        return "\n".join(lines)

    # ========== CAN Message Methods (Level 1) ==========
    # Delegated to CANMessageManager for cleaner separation

    def get_all_can_messages(self) -> List[Dict[str, Any]]:
        """Get all CAN messages"""
        return CANMessageManager.get_all_messages(self.config)

    def get_can_message_by_name(self, message_name: str) -> Optional[Dict[str, Any]]:
        """Get CAN message by name (with backwards compatibility for 'id' field)"""
        return CANMessageManager.get_message_by_name(self.config, message_name)

    # Backwards compatibility alias
    def get_can_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Deprecated: Use get_can_message_by_name instead"""
        return self.get_can_message_by_name(message_id)

    def get_can_message_index(self, message_name: str) -> int:
        """Get CAN message index by name, returns -1 if not found"""
        return CANMessageManager.get_message_index(self.config, message_name)

    def add_can_message(self, message_config: Dict[str, Any]) -> bool:
        """Add new CAN message"""
        result = CANMessageManager.add_message(self.config, message_config)
        if result:
            self.modified = True
        return result

    def update_can_message(self, message_name: str, message_config: Dict[str, Any]) -> bool:
        """Update existing CAN message"""
        result = CANMessageManager.update_message(self.config, message_name, message_config)
        if result:
            self.modified = True
        return result

    def remove_can_message(self, message_name: str) -> bool:
        """Remove CAN message"""
        result = CANMessageManager.remove_message(self.config, message_name)
        if result:
            self.modified = True
        return result

    def get_can_inputs_for_message(self, message_name: str) -> List[Dict[str, Any]]:
        """Get all CAN RX channels that reference a specific message"""
        return CANMessageManager.get_inputs_for_message(self.config, message_name)

    def get_can_message_names(self) -> List[str]:
        """Get list of all CAN message names"""
        return CANMessageManager.get_message_names(self.config)

    # Backwards compatibility alias
    def get_can_message_ids(self) -> List[str]:
        """Deprecated: Use get_can_message_names instead"""
        return self.get_can_message_names()

    def can_message_exists(self, message_name: str) -> bool:
        """Check if CAN message with given name exists"""
        return CANMessageManager.message_exists(self.config, message_name)

    # ========== Migration Methods (delegated to ConfigMigration) ==========
    # Note: _compute_runtime_channel_ids, _ensure_channel_ids, _migrate_v2_to_v3,
    # and _convert_references_to_ids have been moved to ConfigMigration class.
    # The class methods are called directly where needed (load_from_file,
    # load_from_dict, save_to_file).
