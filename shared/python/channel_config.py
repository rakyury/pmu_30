"""
PMU-30 Binary Channel Configuration - Python Port

Mirrors channel_config.h/.c for Python compatibility.
Provides serialization and deserialization of binary config format.
"""

import struct
from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional, Any, Dict
import zlib


# ============================================================================
# Constants
# ============================================================================

CFG_MAGIC = 0x43464733  # "CFG3"
CFG_VERSION = 2

CFG_MAX_INPUTS = 8
CFG_MAX_NAME_LEN = 31
CFG_MAX_UNIT_LEN = 7
CFG_MAX_TABLE_2D_SIZE = 16
CFG_MAX_TABLE_3D_X = 8
CFG_MAX_TABLE_3D_Y = 8
CFG_MAX_SWITCH_CASES = 8
CFG_MAX_ENUM_VALUES = 16

CH_REF_NONE = 0xFFFF


# ============================================================================
# Channel Types (from channel_types.h)
# ============================================================================

class ChannelType(IntEnum):
    NONE = 0x00
    DIGITAL_INPUT = 0x01
    ANALOG_INPUT = 0x02
    FREQUENCY_INPUT = 0x03
    CAN_INPUT = 0x04

    POWER_OUTPUT = 0x10
    PWM_OUTPUT = 0x11
    HBRIDGE = 0x12
    CAN_OUTPUT = 0x13

    TIMER = 0x20
    LOGIC = 0x21
    MATH = 0x22
    TABLE_2D = 0x23
    TABLE_3D = 0x24
    FILTER = 0x25
    PID = 0x26
    NUMBER = 0x27
    SWITCH = 0x28
    ENUM = 0x29
    COUNTER = 0x2A
    HYSTERESIS = 0x2B
    FLIPFLOP = 0x2C

    SYSTEM = 0xF0


class HwDevice(IntEnum):
    NONE = 0x00
    GPIO = 0x01
    ADC = 0x02
    PWM = 0x03
    DAC = 0x04
    PROFET = 0x05
    HBRIDGE = 0x06
    CAN = 0x07
    FREQ = 0x08


class ChannelFlags(IntEnum):
    ENABLED = 0x01
    INVERTED = 0x02
    BUILTIN = 0x04
    READONLY = 0x08
    HIDDEN = 0x10
    FAULT = 0x20


class CfgFlags(IntEnum):
    COMPRESSED = 0x0001
    ENCRYPTED = 0x0002
    PARTIAL = 0x0004
    DEFAULTS = 0x0008


# ============================================================================
# Configuration Structures
# ============================================================================

@dataclass
class CfgChannelHeader:
    """Binary channel header (14 bytes)"""
    id: int = 0
    type: int = 0
    flags: int = 0
    hw_device: int = 0
    hw_index: int = 0
    source_id: int = CH_REF_NONE
    default_value: int = 0
    name_len: int = 0
    config_size: int = 0

    FORMAT = "<HBBBBHiBB"
    SIZE = 14

    def pack(self) -> bytes:
        return struct.pack(
            self.FORMAT,
            self.id, self.type, self.flags, self.hw_device, self.hw_index,
            self.source_id, self.default_value, self.name_len, self.config_size
        )

    @classmethod
    def unpack(cls, data: bytes) -> "CfgChannelHeader":
        values = struct.unpack(cls.FORMAT, data[:cls.SIZE])
        return cls(*values)


@dataclass
class CfgFileHeader:
    """Binary config file header (32 bytes)"""
    magic: int = CFG_MAGIC
    version: int = CFG_VERSION
    device_type: int = 0
    total_size: int = 32
    crc32: int = 0
    channel_count: int = 0
    flags: int = 0
    timestamp: int = 0
    reserved: bytes = field(default_factory=lambda: bytes(8))

    FORMAT = "<IHHIIHHI8s"
    SIZE = 32

    def pack(self) -> bytes:
        return struct.pack(
            self.FORMAT,
            self.magic, self.version, self.device_type, self.total_size,
            self.crc32, self.channel_count, self.flags, self.timestamp,
            self.reserved
        )

    @classmethod
    def unpack(cls, data: bytes) -> "CfgFileHeader":
        values = struct.unpack(cls.FORMAT, data[:cls.SIZE])
        return cls(*values)

    def is_valid(self) -> bool:
        return self.magic == CFG_MAGIC and self.version == CFG_VERSION


# ============================================================================
# Type-Specific Configurations
# ============================================================================

