"""
Channel Factory - Factory pattern for creating channel instances

This module contains the ChannelFactory class and CHANNEL_CLASS_MAP.
"""

from typing import Dict, Any, Type

from .enums import ChannelType
from .base import ChannelBase
from .inputs import DigitalInputChannel, AnalogInputChannel
from .outputs import PowerOutputChannel, HBridgeChannel
from .can import CanRxChannel, CanTxChannel
from .logic import LogicChannel, NumberChannel
from .tables import Table2DChannel, Table3DChannel, SwitchChannel
from .filters import FilterChannel, TimerChannel
from .advanced import (
    LuaScriptChannel,
    PIDChannel,
    HandlerChannel,
    WiperChannel,
    BlinkerChannel,
)


# Channel Type to Class mapping
CHANNEL_CLASS_MAP: Dict[ChannelType, Type[ChannelBase]] = {
    ChannelType.DIGITAL_INPUT: DigitalInputChannel,
    ChannelType.ANALOG_INPUT: AnalogInputChannel,
    ChannelType.POWER_OUTPUT: PowerOutputChannel,
    ChannelType.HBRIDGE: HBridgeChannel,
    ChannelType.LOGIC: LogicChannel,
    ChannelType.NUMBER: NumberChannel,
    ChannelType.TIMER: TimerChannel,
    ChannelType.FILTER: FilterChannel,
    ChannelType.TABLE_2D: Table2DChannel,
    ChannelType.TABLE_3D: Table3DChannel,
    ChannelType.SWITCH: SwitchChannel,
    ChannelType.CAN_RX: CanRxChannel,
    ChannelType.CAN_TX: CanTxChannel,
    ChannelType.LUA_SCRIPT: LuaScriptChannel,
    ChannelType.PID: PIDChannel,
    ChannelType.HANDLER: HandlerChannel,
    ChannelType.WIPER: WiperChannel,
    ChannelType.BLINKER: BlinkerChannel,
}


class ChannelFactory:
    """Factory for creating Channel instances"""

    @staticmethod
    def create(channel_type: ChannelType, **kwargs) -> ChannelBase:
        """Create Channel instance by type"""
        channel_class = CHANNEL_CLASS_MAP.get(channel_type)
        if channel_class:
            # Pass channel_type to constructor (required by ChannelBase)
            return channel_class(channel_type=channel_type, **kwargs)
        raise ValueError(f"Unknown channel type: {channel_type}")

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> ChannelBase:
        """Create Channel from dictionary"""
        channel_type_str = data.get("channel_type", data.get("gpio_type", "digital_input"))
        channel_type = ChannelType(channel_type_str)
        channel_class = CHANNEL_CLASS_MAP.get(channel_type)
        if channel_class:
            return channel_class.from_dict(data)
        raise ValueError(f"Unknown channel type: {channel_type_str}")
