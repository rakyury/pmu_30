"""
Input Channels - Digital and Analog input channel types

This module contains input channel classes for physical inputs.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any

from .enums import (
    ChannelType,
    DigitalInputSubtype,
    ButtonMode,
    AnalogInputSubtype,
    EdgeType,
)
from .base import ChannelBase


@dataclass
class DigitalInputChannel(ChannelBase):
    """Digital input channel with multiple subtypes"""
    subtype: DigitalInputSubtype = DigitalInputSubtype.SWITCH_ACTIVE_LOW
    input_pin: int = 0  # D1-D8 -> 0-7
    enable_pullup: bool = False
    threshold_voltage: float = 2.5
    debounce_ms: int = 50
    invert: bool = False  # Invert input logic
    # Frequency/RPM specific
    trigger_edge: EdgeType = EdgeType.RISING
    multiplier: float = 1.0
    divider: float = 1.0
    timeout_ms: int = 1000
    number_of_teeth: int = 1  # RPM specific
    # Button function mode (ECUMaster compatible)
    button_mode: ButtonMode = ButtonMode.DIRECT
    # Long press settings
    long_press_ms: int = 500             # Time threshold for long press detection
    long_press_output: str = ""          # Separate output for long press (optional)
    # Double click settings
    double_click_ms: int = 300           # Window for detecting double clicks
    double_click_output: str = ""        # Separate output for double click (optional)
    # Press and hold settings
    hold_start_ms: int = 500             # Time to start progressive action
    hold_full_ms: int = 2000             # Time to reach full action
    # Latching/Toggle settings
    reset_channel: str = ""              # Channel to reset latch/toggle
    # CAN Keypad button specific (ECUMaster style)
    keypad_id: str = ""                  # Reference to parent keypad ID
    button_index: int = 0                # Button index (0-15)

    def __post_init__(self):
        self.channel_type = ChannelType.DIGITAL_INPUT

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["subtype"] = self.subtype.value
        data["input_pin"] = self.input_pin
        data["enable_pullup"] = self.enable_pullup
        data["threshold_voltage"] = self.threshold_voltage
        data["debounce_ms"] = self.debounce_ms
        data["invert"] = self.invert

        # Frequency/RPM specific fields
        if self.subtype in [DigitalInputSubtype.FREQUENCY, DigitalInputSubtype.RPM]:
            data["trigger_edge"] = self.trigger_edge.value
            data["multiplier"] = self.multiplier
            data["divider"] = self.divider
            data["timeout_ms"] = self.timeout_ms

        # RPM specific
        if self.subtype == DigitalInputSubtype.RPM:
            data["number_of_teeth"] = self.number_of_teeth

        # Button function settings (for switch subtypes)
        if self.subtype in [DigitalInputSubtype.SWITCH_ACTIVE_LOW, DigitalInputSubtype.SWITCH_ACTIVE_HIGH]:
            data["button_mode"] = self.button_mode.value
            if self.button_mode == ButtonMode.LONG_PRESS:
                data["long_press_ms"] = self.long_press_ms
                data["long_press_output"] = self.long_press_output
            elif self.button_mode == ButtonMode.DOUBLE_CLICK:
                data["double_click_ms"] = self.double_click_ms
                data["double_click_output"] = self.double_click_output
            elif self.button_mode == ButtonMode.PRESS_AND_HOLD:
                data["hold_start_ms"] = self.hold_start_ms
                data["hold_full_ms"] = self.hold_full_ms
            elif self.button_mode in [ButtonMode.LATCHING, ButtonMode.TOGGLE]:
                data["reset_channel"] = self.reset_channel

        # CAN Keypad button specific fields
        if self.subtype == DigitalInputSubtype.KEYPAD_BUTTON:
            data["keypad_id"] = self.keypad_id
            data["button_index"] = self.button_index
            data["button_mode"] = self.button_mode.value

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DigitalInputChannel':
        # Parse button mode
        button_mode_str = data.get("button_mode", "direct")
        try:
            button_mode = ButtonMode(button_mode_str)
        except ValueError:
            button_mode = ButtonMode.DIRECT

        return cls(
            name=data.get("channel_name", ""),
            channel_type=ChannelType.DIGITAL_INPUT,
            channel_id=data.get("channel_id", 0),
            subtype=DigitalInputSubtype(data.get("subtype", "switch_active_low")),
            input_pin=data.get("input_pin", 0),
            enable_pullup=data.get("enable_pullup", False),
            threshold_voltage=data.get("threshold_voltage", 2.5),
            debounce_ms=data.get("debounce_ms", 50),
            invert=data.get("invert", False),
            trigger_edge=EdgeType(data.get("trigger_edge", "rising")),
            multiplier=data.get("multiplier", 1.0),
            divider=data.get("divider", 1.0),
            timeout_ms=data.get("timeout_ms", 1000),
            number_of_teeth=data.get("number_of_teeth", 1),
            button_mode=button_mode,
            long_press_ms=data.get("long_press_ms", 500),
            long_press_output=data.get("long_press_output", ""),
            double_click_ms=data.get("double_click_ms", 300),
            double_click_output=data.get("double_click_output", ""),
            hold_start_ms=data.get("hold_start_ms", 500),
            hold_full_ms=data.get("hold_full_ms", 2000),
            reset_channel=data.get("reset_channel", ""),
            # CAN Keypad button specific
            keypad_id=data.get("keypad_id", ""),
            button_index=data.get("button_index", 0)
        )

    def validate(self) -> List[str]:
        errors = super().validate()
        # Keypad buttons don't use physical input pins
        if self.subtype == DigitalInputSubtype.KEYPAD_BUTTON:
            if not self.keypad_id:
                errors.append("Keypad ID is required for keypad buttons")
            if not 0 <= self.button_index <= 15:
                errors.append("Button index must be between 0 and 15")
        else:
            if not 0 <= self.input_pin <= 7:
                errors.append("Input pin must be between 0 and 7 (D1-D8)")
        if self.threshold_voltage < 0 or self.threshold_voltage > 30:
            errors.append("Threshold voltage must be between 0 and 30V")
        if self.subtype == DigitalInputSubtype.RPM and self.number_of_teeth < 1:
            errors.append("Number of teeth must be at least 1")
        # Button mode validation
        if self.button_mode == ButtonMode.LONG_PRESS:
            if self.long_press_ms < 100:
                errors.append("Long press time must be at least 100ms")
        elif self.button_mode == ButtonMode.DOUBLE_CLICK:
            if self.double_click_ms < 50 or self.double_click_ms > 1000:
                errors.append("Double click window must be between 50ms and 1000ms")
        elif self.button_mode == ButtonMode.PRESS_AND_HOLD:
            if self.hold_start_ms >= self.hold_full_ms:
                errors.append("Hold start time must be less than hold full time")
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
            name=data.get("channel_name", ""),
            channel_type=ChannelType.ANALOG_INPUT,
            channel_id=data.get("channel_id", 0),
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
