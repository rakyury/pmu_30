"""
CAN Message Management Module

Handles CAN message CRUD operations for PMU-30 configurations.
Extracted from ConfigManager for better separation of concerns.
"""

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class CANMessageManager:
    """Manages CAN message operations on a configuration dictionary.

    This class provides static methods that operate on a config dict,
    allowing ConfigManager to delegate CAN operations cleanly.
    """

    @staticmethod
    def get_all_messages(config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get all CAN messages from config."""
        return config.get("can_messages", [])

    @staticmethod
    def get_message_by_name(config: Dict[str, Any], message_name: str) -> Optional[Dict[str, Any]]:
        """Get CAN message by name (with backwards compatibility for 'id' field)."""
        for msg in config.get("can_messages", []):
            name = msg.get("name", "") or msg.get("id", "")
            if name == message_name:
                return msg
        return None

    @staticmethod
    def get_message_index(config: Dict[str, Any], message_name: str) -> int:
        """Get CAN message index by name, returns -1 if not found."""
        for i, msg in enumerate(config.get("can_messages", [])):
            name = msg.get("name", "") or msg.get("id", "")
            if name == message_name:
                return i
        return -1

    @staticmethod
    def add_message(config: Dict[str, Any], message_config: Dict[str, Any]) -> bool:
        """Add new CAN message to config."""
        if "can_messages" not in config:
            config["can_messages"] = []

        message_name = message_config.get("name", "") or message_config.get("id", "")
        if CANMessageManager.get_message_by_name(config, message_name):
            logger.error(f"CAN message with name '{message_name}' already exists")
            return False

        config["can_messages"].append(message_config)
        logger.info(f"Added CAN message: {message_name}")
        return True

    @staticmethod
    def update_message(config: Dict[str, Any], message_name: str, message_config: Dict[str, Any]) -> bool:
        """Update existing CAN message in config."""
        index = CANMessageManager.get_message_index(config, message_name)
        if index < 0:
            logger.error(f"CAN message '{message_name}' not found")
            return False

        config["can_messages"][index] = message_config
        logger.info(f"Updated CAN message: {message_name}")
        return True

    @staticmethod
    def remove_message(config: Dict[str, Any], message_name: str) -> bool:
        """Remove CAN message from config."""
        index = CANMessageManager.get_message_index(config, message_name)
        if index < 0:
            logger.error(f"CAN message '{message_name}' not found")
            return False

        config["can_messages"].pop(index)
        logger.info(f"Removed CAN message: {message_name}")
        return True

    @staticmethod
    def get_inputs_for_message(config: Dict[str, Any], message_name: str) -> List[Dict[str, Any]]:
        """Get all CAN RX channels that reference a specific message."""
        can_inputs = []
        for ch in config.get("channels", []):
            if ch.get("channel_type") == "can_rx" and ch.get("message_ref") == message_name:
                can_inputs.append(ch)
        return can_inputs

    @staticmethod
    def get_message_names(config: Dict[str, Any]) -> List[str]:
        """Get list of all CAN message names."""
        result = []
        for msg in config.get("can_messages", []):
            name = msg.get("name", "") or msg.get("id", "")
            if name:
                result.append(name)
        return result

    @staticmethod
    def message_exists(config: Dict[str, Any], message_name: str) -> bool:
        """Check if CAN message with given name exists."""
        return CANMessageManager.get_message_by_name(config, message_name) is not None
