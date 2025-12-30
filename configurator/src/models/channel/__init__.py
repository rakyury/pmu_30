"""
Channel Module - Unified Channel Model for PMU-30 Configurator

This package provides all channel types, enums, and utilities.
Re-exports all public APIs for backward compatibility.

Usage:
    from models.channel import ChannelType, ChannelBase, ChannelFactory
    from models.channel import DigitalInputChannel, AnalogInputChannel
    from models.channel import LogicChannel, NumberChannel
"""

# ============================================================================
# Enums
# ============================================================================
from .enums import (
    ChannelType,
    DigitalInputSubtype,
    ButtonMode,
    AnalogInputSubtype,
    LogicOperation,
    LogicPolarity,
    LogicDefaultState,
    ChannelMultiplier,
    MathOperation,
    FilterType,
    EdgeType,
    CanMessageType,
    CanTimeoutBehavior,
    CanDataType,
    CanDataFormat,
    TimerMode,
    LuaTriggerType,
    LuaPriority,
    HBridgeMode,
    HBridgeMotorPreset,
    EventType,
    ActionType,
    WiperMode,
    BlinkerMode,
)

# ============================================================================
# Base class and utilities
# ============================================================================
from .base import (
    ChannelBase,
    CHANNEL_PREFIX_MAP,
    get_channel_prefix,
    get_channel_display_name,
)

# ============================================================================
# Input channels
# ============================================================================
from .inputs import (
    DigitalInputChannel,
    AnalogInputChannel,
)

# ============================================================================
# Output channels
# ============================================================================
from .outputs import (
    PowerOutputChannel,
    HBridgeChannel,
)

# ============================================================================
# CAN channels
# ============================================================================
from .can import (
    CanMessage,
    CanRxChannel,
    CanTxSignal,
    CanTxChannel,
)

# ============================================================================
# Logic channels
# ============================================================================
from .logic import (
    LogicChannel,
    NumberChannel,
)

# ============================================================================
# Table channels
# ============================================================================
from .tables import (
    Table2DChannel,
    Table3DChannel,
    SwitchChannel,
)

# ============================================================================
# Filter channels
# ============================================================================
from .filters import (
    FilterChannel,
    TimerChannel,
)

# ============================================================================
# Advanced channels
# ============================================================================
from .advanced import (
    LuaScriptChannel,
    PIDChannel,
    HandlerChannel,
    WiperChannel,
    BlinkerChannel,
)

# ============================================================================
# Factory
# ============================================================================
from .factory import (
    ChannelFactory,
    CHANNEL_CLASS_MAP,
)

# ============================================================================
# Public API
# ============================================================================
__all__ = [
    # Enums
    "ChannelType",
    "DigitalInputSubtype",
    "ButtonMode",
    "AnalogInputSubtype",
    "LogicOperation",
    "LogicPolarity",
    "LogicDefaultState",
    "ChannelMultiplier",
    "MathOperation",
    "FilterType",
    "EdgeType",
    "CanMessageType",
    "CanTimeoutBehavior",
    "CanDataType",
    "CanDataFormat",
    "TimerMode",
    "LuaTriggerType",
    "LuaPriority",
    "HBridgeMode",
    "HBridgeMotorPreset",
    "EventType",
    "ActionType",
    "WiperMode",
    "BlinkerMode",
    # Base
    "ChannelBase",
    "CHANNEL_PREFIX_MAP",
    "get_channel_prefix",
    "get_channel_display_name",
    # Inputs
    "DigitalInputChannel",
    "AnalogInputChannel",
    # Outputs
    "PowerOutputChannel",
    "HBridgeChannel",
    # CAN
    "CanMessage",
    "CanRxChannel",
    "CanTxSignal",
    "CanTxChannel",
    # Logic
    "LogicChannel",
    "NumberChannel",
    # Tables
    "Table2DChannel",
    "Table3DChannel",
    "SwitchChannel",
    # Filters
    "FilterChannel",
    "TimerChannel",
    # Advanced
    "LuaScriptChannel",
    "PIDChannel",
    "HandlerChannel",
    "WiperChannel",
    "BlinkerChannel",
    # Factory
    "ChannelFactory",
    "CHANNEL_CLASS_MAP",
]
