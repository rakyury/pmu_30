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

def serialize_ui_channels_for_executor(channels: List[Dict]) -> bytes:
    """
    Convert UI channel configs to binary format for Channel Executor.

    Args:
        channels: List of channel dicts from UI (project_tree.get_all_channels())

    Returns:
        Binary data for LOAD_BINARY_CONFIG command
    """
    import struct

    # Channel types that go to executor (virtual channels)
    EXECUTOR_TYPES = {
        "timer": ChannelType.TIMER,
        "logic": ChannelType.LOGIC,
        "math": ChannelType.MATH,
        "filter": ChannelType.FILTER,
        "pid": ChannelType.PID,
        "table_2d": ChannelType.TABLE_2D,
        "switch": ChannelType.SWITCH,
        "number": ChannelType.NUMBER,
        "counter": ChannelType.COUNTER,
        "hysteresis": ChannelType.HYSTERESIS,
        "flipflop": ChannelType.FLIPFLOP,
    }

    channel_data = []

    for ch in channels:
        ch_type_str = ch.get("type", "")
        ch_type = EXECUTOR_TYPES.get(ch_type_str)

        if ch_type is None:
            continue  # Not an executor channel type

        channel_id = ch.get("channel_id")
        if channel_id is None:
            continue

        # Convert UI config to binary config struct
        config_bytes = _ui_config_to_binary(ch_type_str, ch)
        if config_bytes is None:
            continue

        config_size = len(config_bytes)
        header = struct.pack('<HBB', int(channel_id), int(ch_type), config_size)
        channel_data.append(header + config_bytes)

    # Build final binary
    channel_count = len(channel_data)
    result = struct.pack('<H', channel_count)
    for data in channel_data:
        result += data

    logger.debug(f"Converted {channel_count} UI channels to executor format ({len(result)} bytes)")
    return result


def _ui_config_to_binary(ch_type: str, config: Dict) -> Optional[bytes]:
    """Convert UI config dict to binary config struct."""
    import struct

    try:
        if ch_type == "timer":
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
            return None
    except Exception as e:
        logger.error(f"Failed to serialize {ch_type}: {e}")
        return None


def _get_channel_ref(value) -> int:
    """Convert channel reference to int, defaulting to CH_REF_NONE."""
    if value is None or value == "" or value == "None":
        return CH_REF_NONE
    return int(value)


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
    """Serialize logic to CfgLogic_t (26 bytes)."""
    import struct

    OP_MAP = {"and": 0, "or": 1, "not": 2, "xor": 3, "nand": 4, "nor": 5,
              "gt": 6, "ge": 7, "lt": 8, "le": 9, "eq": 10, "ne": 11}

    operation = OP_MAP.get(config.get('operation', 'and'), 0)
    input_channels = config.get('input_channels', [])
    input_count = len(input_channels)

    inputs = [_get_channel_ref(ch) for ch in input_channels[:8]]
    while len(inputs) < 8:
        inputs.append(CH_REF_NONE)

    compare_value = int(config.get('compare_value', 0))
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
