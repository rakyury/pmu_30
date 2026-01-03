"""
Channel Enums - All enumeration types for PMU-30 channels

This module contains all Enum classes used by channel types.
"""

from enum import Enum


class ChannelType(Enum):
    """All supported channel types"""
    DIGITAL_INPUT = "digital_input"
    ANALOG_INPUT = "analog_input"
    POWER_OUTPUT = "power_output"
    HBRIDGE = "hbridge"
    CAN_RX = "can_rx"
    CAN_TX = "can_tx"
    LOGIC = "logic"
    NUMBER = "number"
    TABLE_2D = "table_2d"
    TABLE_3D = "table_3d"
    SWITCH = "switch"
    TIMER = "timer"
    FILTER = "filter"
    LUA_SCRIPT = "lua_script"
    PID = "pid"
    BLINKMARINE_KEYPAD = "blinkmarine_keypad"
    HANDLER = "handler"
    WIPER = "wiper"          # Wiper control module
    BLINKER = "blinker"      # Turn signal/hazard module
    # System channels (predefined, read-only)
    SYSTEM = "system"
    OUTPUT_STATUS = "output_status"


class DigitalInputSubtype(Enum):
    """Digital input subtypes"""
    SWITCH_ACTIVE_LOW = "switch_active_low"
    SWITCH_ACTIVE_HIGH = "switch_active_high"
    FREQUENCY = "frequency"
    RPM = "rpm"
    FLEX_FUEL = "flex_fuel"
    BEACON = "beacon"
    PULS_OIL_SENSOR = "puls_oil_sensor"
    KEYPAD_BUTTON = "keypad_button"  # Virtual button from CAN keypad


class ButtonMode(Enum):
    """Button function modes (ECUMaster compatible)"""
    DIRECT = "direct"               # Direct input passthrough (default)
    MOMENTARY = "momentary"         # Output only while pressed
    TOGGLE = "toggle"               # Toggle output on press
    LATCHING = "latching"           # Stay pressed until manual release (via reset channel)
    LONG_PRESS = "long_press"       # Different action for long hold
    DOUBLE_CLICK = "double_click"   # Detect double clicks
    PRESS_AND_HOLD = "press_and_hold"  # Timed action with progression


class AnalogInputSubtype(Enum):
    """Analog input subtypes"""
    SWITCH_ACTIVE_LOW = "switch_active_low"
    SWITCH_ACTIVE_HIGH = "switch_active_high"
    ROTARY_SWITCH = "rotary_switch"
    LINEAR = "linear"
    CALIBRATED = "calibrated"


class LogicOperation(Enum):
    """Logic operations with binary code mapping for firmware communication"""
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

    @property
    def binary_code(self) -> int:
        """Get firmware binary code for this operation"""
        codes = {
            "and": 0x00, "or": 0x01, "xor": 0x02, "nand": 0x03, "nor": 0x04,
            "is_true": 0x06, "is_false": 0x07,
            "greater": 0x10, "greater_equal": 0x11,
            "less": 0x12, "less_equal": 0x13,
            "equal": 0x14, "not_equal": 0x15,
            "in_range": 0x20, "hysteresis": 0x21,
            "edge_rising": 0x30, "edge_falling": 0x31,
            "changed": 0x40, "set_reset_latch": 0x41,
            "toggle": 0x42, "pulse": 0x43, "flash": 0x44,
        }
        return codes.get(self.value, 0x06)  # Default to IS_TRUE

    @classmethod
    def from_binary_code(cls, code: int) -> "LogicOperation":
        """Create LogicOperation from firmware binary code"""
        reverse_map = {
            0x00: "and", 0x01: "or", 0x02: "xor", 0x03: "nand", 0x04: "nor",
            0x06: "is_true", 0x07: "is_false",
            0x10: "greater", 0x11: "greater_equal",
            0x12: "less", 0x13: "less_equal",
            0x14: "equal", 0x15: "not_equal",
            0x20: "in_range", 0x21: "hysteresis",
            0x30: "edge_rising", 0x31: "edge_falling",
            0x40: "changed", 0x41: "set_reset_latch",
            0x42: "toggle", 0x43: "pulse", 0x44: "flash",
        }
        op_name = reverse_map.get(code, "is_true")
        return cls(op_name)


class LogicPolarity(Enum):
    """Hysteresis polarity"""
    NORMAL = "normal"
    INVERTED = "inverted"


class LogicDefaultState(Enum):
    """Default state for latches"""
    OFF = "off"
    ON = "on"


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
# CAN Message/Input Types
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


# ============================================================================
# Lua Script Types
# ============================================================================

class LuaTriggerType(Enum):
    """Lua script trigger types"""
    MANUAL = "manual"
    PERIODIC = "periodic"
    ON_INPUT_CHANGE = "on_input_change"
    ON_VIRTUAL_CHANGE = "on_virtual_change"
    ON_STARTUP = "on_startup"


class LuaPriority(Enum):
    """Lua script execution priority"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


# ============================================================================
# H-Bridge Types
# ============================================================================

class HBridgeMode(Enum):
    """H-Bridge operating modes"""
    COAST = "coast"           # Both switches OFF - motor coasts
    FORWARD = "forward"       # Forward direction
    REVERSE = "reverse"       # Reverse direction
    BRAKE = "brake"           # Active brake (both switches ON)
    WIPER_PARK = "wiper_park" # Wiper park sequence
    PID_POSITION = "pid_position"  # PID position control


class HBridgeMotorPreset(Enum):
    """Predefined motor configurations"""
    WIPER = "wiper"           # Windshield wiper motor
    WINDOW = "window"         # Power window motor
    SEAT = "seat"             # Seat adjustment motor
    VALVE = "valve"           # Valve actuator
    PUMP = "pump"             # Fluid pump motor
    CUSTOM = "custom"         # User-defined parameters


# ============================================================================
# Handler Types
# ============================================================================

class EventType(Enum):
    """Event types that can trigger handlers"""
    # Channel state events
    CHANNEL_ON = "channel_on"           # Channel turned ON (rising edge)
    CHANNEL_OFF = "channel_off"         # Channel turned OFF (falling edge)
    # Fault events
    CHANNEL_FAULT = "channel_fault"     # Channel entered fault state
    CHANNEL_CLEARED = "channel_cleared" # Channel fault cleared
    # Threshold events (for analog inputs)
    THRESHOLD_HIGH = "threshold_high"   # Input crossed threshold (rising)
    THRESHOLD_LOW = "threshold_low"     # Input crossed threshold (falling)
    # System events
    SYSTEM_UNDERVOLT = "system_undervolt"   # System undervoltage
    SYSTEM_OVERVOLT = "system_overvolt"     # System overvoltage
    SYSTEM_OVERTEMP = "system_overtemp"     # System overtemperature


class ActionType(Enum):
    """Action types that handlers can execute"""
    WRITE_CHANNEL = "write_channel"     # Write value to virtual channel
    SEND_CAN = "send_can"               # Send CAN message
    SEND_LIN = "send_lin"               # Send LIN message
    RUN_LUA = "run_lua"                 # Call Lua function
    SET_OUTPUT = "set_output"           # Set output state directly


# ============================================================================
# Wiper Types
# ============================================================================

class WiperMode(Enum):
    """Wiper operating modes"""
    OFF = "off"
    SLOW = "slow"
    FAST = "fast"
    INTERMITTENT = "intermittent"
    WASH = "wash"


# ============================================================================
# Blinker Types
# ============================================================================

class BlinkerMode(Enum):
    """Blinker operating modes"""
    OFF = "off"
    LEFT = "left"
    RIGHT = "right"
    HAZARD = "hazard"