@dataclass
class CfgDigitalInput:
    """Digital input configuration (4 bytes)"""
    active_high: int = 1
    use_pullup: int = 0
    debounce_ms: int = 50

    FORMAT = "<BBH"
    SIZE = 4

    def pack(self) -> bytes:
        return struct.pack(self.FORMAT, self.active_high, self.use_pullup, self.debounce_ms)

    @classmethod
    def unpack(cls, data: bytes) -> "CfgDigitalInput":
        values = struct.unpack(cls.FORMAT, data[:cls.SIZE])
        return cls(*values)


@dataclass
class CfgAnalogInput:
    """Analog input configuration (20 bytes)"""
    raw_min: int = 0
    raw_max: int = 4095
    scaled_min: int = 0
    scaled_max: int = 10000
    filter_ms: int = 10
    filter_type: int = 0
    samples: int = 4

    FORMAT = "<iiiiHBB"
    SIZE = 20

    def pack(self) -> bytes:
        return struct.pack(
            self.FORMAT,
            self.raw_min, self.raw_max, self.scaled_min, self.scaled_max,
            self.filter_ms, self.filter_type, self.samples
        )

    @classmethod
    def unpack(cls, data: bytes) -> "CfgAnalogInput":
        values = struct.unpack(cls.FORMAT, data[:cls.SIZE])
        return cls(*values)


@dataclass
class CfgFrequencyInput:
    """Frequency input configuration (20 bytes)"""
    min_freq_hz: int = 0
    max_freq_hz: int = 10000
    timeout_ms: int = 1000
    edge_mode: int = 0
    pulses_per_rev: int = 1
    scale_num: int = 1
    scale_den: int = 1

    FORMAT = "<IIHBB ii"
    SIZE = 20

    def pack(self) -> bytes:
        return struct.pack(
            self.FORMAT,
            self.min_freq_hz, self.max_freq_hz, self.timeout_ms,
            self.edge_mode, self.pulses_per_rev, self.scale_num, self.scale_den
        )

    @classmethod
    def unpack(cls, data: bytes) -> "CfgFrequencyInput":
        values = struct.unpack(cls.FORMAT, data[:cls.SIZE])
        return cls(*values)


@dataclass
class CfgCanInput:
    """CAN input configuration (18 bytes).

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
    can_id: int = 0
    bus: int = 0
    start_bit: int = 0
    bit_length: int = 8
    byte_order: int = 0
    is_signed: int = 0
    is_extended: int = 0
    scale_num: int = 1
    scale_den: int = 1
    offset: int = 0
    timeout_ms: int = 1000

    FORMAT = "<IBBBBBB hhhH"
    SIZE = 18

    def pack(self) -> bytes:
        return struct.pack(
            self.FORMAT,
            self.can_id, self.bus, self.start_bit, self.bit_length,
            self.byte_order, self.is_signed, self.is_extended,
            self.scale_num, self.scale_den, self.offset, self.timeout_ms
        )

    @classmethod
    def unpack(cls, data: bytes) -> "CfgCanInput":
        values = struct.unpack(cls.FORMAT, data[:cls.SIZE])
        return cls(*values)


@dataclass
class CfgCanOutput:
    """CAN output configuration (18 bytes).

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
    can_id: int = 0
    bus: int = 0
    dlc: int = 8
    start_bit: int = 0
    bit_length: int = 8
    byte_order: int = 0
    is_extended: int = 0
    period_ms: int = 100
    scale_num: int = 1
    scale_den: int = 1
    offset: int = 0

    FORMAT = "<IBBBBBB Hhhh"
    SIZE = 18

    def pack(self) -> bytes:
        return struct.pack(
            self.FORMAT,
            self.can_id, self.bus, self.dlc, self.start_bit, self.bit_length,
            self.byte_order, self.is_extended, self.period_ms,
            self.scale_num, self.scale_den, self.offset
        )

    @classmethod
    def unpack(cls, data: bytes) -> "CfgCanOutput":
        values = struct.unpack(cls.FORMAT, data[:cls.SIZE])
        return cls(*values)


@dataclass
class CfgPowerOutput:
    """Power output configuration (12 bytes)"""
    current_limit_ma: int = 10000
    inrush_time_ms: int = 100
    inrush_limit_ma: int = 20000
    retry_count: int = 3
    retry_delay_s: int = 5
    pwm_frequency: int = 0
    soft_start_ms: int = 0
    flags: int = 0

    FORMAT = "<HHHBBHBB"
    SIZE = 12

    def pack(self) -> bytes:
        return struct.pack(
            self.FORMAT,
            self.current_limit_ma, self.inrush_time_ms, self.inrush_limit_ma,
            self.retry_count, self.retry_delay_s, self.pwm_frequency,
            self.soft_start_ms, self.flags
        )

    @classmethod
    def unpack(cls, data: bytes) -> "CfgPowerOutput":
        values = struct.unpack(cls.FORMAT, data[:cls.SIZE])
        return cls(*values)


