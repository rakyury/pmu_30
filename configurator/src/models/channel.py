"""
Channel - Unified Channel Model for PMU-30 Configurator

All channels in the system are virtual channels with different types.
Each channel generates a value that can be used by other channels.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class ChannelType(Enum):
    """All supported channel types"""
    DIGITAL_INPUT = "digital_input"
    ANALOG_INPUT = "analog_input"
    POWER_OUTPUT = "power_output"
    CAN_RX = "can_rx"
    CAN_TX = "can_tx"
    LOGIC = "logic"
    NUMBER = "number"
    TABLE_2D = "table_2d"
    TABLE_3D = "table_3d"
    SWITCH = "switch"
    TIMER = "timer"
    FILTER = "filter"
    ENUM = "enum"
    LUA_SCRIPT = "lua_script"


class DigitalInputSubtype(Enum):
    """Digital input subtypes"""
    SWITCH_ACTIVE_LOW = "switch_active_low"
    SWITCH_ACTIVE_HIGH = "switch_active_high"
    FREQUENCY = "frequency"
    RPM = "rpm"
    FLEX_FUEL = "flex_fuel"
    BEACON = "beacon"
    PULS_OIL_SENSOR = "puls_oil_sensor"


class AnalogInputSubtype(Enum):
    """Analog input subtypes"""
    SWITCH_ACTIVE_LOW = "switch_active_low"
    SWITCH_ACTIVE_HIGH = "switch_active_high"
    ROTARY_SWITCH = "rotary_switch"
    LINEAR = "linear"
    CALIBRATED = "calibrated"


class LogicOperation(Enum):
    """Logic operations"""
    # Basic logic
    IS_TRUE = "is_true"           # Channel != 0
    IS_FALSE = "is_false"         # Channel == 0
    # Comparison (channel vs constant)
    EQUAL = "equal"               # Channel == Constant
    NOT_EQUAL = "not_equal"       # Channel != Constant
    LESS = "less"                 # Channel < Constant
    GREATER = "greater"           # Channel > Constant
    LESS_EQUAL = "less_equal"     # Channel <= Constant
    GREATER_EQUAL = "greater_equal"  # Channel >= Constant
    IN_RANGE = "in_range"         # min <= Channel <= max
    # Multi-input logic
    AND = "and"                   # Channel1 AND Channel2
    OR = "or"                     # Channel1 OR Channel2
    XOR = "xor"                   # Channel1 XOR Channel2
    NOT = "not"                   # NOT Channel
    NAND = "nand"                 # NOT (Channel1 AND Channel2)
    NOR = "nor"                   # NOT (Channel1 OR Channel2)
    # Edge detection
    EDGE_RISING = "edge_rising"   # Rising edge (0->1)
    EDGE_FALLING = "edge_falling" # Falling edge (1->0)
    # Advanced
    CHANGED = "changed"           # Value changed by threshold within time
    HYSTERESIS = "hysteresis"     # Upper/lower threshold with polarity
    SET_RESET_LATCH = "set_reset_latch"  # SR latch
    TOGGLE = "toggle"             # Toggle on edge
    PULSE = "pulse"               # Generate pulse on edge
    FLASH = "flash"               # Periodic on/off when channel active


class ChannelMultiplier(Enum):
    """Channel value multiplier for math operations"""
    RAW = "raw"
    MUL_1 = "*1"
    MUL_10 = "*10"
    MUL_100 = "*100"
    MUL_1000 = "*1000"


class MathOperation(Enum):
    """Math operations for Number channel"""
    CONSTANT = "constant"
    CHANNEL = "channel"  # Channel or constant
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    DIVIDE = "divide"
    MODULO = "modulo"
    MIN = "min"
    MAX = "max"
    CLAMP = "clamp"
    LOOKUP2 = "lookup2"
    LOOKUP3 = "lookup3"
    LOOKUP4 = "lookup4"
    LOOKUP5 = "lookup5"


class FilterType(Enum):
    """Filter types"""
    MOVING_AVG = "moving_avg"
    LOW_PASS = "low_pass"
    MIN_WINDOW = "min_window"
    MAX_WINDOW = "max_window"
    MEDIAN = "median"


class EdgeType(Enum):
    """Edge detection types"""
    RISING = "rising"
    FALLING = "falling"
    BOTH = "both"


# ============================================================================
# CAN Message/Input Types (Two-Level Architecture)
# ============================================================================

class CanMessageType(Enum):
    """CAN Message types"""
    NORMAL = "normal"           # Standard single-frame message
    COMPOUND = "compound"       # Multiplexed message (multiple IDs)
    PMU1_RX = "pmu1_rx"        # Predefined PMU1 receive format
    PMU2_RX = "pmu2_rx"        # Predefined PMU2 receive format
    PMU3_RX = "pmu3_rx"        # Predefined PMU3 receive format


class CanTimeoutBehavior(Enum):
    """Timeout behavior for CAN inputs"""
    USE_DEFAULT = "use_default"
    HOLD_LAST = "hold_last"
    SET_ZERO = "set_zero"


class CanDataType(Enum):
    """CAN signal data types"""
    UNSIGNED = "unsigned"
    SIGNED = "signed"
    FLOAT = "float"


class CanDataFormat(Enum):
    """Predefined data formats"""
    BIT_8 = "8bit"
    BIT_16 = "16bit"
    BIT_32 = "32bit"
    CUSTOM = "custom"


class TimerMode(Enum):
    """Timer counting modes"""
    COUNT_UP = "count_up"
    COUNT_DOWN = "count_down"


@dataclass
class ChannelBase:
    """Base class for all channels"""
    id: str
    channel_type: ChannelType

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "channel_type": self.channel_type.value
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChannelBase':
        """Create from dictionary"""
        return cls(
            id=data.get("id", ""),
            channel_type=ChannelType(data.get("channel_type", "digital_input"))
        )

    def validate(self) -> List[str]:
        """Validate configuration, return list of errors"""
        errors = []
        if not self.id:
            errors.append("ID is required")
        return errors

    def get_output_channels(self) -> List[str]:
        """Get list of channels this channel outputs"""
        return [self.id]

    def get_input_channels(self) -> List[str]:
        """Get list of channels this channel reads from"""
        return []


@dataclass
class DigitalInputChannel(ChannelBase):
    """Digital input channel with multiple subtypes"""
    subtype: DigitalInputSubtype = DigitalInputSubtype.SWITCH_ACTIVE_LOW
    input_pin: int = 0  # D1-D8 -> 0-7
    enable_pullup: bool = False
    threshold_voltage: float = 2.5
    debounce_ms: int = 50
    # Frequency/RPM specific
    trigger_edge: EdgeType = EdgeType.RISING
    multiplier: float = 1.0
    divider: float = 1.0
    timeout_ms: int = 1000
    number_of_teeth: int = 1  # RPM specific

    def __post_init__(self):
        self.channel_type = ChannelType.DIGITAL_INPUT

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["subtype"] = self.subtype.value
        data["input_pin"] = self.input_pin
        data["enable_pullup"] = self.enable_pullup
        data["threshold_voltage"] = self.threshold_voltage
        data["debounce_ms"] = self.debounce_ms

        # Frequency/RPM specific fields
        if self.subtype in [DigitalInputSubtype.FREQUENCY, DigitalInputSubtype.RPM]:
            data["trigger_edge"] = self.trigger_edge.value
            data["multiplier"] = self.multiplier
            data["divider"] = self.divider
            data["timeout_ms"] = self.timeout_ms

        # RPM specific
        if self.subtype == DigitalInputSubtype.RPM:
            data["number_of_teeth"] = self.number_of_teeth

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DigitalInputChannel':
        return cls(
            id=data.get("id", ""),
            channel_type=ChannelType.DIGITAL_INPUT,
            subtype=DigitalInputSubtype(data.get("subtype", "switch_active_low")),
            input_pin=data.get("input_pin", 0),
            enable_pullup=data.get("enable_pullup", False),
            threshold_voltage=data.get("threshold_voltage", 2.5),
            debounce_ms=data.get("debounce_ms", 50),
            trigger_edge=EdgeType(data.get("trigger_edge", "rising")),
            multiplier=data.get("multiplier", 1.0),
            divider=data.get("divider", 1.0),
            timeout_ms=data.get("timeout_ms", 1000),
            number_of_teeth=data.get("number_of_teeth", 1)
        )

    def validate(self) -> List[str]:
        errors = super().validate()
        if not 0 <= self.input_pin <= 7:
            errors.append("Input pin must be between 0 and 7 (D1-D8)")
        if self.threshold_voltage < 0 or self.threshold_voltage > 30:
            errors.append("Threshold voltage must be between 0 and 30V")
        if self.subtype == DigitalInputSubtype.RPM and self.number_of_teeth < 1:
            errors.append("Number of teeth must be at least 1")
        return errors


@dataclass
class AnalogInputChannel(ChannelBase):
    """Analog input channel"""
    subtype: AnalogInputSubtype = AnalogInputSubtype.LINEAR
    input_pin: int = 0  # A1-A20 -> 0-19
    pullup_option: str = "1m_down"  # none, 1m_down, 10k_up, 10k_down, 100k_up, 100k_down
    decimal_places: int = 0
    # Switch mode (active low/high)
    threshold_high: float = 2.5
    threshold_high_time_ms: int = 50
    threshold_low: float = 1.5
    threshold_low_time_ms: int = 50
    # Rotary switch mode
    positions: int = 4
    debounce_ms: int = 50
    # Linear mode
    min_voltage: float = 0.0
    max_voltage: float = 5.0
    min_value: float = 0.0
    max_value: float = 100.0
    # Calibrated mode
    calibration_points: List[Dict[str, float]] = field(default_factory=list)

    def __post_init__(self):
        self.channel_type = ChannelType.ANALOG_INPUT

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["subtype"] = self.subtype.value
        data["input_pin"] = self.input_pin
        data["pullup_option"] = self.pullup_option
        data["decimal_places"] = self.decimal_places

        # Switch mode (active low/high)
        if self.subtype in [AnalogInputSubtype.SWITCH_ACTIVE_LOW, AnalogInputSubtype.SWITCH_ACTIVE_HIGH]:
            data["threshold_high"] = self.threshold_high
            data["threshold_high_time_ms"] = self.threshold_high_time_ms
            data["threshold_low"] = self.threshold_low
            data["threshold_low_time_ms"] = self.threshold_low_time_ms

        # Rotary switch mode
        elif self.subtype == AnalogInputSubtype.ROTARY_SWITCH:
            data["positions"] = self.positions
            data["debounce_ms"] = self.debounce_ms

        # Linear mode
        elif self.subtype == AnalogInputSubtype.LINEAR:
            data["min_voltage"] = self.min_voltage
            data["max_voltage"] = self.max_voltage
            data["min_value"] = self.min_value
            data["max_value"] = self.max_value

        # Calibrated mode
        elif self.subtype == AnalogInputSubtype.CALIBRATED:
            data["calibration_points"] = self.calibration_points

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnalogInputChannel':
        return cls(
            id=data.get("id", ""),
            channel_type=ChannelType.ANALOG_INPUT,
            subtype=AnalogInputSubtype(data.get("subtype", "linear")),
            input_pin=data.get("input_pin", 0),
            pullup_option=data.get("pullup_option", "1m_down"),
            decimal_places=data.get("decimal_places", 0),
            threshold_high=data.get("threshold_high", 2.5),
            threshold_high_time_ms=data.get("threshold_high_time_ms", 50),
            threshold_low=data.get("threshold_low", 1.5),
            threshold_low_time_ms=data.get("threshold_low_time_ms", 50),
            positions=data.get("positions", 4),
            debounce_ms=data.get("debounce_ms", 50),
            min_voltage=data.get("min_voltage", 0.0),
            max_voltage=data.get("max_voltage", 5.0),
            min_value=data.get("min_value", 0.0),
            max_value=data.get("max_value", 100.0),
            calibration_points=data.get("calibration_points", [])
        )


@dataclass
class PowerOutputChannel(ChannelBase):
    """Power output channel (PROFET)"""
    output_pins: List[int] = field(default_factory=lambda: [0])  # O1-O30 -> 0-29
    source_channel: str = ""  # Control source channel
    # PWM
    pwm_enabled: bool = False
    pwm_frequency_hz: int = 1000
    duty_channel: str = ""  # Channel for duty control
    duty_fixed: float = 100.0  # Fixed duty if no channel
    soft_start_ms: int = 0
    # Protection
    current_limit_a: float = 25.0
    inrush_current_a: float = 50.0
    inrush_time_ms: int = 100
    retry_count: int = 3
    retry_forever: bool = False

    def __post_init__(self):
        self.channel_type = ChannelType.POWER_OUTPUT

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "output_pins": self.output_pins,
            "source_channel": self.source_channel,
            "pwm_enabled": self.pwm_enabled,
            "pwm_frequency_hz": self.pwm_frequency_hz,
            "duty_channel": self.duty_channel,
            "duty_fixed": self.duty_fixed,
            "soft_start_ms": self.soft_start_ms,
            "current_limit_a": self.current_limit_a,
            "inrush_current_a": self.inrush_current_a,
            "inrush_time_ms": self.inrush_time_ms,
            "retry_count": self.retry_count,
            "retry_forever": self.retry_forever
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PowerOutputChannel':
        return cls(
            id=data.get("id", ""),
            channel_type=ChannelType.POWER_OUTPUT,
            output_pins=data.get("output_pins", [0]),
            source_channel=data.get("source_channel", ""),
            pwm_enabled=data.get("pwm_enabled", False),
            pwm_frequency_hz=data.get("pwm_frequency_hz", 1000),
            duty_channel=data.get("duty_channel", ""),
            duty_fixed=data.get("duty_fixed", 100.0),
            soft_start_ms=data.get("soft_start_ms", 0),
            current_limit_a=data.get("current_limit_a", 25.0),
            inrush_current_a=data.get("inrush_current_a", 50.0),
            inrush_time_ms=data.get("inrush_time_ms", 100),
            retry_count=data.get("retry_count", 3),
            retry_forever=data.get("retry_forever", False)
        )

    def get_input_channels(self) -> List[str]:
        channels = []
        if self.source_channel:
            channels.append(self.source_channel)
        if self.duty_channel:
            channels.append(self.duty_channel)
        return channels


class LogicPolarity(Enum):
    """Hysteresis polarity"""
    NORMAL = "normal"
    INVERTED = "inverted"


class LogicDefaultState(Enum):
    """Default state for latches"""
    OFF = "off"
    ON = "on"


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

        # NOT: single channel + delays
        elif op == LogicOperation.NOT:
            data["channel"] = self.channel
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

        # FLASH: channel + time_on + time_off
        elif op == LogicOperation.FLASH:
            data["channel"] = self.channel
            data["time_on_s"] = self.time_on_s
            data["time_off_s"] = self.time_off_s

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogicChannel':
        return cls(
            id=data.get("id", ""),
            channel_type=ChannelType.LOGIC,
            operation=LogicOperation(data.get("operation", "is_true")),
            channel=data.get("channel", ""),
            channel_2=data.get("channel_2", ""),
            true_delay_s=data.get("true_delay_s", 0.0),
            false_delay_s=data.get("false_delay_s", 0.0),
            constant=data.get("constant", 0.0),
            threshold=data.get("threshold", 0.0),
            time_on_s=data.get("time_on_s", 0.0),
            polarity=LogicPolarity(data.get("polarity", "normal")),
            upper_value=data.get("upper_value", 100.0),
            lower_value=data.get("lower_value", 0.0),
            set_channel=data.get("set_channel", ""),
            reset_channel=data.get("reset_channel", ""),
            default_state=LogicDefaultState(data.get("default_state", "off")),
            edge=EdgeType(data.get("edge", "rising")),
            toggle_channel=data.get("toggle_channel", ""),
            pulse_count=data.get("pulse_count", 1),
            retrigger=data.get("retrigger", False),
            time_off_s=data.get("time_off_s", 0.5)
        )

    def get_input_channels(self) -> List[str]:
        """Get list of channels this channel reads from"""
        channels = []
        op = self.operation

        if op in [LogicOperation.IS_TRUE, LogicOperation.IS_FALSE,
                  LogicOperation.EQUAL, LogicOperation.NOT_EQUAL,
                  LogicOperation.LESS, LogicOperation.GREATER,
                  LogicOperation.LESS_EQUAL, LogicOperation.GREATER_EQUAL,
                  LogicOperation.IN_RANGE, LogicOperation.NOT,
                  LogicOperation.EDGE_RISING, LogicOperation.EDGE_FALLING,
                  LogicOperation.CHANGED, LogicOperation.HYSTERESIS,
                  LogicOperation.FLASH]:
            if self.channel:
                channels.append(self.channel)

        elif op in [LogicOperation.AND, LogicOperation.OR, LogicOperation.XOR,
                    LogicOperation.NAND, LogicOperation.NOR]:
            if self.channel:
                channels.append(self.channel)
            if self.channel_2:
                channels.append(self.channel_2)

        elif op == LogicOperation.SET_RESET_LATCH:
            if self.set_channel:
                channels.append(self.set_channel)
            if self.reset_channel:
                channels.append(self.reset_channel)

        elif op == LogicOperation.TOGGLE:
            if self.toggle_channel:
                channels.append(self.toggle_channel)
            if self.set_channel:
                channels.append(self.set_channel)
            if self.reset_channel:
                channels.append(self.reset_channel)

        elif op == LogicOperation.PULSE:
            if self.channel:
                channels.append(self.channel)

        return channels

    def validate(self) -> List[str]:
        errors = super().validate()
        op = self.operation

        if op in [LogicOperation.IS_TRUE, LogicOperation.IS_FALSE,
                  LogicOperation.EQUAL, LogicOperation.NOT_EQUAL,
                  LogicOperation.LESS, LogicOperation.GREATER,
                  LogicOperation.LESS_EQUAL, LogicOperation.GREATER_EQUAL,
                  LogicOperation.IN_RANGE, LogicOperation.NOT,
                  LogicOperation.EDGE_RISING, LogicOperation.EDGE_FALLING,
                  LogicOperation.CHANGED, LogicOperation.HYSTERESIS,
                  LogicOperation.FLASH, LogicOperation.PULSE]:
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
            id=data.get("id", ""),
            channel_type=ChannelType.NUMBER,
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
            id=data.get("id", ""),
            channel_type=ChannelType.TIMER,
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
            id=data.get("id", ""),
            channel_type=ChannelType.FILTER,
            filter_type=FilterType(data.get("filter_type", "moving_avg")),
            input_channel=data.get("input_channel", ""),
            window_size=data.get("window_size", 10),
            time_constant=data.get("time_constant", 0.1)
        )

    def get_input_channels(self) -> List[str]:
        return [self.input_channel] if self.input_channel else []


@dataclass
class EnumItem:
    """Single enumeration item"""
    value: int
    text: str
    color: str = "#FFFFFF"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "text": self.text,
            "color": self.color
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnumItem':
        return cls(
            value=data.get("value", 0),
            text=data.get("text", ""),
            color=data.get("color", "#FFFFFF")
        )


@dataclass
class EnumChannel(ChannelBase):
    """Enumeration channel"""
    is_bitfield: bool = False
    items: List[EnumItem] = field(default_factory=list)

    def __post_init__(self):
        self.channel_type = ChannelType.ENUM

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "is_bitfield": self.is_bitfield,
            "items": [item.to_dict() for item in self.items]
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EnumChannel':
        items = [EnumItem.from_dict(item) for item in data.get("items", [])]
        return cls(
            id=data.get("id", ""),
            channel_type=ChannelType.ENUM,
            is_bitfield=data.get("is_bitfield", False),
            items=items
        )


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
            id=data.get("id", ""),
            channel_type=ChannelType.TABLE_2D,
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
        data = super().to_dict()
        data.update({
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
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Table3DChannel':
        return cls(
            id=data.get("id", ""),
            channel_type=ChannelType.TABLE_3D,
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
            id=data.get("id", ""),
            channel_type=ChannelType.SWITCH,
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


# ============================================================================
# CAN Message Object (Level 1 - Container)
# ============================================================================

@dataclass
class CanMessage:
    """CAN Message Object - defines CAN frame structure (Level 1)

    This is NOT a channel, but a container for CAN frame properties.
    Multiple CanRxChannels (CAN Inputs) can reference the same CanMessage.
    """
    id: str                                    # Unique message ID (e.g., "msg_ecu_base")
    name: str = ""                             # Human-readable name
    can_bus: int = 1                           # CAN bus (1-4)
    base_id: int = 0                           # Base CAN ID (11-bit or 29-bit)
    is_extended: bool = False                  # Extended (29-bit) ID
    message_type: CanMessageType = CanMessageType.NORMAL
    frame_count: int = 1                       # 1-8 for compound messages
    dlc: int = 8                               # Data Length Code (0-64)
    timeout_ms: int = 500                      # Reception timeout
    enabled: bool = True
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "can_bus": self.can_bus,
            "base_id": self.base_id,
            "is_extended": self.is_extended,
            "message_type": self.message_type.value,
            "frame_count": self.frame_count,
            "dlc": self.dlc,
            "timeout_ms": self.timeout_ms,
            "enabled": self.enabled,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CanMessage':
        """Create from dictionary"""
        msg_type_str = data.get("message_type", "normal")
        try:
            msg_type = CanMessageType(msg_type_str)
        except ValueError:
            msg_type = CanMessageType.NORMAL

        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            can_bus=data.get("can_bus", 1),
            base_id=data.get("base_id", 0),
            is_extended=data.get("is_extended", False),
            message_type=msg_type,
            frame_count=data.get("frame_count", 1),
            dlc=data.get("dlc", 8),
            timeout_ms=data.get("timeout_ms", 500),
            enabled=data.get("enabled", True),
            description=data.get("description", "")
        )

    def validate(self) -> List[str]:
        """Validate configuration, return list of errors"""
        errors = []
        if not self.id:
            errors.append("Message ID is required")
        if not self.id.replace("_", "").isalnum():
            errors.append("Message ID must contain only letters, numbers, and underscores")
        if self.can_bus < 1 or self.can_bus > 4:
            errors.append("CAN bus must be between 1 and 4")
        if self.is_extended:
            if self.base_id < 0 or self.base_id > 0x1FFFFFFF:
                errors.append("Extended CAN ID must be between 0 and 0x1FFFFFFF")
        else:
            if self.base_id < 0 or self.base_id > 0x7FF:
                errors.append("Standard CAN ID must be between 0 and 0x7FF")
        if self.frame_count < 1 or self.frame_count > 8:
            errors.append("Frame count must be between 1 and 8")
        if self.dlc < 0 or self.dlc > 64:
            errors.append("DLC must be between 0 and 64")
        if self.timeout_ms < 0 or self.timeout_ms > 65535:
            errors.append("Timeout must be between 0 and 65535 ms")
        return errors

    def get_id_string(self) -> str:
        """Get formatted CAN ID string (hex)"""
        if self.is_extended:
            return f"0x{self.base_id:08X}"
        return f"0x{self.base_id:03X}"


# ============================================================================
# CAN Input Channel (Level 2 - Signal Extraction)
# ============================================================================

@dataclass
class CanRxChannel(ChannelBase):
    """CAN Input (Signal) - extracts data from CAN Message Object (Level 2)

    New architecture: References a CanMessage by message_ref.
    Legacy fields (can_bus, message_id, is_extended) kept for backwards compatibility.
    """
    # New fields - Message reference
    message_ref: str = ""                      # Reference to CanMessage.id

    # Frame offset (for compound/multiplexed messages)
    frame_offset: int = 0                      # +0 to +7 for compound messages

    # Data extraction
    data_type: CanDataType = CanDataType.UNSIGNED
    data_format: CanDataFormat = CanDataFormat.BIT_16
    byte_order: str = "little_endian"          # little_endian or big_endian
    byte_offset: int = 0                       # 0-7 byte position

    # Custom bitfield (when data_format == CUSTOM)
    start_bit: int = 0
    bit_length: int = 16

    # Scaling (Ecumaster style: multiplier/divider instead of factor)
    multiplier: float = 1.0
    divider: float = 1.0
    offset: float = 0.0
    decimal_places: int = 0

    # Timeout behavior
    default_value: float = 0.0
    timeout_behavior: CanTimeoutBehavior = CanTimeoutBehavior.USE_DEFAULT

    # Legacy fields (kept for backwards compatibility / migration)
    can_bus: int = 1                           # Deprecated - use message_ref
    message_id: int = 0                        # Deprecated - use message_ref
    is_extended: bool = False                  # Deprecated - use message_ref
    length: int = 8                            # Deprecated - use bit_length
    value_type: str = "unsigned"               # Deprecated - use data_type
    factor: float = 1.0                        # Deprecated - use multiplier
    timeout_ms: int = 1000                     # Deprecated - use CanMessage.timeout_ms

    def __post_init__(self):
        self.channel_type = ChannelType.CAN_RX

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()

        # New architecture fields (always saved)
        data.update({
            "message_ref": self.message_ref,
            "frame_offset": self.frame_offset,
            "data_type": self.data_type.value if isinstance(self.data_type, CanDataType) else self.data_type,
            "data_format": self.data_format.value if isinstance(self.data_format, CanDataFormat) else self.data_format,
            "byte_order": self.byte_order,
            "byte_offset": self.byte_offset,
            "start_bit": self.start_bit,
            "bit_length": self.bit_length,
            "multiplier": self.multiplier,
            "divider": self.divider,
            "offset": self.offset,
            "decimal_places": self.decimal_places,
            "default_value": self.default_value,
            "timeout_behavior": self.timeout_behavior.value if isinstance(self.timeout_behavior, CanTimeoutBehavior) else self.timeout_behavior,
        })

        # Legacy fields (for backwards compatibility)
        if not self.message_ref:
            # Only include legacy fields if message_ref is not set
            data.update({
                "can_bus": self.can_bus,
                "message_id": self.message_id,
                "is_extended": self.is_extended,
                "length": self.length,
                "value_type": self.value_type,
                "factor": self.factor,
                "timeout_ms": self.timeout_ms
            })

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CanRxChannel':
        # Parse data_type
        data_type_str = data.get("data_type", data.get("value_type", "unsigned"))
        try:
            data_type = CanDataType(data_type_str)
        except ValueError:
            data_type = CanDataType.UNSIGNED

        # Parse data_format
        data_format_str = data.get("data_format", "16bit")
        try:
            data_format = CanDataFormat(data_format_str)
        except ValueError:
            data_format = CanDataFormat.BIT_16

        # Parse timeout_behavior
        timeout_beh_str = data.get("timeout_behavior", "use_default")
        try:
            timeout_behavior = CanTimeoutBehavior(timeout_beh_str)
        except ValueError:
            timeout_behavior = CanTimeoutBehavior.USE_DEFAULT

        return cls(
            id=data.get("id", ""),
            channel_type=ChannelType.CAN_RX,
            # New fields
            message_ref=data.get("message_ref", ""),
            frame_offset=data.get("frame_offset", 0),
            data_type=data_type,
            data_format=data_format,
            byte_order=data.get("byte_order", "little_endian"),
            byte_offset=data.get("byte_offset", 0),
            start_bit=data.get("start_bit", 0),
            bit_length=data.get("bit_length", data.get("length", 16)),
            multiplier=data.get("multiplier", data.get("factor", 1.0)),
            divider=data.get("divider", 1.0),
            offset=data.get("offset", 0.0),
            decimal_places=data.get("decimal_places", 0),
            default_value=data.get("default_value", 0.0),
            timeout_behavior=timeout_behavior,
            # Legacy fields
            can_bus=data.get("can_bus", 1),
            message_id=data.get("message_id", 0),
            is_extended=data.get("is_extended", False),
            length=data.get("length", 8),
            value_type=data.get("value_type", "unsigned"),
            factor=data.get("factor", 1.0),
            timeout_ms=data.get("timeout_ms", 1000)
        )

    def validate(self) -> List[str]:
        """Validate configuration, return list of errors"""
        errors = super().validate()

        # New architecture validation
        if self.message_ref:
            if self.frame_offset < 0 or self.frame_offset > 7:
                errors.append("Frame offset must be between 0 and 7")
            if self.byte_offset < 0 or self.byte_offset > 7:
                errors.append("Byte offset must be between 0 and 7")
            if self.data_format == CanDataFormat.CUSTOM:
                if self.start_bit < 0 or self.start_bit > 63:
                    errors.append("Start bit must be between 0 and 63")
                if self.bit_length < 1 or self.bit_length > 64:
                    errors.append("Bit length must be between 1 and 64")
            if self.divider == 0:
                errors.append("Divider cannot be zero")

        return errors


@dataclass
class CanTxSignal:
    """Single CAN transmit signal"""
    source_channel: str
    start_bit: int = 0
    length: int = 8
    byte_order: str = "little_endian"
    factor: float = 1.0
    offset: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_channel": self.source_channel,
            "start_bit": self.start_bit,
            "length": self.length,
            "byte_order": self.byte_order,
            "factor": self.factor,
            "offset": self.offset
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CanTxSignal':
        return cls(
            source_channel=data.get("source_channel", ""),
            start_bit=data.get("start_bit", 0),
            length=data.get("length", 8),
            byte_order=data.get("byte_order", "little_endian"),
            factor=data.get("factor", 1.0),
            offset=data.get("offset", 0.0)
        )


@dataclass
class CanTxChannel(ChannelBase):
    """CAN transmit channel"""
    can_bus: int = 1
    message_id: int = 0
    is_extended: bool = False
    cycle_time_ms: int = 100
    signals: List[CanTxSignal] = field(default_factory=list)

    def __post_init__(self):
        self.channel_type = ChannelType.CAN_TX

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "can_bus": self.can_bus,
            "message_id": self.message_id,
            "is_extended": self.is_extended,
            "cycle_time_ms": self.cycle_time_ms,
            "signals": [sig.to_dict() for sig in self.signals]
        })
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CanTxChannel':
        signals = [CanTxSignal.from_dict(sig) for sig in data.get("signals", [])]
        return cls(
            id=data.get("id", ""),
            channel_type=ChannelType.CAN_TX,
            can_bus=data.get("can_bus", 1),
            message_id=data.get("message_id", 0),
            is_extended=data.get("is_extended", False),
            cycle_time_ms=data.get("cycle_time_ms", 100),
            signals=signals
        )

    def get_input_channels(self) -> List[str]:
        return [sig.source_channel for sig in self.signals if sig.source_channel]


# Channel Type to Class mapping
CHANNEL_CLASS_MAP = {
    ChannelType.DIGITAL_INPUT: DigitalInputChannel,
    ChannelType.ANALOG_INPUT: AnalogInputChannel,
    ChannelType.POWER_OUTPUT: PowerOutputChannel,
    ChannelType.LOGIC: LogicChannel,
    ChannelType.NUMBER: NumberChannel,
    ChannelType.TIMER: TimerChannel,
    ChannelType.FILTER: FilterChannel,
    ChannelType.ENUM: EnumChannel,
    ChannelType.TABLE_2D: Table2DChannel,
    ChannelType.TABLE_3D: Table3DChannel,
    ChannelType.SWITCH: SwitchChannel,
    ChannelType.CAN_RX: CanRxChannel,
    ChannelType.CAN_TX: CanTxChannel,
}


class ChannelFactory:
    """Factory for creating Channel instances"""

    @staticmethod
    def create(channel_type: ChannelType, **kwargs) -> ChannelBase:
        """Create Channel instance by type"""
        channel_class = CHANNEL_CLASS_MAP.get(channel_type)
        if channel_class:
            return channel_class(**kwargs)
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


# Prefix mapping for channel IDs
CHANNEL_PREFIX_MAP = {
    ChannelType.DIGITAL_INPUT: "di_",
    ChannelType.ANALOG_INPUT: "ai_",
    ChannelType.POWER_OUTPUT: "out_",
    ChannelType.LOGIC: "l_",
    ChannelType.NUMBER: "n_",
    ChannelType.TIMER: "tm_",
    ChannelType.FILTER: "flt_",
    ChannelType.ENUM: "e_",
    ChannelType.TABLE_2D: "t2d_",
    ChannelType.TABLE_3D: "t3d_",
    ChannelType.SWITCH: "sw_",
    ChannelType.CAN_RX: "crx_",
    ChannelType.CAN_TX: "ctx_",
}


def get_channel_prefix(channel_type: ChannelType) -> str:
    """Get standard prefix for channel type"""
    return CHANNEL_PREFIX_MAP.get(channel_type, "")


def get_channel_display_name(channel_type: ChannelType) -> str:
    """Get human-readable name for channel type"""
    names = {
        ChannelType.DIGITAL_INPUT: "Digital Input",
        ChannelType.ANALOG_INPUT: "Analog Input",
        ChannelType.POWER_OUTPUT: "Power Output",
        ChannelType.LOGIC: "Logic Function",
        ChannelType.NUMBER: "Math/Number",
        ChannelType.TIMER: "Timer",
        ChannelType.FILTER: "Filter",
        ChannelType.ENUM: "Enumeration",
        ChannelType.TABLE_2D: "2D Table",
        ChannelType.TABLE_3D: "3D Table",
        ChannelType.SWITCH: "Switch",
        ChannelType.CAN_RX: "CAN Input",
        ChannelType.CAN_TX: "CAN Output",
    }
    return names.get(channel_type, channel_type.value)


# Backwards compatibility aliases
GPIOType = ChannelType
GPIOBase = ChannelBase
DigitalInputGPIO = DigitalInputChannel
AnalogInputGPIO = AnalogInputChannel
PowerOutputGPIO = PowerOutputChannel
LogicGPIO = LogicChannel
NumberGPIO = NumberChannel
TimerGPIO = TimerChannel
FilterGPIO = FilterChannel
EnumGPIO = EnumChannel
Table2DGPIO = Table2DChannel
Table3DGPIO = Table3DChannel
SwitchGPIO = SwitchChannel
CanRxGPIO = CanRxChannel
CanTxGPIO = CanTxChannel
GPIO_CLASS_MAP = CHANNEL_CLASS_MAP
GPIOFactory = ChannelFactory
GPIO_PREFIX_MAP = CHANNEL_PREFIX_MAP
GPIO_TYPE_PREFIXES = CHANNEL_PREFIX_MAP
get_gpio_prefix = get_channel_prefix
get_gpio_display_name = get_channel_display_name
