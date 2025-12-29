"""
Table Channels - Lookup table and switch channel types

This module contains 2D/3D table and switch channel classes.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any

from .enums import ChannelType, EdgeType
from .base import ChannelBase


@dataclass
class Table2DChannel(ChannelBase):
    """2D lookup table channel"""
    x_axis_channel: str = ""
    # Axis configuration for auto-generation
    x_min: float = 0.0
    x_max: float = 100.0
    x_step: float = 10.0
    # X axis values (generated or custom)
    x_values: List[float] = field(default_factory=list)
    # Output values corresponding to x_values
    output_values: List[float] = field(default_factory=list)
    # Decimal places for display
    decimal_places: int = 0

    def __post_init__(self):
        self.channel_type = ChannelType.TABLE_2D

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "x_axis_channel": self.x_axis_channel,
            "x_min": self.x_min,
            "x_max": self.x_max,
            "x_step": self.x_step,
            "x_values": self.x_values,
            "output_values": self.output_values,
            "decimal_places": self.decimal_places
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Table2DChannel':
        return cls(
            name=data.get("channel_name", ""),
            channel_type=ChannelType.TABLE_2D,
            channel_id=data.get("channel_id", 0),
            x_axis_channel=data.get("x_axis_channel", ""),
            x_min=data.get("x_min", 0.0),
            x_max=data.get("x_max", 100.0),
            x_step=data.get("x_step", 10.0),
            x_values=data.get("x_values", []),
            output_values=data.get("output_values", []),
            decimal_places=data.get("decimal_places", 0)
        )

    def get_input_channels(self) -> List[str]:
        return [self.x_axis_channel] if self.x_axis_channel else []

    def generate_axis_values(self) -> List[float]:
        """Generate axis values based on min, max, step"""
        if self.x_step <= 0:
            return [self.x_min]
        values = []
        v = self.x_min
        while v <= self.x_max:
            values.append(v)
            v += self.x_step
        return values


@dataclass
class Table3DChannel(ChannelBase):
    """3D lookup table channel"""
    x_axis_channel: str = ""
    y_axis_channel: str = ""
    # X axis configuration
    x_min: float = 0.0
    x_max: float = 100.0
    x_step: float = 10.0
    x_values: List[float] = field(default_factory=list)
    # Y axis configuration
    y_min: float = 0.0
    y_max: float = 100.0
    y_step: float = 10.0
    y_values: List[float] = field(default_factory=list)
    # Output data: 2D matrix [y_index][x_index]
    data: List[List[float]] = field(default_factory=list)
    # Decimal places for display
    decimal_places: int = 0

    def __post_init__(self):
        self.channel_type = ChannelType.TABLE_3D

    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result.update({
            "x_axis_channel": self.x_axis_channel,
            "y_axis_channel": self.y_axis_channel,
            "x_min": self.x_min,
            "x_max": self.x_max,
            "x_step": self.x_step,
            "x_values": self.x_values,
            "y_min": self.y_min,
            "y_max": self.y_max,
            "y_step": self.y_step,
            "y_values": self.y_values,
            "data": self.data,
            "decimal_places": self.decimal_places
        })
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Table3DChannel':
        return cls(
            name=data.get("channel_name", ""),
            channel_type=ChannelType.TABLE_3D,
            channel_id=data.get("channel_id", 0),
            x_axis_channel=data.get("x_axis_channel", ""),
            y_axis_channel=data.get("y_axis_channel", ""),
            x_min=data.get("x_min", 0.0),
            x_max=data.get("x_max", 100.0),
            x_step=data.get("x_step", 10.0),
            x_values=data.get("x_values", []),
            y_min=data.get("y_min", 0.0),
            y_max=data.get("y_max", 100.0),
            y_step=data.get("y_step", 10.0),
            y_values=data.get("y_values", []),
            data=data.get("data", []),
            decimal_places=data.get("decimal_places", 0)
        )

    def get_input_channels(self) -> List[str]:
        channels = []
        if self.x_axis_channel:
            channels.append(self.x_axis_channel)
        if self.y_axis_channel:
            channels.append(self.y_axis_channel)
        return channels

    def generate_x_values(self) -> List[float]:
        """Generate X axis values based on min, max, step"""
        if self.x_step <= 0:
            return [self.x_min]
        values = []
        v = self.x_min
        while v <= self.x_max:
            values.append(v)
            v += self.x_step
        return values

    def generate_y_values(self) -> List[float]:
        """Generate Y axis values based on min, max, step"""
        if self.y_step <= 0:
            return [self.y_min]
        values = []
        v = self.y_min
        while v <= self.y_max:
            values.append(v)
            v += self.y_step
        return values


@dataclass
class SwitchChannel(ChannelBase):
    """Switch/State machine channel"""
    switch_type: str = "latching"  # latching, press_hold
    input_up_channel: str = ""
    input_up_edge: EdgeType = EdgeType.RISING
    input_down_channel: str = ""
    input_down_edge: EdgeType = EdgeType.RISING
    state_first: int = 0
    state_last: int = 10
    state_default: int = 0

    def __post_init__(self):
        self.channel_type = ChannelType.SWITCH

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "switch_type": self.switch_type,
            "input_up_channel": self.input_up_channel,
            "input_up_edge": self.input_up_edge.value,
            "input_down_channel": self.input_down_channel,
            "input_down_edge": self.input_down_edge.value,
            "state_first": self.state_first,
            "state_last": self.state_last,
            "state_default": self.state_default
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SwitchChannel':
        return cls(
            name=data.get("channel_name", ""),
            channel_type=ChannelType.SWITCH,
            channel_id=data.get("channel_id", 0),
            switch_type=data.get("switch_type", "latching"),
            input_up_channel=data.get("input_up_channel", ""),
            input_up_edge=EdgeType(data.get("input_up_edge", "rising")),
            input_down_channel=data.get("input_down_channel", ""),
            input_down_edge=EdgeType(data.get("input_down_edge", "rising")),
            state_first=data.get("state_first", 0),
            state_last=data.get("state_last", 10),
            state_default=data.get("state_default", 0)
        )

    def get_input_channels(self) -> List[str]:
        channels = []
        if self.input_up_channel:
            channels.append(self.input_up_channel)
        if self.input_down_channel:
            channels.append(self.input_down_channel)
        return channels