@dataclass
class CfgTimer:
    """Timer configuration (16 bytes)"""
    mode: int = 0
    trigger_mode: int = 0
    trigger_id: int = CH_REF_NONE
    delay_ms: int = 1000
    on_time_ms: int = 500
    off_time_ms: int = 500
    auto_reset: int = 0
    reserved: bytes = field(default_factory=lambda: bytes(3))

    FORMAT = "<BBHIHHB3s"
    SIZE = 16

    def pack(self) -> bytes:
        return struct.pack(
            self.FORMAT,
            self.mode, self.trigger_mode, self.trigger_id, self.delay_ms,
            self.on_time_ms, self.off_time_ms, self.auto_reset, self.reserved
        )

    @classmethod
    def unpack(cls, data: bytes) -> "CfgTimer":
        values = struct.unpack(cls.FORMAT, data[:cls.SIZE])
        return cls(*values)


@dataclass
class CfgLogic:
    """Logic configuration (26 bytes)"""
    operation: int = 0
    input_count: int = 0
    inputs: List[int] = field(default_factory=lambda: [CH_REF_NONE] * CFG_MAX_INPUTS)
    compare_value: int = 0
    invert_output: int = 0
    reserved: bytes = field(default_factory=lambda: bytes(3))

    FORMAT = "<BB8HiB3s"
    SIZE = 26  # BB=2 + 8H=16 + i=4 + B=1 + 3s=3 = 26

    def pack(self) -> bytes:
        inputs = self.inputs[:CFG_MAX_INPUTS]
        while len(inputs) < CFG_MAX_INPUTS:
            inputs.append(CH_REF_NONE)
        return struct.pack(
            self.FORMAT,
            self.operation, self.input_count, *inputs,
            self.compare_value, self.invert_output, self.reserved
        )

    @classmethod
    def unpack(cls, data: bytes) -> "CfgLogic":
        values = struct.unpack(cls.FORMAT, data[:cls.SIZE])
        return cls(
            operation=values[0],
            input_count=values[1],
            inputs=list(values[2:10]),
            compare_value=values[10],
            invert_output=values[11],
            reserved=values[12]
        )


@dataclass
class CfgMath:
    """Math configuration (32 bytes)"""
    operation: int = 0
    input_count: int = 0
    inputs: List[int] = field(default_factory=lambda: [CH_REF_NONE] * CFG_MAX_INPUTS)
    constant: int = 0
    min_value: int = -2147483648
    max_value: int = 2147483647
    scale_num: int = 1
    scale_den: int = 1

    FORMAT = "<BB8Hiiihh"
    SIZE = 32

    def pack(self) -> bytes:
        inputs = self.inputs[:CFG_MAX_INPUTS]
        while len(inputs) < CFG_MAX_INPUTS:
            inputs.append(CH_REF_NONE)
        return struct.pack(
            self.FORMAT,
            self.operation, self.input_count, *inputs,
            self.constant, self.min_value, self.max_value,
            self.scale_num, self.scale_den
        )

    @classmethod
    def unpack(cls, data: bytes) -> "CfgMath":
        values = struct.unpack(cls.FORMAT, data[:cls.SIZE])
        return cls(
            operation=values[0],
            input_count=values[1],
            inputs=list(values[2:10]),
            constant=values[10],
            min_value=values[11],
            max_value=values[12],
            scale_num=values[13],
            scale_den=values[14]
        )


