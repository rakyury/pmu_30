"""
Filter Channels - Filter and timer channel types

This module contains filter and timer channel classes.
"""

from dataclasses import dataclass
from typing import List, Dict, Any

from .enums import ChannelType, FilterType, EdgeType, TimerMode
from .base import ChannelBase


@dataclass
class FilterChannel(ChannelBase):
    """Filter channel"""
    filter_type: FilterType = FilterType.MOVING_AVG
    input_channel: str = ""
    window_size: int = 10
    time_constant: float = 0.1

    def __post_init__(self):
        self.channel_type = ChannelType.FILTER

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["filter_type"] = self.filter_type.value
        data["input_channel"] = self.input_channel

        # Window-based filters
        if self.filter_type in [FilterType.MOVING_AVG, FilterType.MIN_WINDOW,
                                 FilterType.MAX_WINDOW, FilterType.MEDIAN]:
            data["window_size"] = self.window_size

        # Time constant-based filter
        elif self.filter_type == FilterType.LOW_PASS:
            data["time_constant"] = self.time_constant

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FilterChannel':
        return cls(
            name=data.get("channel_name", ""),
            channel_type=ChannelType.FILTER,
            channel_id=data.get("channel_id", 0),
            filter_type=FilterType(data.get("filter_type", "moving_avg")),
            input_channel=data.get("input_channel", ""),
            window_size=data.get("window_size", 10),
            time_constant=data.get("time_constant", 0.1)
        )

    def get_input_channels(self) -> List[str]:
        return [self.input_channel] if self.input_channel else []


@dataclass
class TimerChannel(ChannelBase):
    """Timer channel"""
    start_channel: str = ""
    start_edge: EdgeType = EdgeType.RISING
    stop_channel: str = ""
    stop_edge: EdgeType = EdgeType.FALLING
    mode: TimerMode = TimerMode.COUNT_UP
    limit_hours: int = 0
    limit_minutes: int = 0
    limit_seconds: int = 0

    def __post_init__(self):
        self.channel_type = ChannelType.TIMER

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "start_channel": self.start_channel,
            "start_edge": self.start_edge.value,
            "stop_channel": self.stop_channel,
            "stop_edge": self.stop_edge.value,
            "mode": self.mode.value,
            "limit_hours": self.limit_hours,
            "limit_minutes": self.limit_minutes,
            "limit_seconds": self.limit_seconds
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TimerChannel':
        return cls(
            name=data.get("channel_name", ""),
            channel_type=ChannelType.TIMER,
            channel_id=data.get("channel_id", 0),
            start_channel=data.get("start_channel", ""),
            start_edge=EdgeType(data.get("start_edge", "rising")),
            stop_channel=data.get("stop_channel", ""),
            stop_edge=EdgeType(data.get("stop_edge", "falling")),
            mode=TimerMode(data.get("mode", "count_up")),
            limit_hours=data.get("limit_hours", 0),
            limit_minutes=data.get("limit_minutes", 0),
            limit_seconds=data.get("limit_seconds", 0)
        )

    def get_input_channels(self) -> List[str]:
        channels = []
        if self.start_channel:
            channels.append(self.start_channel)
        if self.stop_channel:
            channels.append(self.stop_channel)
        return channels

    def validate(self) -> List[str]:
        errors = super().validate()
        if not self.start_channel:
            errors.append("Start channel is required")
        return errors
