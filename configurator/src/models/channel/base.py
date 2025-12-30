"""
Channel Base - Base class and utilities for all channels

This module contains the ChannelBase class and utility functions.
"""

from dataclasses import dataclass
from typing import List, Dict, Any

from .enums import ChannelType


@dataclass
class ChannelBase:
    """Base class for all channels.

    Architecture:
    - channel_id: Numeric, unique identifier (0-65535), auto-generated, NOT editable
    - name: User-defined string, editable, unique, used for display and references
    """
    name: str  # User-editable identifier (was 'id')
    channel_type: ChannelType
    channel_id: int = 0  # Numeric unique ID, auto-generated

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "channel_id": self.channel_id,
            "channel_name": self.name,
            "channel_type": self.channel_type.value
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChannelBase':
        """Create from dictionary"""
        # Use 'channel_name' field (current format)
        name = data.get("channel_name", "")
        if not name:
            raise ValueError("Channel missing required 'channel_name' field")
        return cls(
            name=name,
            channel_type=ChannelType(data.get("channel_type", "digital_input")),
            channel_id=data.get("channel_id", 0)
        )

    def validate(self) -> List[str]:
        """Validate configuration, return list of errors"""
        errors = []
        if not self.name:
            errors.append("Name is required")
        return errors

    def get_output_channels(self) -> List[str]:
        """Get list of channels this channel outputs"""
        return [self.name]

    def get_input_channels(self) -> List[str]:
        """Get list of channels this channel reads from"""
        return []


# ============================================================================
# Channel Prefix Map and Utility Functions
# ============================================================================

CHANNEL_PREFIX_MAP = {
    ChannelType.DIGITAL_INPUT: "di_",
    ChannelType.ANALOG_INPUT: "ai_",
    ChannelType.POWER_OUTPUT: "out_",
    ChannelType.HBRIDGE: "hb_",
    ChannelType.LOGIC: "l_",
    ChannelType.NUMBER: "n_",
    ChannelType.TIMER: "tm_",
    ChannelType.FILTER: "flt_",
    ChannelType.TABLE_2D: "t2d_",
    ChannelType.TABLE_3D: "t3d_",
    ChannelType.SWITCH: "sw_",
    ChannelType.CAN_RX: "crx_",
    ChannelType.CAN_TX: "ctx_",
    ChannelType.LUA_SCRIPT: "lua_",
    ChannelType.PID: "pid_",
    ChannelType.HANDLER: "h_",
}


def get_channel_prefix(channel_type: ChannelType) -> str:
    """Get standard prefix for channel type"""
    return CHANNEL_PREFIX_MAP.get(channel_type, "")


def get_channel_display_name(channel_type: ChannelType) -> str:
    """Get human-readable name for channel type"""
    names = {
        ChannelType.DIGITAL_INPUT: "Digital Input",
        ChannelType.ANALOG_INPUT: "Analog Input",
        ChannelType.POWER_OUTPUT: "Power Output",
        ChannelType.HBRIDGE: "H-Bridge Motor",
        ChannelType.LOGIC: "Logic Function",
        ChannelType.NUMBER: "Math/Number",
        ChannelType.TIMER: "Timer",
        ChannelType.FILTER: "Filter",
        ChannelType.TABLE_2D: "2D Table",
        ChannelType.TABLE_3D: "3D Table",
        ChannelType.SWITCH: "Switch",
        ChannelType.CAN_RX: "CAN Input",
        ChannelType.CAN_TX: "CAN Output",
        ChannelType.LUA_SCRIPT: "Lua Script",
        ChannelType.PID: "PID Controller",
        ChannelType.HANDLER: "Event Handler",
    }
    return names.get(channel_type, channel_type.value)
