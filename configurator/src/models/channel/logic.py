"""
Logic Channels - Logic and math operation channel types

This module contains logic and number channel classes.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any

from .enums import (
    ChannelType,
    LogicOperation,
    LogicPolarity,
    LogicDefaultState,
    EdgeType,
    MathOperation,
    ChannelMultiplier,
)
from .base import ChannelBase


@dataclass
class LogicChannel(ChannelBase):
    """Logic function channel"""
    operation: LogicOperation = LogicOperation.IS_TRUE

    # Common: channel input (for is_true, is_false, comparisons, changed, hysteresis, flash)
    channel: str = ""
    # For AND/OR: second channel
    channel_2: str = ""

    # Delays (in seconds, for is_true, is_false, comparisons, and/or)
    true_delay_s: float = 0.0
    false_delay_s: float = 0.0

    # For comparison operations: constant value
    constant: float = 0.0

    # For CHANGED operation
    threshold: float = 0.0
    time_on_s: float = 0.0

    # For HYSTERESIS operation
    polarity: LogicPolarity = LogicPolarity.NORMAL
    upper_value: float = 100.0
    lower_value: float = 0.0

    # For SET_RESET_LATCH
    set_channel: str = ""
    reset_channel: str = ""
    default_state: LogicDefaultState = LogicDefaultState.OFF

    # For TOGGLE operation
    edge: EdgeType = EdgeType.RISING
    toggle_channel: str = ""
    # set_channel and reset_channel reused from latch
    # default_state reused from latch

    # For PULSE operation
    # edge reused
    # channel reused
    pulse_count: int = 1
    # time_on_s reused
    retrigger: bool = False

    # For FLASH operation
    # channel reused
    # time_on_s reused
    time_off_s: float = 0.5

    def __post_init__(self):
        self.channel_type = ChannelType.LOGIC

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["operation"] = self.operation.value
        op = self.operation

        # IS_TRUE, IS_FALSE: channel + delays
        if op in [LogicOperation.IS_TRUE, LogicOperation.IS_FALSE]:
            data["channel"] = self.channel
            data["true_delay_s"] = self.true_delay_s
            data["false_delay_s"] = self.false_delay_s

        # Comparison operations: channel + constant + delays
        elif op in [LogicOperation.EQUAL, LogicOperation.NOT_EQUAL,
                    LogicOperation.LESS, LogicOperation.GREATER,
                    LogicOperation.LESS_EQUAL, LogicOperation.GREATER_EQUAL]:
            data["channel"] = self.channel
            data["constant"] = self.constant
            data["true_delay_s"] = self.true_delay_s
            data["false_delay_s"] = self.false_delay_s

        # IN_RANGE: channel + lower/upper values + delays
        elif op == LogicOperation.IN_RANGE:
            data["channel"] = self.channel
            data["lower_value"] = self.lower_value
            data["upper_value"] = self.upper_value
            data["true_delay_s"] = self.true_delay_s
            data["false_delay_s"] = self.false_delay_s

        # AND, OR, XOR, NAND, NOR: two channels + delays
        elif op in [LogicOperation.AND, LogicOperation.OR, LogicOperation.XOR,
                    LogicOperation.NAND, LogicOperation.NOR]:
            data["channel"] = self.channel
            data["channel_2"] = self.channel_2
            data["true_delay_s"] = self.true_delay_s
            data["false_delay_s"] = self.false_delay_s

        # EDGE_RISING, EDGE_FALLING: channel only
        elif op in [LogicOperation.EDGE_RISING, LogicOperation.EDGE_FALLING]:
            data["channel"] = self.channel

        # CHANGED: channel + threshold + time_on
        elif op == LogicOperation.CHANGED:
            data["channel"] = self.channel
            data["threshold"] = self.threshold
            data["time_on_s"] = self.time_on_s

        # HYSTERESIS: channel + polarity + upper/lower
        elif op == LogicOperation.HYSTERESIS:
            data["channel"] = self.channel
            data["polarity"] = self.polarity.value
            data["upper_value"] = self.upper_value
            data["lower_value"] = self.lower_value

        # SET_RESET_LATCH: set/reset channels + default
        elif op == LogicOperation.SET_RESET_LATCH:
            data["set_channel"] = self.set_channel
            data["reset_channel"] = self.reset_channel
            data["default_state"] = self.default_state.value

        # TOGGLE: toggle channel + optional set/reset + edge + default
        elif op == LogicOperation.TOGGLE:
            data["toggle_channel"] = self.toggle_channel
            data["edge"] = self.edge.value
            data["default_state"] = self.default_state.value
            if self.set_channel:
                data["set_channel"] = self.set_channel
            if self.reset_channel:
                data["reset_channel"] = self.reset_channel

        # PULSE: channel + edge + pulse_count + time_on + retrigger
        elif op == LogicOperation.PULSE:
            data["channel"] = self.channel
            data["edge"] = self.edge.value
            data["pulse_count"] = self.pulse_count
            data["time_on_s"] = self.time_on_s
            data["retrigger"] = self.retrigger

        # FLASH: channel + time_on/off
        elif op == LogicOperation.FLASH:
            data["channel"] = self.channel
            data["time_on_s"] = self.time_on_s
            data["time_off_s"] = self.time_off_s

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogicChannel':
        # Parse operation
        op_str = data.get("operation", "is_true")
        try:
            operation = LogicOperation(op_str)
        except ValueError:
            operation = LogicOperation.IS_TRUE

        # Parse polarity
        pol_str = data.get("polarity", "normal")
        try:
            polarity = LogicPolarity(pol_str)
        except ValueError:
            polarity = LogicPolarity.NORMAL

        # Parse default_state
        def_str = data.get("default_state", "off")
        try:
            default_state = LogicDefaultState(def_str)
        except ValueError:
            default_state = LogicDefaultState.OFF

        # Parse edge
        edge_str = data.get("edge", "rising")
        try:
            edge = EdgeType(edge_str)
        except ValueError:
            edge = EdgeType.RISING

        return cls(
            name=data.get("channel_name", ""),
            channel_type=ChannelType.LOGIC,
            channel_id=data.get("channel_id", 0),
            operation=operation,
            channel=data.get("channel", ""),
            channel_2=data.get("channel_2", ""),
            true_delay_s=data.get("true_delay_s", 0.0),
            false_delay_s=data.get("false_delay_s", 0.0),
            constant=data.get("constant", 0.0),
            threshold=data.get("threshold", 0.0),
            time_on_s=data.get("time_on_s", 0.0),
            polarity=polarity,
            upper_value=data.get("upper_value", 100.0),
            lower_value=data.get("lower_value", 0.0),
            set_channel=data.get("set_channel", ""),
            reset_channel=data.get("reset_channel", ""),
            default_state=default_state,
            edge=edge,
            toggle_channel=data.get("toggle_channel", ""),
            pulse_count=data.get("pulse_count", 1),
            retrigger=data.get("retrigger", False),
            time_off_s=data.get("time_off_s", 0.5),
        )

    def get_input_channels(self) -> List[str]:
        op = self.operation
        channels = []

        if op in [LogicOperation.IS_TRUE, LogicOperation.IS_FALSE,
                  LogicOperation.EQUAL, LogicOperation.NOT_EQUAL,
                  LogicOperation.LESS, LogicOperation.GREATER,
                  LogicOperation.LESS_EQUAL, LogicOperation.GREATER_EQUAL,
                  LogicOperation.IN_RANGE,
                  LogicOperation.EDGE_RISING, LogicOperation.EDGE_FALLING,
                  LogicOperation.CHANGED, LogicOperation.HYSTERESIS,
                  LogicOperation.PULSE, LogicOperation.FLASH]:
            if self.channel:
                channels.append(self.channel)

        if op in [LogicOperation.AND, LogicOperation.OR, LogicOperation.XOR,
                  LogicOperation.NAND, LogicOperation.NOR]:
            if self.channel:
                channels.append(self.channel)
            if self.channel_2:
                channels.append(self.channel_2)

        if op == LogicOperation.SET_RESET_LATCH:
            if self.set_channel:
                channels.append(self.set_channel)
            if self.reset_channel:
                channels.append(self.reset_channel)

        if op == LogicOperation.TOGGLE:
            if self.toggle_channel:
                channels.append(self.toggle_channel)
            if self.set_channel:
                channels.append(self.set_channel)
            if self.reset_channel:
                channels.append(self.reset_channel)

        return channels

    def validate(self) -> List[str]:
        errors = super().validate()
        op = self.operation

        # Check required fields based on operation
        if op in [LogicOperation.IS_TRUE, LogicOperation.IS_FALSE,
                  LogicOperation.EQUAL, LogicOperation.NOT_EQUAL,
                  LogicOperation.LESS, LogicOperation.GREATER,
                  LogicOperation.LESS_EQUAL, LogicOperation.GREATER_EQUAL,
                  LogicOperation.IN_RANGE,
                  LogicOperation.EDGE_RISING, LogicOperation.EDGE_FALLING,
                  LogicOperation.CHANGED, LogicOperation.HYSTERESIS,
                  LogicOperation.PULSE, LogicOperation.FLASH]:
            if not self.channel:
                errors.append("Channel is required")

        if op in [LogicOperation.AND, LogicOperation.OR, LogicOperation.XOR,
                  LogicOperation.NAND, LogicOperation.NOR]:
            if not self.channel:
                errors.append("Channel #1 is required")
            if not self.channel_2:
                errors.append("Channel #2 is required")

        if op == LogicOperation.IN_RANGE:
            if self.lower_value >= self.upper_value:
                errors.append("Lower value must be less than upper value")

        if op == LogicOperation.SET_RESET_LATCH:
            if not self.set_channel:
                errors.append("Set channel is required")
            if not self.reset_channel:
                errors.append("Reset channel is required")

        if op == LogicOperation.TOGGLE:
            if not self.toggle_channel:
                errors.append("Toggle channel is required")

        if op == LogicOperation.HYSTERESIS:
            if self.lower_value >= self.upper_value:
                errors.append("Lower value must be less than upper value")

        return errors


@dataclass
class NumberChannel(ChannelBase):
    """Math/Number operation channel"""
    operation: MathOperation = MathOperation.CONSTANT
    # Input channel with multiplier: [(channel_id, multiplier), ...]
    inputs: List[str] = field(default_factory=list)
    input_multipliers: List[str] = field(default_factory=list)  # ChannelMultiplier values
    # Constant value (for CONSTANT and CHANNEL operations)
    constant_value: float = 0.0
    # Clamp parameters
    clamp_min: float = 0.0
    clamp_max: float = 100.0
    # Lookup values (for LOOKUP2-5 operations)
    lookup_values: List[float] = field(default_factory=list)
    # Decimal places for display
    decimal_places: int = 2

    def __post_init__(self):
        self.channel_type = ChannelType.NUMBER

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["operation"] = self.operation.value
        data["decimal_places"] = self.decimal_places
        op = self.operation

        # CONSTANT: only constant_value
        if op == MathOperation.CONSTANT:
            data["constant_value"] = self.constant_value

        # CHANNEL: one input with multiplier and optional constant
        elif op == MathOperation.CHANNEL:
            data["inputs"] = self.inputs[:1] if self.inputs else []
            data["input_multipliers"] = self.input_multipliers[:1] if self.input_multipliers else []
            data["constant_value"] = self.constant_value

        # Binary operations: two inputs with multipliers
        elif op in [MathOperation.ADD, MathOperation.SUBTRACT,
                    MathOperation.MULTIPLY, MathOperation.DIVIDE,
                    MathOperation.MODULO, MathOperation.MIN, MathOperation.MAX]:
            data["inputs"] = self.inputs[:2] if self.inputs else []
            data["input_multipliers"] = self.input_multipliers[:2] if self.input_multipliers else []

        # CLAMP: one input + min/max
        elif op == MathOperation.CLAMP:
            data["inputs"] = self.inputs[:1] if self.inputs else []
            data["input_multipliers"] = self.input_multipliers[:1] if self.input_multipliers else []
            data["clamp_min"] = self.clamp_min
            data["clamp_max"] = self.clamp_max

        # LOOKUP: one input + lookup values
        elif op in [MathOperation.LOOKUP2, MathOperation.LOOKUP3,
                    MathOperation.LOOKUP4, MathOperation.LOOKUP5]:
            data["inputs"] = self.inputs[:1] if self.inputs else []
            data["input_multipliers"] = self.input_multipliers[:1] if self.input_multipliers else []
            data["lookup_values"] = self.lookup_values

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NumberChannel':
        return cls(
            name=data.get("channel_name", ""),
            channel_type=ChannelType.NUMBER,
            channel_id=data.get("channel_id", 0),
            operation=MathOperation(data.get("operation", "constant")),
            inputs=data.get("inputs", []),
            input_multipliers=data.get("input_multipliers", []),
            constant_value=data.get("constant_value", 0.0),
            clamp_min=data.get("clamp_min", 0.0),
            clamp_max=data.get("clamp_max", 100.0),
            lookup_values=data.get("lookup_values", []),
            decimal_places=data.get("decimal_places", 2)
        )

    def get_input_channels(self) -> List[str]:
        return self.inputs.copy()
