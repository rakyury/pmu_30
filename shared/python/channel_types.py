"""
PMU-30 Channel Types - Python definitions

Mirrors channel_types.h for Python compatibility.
"""

from enum import IntEnum


class ChannelType(IntEnum):
    """Channel type enumeration - mirrors ChannelType_t"""

    NONE = 0x00

    # Inputs (may have hw_binding)
    DIGITAL_INPUT = 0x01
    ANALOG_INPUT = 0x02
    FREQUENCY_INPUT = 0x03
    CAN_INPUT = 0x04

    # Outputs (may have hw_binding)
    POWER_OUTPUT = 0x10
    PWM_OUTPUT = 0x11
    HBRIDGE = 0x12
    CAN_OUTPUT = 0x13

    # Virtual (no hw_binding)
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

    # System (builtin, readonly)
    SYSTEM = 0xF0


class HwDevice(IntEnum):
    """Hardware device type - mirrors HwDevice_t"""

    NONE = 0x00
    GPIO = 0x01
    ADC = 0x02
    PWM = 0x03
    DAC = 0x04
    PROFET = 0x05
    HBRIDGE = 0x06
    CAN = 0x07
    FREQ = 0x08


class DataType(IntEnum):
    """Data type for value representation - mirrors DataType_t"""

    BOOL = 0x00
    UINT8 = 0x01
    INT8 = 0x02
    UINT16 = 0x03
    INT16 = 0x04
    UINT32 = 0x05
    INT32 = 0x06
    FLOAT32 = 0x07


class ChannelFlags(IntEnum):
    """Channel flags bitmask - mirrors ChannelFlags_t"""

    ENABLED = 0x01
    INVERTED = 0x02
    BUILTIN = 0x04
    READONLY = 0x08
    HIDDEN = 0x10
    FAULT = 0x20


# Magic numbers and version
PMU_CONFIG_MAGIC = 0x504D5533  # "PMU3"
PMU_CONFIG_VERSION = 1
PMU_TELEM_MAGIC = 0x544C4D33  # "TLM3"
PMU_TELEM_VERSION = 1

# Channel reference: no channel
CH_REF_NONE = 0xFFFF
