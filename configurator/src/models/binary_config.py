"""
PMU-30 Binary Configuration Manager
Version 4.0 - Binary-only format, no JSON

Owner: R2 m-sport

Uses shared library channel_config.py for binary serialization.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import time

# Add shared library to path
shared_path = Path(__file__).parent.parent.parent.parent / "shared" / "python"
if str(shared_path) not in sys.path:
    sys.path.insert(0, str(shared_path))

from channel_config import (
    ConfigFile, Channel, CfgChannelHeader, CfgFileHeader,
    ChannelType, ChannelFlags, HwDevice,
    CfgLogic, CfgMath, CfgTimer, CfgFilter, CfgPid,
    CfgPowerOutput, CfgDigitalInput, CfgAnalogInput,
    CfgTable2D, CfgNumber, CfgCanInput, CfgFrequencyInput,
    CFG_MAGIC, CFG_VERSION, CH_REF_NONE
)

logger = logging.getLogger(__name__)


class BinaryConfigManager:
    """Manages PMU-30 configuration in binary format only"""

    # Device types
    DEVICE_PMU30 = 0x0030
    DEVICE_PMU16 = 0x0016

    def __init__(self):
        self.config = ConfigFile(device_type=self.DEVICE_PMU30)
        self.current_file: Optional[Path] = None
        self.modified: bool = False
        self._channel_map: Dict[int, Channel] = {}  # id -> Channel

    @property
    def channels(self) -> List[Channel]:
        """Get all channels"""
        return self.config.channels

    def new_config(self) -> None:
        """Create new empty configuration"""
        self.config = ConfigFile(
            device_type=self.DEVICE_PMU30,
            timestamp=int(time.time())
        )
        self.current_file = None
        self.modified = False
        self._channel_map.clear()
        logger.info("Created new binary configuration")

    def set_channels_from_dicts(self, channel_dicts: List[Dict]) -> None:
        """
        Convert UI channel dictionaries to binary Channel dataclasses.

        Args:
            channel_dicts: List of channel configuration dictionaries from UI
        """
        from .channel import LogicOperation as UILogicOp

        self.config.channels.clear()
        self._channel_map.clear()

        for ch_dict in channel_dicts:
            ch_type_str = ch_dict.get("channel_type", "")
            ch_id = ch_dict.get("channel_id", 0)
            ch_name = ch_dict.get("name", "") or ch_dict.get("channel_name", "") or ch_dict.get("id", "")
            enabled = ch_dict.get("enabled", True)

            # Map UI channel type to binary ChannelType
            type_map = {
                "power_output": ChannelType.POWER_OUTPUT,
                "logic": ChannelType.LOGIC,
                "timer": ChannelType.TIMER,
                "digital_input": ChannelType.DIGITAL_INPUT,
                "analog_input": ChannelType.ANALOG_INPUT,
                "filter": ChannelType.FILTER,
                "number": ChannelType.NUMBER,
                "table_2d": ChannelType.TABLE_2D,
                "table_3d": ChannelType.TABLE_3D,
                "pid": ChannelType.PID,
                "switch": ChannelType.SWITCH,
            }

            binary_type = type_map.get(ch_type_str)
            if not binary_type:
                logger.warning(f"Unknown channel type: {ch_type_str}, skipping")
                continue

            # Build config object based on type
            config_obj = None

            if ch_type_str == "logic":
                # Get operation as binary code
                op_str = ch_dict.get("operation", "is_true")
                try:
                    op_enum = UILogicOp(op_str)
                    op_code = op_enum.binary_code
                except ValueError:
                    op_code = 0x06  # Default to IS_TRUE

                inputs = ch_dict.get("inputs", [])
                if not inputs and ch_dict.get("channel"):
                    inputs = [ch_dict.get("channel")]
                if ch_dict.get("channel_2"):
                    inputs.append(ch_dict.get("channel_2"))

                config_obj = CfgLogic(
                    operation=op_code,
                    input_count=len(inputs),
                    inputs=tuple(inputs + [0] * (8 - len(inputs))),
                    compare_value=int(ch_dict.get("threshold", 0) or ch_dict.get("constant", 0)),
                    invert_output=ch_dict.get("invert", False),
                )

            elif ch_type_str == "power_output":
                config_obj = CfgPowerOutput(
                    inrush_time_ms=ch_dict.get("inrush_time_ms", 100),
                    current_limit_ma=ch_dict.get("current_limit_ma", 10000),
                    retry_count=ch_dict.get("retry_count", 3),
                    retry_delay_s=ch_dict.get("retry_delay_s", 1),
                    soft_start_ms=ch_dict.get("soft_start_ms", 0),
                )

            elif ch_type_str == "timer":
                mode_map = {"oneshot": 0, "toggle": 1, "pulse": 2, "blink": 3, "flash": 4}
                mode = mode_map.get(ch_dict.get("mode", "oneshot"), 0)
                config_obj = CfgTimer(
                    mode=mode,
                    trigger_channel_id=ch_dict.get("trigger_channel", 0xFFFF),
                    delay_ms=ch_dict.get("delay_ms", 0),
                    on_time_ms=ch_dict.get("on_time_ms", 1000),
                    off_time_ms=ch_dict.get("off_time_ms", 1000),
                )

            # Create Channel dataclass
            source_id = ch_dict.get("source_channel", CH_REF_NONE)
            if isinstance(source_id, str):
                source_id = CH_REF_NONE  # Need to resolve name to ID

            hw_index = ch_dict.get("hw_index", 0) or 0
            hw_device = ch_dict.get("hw_device", 0) or 0

            channel = Channel(
                id=ch_id,
                type=binary_type,
                flags=ChannelFlags.ENABLED if enabled else 0,
                hw_device=hw_device,
                hw_index=hw_index,
                source_id=source_id if isinstance(source_id, int) else CH_REF_NONE,
                default_value=ch_dict.get("default_value", 0),
                name=ch_name[:31] if ch_name else "",
                config=config_obj,
            )

            self.config.channels.append(channel)
            self._channel_map[ch_id] = channel

        self.modified = True
        logger.info(f"Loaded {len(self.config.channels)} channels from UI dicts")

    def load_from_file(self, filepath: str) -> Tuple[bool, Optional[str]]:
        """
        Load configuration from binary file (.pmu30 extension)

        Auto-detects format:
        - Full format: has CFG_MAGIC header (0x43464733)
        - Raw format: starts with channel count (firmware GET_CONFIG format)

        Args:
            filepath: Path to binary configuration file

        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        import struct

        try:
            path = Path(filepath)

            if not path.exists():
                return False, f"Configuration file not found: {filepath}"

            with open(path, "rb") as f:
                data = f.read()

            if len(data) < 4:
                return False, "File too small"

            # Check if this is full format (starts with CFG_MAGIC)
            magic = struct.unpack("<I", data[:4])[0]
            if magic == CFG_MAGIC:
                # Full ConfigFile format
                self.config = ConfigFile.deserialize(data)
                logger.info("Loaded full ConfigFile format")
            else:
                # Raw format (channel count + channel data)
                success, error = self.load_from_raw_bytes(data)
                if not success:
                    return False, error
                logger.info("Loaded raw channel format")

            self.current_file = path
            self.modified = False

            # Build channel map
            self._channel_map = {ch.id: ch for ch in self.config.channels}

            logger.info(f"Loaded binary config from: {filepath}")
            logger.info(f"  Channels: {len(self.config.channels)}")

            return True, None

        except ValueError as e:
            error_msg = f"Invalid binary config: {e}"
            logger.error(error_msg)
            return False, error_msg

        except Exception as e:
            error_msg = f"Failed to load configuration: {e}"
            logger.error(error_msg)
            return False, error_msg

    def load_from_bytes(self, data: bytes) -> Tuple[bool, Optional[str]]:
        """
        Load configuration from bytes (full file format with header)

        Args:
            data: Binary configuration data with file header

        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            self.config = ConfigFile.deserialize(data)
            self.current_file = None
            self.modified = False

            # Build channel map
            self._channel_map = {ch.id: ch for ch in self.config.channels}

            logger.info(f"Loaded binary config from device")
            logger.info(f"  Channels: {len(self.config.channels)}")

            return True, None

        except ValueError as e:
            return False, f"Invalid binary config: {e}"

        except Exception as e:
            return False, f"Failed to load configuration: {e}"

    def load_from_raw_bytes(self, data: bytes) -> Tuple[bool, Optional[str]]:
        """
        Load configuration from raw channel data (no file header).

        This is the format sent by firmware via GET_CONFIG:
        [2 bytes] channel_count (LE)
        For each channel:
          CfgChannelHeader (14 bytes)
          name (name_len bytes)
          config (config_size bytes)

        Args:
            data: Raw channel data without file header

        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        import struct

        try:
            if len(data) < 2:
                return False, "Data too short for channel count"

            # Read channel count
            channel_count = struct.unpack('<H', data[:2])[0]
            offset = 2

            channels = []
            for i in range(channel_count):
                if offset >= len(data):
                    return False, f"Unexpected end of data at channel {i}"

                try:
                    channel, consumed = Channel.deserialize(data[offset:])
                    channels.append(channel)
                    offset += consumed
                except Exception as e:
                    return False, f"Failed to parse channel {i}: {e}"

            # Create new config with parsed channels
            self.config = ConfigFile(
                device_type=self.DEVICE_PMU30,
                channels=channels
            )
            self.current_file = None
            self.modified = False

            # Build channel map
            self._channel_map = {ch.id: ch for ch in self.config.channels}

            logger.info(f"Loaded raw binary config from device")
            logger.info(f"  Channels: {len(channels)}")

            return True, None

        except struct.error as e:
            return False, f"Binary parse error: {e}"

        except Exception as e:
            return False, f"Failed to load raw configuration: {e}"

    def save_to_file(self, filepath: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Save configuration to binary file

        Args:
            filepath: Path to save to (uses current_file if None)

        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            if filepath:
                path = Path(filepath)
            elif self.current_file:
                path = self.current_file
            else:
                return False, "No filepath specified"

            # Update timestamp
            self.config.timestamp = int(time.time())

            # Save
            self.config.save(str(path))

            self.current_file = path
            self.modified = False

            logger.info(f"Saved binary config to: {path}")
            return True, None

        except Exception as e:
            error_msg = f"Failed to save configuration: {e}"
            logger.error(error_msg)
            return False, error_msg

    def to_bytes(self) -> bytes:
        """
        Serialize configuration to bytes (for sending to device)

        Returns:
            Binary configuration data
        """
        self.config.timestamp = int(time.time())
        return self.config.serialize()

    # ========================================================================
    # Channel Management
    # ========================================================================

    def add_channel(self, channel: Channel) -> bool:
        """Add a channel to the configuration"""
        if channel.id in self._channel_map:
            logger.warning(f"Channel {channel.id} already exists, replacing")
            self.remove_channel(channel.id)

        self.config.channels.append(channel)
        self._channel_map[channel.id] = channel
        self.modified = True
        return True

    def remove_channel(self, channel_id: int) -> bool:
        """Remove a channel by ID"""
        if channel_id not in self._channel_map:
            return False

        self.config.channels = [ch for ch in self.config.channels if ch.id != channel_id]
        del self._channel_map[channel_id]
        self.modified = True
        return True

    def get_channel(self, channel_id: int) -> Optional[Channel]:
        """Get channel by ID"""
        return self._channel_map.get(channel_id)

    def get_channel_by_name(self, name: str) -> Optional[Channel]:
        """Get channel by name"""
        for ch in self.config.channels:
            if ch.name == name:
                return ch
        return None

    def update_channel(self, channel: Channel) -> bool:
        """Update an existing channel"""
        if channel.id not in self._channel_map:
            return False

        # Replace in list
        for i, ch in enumerate(self.config.channels):
            if ch.id == channel.id:
                self.config.channels[i] = channel
                break

        self._channel_map[channel.id] = channel
        self.modified = True
        return True

    def get_next_channel_id(self, channel_type: ChannelType) -> int:
        """
        Get next available channel ID for a given type

        Channel ID ranges:
        - 0-99: Physical inputs
        - 100-199: Physical outputs
        - 200-999: Virtual channels
        - 1000-1023: System channels
        """
        if channel_type in (ChannelType.DIGITAL_INPUT, ChannelType.ANALOG_INPUT,
                           ChannelType.FREQUENCY_INPUT, ChannelType.CAN_INPUT):
            base, max_id = 0, 99
        elif channel_type in (ChannelType.POWER_OUTPUT, ChannelType.PWM_OUTPUT,
                             ChannelType.HBRIDGE, ChannelType.CAN_OUTPUT):
            base, max_id = 100, 199
        else:
            base, max_id = 200, 999

        used = {ch.id for ch in self.config.channels if base <= ch.id <= max_id}

        for i in range(base, max_id + 1):
            if i not in used:
                return i

        raise ValueError(f"No available channel IDs in range {base}-{max_id}")

    # ========================================================================
    # Filtering and Queries
    # ========================================================================

    def get_channels_by_type(self, channel_type: ChannelType) -> List[Channel]:
        """Get all channels of a specific type"""
        return [ch for ch in self.config.channels if ch.type == channel_type]

    def get_input_channels(self) -> List[Channel]:
        """Get all input channels"""
        input_types = {
            ChannelType.DIGITAL_INPUT, ChannelType.ANALOG_INPUT,
            ChannelType.FREQUENCY_INPUT, ChannelType.CAN_INPUT
        }
        return [ch for ch in self.config.channels if ch.type in input_types]

    def get_output_channels(self) -> List[Channel]:
        """Get all output channels"""
        output_types = {
            ChannelType.POWER_OUTPUT, ChannelType.PWM_OUTPUT,
            ChannelType.HBRIDGE, ChannelType.CAN_OUTPUT
        }
        return [ch for ch in self.config.channels if ch.type in output_types]

    def get_virtual_channels(self) -> List[Channel]:
        """Get all virtual/calculated channels"""
        virtual_types = {
            ChannelType.LOGIC, ChannelType.MATH, ChannelType.TIMER,
            ChannelType.FILTER, ChannelType.PID, ChannelType.TABLE_2D,
            ChannelType.TABLE_3D, ChannelType.NUMBER, ChannelType.SWITCH,
            ChannelType.ENUM, ChannelType.COUNTER, ChannelType.HYSTERESIS,
            ChannelType.FLIPFLOP
        }
        return [ch for ch in self.config.channels if ch.type in virtual_types]

    # ========================================================================
    # Factory Methods for Creating Channels
    # ========================================================================

    def create_logic_channel(
        self,
        name: str,
        operation: int,
        inputs: List[int],
        compare_value: int = 0,
        invert: bool = False
    ) -> Channel:
        """Create a logic channel"""
        channel_id = self.get_next_channel_id(ChannelType.LOGIC)

        config = CfgLogic(
            operation=operation,
            input_count=len(inputs),
            inputs=inputs,
            compare_value=compare_value,
            invert_output=1 if invert else 0
        )

        return Channel(
            id=channel_id,
            type=ChannelType.LOGIC,
            flags=ChannelFlags.ENABLED,
            name=name,
            config=config
        )

    def create_math_channel(
        self,
        name: str,
        operation: int,
        inputs: List[int],
        constant: int = 0,
        min_value: int = -2147483648,
        max_value: int = 2147483647
    ) -> Channel:
        """Create a math channel"""
        channel_id = self.get_next_channel_id(ChannelType.MATH)

        config = CfgMath(
            operation=operation,
            input_count=len(inputs),
            inputs=inputs,
            constant=constant,
            min_value=min_value,
            max_value=max_value
        )

        return Channel(
            id=channel_id,
            type=ChannelType.MATH,
            flags=ChannelFlags.ENABLED,
            name=name,
            config=config
        )

    def create_timer_channel(
        self,
        name: str,
        trigger_id: int,
        delay_ms: int,
        mode: int = 0,
        trigger_mode: int = 0
    ) -> Channel:
        """Create a timer channel"""
        channel_id = self.get_next_channel_id(ChannelType.TIMER)

        config = CfgTimer(
            mode=mode,
            trigger_mode=trigger_mode,
            trigger_id=trigger_id,
            delay_ms=delay_ms
        )

        return Channel(
            id=channel_id,
            type=ChannelType.TIMER,
            flags=ChannelFlags.ENABLED,
            name=name,
            config=config
        )

    def create_power_output(
        self,
        name: str,
        hw_index: int,
        source_id: int = CH_REF_NONE,
        current_limit_ma: int = 10000
    ) -> Channel:
        """Create a power output channel"""
        channel_id = self.get_next_channel_id(ChannelType.POWER_OUTPUT)

        config = CfgPowerOutput(
            current_limit_ma=current_limit_ma
        )

        return Channel(
            id=channel_id,
            type=ChannelType.POWER_OUTPUT,
            flags=ChannelFlags.ENABLED,
            hw_device=HwDevice.PROFET,
            hw_index=hw_index,
            source_id=source_id,
            name=name,
            config=config
        )

    # ========================================================================
    # Single Channel Serialization (for atomic updates)
    # ========================================================================

    def serialize_single_channel(self, channel_dict: Dict, channel_lookup: Dict[str, int] = None) -> bytes:
        """
        Serialize a single channel to binary format for atomic updates.

        This is used by DeviceController.update_channel_config() to send
        a single channel update without re-uploading the entire configuration.

        Format matches firmware expectation:
        - CfgChannelHeader (14 bytes): id + type + flags + hw + source_id + default + name_len + config_size
        - name (name_len bytes)
        - config (config_size bytes)

        Args:
            channel_dict: Channel configuration dictionary from UI
            channel_lookup: Optional dict mapping channel names to IDs for reference resolution

        Returns:
            Binary data for SET_CHANNEL_CONFIG command
        """
        import struct
        global _channel_name_to_id

        # Temporarily set global lookup if provided
        if channel_lookup:
            _channel_name_to_id = channel_lookup

        # Channel type mapping
        ALL_CHANNEL_TYPES = {
            "digital_input": ChannelType.DIGITAL_INPUT,
            "analog_input": ChannelType.ANALOG_INPUT,
            "frequency_input": ChannelType.FREQUENCY_INPUT,
            "can_rx": ChannelType.CAN_INPUT,
            "power_output": ChannelType.POWER_OUTPUT,
            "pwm_output": ChannelType.PWM_OUTPUT,
            "hbridge": ChannelType.HBRIDGE,
            "can_tx": ChannelType.CAN_OUTPUT,
            "timer": ChannelType.TIMER,
            "logic": ChannelType.LOGIC,
            "math": ChannelType.MATH,
            "filter": ChannelType.FILTER,
            "pid": ChannelType.PID,
            "table_2d": ChannelType.TABLE_2D,
            "table_3d": ChannelType.TABLE_3D,
            "switch": ChannelType.SWITCH,
            "number": ChannelType.NUMBER,
            "counter": ChannelType.COUNTER,
            "hysteresis": ChannelType.HYSTERESIS,
            "flipflop": ChannelType.FLIPFLOP,
        }

        ch_type_str = channel_dict.get("channel_type", "") or channel_dict.get("type", "")
        ch_type = ALL_CHANNEL_TYPES.get(ch_type_str)

        if ch_type is None:
            raise ValueError(f"Unknown channel type: {ch_type_str}")

        channel_id = channel_dict.get("channel_id")
        if channel_id is None:
            raise ValueError("Channel must have channel_id")

        # Get channel name (max 31 chars)
        name = channel_dict.get("name", "") or channel_dict.get("channel_name", "") or ""
        name_bytes = name.encode('utf-8')[:31]
        name_len = len(name_bytes)

        # Get common fields
        flags = 0x01 if channel_dict.get("enabled", True) else 0x00
        source_id = channel_dict.get("source_channel", 0xFFFF)
        if source_id is None or source_id == "" or not isinstance(source_id, int):
            source_id = 0xFFFF  # CH_REF_NONE
        default_value = 0

        # Get hardware info
        hw_device = 0  # NONE
        hw_index = 0
        pins = channel_dict.get("pins", [])

        # Set hw_device and hw_index based on channel type
        if ch_type_str == "digital_input":
            hw_device = 0x01  # GPIO
            hw_index = pins[0] if pins else 0
        elif ch_type_str == "analog_input":
            hw_device = 0x02  # ADC
            hw_index = pins[0] if pins else 0
        elif ch_type_str == "power_output":
            hw_device = 0x05  # PROFET
            hw_index = pins[0] if pins else 0
        elif ch_type_str == "pwm_output":
            hw_device = 0x06  # PWM
            hw_index = pins[0] if pins else 0
        elif ch_type_str == "hbridge":
            hw_device = 0x07  # HBRIDGE
            hw_index = pins[0] if pins else 0

        # Get type-specific config bytes
        config_bytes = _ui_config_to_binary(ch_type_str, channel_dict) or b''
        config_size = len(config_bytes)

        # Build 14-byte CfgChannelHeader_t
        header = struct.pack('<HBBBBHiBB',
            int(channel_id),    # id: 2B
            int(ch_type),       # type: 1B
            flags,              # flags: 1B
            hw_device,          # hw_device: 1B
            hw_index,           # hw_index: 1B
            source_id,          # source_id: 2B
            default_value,      # default_value: 4B (signed)
            name_len,           # name_len: 1B
            config_size         # config_size: 1B
        )

        logger.debug(f"Serialized single channel {channel_id} ({ch_type_str}): "
                     f"header={len(header)}B, name={name_len}B, config={config_size}B")

        return header + name_bytes + config_bytes

    # ========================================================================
    # Statistics
    # ========================================================================

    def get_stats(self) -> Dict[str, int]:
        """Get configuration statistics"""
        stats = {
            "total_channels": len(self.config.channels),
            "inputs": len(self.get_input_channels()),
            "outputs": len(self.get_output_channels()),
            "virtual": len(self.get_virtual_channels()),
            "size_bytes": len(self.to_bytes())
        }
        return stats

    # ========================================================================
    # Channel Executor Serialization (Simplified Format)
    # ========================================================================

    def serialize_for_executor(self) -> bytes:
        """
        Serialize virtual channels for PMU_ChannelExec_LoadConfig.

        Simplified format (no file header, no channel names):
        [2 bytes] channel_count (LE)
        For each channel:
          [2 bytes] channel_id (LE)
          [1 byte]  type (ChannelType_t)
          [1 byte]  config_size
          [N bytes] config_data

        Returns:
            Binary data for LOAD_BINARY_CONFIG command
        """
        import struct

        virtual_channels = self.get_virtual_channels()
        channel_data = []

        for ch in virtual_channels:
            if ch.config is None:
                continue

            # Serialize config
            config_bytes = ch.config.pack()
            config_size = len(config_bytes)

            # Channel header: id (2B) + type (1B) + size (1B)
            header = struct.pack('<HBB', ch.id, ch.type, config_size)
            channel_data.append(header + config_bytes)

        # Build final binary: [count:2B LE][channel_data...]
        channel_count = len(channel_data)
        result = struct.pack('<H', channel_count)
        for data in channel_data:
            result += data

        logger.debug(f"Serialized {channel_count} channels for executor ({len(result)} bytes)")
        return result


# ============================================================================
# UI Config to Binary Converter (for device_mixin.py integration)
# ============================================================================

# Module-level lookup table for channel name -> ID resolution
# Set before serialization, cleared after
_channel_name_to_id: Dict[str, int] = {}


def serialize_ui_channels_for_executor(channels: List[Dict]) -> bytes:
    """
    Convert UI channel configs to binary format for device storage.

    Includes ALL channel types (not just executor types) so that GET_CONFIG
    returns the complete configuration including Digital Inputs, Analog Inputs, etc.

    Args:
        channels: List of channel dicts from UI (project_tree.get_all_channels())

    Returns:
        Binary data for LOAD_BINARY_CONFIG command

    Note:
        All channel types are serialized with names for persistence.
        Channel Executor only processes virtual channel types, but all
        types are stored so GET_CONFIG returns the complete config.
    """
    global _channel_name_to_id
    import struct

    # Build name-to-ID lookup table for all channels
    # This allows resolving channel references like "Digital Input 1" to their IDs
    _channel_name_to_id = {}
    for ch in channels:
        ch_id = ch.get("channel_id")
        if ch_id is not None:
            # Add by name
            name = ch.get("name") or ch.get("channel_name", "")
            if name:
                _channel_name_to_id[name] = ch_id
            # Also add by id string (for backwards compatibility)
            ch_id_str = ch.get("id", "")
            if ch_id_str:
                _channel_name_to_id[str(ch_id_str)] = ch_id

    logger.debug(f"Built channel lookup with {len(_channel_name_to_id)} entries")

    # ALL channel types for complete config persistence
    ALL_CHANNEL_TYPES = {
        # Hardware inputs
        "digital_input": ChannelType.DIGITAL_INPUT,
        "analog_input": ChannelType.ANALOG_INPUT,
        "frequency_input": ChannelType.FREQUENCY_INPUT,
        "can_rx": ChannelType.CAN_INPUT,
        # Hardware outputs
        "power_output": ChannelType.POWER_OUTPUT,
        "pwm_output": ChannelType.PWM_OUTPUT,
        "hbridge": ChannelType.HBRIDGE,
        "can_tx": ChannelType.CAN_OUTPUT,
        # Virtual channels (processed by Channel Executor)
        "timer": ChannelType.TIMER,
        "logic": ChannelType.LOGIC,
        "math": ChannelType.MATH,
        "filter": ChannelType.FILTER,
        "pid": ChannelType.PID,
        "table_2d": ChannelType.TABLE_2D,
        "table_3d": ChannelType.TABLE_3D,
        "switch": ChannelType.SWITCH,
        "number": ChannelType.NUMBER,
        "counter": ChannelType.COUNTER,
        "hysteresis": ChannelType.HYSTERESIS,
        "flipflop": ChannelType.FLIPFLOP,
    }

    channel_data = []

    # First pass: collect all referenced channel IDs
    referenced_ids = set()
    for ch in channels:
        ch_type = ch.get("channel_type", "")
        if ch_type == "logic":
            for ref in ch.get("input_channels", []):
                if isinstance(ref, int) and ref > 0:
                    referenced_ids.add(ref)
        elif ch_type in ("timer", "filter", "table_2d", "table_3d"):
            for key in ("input_channel", "start_channel", "x_axis_channel"):
                ref = ch.get(key)
                if isinstance(ref, int) and ref > 0:
                    referenced_ids.add(ref)
        elif ch_type == "pid":
            for key in ("setpoint_channel", "feedback_channel"):
                ref = ch.get(key)
                if isinstance(ref, int) and ref > 0:
                    referenced_ids.add(ref)
        elif ch_type == "power_output":
            ref = ch.get("source_id")
            if isinstance(ref, int) and ref > 0:
                referenced_ids.add(ref)

    for ch in channels:
        # Include system channels if they are referenced by other channels
        if ch.get("system", False):
            ch_id = ch.get("channel_id")
            if ch_id not in referenced_ids:
                continue  # Skip unreferenced system channels
            # Referenced system channel - include it
            logger.debug(f"Including referenced system channel: {ch.get('name')} (id={ch_id})")

        ch_type_str = ch.get("channel_type", "") or ch.get("type", "")
        ch_type = ALL_CHANNEL_TYPES.get(ch_type_str)

        if ch_type is None:
            logger.debug(f"Skipping unknown channel type: {ch_type_str}")
            continue

        channel_id = ch.get("channel_id")
        if channel_id is None:
            continue

        # Get channel name for persistence (max 31 chars)
        name = ch.get("name", "") or ch.get("channel_name", "") or ""
        name_bytes = name.encode('utf-8')[:31]
        name_len = len(name_bytes)

        # Get common fields
        flags = 0x01 if ch.get("enabled", True) else 0x00
        source_ref = ch.get("source_channel", 0xFFFF)
        # Resolve channel name to ID using lookup table
        source_id = _get_channel_ref(source_ref) if source_ref else 0xFFFF
        default_value = 0

        # Get hardware info
        hw_device = 0  # NONE
        hw_index = 0
        pins = ch.get("pins", [])

        # Set hw_device and hw_index based on channel type
        if ch_type_str == "digital_input":
            hw_device = 0x01  # GPIO
            hw_index = pins[0] if pins else 0
        elif ch_type_str == "analog_input":
            hw_device = 0x02  # ADC
            hw_index = pins[0] if pins else 0
        elif ch_type_str == "power_output":
            hw_device = 0x05  # PROFET
            hw_index = pins[0] if pins else 0
        elif ch_type_str == "pwm_output":
            hw_device = 0x06  # PWM
            hw_index = pins[0] if pins else 0
        elif ch_type_str == "hbridge":
            hw_device = 0x07  # HBRIDGE
            hw_index = pins[0] if pins else 0

        # Get type-specific config bytes
        config_bytes = _ui_config_to_binary(ch_type_str, ch) or b''
        config_size = len(config_bytes)

        # Build 14-byte CfgChannelHeader_t
        # struct: id(2) + type(1) + flags(1) + hw_device(1) + hw_index(1) +
        #         source_id(2) + default_value(4) + name_len(1) + config_size(1)
        header = struct.pack('<HBBBBHiBB',
            int(channel_id),    # id: 2B
            int(ch_type),       # type: 1B
            flags,              # flags: 1B
            hw_device,          # hw_device: 1B
            hw_index,           # hw_index: 1B
            source_id,          # source_id: 2B
            default_value,      # default_value: 4B (signed)
            name_len,           # name_len: 1B
            config_size         # config_size: 1B
        )

        # Append header + name + config
        channel_data.append(header + name_bytes + config_bytes)

    # Build final binary
    channel_count = len(channel_data)
    result = struct.pack('<H', channel_count)
    for data in channel_data:
        result += data

    logger.info(f"Serialized {channel_count} channels to binary format ({len(result)} bytes)")
    logger.info(f"  Binary hex: {result.hex()}")
    return result


def _ui_config_to_binary(ch_type: str, config: Dict) -> Optional[bytes]:
    """Convert UI config dict to binary config struct."""
    import struct

    try:
        # Hardware input channels
        if ch_type == "digital_input":
            return _serialize_digital_input(config)
        elif ch_type == "analog_input":
            return _serialize_analog_input(config)
        elif ch_type == "frequency_input":
            return _serialize_frequency_input(config)
        elif ch_type == "can_rx":
            return _serialize_can_input(config)
        # Hardware output channels
        elif ch_type == "power_output":
            return _serialize_power_output(config)
        elif ch_type == "pwm_output":
            return _serialize_pwm_output(config)
        elif ch_type == "hbridge":
            return _serialize_hbridge(config)
        elif ch_type == "can_tx":
            return _serialize_can_output(config)
        # Virtual channels
        elif ch_type == "timer":
            return _serialize_timer(config)
        elif ch_type == "logic":
            return _serialize_logic(config)
        elif ch_type == "filter":
            return _serialize_filter(config)
        elif ch_type == "table_2d":
            return _serialize_table_2d(config)
        elif ch_type == "switch":
            return _serialize_switch(config)
        elif ch_type == "number":
            return _serialize_number(config)
        elif ch_type == "pid":
            return _serialize_pid(config)
        elif ch_type == "counter":
            return _serialize_counter(config)
        elif ch_type == "hysteresis":
            return _serialize_hysteresis(config)
        elif ch_type == "flipflop":
            return _serialize_flipflop(config)
        elif ch_type == "math":
            return _serialize_math(config)
        else:
            return b''  # Return empty config for unknown types
    except Exception as e:
        logger.error(f"Failed to serialize {ch_type}: {e}")
        return b''


def _get_channel_ref(value, channel_lookup: Dict[str, int] = None) -> int:
    """Convert channel reference to int, resolving names to IDs.

    Uses module-level _channel_name_to_id lookup table (built by
    serialize_ui_channels_for_executor) and system channel definitions.

    Args:
        value: Channel ID (int) or channel name (str)
        channel_lookup: Optional dict mapping channel names to IDs (overrides global)

    Returns:
        Numeric channel ID, or CH_REF_NONE if not resolvable
    """
    global _channel_name_to_id

    if value is None or value == "" or value == "None":
        return CH_REF_NONE

    # Already an int - return directly
    if isinstance(value, int):
        return value

    # String value - try to resolve
    if isinstance(value, str):
        # Try to convert numeric string
        if value.isdigit():
            return int(value)

        # Check explicit lookup table first (if provided)
        if channel_lookup and value in channel_lookup:
            return channel_lookup[value]

        # Check module-level lookup table (user channels)
        if _channel_name_to_id and value in _channel_name_to_id:
            resolved_id = _channel_name_to_id[value]
            logger.debug(f"Resolved user channel '{value}' -> {resolved_id}")
            return resolved_id

        # Check system channels by name
        system_name_to_id = _get_system_channel_name_to_id()
        if value in system_name_to_id:
            resolved_id = system_name_to_id[value]
            logger.debug(f"Resolved system channel '{value}' -> {resolved_id}")
            return resolved_id

        # Fallback: try int conversion (may fail for non-numeric strings)
        try:
            return int(value)
        except ValueError:
            logger.warning(f"Could not resolve channel reference: {value}")
            return CH_REF_NONE

    return CH_REF_NONE


def _get_system_channel_name_to_id() -> Dict[str, int]:
    """Get mapping of system channel names to IDs.

    Returns dict like: {"one": 1013, "zero": 1012, "pmu.status": 1007, ...}
    """
    # Import here to avoid circular import
    from .channel_display_service import ChannelDisplayService

    name_to_id = {}
    for ch_id, ch_name, _ in ChannelDisplayService.SYSTEM_CHANNELS:
        name_to_id[ch_name] = ch_id

    return name_to_id


# ============================================================================
# Hardware Channel Serialization
# ============================================================================

def _serialize_digital_input(config: Dict) -> bytes:
    """Serialize digital input to CfgDigitalInput_t (4 bytes).

    FORMAT = "<BBH" matches channel_config.py CfgDigitalInput
    """
    import struct

    # Preserve raw integer values for correct roundtrip
    active_high = int(config.get('active_high', 1))
    use_pullup = int(config.get('use_pullup', 1))
    # Use debounce_ms if present, else debounce_time if present, else 0
    if 'debounce_ms' in config:
        debounce_ms = int(config['debounce_ms'])
    elif 'debounce_time' in config:
        debounce_ms = int(config['debounce_time'])
    else:
        debounce_ms = 0

    return struct.pack('<BBH',
        active_high,        # active_high: 1B
        use_pullup,         # use_pullup: 1B
        debounce_ms         # debounce_ms: 2B
    )


def _serialize_analog_input(config: Dict) -> bytes:
    """Serialize analog input to CfgAnalogInput_t (20 bytes).

    FORMAT = "<iiiiHBB" matches channel_config.py CfgAnalogInput
    """
    import struct

    raw_min = int(config.get('raw_min', 0) or config.get('cal_raw_low', 0))
    raw_max = int(config.get('raw_max', 4095) or config.get('cal_raw_high', 4095))
    scaled_min = int(config.get('scaled_min', 0) or config.get('cal_scaled_low', 0))
    scaled_max = int(config.get('scaled_max', 100) or config.get('cal_scaled_high', 100))
    filter_ms = int(config.get('filter_ms', 10))
    filter_type = int(config.get('filter_type', 0))
    samples = int(config.get('samples', 4))

    return struct.pack('<iiiiHBB',
        raw_min,            # raw_min: 4B (signed)
        raw_max,            # raw_max: 4B (signed)
        scaled_min,         # scaled_min: 4B (signed)
        scaled_max,         # scaled_max: 4B (signed)
        filter_ms,          # filter_ms: 2B
        filter_type,        # filter_type: 1B
        samples             # samples: 1B
    )


def _serialize_frequency_input(config: Dict) -> bytes:
    """Serialize frequency input to CfgFrequencyInput_t (20 bytes).

    FORMAT = "<IIHBB ii" matches channel_config.py CfgFrequencyInput
    """
    import struct

    min_freq = int(config.get('min_freq_hz', 0))
    max_freq = int(config.get('max_freq_hz', 10000))
    pulses_per_rev = int(config.get('pulses_per_rev', 1))
    edge_mode = int(config.get('edge_mode', 0))
    reserved = 0
    scale_num = int(config.get('scale_num', 1))
    scale_den = int(config.get('scale_den', 1))

    return struct.pack('<IIHBBii',
        min_freq,           # min_freq_hz: 4B
        max_freq,           # max_freq_hz: 4B
        pulses_per_rev,     # pulses_per_rev: 2B
        edge_mode,          # edge_mode: 1B
        reserved,           # reserved: 1B
        scale_num,          # scale_num: 4B (signed)
        scale_den           # scale_den: 4B (signed)
    )


def _serialize_can_input(config: Dict) -> bytes:
    """Serialize CAN input to CfgCanInput_t (18 bytes).

    Matches C struct CfgCanInput_t in shared/channel_config.h:
    - can_id: uint32 (4B)
    - bus: uint8 (1B)
    - start_bit: uint8 (1B)
    - bit_length: uint8 (1B)
    - byte_order: uint8 (1B) - 0=little-endian, 1=big-endian
    - is_signed: uint8 (1B)
    - is_extended: uint8 (1B)
    - scale_num: int16 (2B)
    - scale_den: int16 (2B)
    - offset: int16 (2B)
    - timeout_ms: uint16 (2B)
    """
    import struct

    can_id = int(config.get('can_id', 0))
    bus = int(config.get('bus', 0))
    start_bit = int(config.get('start_bit', 0))
    bit_length = int(config.get('bit_length', 8))
    byte_order = int(config.get('byte_order', 0))
    is_signed = 1 if config.get('is_signed', False) else 0
    is_extended = 1 if config.get('is_extended', False) else 0
    scale_num = int(config.get('scale_num', 1))
    scale_den = int(config.get('scale_den', 1))
    offset = int(config.get('offset', 0))
    timeout_ms = int(config.get('timeout_ms', 1000))

    return struct.pack('<IBBBBBB hhhH',
        can_id,             # can_id: 4B
        bus,                # bus: 1B
        start_bit,          # start_bit: 1B
        bit_length,         # bit_length: 1B
        byte_order,         # byte_order: 1B
        is_signed,          # is_signed: 1B
        is_extended,        # is_extended: 1B
        scale_num,          # scale_num: 2B (signed)
        scale_den,          # scale_den: 2B (signed)
        offset,             # offset: 2B (signed)
        timeout_ms          # timeout_ms: 2B
    )


def _serialize_power_output(config: Dict) -> bytes:
    """Serialize power output to CfgPowerOutput_t (12 bytes).

    FORMAT = "<HHHBBHBB" matches channel_config.py CfgPowerOutput
    """
    import struct

    # Use 0 as defaults to preserve original values during roundtrip
    current_limit = int(config.get('current_limit_ma', 0))
    inrush_limit = int(config.get('inrush_limit_ma', 0))
    inrush_time = int(config.get('inrush_time_ms', 0))
    retry_count = int(config.get('retry_count', 0))
    retry_delay_s = int(config.get('retry_delay_s', 0))
    pwm_frequency = int(config.get('pwm_frequency', 0))
    soft_start_ms = int(config.get('soft_start_ms', 0))
    flags = int(config.get('flags', 0))

    return struct.pack('<HHHBBHBB',
        current_limit,      # current_limit_ma: 2B
        inrush_limit,       # inrush_limit_ma: 2B
        inrush_time,        # inrush_time_ms: 2B
        retry_count,        # retry_count: 1B
        retry_delay_s,      # retry_delay_s: 1B
        pwm_frequency,      # pwm_frequency: 2B
        soft_start_ms,      # soft_start_ms: 1B
        flags               # flags: 1B
    )


def _serialize_pwm_output(config: Dict) -> bytes:
    """Serialize PWM output to CfgPwmOutput_t (12 bytes)."""
    import struct

    frequency = int(config.get('frequency_hz', 1000))
    min_duty = int(config.get('min_duty', 0))
    max_duty = int(config.get('max_duty', 10000))
    default_duty = int(config.get('default_duty', 0))

    return struct.pack('<IHHHH',
        frequency,          # frequency_hz: 4B
        min_duty,           # min_duty: 2B
        max_duty,           # max_duty: 2B
        default_duty,       # default_duty: 2B
        0                   # reserved: 2B
    )


def _serialize_hbridge(config: Dict) -> bytes:
    """Serialize H-Bridge to CfgHBridge_t (8 bytes)."""
    import struct

    frequency = int(config.get('frequency_hz', 1000))
    deadband = int(config.get('deadband_us', 0))
    max_rate = int(config.get('max_rate', 0))

    return struct.pack('<IHHH',
        frequency,          # frequency_hz: 4B
        deadband,           # deadband_us: 2B
        max_rate            # max_rate: 2B
    )


def _serialize_can_output(config: Dict) -> bytes:
    """Serialize CAN output to CfgCanOutput_t (18 bytes).

    Matches C struct CfgCanOutput_t in shared/channel_config.h:
    - can_id: uint32 (4B)
    - bus: uint8 (1B)
    - dlc: uint8 (1B)
    - start_bit: uint8 (1B)
    - bit_length: uint8 (1B)
    - byte_order: uint8 (1B) - 0=little-endian, 1=big-endian
    - is_extended: uint8 (1B)
    - period_ms: uint16 (2B) - 0=on-change
    - scale_num: int16 (2B)
    - scale_den: int16 (2B)
    - offset: int16 (2B)
    """
    import struct

    can_id = int(config.get('can_id', 0))
    bus = int(config.get('bus', 0))
    dlc = int(config.get('dlc', 8))
    start_bit = int(config.get('start_bit', 0))
    bit_length = int(config.get('bit_length', 8))
    byte_order = int(config.get('byte_order', 0))
    is_extended = 1 if config.get('is_extended', False) else 0
    period_ms = int(config.get('period_ms', 100))
    scale_num = int(config.get('scale_num', 1))
    scale_den = int(config.get('scale_den', 1))
    offset = int(config.get('offset', 0))

    return struct.pack('<IBBBBBB Hhhh',
        can_id,             # can_id: 4B
        bus,                # bus: 1B
        dlc,                # dlc: 1B
        start_bit,          # start_bit: 1B
        bit_length,         # bit_length: 1B
        byte_order,         # byte_order: 1B
        is_extended,        # is_extended: 1B
        period_ms,          # period_ms: 2B
        scale_num,          # scale_num: 2B (signed)
        scale_den,          # scale_den: 2B (signed)
        offset              # offset: 2B (signed)
    )


# ============================================================================
# Virtual Channel Serialization
# ============================================================================

def _serialize_timer(config: Dict) -> bytes:
    """Serialize timer to CfgTimer_t (16 bytes)."""
    import struct

    # Timer mode mapping
    MODE_MAP = {"one_shot": 0, "retriggerable": 1, "delay": 2, "pulse": 3, "blink": 4}

    hours = config.get('limit_hours', 0)
    minutes = config.get('limit_minutes', 0)
    seconds = config.get('limit_seconds', 0)
    delay_ms = int((hours * 3600 + minutes * 60 + seconds) * 1000)

    trigger_id = _get_channel_ref(config.get('start_channel'))
    mode = MODE_MAP.get(config.get('timer_mode', 'one_shot'), 0)

    return struct.pack('<BBHIHHB3s', mode, 0, trigger_id, delay_ms, 0, 0, 0, bytes(3))


def _serialize_logic(config: Dict) -> bytes:
    """Serialize logic to CfgLogic_t (26 bytes).

    Handles both formats:
    - Serialization format: input_channels = [id1, id2, ...]
    - UI format: channel = "name1", channel_2 = "name2"

    Channel names (e.g., "one", "Digital Input 1") are resolved to numeric IDs.
    """
    import struct

    # Must match firmware LogicOp_t enum in shared/engine/logic.h
    OP_MAP = {
        "and": 0x00, "or": 0x01, "xor": 0x02, "nand": 0x03, "nor": 0x04,
        "is_true": 0x06, "is_false": 0x07,
        "greater": 0x10, "gt": 0x10, "greater_equal": 0x11, "ge": 0x11,
        "less": 0x12, "lt": 0x12, "less_equal": 0x13, "le": 0x13,
        "equal": 0x14, "eq": 0x14, "not_equal": 0x15, "ne": 0x15,
        "range": 0x20, "in_range": 0x20, "outside": 0x21,
        # Additional operations from LogicDialog
        "edge_rising": 0x30, "edge_falling": 0x31,
        "changed": 0x32, "hysteresis": 0x33, "set_reset_latch": 0x34,
        "toggle": 0x35, "pulse": 0x36, "flash": 0x37
    }

    # Convert to lowercase to match OP_MAP keys (parser may return uppercase)
    op_str = config.get('operation', 'is_true')
    logger.info(f"[LOGIC DEBUG] Raw operation from config: '{op_str}' (type={type(op_str).__name__})")
    if isinstance(op_str, str):
        op_str = op_str.lower()
    operation = OP_MAP.get(op_str, 0x06)
    logger.info(f"[LOGIC DEBUG] After lowercase: '{op_str}' -> operation code: 0x{operation:02X}")

    # Handle both formats: input_channels list OR channel/channel_2 fields
    input_channels = config.get('input_channels', [])
    if not input_channels:
        # UI format - build input_channels from channel/channel_2 fields
        channel = config.get('channel')
        channel_2 = config.get('channel_2')
        # Some operations use different field names
        set_channel = config.get('set_channel')
        reset_channel = config.get('reset_channel')
        toggle_channel = config.get('toggle_channel')

        if channel:
            input_channels.append(channel)
        if channel_2:
            input_channels.append(channel_2)
        if set_channel and set_channel not in input_channels:
            input_channels.append(set_channel)
        if reset_channel and reset_channel not in input_channels:
            input_channels.append(reset_channel)
        if toggle_channel and toggle_channel not in input_channels:
            input_channels.append(toggle_channel)

    input_count = len(input_channels)

    # Resolve channel names to IDs (handles "one", "Digital Input 1", etc.)
    inputs = [_get_channel_ref(ch) for ch in input_channels[:8]]
    while len(inputs) < 8:
        inputs.append(CH_REF_NONE)

    # Get compare value - handle constant field from UI
    compare_value = config.get('compare_value', config.get('constant', 0))
    if isinstance(compare_value, float):
        compare_value = int(compare_value * 100)  # Scale factor for firmware
    else:
        compare_value = int(compare_value)

    invert = 1 if config.get('invert_output', False) else 0

    return struct.pack('<BB8HiB3s', operation, input_count, *inputs, compare_value, invert, bytes(3))


def _serialize_filter(config: Dict) -> bytes:
    """Serialize filter to CfgFilter_t (8 bytes)."""
    import struct

    input_id = _get_channel_ref(config.get('input_channel'))
    time_const = config.get('time_constant', 0.1)
    time_constant_ms = int(time_const * 1000)

    return struct.pack('<HBBHBB', input_id, 0, 4, time_constant_ms, 128, 0)


def _serialize_table_2d(config: Dict) -> bytes:
    """Serialize 2D table to CfgTable2D_t (68 bytes)."""
    import struct

    input_id = _get_channel_ref(config.get('x_axis_channel'))
    x_values = config.get('x_values', [])
    y_values = config.get('output_values', [])
    point_count = len(x_values)

    x_int = [int(v) for v in x_values[:16]]
    y_int = [int(v) for v in y_values[:16]]
    while len(x_int) < 16:
        x_int.append(0)
    while len(y_int) < 16:
        y_int.append(0)

    return struct.pack('<HBB16h16h', input_id, point_count, 0, *x_int, *y_int)


def _serialize_switch(config: Dict) -> bytes:
    """Serialize switch to CfgSwitch_t (104 bytes)."""
    import struct

    selector_id = _get_channel_ref(config.get('input_channel_up'))
    first_state = config.get('first_state', 0)
    last_state = config.get('last_state', 2)
    case_count = last_state - first_state + 1

    cases = []
    for i in range(8):
        if i < case_count:
            cases.extend([first_state + i, 0, i])
        else:
            cases.extend([0, 0, 0])

    default_value = config.get('default_value', 0)

    return struct.pack('<HBB24ii', selector_id, case_count, 0, *cases, default_value)


def _serialize_number(config: Dict) -> bytes:
    """Serialize number to CfgNumber_t (20 bytes)."""
    import struct

    value = int(config.get('constant_value', 0) * 100)
    min_val = int(config.get('min_value', -1000000))
    max_val = int(config.get('max_value', 1000000))
    step = int(config.get('step', 1))

    return struct.pack('<iiiiBB2s', value, min_val, max_val, step, 0, 0, bytes(2))


def _serialize_pid(config: Dict) -> bytes:
    """Serialize PID to CfgPid_t (22 bytes)."""
    import struct

    setpoint_id = _get_channel_ref(config.get('setpoint_channel'))
    feedback_id = _get_channel_ref(config.get('feedback_channel'))

    kp = int(config.get('kp', 1.0) * 1000)
    ki = int(config.get('ki', 0.0) * 1000)
    kd = int(config.get('kd', 0.0) * 1000)
    output_min = int(config.get('output_min', 0))
    output_max = int(config.get('output_max', 10000))

    return struct.pack('<HHhhhhhhhhBB', setpoint_id, feedback_id, kp, ki, kd,
                       output_min, output_max, 0, 10000, 0, 1, 0)


def _serialize_counter(config: Dict) -> bytes:
    """Serialize counter to CfgCounter_t (16 bytes)."""
    import struct

    inc_id = _get_channel_ref(config.get('increment_channel'))
    dec_id = _get_channel_ref(config.get('decrement_channel'))
    reset_id = _get_channel_ref(config.get('reset_channel'))

    initial = int(config.get('initial_value', 0))
    min_val = int(config.get('min_value', 0))
    max_val = int(config.get('max_value', 100))
    step = int(config.get('step', 1))
    wrap = 1 if config.get('wrap', False) else 0

    return struct.pack('<HHHhhhhBB', inc_id, dec_id, reset_id, initial, min_val, max_val, step, wrap, 1)


def _serialize_hysteresis(config: Dict) -> bytes:
    """Serialize hysteresis to CfgHysteresis_t (12 bytes)."""
    import struct

    input_id = _get_channel_ref(config.get('input_channel'))
    threshold_high = int(config.get('threshold_high', 100))
    threshold_low = int(config.get('threshold_low', 0))
    invert = 1 if config.get('invert', False) else 0

    return struct.pack('<HBBii', input_id, 0, invert, threshold_high, threshold_low)


def _serialize_flipflop(config: Dict) -> bytes:
    """Serialize flipflop to CfgFlipFlop_t (12 bytes)."""
    import struct

    set_id = _get_channel_ref(config.get('set_channel'))
    reset_id = _get_channel_ref(config.get('reset_channel'))
    clock_id = _get_channel_ref(config.get('clock_channel'))

    ff_type = config.get('ff_type', 0)
    initial = 1 if config.get('initial_state', False) else 0

    return struct.pack('<BBHHHB3s', ff_type, 0, set_id, reset_id, clock_id, initial, bytes(3))


def _serialize_math(config: Dict) -> bytes:
    """Serialize math to CfgMath_t (34 bytes)."""
    import struct

    OP_MAP = {"add": 0, "sub": 1, "mul": 2, "div": 3, "min": 4, "max": 5,
              "abs": 6, "neg": 7, "avg": 8, "scale": 9, "clamp": 10}

    operation = OP_MAP.get(config.get('operation', 'add'), 0)
    input_channels = config.get('input_channels', [])
    input_count = len(input_channels)

    inputs = [_get_channel_ref(ch) for ch in input_channels[:8]]
    while len(inputs) < 8:
        inputs.append(CH_REF_NONE)

    constant = int(config.get('constant', 0))
    min_val = int(config.get('min_value', -2147483648))
    max_val = int(config.get('max_value', 2147483647))
    scale_num = int(config.get('scale_num', 1))
    scale_den = int(config.get('scale_den', 1))

    return struct.pack('<BB8Hiiihh', operation, input_count, *inputs,
                       constant, min_val, max_val, scale_num, scale_den)
