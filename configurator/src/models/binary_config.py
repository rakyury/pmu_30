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

    def load_from_file(self, filepath: str) -> Tuple[bool, Optional[str]]:
        """
        Load configuration from binary file (.pmu30 extension)

        Args:
            filepath: Path to binary configuration file

        Returns:
            Tuple[bool, Optional[str]]: (success, error_message)
        """
        try:
            path = Path(filepath)

            if not path.exists():
                return False, f"Configuration file not found: {filepath}"

            self.config = ConfigFile.load(str(path))
            self.current_file = path
            self.modified = False

            # Build channel map
            self._channel_map = {ch.id: ch for ch in self.config.channels}

            logger.info(f"Loaded binary config from: {filepath}")
            logger.info(f"  Device: 0x{self.config.device_type:04X}")
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
        Load configuration from bytes (e.g., from device)

        Args:
            data: Binary configuration data

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