@dataclass
class CfgTable2D:
    """2D table configuration (68 bytes)"""
    input_id: int = CH_REF_NONE
    point_count: int = 2
    reserved: int = 0
    x_values: List[int] = field(default_factory=lambda: [0] * CFG_MAX_TABLE_2D_SIZE)
    y_values: List[int] = field(default_factory=lambda: [0] * CFG_MAX_TABLE_2D_SIZE)

    FORMAT = f"<HBB{CFG_MAX_TABLE_2D_SIZE}h{CFG_MAX_TABLE_2D_SIZE}h"
    SIZE = 68

    def pack(self) -> bytes:
        x = self.x_values[:CFG_MAX_TABLE_2D_SIZE]
        y = self.y_values[:CFG_MAX_TABLE_2D_SIZE]
        while len(x) < CFG_MAX_TABLE_2D_SIZE:
            x.append(0)
        while len(y) < CFG_MAX_TABLE_2D_SIZE:
            y.append(0)
        return struct.pack(
            self.FORMAT,
            self.input_id, self.point_count, self.reserved, *x, *y
        )

    @classmethod
    def unpack(cls, data: bytes) -> "CfgTable2D":
        values = struct.unpack(cls.FORMAT, data[:cls.SIZE])
        return cls(
            input_id=values[0],
            point_count=values[1],
            reserved=values[2],
            x_values=list(values[3:3+CFG_MAX_TABLE_2D_SIZE]),
            y_values=list(values[3+CFG_MAX_TABLE_2D_SIZE:])
        )


@dataclass
class CfgFilter:
    """Filter configuration (8 bytes)"""
    input_id: int = CH_REF_NONE
    filter_type: int = 0
    window_size: int = 4
    time_constant_ms: int = 100
    alpha: int = 128
    reserved: int = 0

    FORMAT = "<HBBHBB"
    SIZE = 8

    def pack(self) -> bytes:
        return struct.pack(
            self.FORMAT,
            self.input_id, self.filter_type, self.window_size,
            self.time_constant_ms, self.alpha, self.reserved
        )

    @classmethod
    def unpack(cls, data: bytes) -> "CfgFilter":
        values = struct.unpack(cls.FORMAT, data[:cls.SIZE])
        return cls(*values)


@dataclass
class CfgPid:
    """PID configuration (22 bytes)"""
    setpoint_id: int = CH_REF_NONE
    feedback_id: int = CH_REF_NONE
    kp: int = 1000
    ki: int = 0
    kd: int = 0
    output_min: int = 0
    output_max: int = 10000
    integral_min: int = 0
    integral_max: int = 10000
    deadband: int = 0
    d_on_measurement: int = 1
    reserved: int = 0

    FORMAT = "<HHhhhhhhhhBB"
    SIZE = 22

    def pack(self) -> bytes:
        return struct.pack(
            self.FORMAT,
            self.setpoint_id, self.feedback_id, self.kp, self.ki, self.kd,
            self.output_min, self.output_max, self.integral_min, self.integral_max,
            self.deadband, self.d_on_measurement, self.reserved
        )

    @classmethod
    def unpack(cls, data: bytes) -> "CfgPid":
        values = struct.unpack(cls.FORMAT, data[:cls.SIZE])
        return cls(*values)


@dataclass
class CfgNumber:
    """Number/constant configuration (20 bytes)"""
    value: int = 0
    min_value: int = -2147483648
    max_value: int = 2147483647
    step: int = 1
    readonly: int = 0
    save_to_flash: int = 0
    reserved: bytes = field(default_factory=lambda: bytes(2))

    FORMAT = "<iiiiBB2s"
    SIZE = 20

    def pack(self) -> bytes:
        return struct.pack(
            self.FORMAT,
            self.value, self.min_value, self.max_value, self.step,
            self.readonly, self.save_to_flash, self.reserved
        )

    @classmethod
    def unpack(cls, data: bytes) -> "CfgNumber":
        values = struct.unpack(cls.FORMAT, data[:cls.SIZE])
        return cls(*values)


# ============================================================================
# Type Config Mapping
# ============================================================================

CONFIG_TYPES: Dict[int, type] = {
    ChannelType.DIGITAL_INPUT: CfgDigitalInput,
    ChannelType.ANALOG_INPUT: CfgAnalogInput,
    ChannelType.FREQUENCY_INPUT: CfgFrequencyInput,
    ChannelType.CAN_INPUT: CfgCanInput,
    ChannelType.POWER_OUTPUT: CfgPowerOutput,
    ChannelType.TIMER: CfgTimer,
    ChannelType.LOGIC: CfgLogic,
    ChannelType.MATH: CfgMath,
    ChannelType.TABLE_2D: CfgTable2D,
    ChannelType.FILTER: CfgFilter,
    ChannelType.PID: CfgPid,
    ChannelType.NUMBER: CfgNumber,
}


def get_config_size(channel_type: int) -> int:
    """Get size of type-specific config"""
    cfg_class = CONFIG_TYPES.get(channel_type)
    return cfg_class.SIZE if cfg_class else 0


def get_config_class(channel_type: int) -> Optional[type]:
    """Get config class for channel type"""
    return CONFIG_TYPES.get(channel_type)


