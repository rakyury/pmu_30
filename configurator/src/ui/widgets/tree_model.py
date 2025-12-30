"""
Project Tree Model
Handles channel data storage and operations separate from the view.
"""

from typing import Dict, Any, Optional, List
from PyQt6.QtCore import QObject, pyqtSignal
from dataclasses import dataclass, field
import copy
import logging

from models.channel import ChannelType, CHANNEL_PREFIX_MAP

logger = logging.getLogger(__name__)


@dataclass
class ChannelData:
    """Wrapper for channel data with type information."""
    channel_type: ChannelType
    data: Dict[str, Any]

    @property
    def id(self) -> str:
        """Get channel ID (name or id field)."""
        return self.data.get("name", self.data.get("id", ""))

    @property
    def channel_id(self) -> int:
        """Get numeric channel ID."""
        return self.data.get("channel_id", 0)


class TreeModel(QObject):
    """
    Model for project tree data.

    Stores channels organized by type and provides CRUD operations.
    Emits signals when data changes to allow views to update.
    """

    # Signals
    channel_added = pyqtSignal(object, dict)  # (ChannelType, channel_data)
    channel_updated = pyqtSignal(str, dict)   # (channel_id, new_data)
    channel_removed = pyqtSignal(str)         # (channel_id)
    data_changed = pyqtSignal()               # General change signal
    channels_loaded = pyqtSignal()            # Bulk load completed

    def __init__(self, parent=None):
        super().__init__(parent)
        # Storage: ChannelType -> List[Dict]
        self._channels: Dict[ChannelType, List[Dict[str, Any]]] = {
            ct: [] for ct in ChannelType
        }
        self._next_channel_id = 1

    def clear(self):
        """Clear all channels."""
        for ct in ChannelType:
            self._channels[ct] = []
        self._next_channel_id = 1
        self.data_changed.emit()

    def add_channel(self, channel_type: ChannelType, data: Dict[str, Any],
                    emit_signal: bool = True) -> Dict[str, Any]:
        """
        Add a channel to the model.

        Args:
            channel_type: Type of channel
            data: Channel configuration data
            emit_signal: Whether to emit change signals

        Returns:
            The added channel data (may have been modified with channel_id)
        """
        # Ensure channel_type is in data
        data = data.copy()
        data["channel_type"] = channel_type.value

        # Assign channel_id if not present
        if "channel_id" not in data:
            data["channel_id"] = self._next_channel_id
            self._next_channel_id += 1
        else:
            # Update next_channel_id if needed
            self._next_channel_id = max(self._next_channel_id, data["channel_id"] + 1)

        self._channels[channel_type].append(data)

        if emit_signal:
            self.channel_added.emit(channel_type, data)
            self.data_changed.emit()

        return data

    def update_channel(self, channel_id: str, new_data: Dict[str, Any]) -> bool:
        """
        Update a channel by its ID (name or id field).

        Args:
            channel_id: The channel's name or id
            new_data: New configuration data

        Returns:
            True if channel was found and updated
        """
        for channel_type, channels in self._channels.items():
            for i, ch in enumerate(channels):
                ch_id = ch.get("name", ch.get("id", ""))
                if ch_id == channel_id:
                    # Preserve channel_type and channel_id
                    new_data = new_data.copy()
                    new_data["channel_type"] = channel_type.value
                    new_data["channel_id"] = ch.get("channel_id", 0)

                    self._channels[channel_type][i] = new_data
                    self.channel_updated.emit(channel_id, new_data)
                    self.data_changed.emit()
                    return True
        return False

    def remove_channel(self, channel_id: str) -> bool:
        """
        Remove a channel by its ID.

        Args:
            channel_id: The channel's name or id

        Returns:
            True if channel was found and removed
        """
        for channel_type, channels in self._channels.items():
            for i, ch in enumerate(channels):
                ch_id = ch.get("name", ch.get("id", ""))
                if ch_id == channel_id:
                    del self._channels[channel_type][i]
                    self.channel_removed.emit(channel_id)
                    self.data_changed.emit()
                    return True
        return False

    def get_channel(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a channel by its ID.

        Args:
            channel_id: The channel's name or id

        Returns:
            Channel data or None if not found
        """
        for channels in self._channels.values():
            for ch in channels:
                ch_id = ch.get("name", ch.get("id", ""))
                if ch_id == channel_id:
                    return ch.copy()
        return None

    def get_channels_by_type(self, channel_type: ChannelType) -> List[Dict[str, Any]]:
        """Get all channels of specified type."""
        return [ch.copy() for ch in self._channels.get(channel_type, [])]

    def get_all_channels(self) -> List[Dict[str, Any]]:
        """Get all channels from all types."""
        channels = []
        for channel_type in ChannelType:
            for ch in self._channels[channel_type]:
                channels.append(ch.copy())
        return channels

    def load_channels(self, channels: List[Dict[str, Any]]):
        """
        Load channels from configuration (bulk load).

        Args:
            channels: List of channel configuration dicts
        """
        self.clear()

        for ch in channels:
            channel_type_str = ch.get("channel_type", "")
            try:
                channel_type = ChannelType(channel_type_str)
                self.add_channel(channel_type, ch, emit_signal=False)
            except ValueError:
                logger.warning(f"Unknown channel type: {channel_type_str}")
                continue

        self.channels_loaded.emit()
        self.data_changed.emit()

    def duplicate_channel(self, channel_id: str, new_name: str = None) -> Optional[Dict[str, Any]]:
        """
        Duplicate a channel.

        Args:
            channel_id: ID of channel to duplicate
            new_name: Name for the copy (default: original + " (Copy)")

        Returns:
            The new channel data or None if original not found
        """
        original = self.get_channel(channel_id)
        if not original:
            return None

        # Deep copy and modify
        new_data = copy.deepcopy(original)
        new_data.pop("channel_id", None)  # Will be assigned new ID

        if new_name:
            new_data["name"] = new_name
        else:
            old_name = new_data.get("name", new_data.get("id", ""))
            new_data["name"] = f"{old_name} (Copy)"

        # Get channel type
        channel_type_str = new_data.get("channel_type", "")
        try:
            channel_type = ChannelType(channel_type_str)
        except ValueError:
            return None

        return self.add_channel(channel_type, new_data)

    def get_next_channel_id(self) -> int:
        """Get the next available channel ID."""
        return self._next_channel_id

    # ========== Pin/Resource usage tracking ==========

    def get_used_output_pins(self, exclude_channel_id: str = None) -> List[int]:
        """Get all output pins currently in use."""
        used_pins = []
        for output in self._channels.get(ChannelType.POWER_OUTPUT, []):
            ch_id = output.get('name', output.get('id', ''))
            if exclude_channel_id and ch_id == exclude_channel_id:
                continue
            pins = output.get('pins', [])
            if isinstance(pins, list):
                used_pins.extend(pins)
            elif isinstance(pins, int):
                used_pins.append(pins)
            channel = output.get('channel')
            if channel is not None and channel not in used_pins:
                used_pins.append(channel)
        return used_pins

    def get_used_analog_input_pins(self, exclude_channel_id: str = None) -> List[int]:
        """Get all analog input pins currently in use."""
        used_pins = []
        for inp in self._channels.get(ChannelType.ANALOG_INPUT, []):
            ch_id = inp.get('name', inp.get('id', ''))
            if exclude_channel_id and ch_id == exclude_channel_id:
                continue
            pin = inp.get('input_pin')
            if pin is not None:
                used_pins.append(pin)
        return used_pins

    def get_used_digital_input_pins(self, exclude_channel_id: str = None) -> List[int]:
        """Get all digital input pins currently in use."""
        used_pins = []
        for inp in self._channels.get(ChannelType.DIGITAL_INPUT, []):
            ch_id = inp.get('name', inp.get('id', ''))
            if exclude_channel_id and ch_id == exclude_channel_id:
                continue
            pin = inp.get('input_pin')
            if pin is not None:
                used_pins.append(pin)
        return used_pins

    def get_used_hbridge_numbers(self, exclude_channel_id: str = None) -> List[int]:
        """Get all H-Bridge numbers currently in use."""
        used_bridges = []
        for hb in self._channels.get(ChannelType.HBRIDGE, []):
            ch_id = hb.get('name', hb.get('id', ''))
            if exclude_channel_id and ch_id == exclude_channel_id:
                continue
            bridge = hb.get('bridge_number')
            if bridge is not None:
                used_bridges.append(bridge)
        return used_bridges

    # ========== Type-specific getters (for compatibility) ==========

    def get_outputs(self) -> List[Dict[str, Any]]:
        return self.get_channels_by_type(ChannelType.POWER_OUTPUT)

    def get_inputs(self) -> List[Dict[str, Any]]:
        return (self.get_channels_by_type(ChannelType.DIGITAL_INPUT) +
                self.get_channels_by_type(ChannelType.ANALOG_INPUT))

    def get_logic_functions(self) -> List[Dict[str, Any]]:
        return self.get_channels_by_type(ChannelType.LOGIC)

    def get_numbers(self) -> List[Dict[str, Any]]:
        return self.get_channels_by_type(ChannelType.NUMBER)

    def get_switches(self) -> List[Dict[str, Any]]:
        return self.get_channels_by_type(ChannelType.SWITCH)

    def get_tables(self) -> List[Dict[str, Any]]:
        return (self.get_channels_by_type(ChannelType.TABLE_2D) +
                self.get_channels_by_type(ChannelType.TABLE_3D))

    def get_timers(self) -> List[Dict[str, Any]]:
        return self.get_channels_by_type(ChannelType.TIMER)

    def get_hbridges(self) -> List[Dict[str, Any]]:
        return self.get_channels_by_type(ChannelType.HBRIDGE)

    def get_pid_controllers(self) -> List[Dict[str, Any]]:
        return self.get_channels_by_type(ChannelType.PID)

    def get_lua_scripts(self) -> List[Dict[str, Any]]:
        return self.get_channels_by_type(ChannelType.LUA_SCRIPT)

    def get_blinkmarine_keypads(self) -> List[Dict[str, Any]]:
        return self.get_channels_by_type(ChannelType.BLINKMARINE_KEYPAD)

    def get_can_inputs(self) -> List[Dict[str, Any]]:
        return self.get_channels_by_type(ChannelType.CAN_RX)

    def get_can_outputs(self) -> List[Dict[str, Any]]:
        return self.get_channels_by_type(ChannelType.CAN_TX)

    def get_handlers(self) -> List[Dict[str, Any]]:
        return self.get_channels_by_type(ChannelType.HANDLER)