# ============================================================================
# Channel Wrapper
# ============================================================================

@dataclass
class Channel:
    """Complete channel with header and config"""
    id: int = 0
    type: int = ChannelType.NONE
    flags: int = ChannelFlags.ENABLED
    hw_device: int = HwDevice.NONE
    hw_index: int = 0
    source_id: int = CH_REF_NONE
    default_value: int = 0
    name: str = ""
    config: Any = None

    def serialize(self) -> bytes:
        """Serialize channel to bytes"""
        name_bytes = self.name.encode("utf-8")[:CFG_MAX_NAME_LEN]
        config_bytes = self.config.pack() if self.config else b""

        header = CfgChannelHeader(
            id=self.id,
            type=self.type,
            flags=self.flags,
            hw_device=self.hw_device,
            hw_index=self.hw_index,
            source_id=self.source_id,
            default_value=self.default_value,
            name_len=len(name_bytes),
            config_size=len(config_bytes)
        )

        return header.pack() + name_bytes + config_bytes

    @classmethod
    def deserialize(cls, data: bytes) -> tuple["Channel", int]:
        """Deserialize channel from bytes. Returns (channel, bytes_consumed)"""
        if len(data) < CfgChannelHeader.SIZE:
            raise ValueError("Buffer too small for header")

        header = CfgChannelHeader.unpack(data)
        offset = CfgChannelHeader.SIZE

        # Read name
        name = data[offset:offset + header.name_len].decode("utf-8")
        offset += header.name_len

        # Read config
        config = None
        cfg_class = get_config_class(header.type)
        if cfg_class and header.config_size >= cfg_class.SIZE:
            config = cfg_class.unpack(data[offset:offset + header.config_size])
        offset += header.config_size

        channel = cls(
            id=header.id,
            type=header.type,
            flags=header.flags,
            hw_device=header.hw_device,
            hw_index=header.hw_index,
            source_id=header.source_id,
            default_value=header.default_value,
            name=name,
            config=config
        )

        return channel, offset


# ============================================================================
# Configuration File
# ============================================================================

@dataclass
class ConfigFile:
    """Complete configuration file"""
    device_type: int = 0
    flags: int = 0
    timestamp: int = 0
    channels: List[Channel] = field(default_factory=list)

    def serialize(self) -> bytes:
        """Serialize complete config to bytes"""
        # Serialize channels
        channel_data = b""
        for ch in self.channels:
            channel_data += ch.serialize()

        # Create header
        header = CfgFileHeader(
            magic=CFG_MAGIC,
            version=CFG_VERSION,
            device_type=self.device_type,
            total_size=CfgFileHeader.SIZE + len(channel_data),
            crc32=0,  # Will be calculated
            channel_count=len(self.channels),
            flags=self.flags,
            timestamp=self.timestamp
        )

        # Calculate CRC
        header.crc32 = zlib.crc32(channel_data) & 0xFFFFFFFF

        return header.pack() + channel_data

    @classmethod
    def deserialize(cls, data: bytes) -> "ConfigFile":
        """Deserialize config file from bytes"""
        if len(data) < CfgFileHeader.SIZE:
            raise ValueError("Buffer too small for file header")

        header = CfgFileHeader.unpack(data)

        if not header.is_valid():
            raise ValueError(f"Invalid config file: magic=0x{header.magic:08X}, version={header.version}")

        if len(data) < header.total_size:
            raise ValueError("Buffer smaller than declared size")

        # Verify CRC
        channel_data = data[CfgFileHeader.SIZE:header.total_size]
        calc_crc = zlib.crc32(channel_data) & 0xFFFFFFFF
        if calc_crc != header.crc32:
            raise ValueError(f"CRC mismatch: expected 0x{header.crc32:08X}, got 0x{calc_crc:08X}")

        # Deserialize channels
        channels = []
        offset = 0
        for _ in range(header.channel_count):
            if offset >= len(channel_data):
                break
            channel, consumed = Channel.deserialize(channel_data[offset:])
            channels.append(channel)
            offset += consumed

        return cls(
            device_type=header.device_type,
            flags=header.flags,
            timestamp=header.timestamp,
            channels=channels
        )

    def save(self, filename: str) -> None:
        """Save config to file"""
        with open(filename, "wb") as f:
            f.write(self.serialize())

    @classmethod
    def load(cls, filename: str) -> "ConfigFile":
        """Load config from file"""
        with open(filename, "rb") as f:
            return cls.deserialize(f.read())
