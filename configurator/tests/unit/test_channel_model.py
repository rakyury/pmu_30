"""
Unit Tests: Channel Model

Tests for channel.py - the unified channel model for PMU-30 Configurator.
Covers:
- ChannelType enum values
- ChannelBase and subclasses
- Serialization (to_dict / from_dict)
- Validation
- Channel ID handling
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from models.channel import (
    # Enums
    ChannelType,
    DigitalInputSubtype,
    AnalogInputSubtype,
    ButtonMode,
    LogicOperation,
    MathOperation,
    FilterType,
    EdgeType,
    CanMessageType,
    CanTimeoutBehavior,
    CanDataType,
    CanDataFormat,
    TimerMode,
    ChannelMultiplier,
    # Classes
    ChannelBase,
    DigitalInputChannel,
    AnalogInputChannel,
)


# ============================================================================
# ChannelType Enum Tests
# ============================================================================

class TestChannelTypeEnum:
    """Test ChannelType enum values."""

    def test_all_channel_types_defined(self):
        """Verify all expected channel types exist."""
        expected_types = [
            "digital_input", "analog_input", "power_output", "hbridge",
            "can_rx", "can_tx", "logic", "number", "table_2d", "table_3d",
            "switch", "timer", "filter", "lua_script", "pid",
            "blinkmarine_keypad", "handler", "wiper", "blinker",
            "system", "output_status"
        ]
        for type_value in expected_types:
            assert ChannelType(type_value) is not None

    def test_channel_type_values(self):
        """Test specific channel type enum values."""
        assert ChannelType.DIGITAL_INPUT.value == "digital_input"
        assert ChannelType.ANALOG_INPUT.value == "analog_input"
        assert ChannelType.POWER_OUTPUT.value == "power_output"
        assert ChannelType.LOGIC.value == "logic"
        assert ChannelType.SYSTEM.value == "system"

    def test_invalid_channel_type_raises(self):
        """Test that invalid channel type raises ValueError."""
        with pytest.raises(ValueError):
            ChannelType("invalid_type")


class TestDigitalInputSubtype:
    """Test DigitalInputSubtype enum."""

    def test_subtypes_defined(self):
        """Verify all digital input subtypes exist."""
        subtypes = [
            "switch_active_low", "switch_active_high", "frequency",
            "rpm", "flex_fuel", "beacon", "puls_oil_sensor", "keypad_button"
        ]
        for subtype in subtypes:
            assert DigitalInputSubtype(subtype) is not None

    def test_keypad_button_subtype(self):
        """Test keypad button subtype for CAN keypads."""
        assert DigitalInputSubtype.KEYPAD_BUTTON.value == "keypad_button"


class TestButtonMode:
    """Test ButtonMode enum for ECUMaster compatibility."""

    def test_button_modes_defined(self):
        """Verify all button modes exist."""
        modes = [
            "direct", "momentary", "toggle", "latching",
            "long_press", "double_click", "press_and_hold"
        ]
        for mode in modes:
            assert ButtonMode(mode) is not None

    def test_default_mode_is_direct(self):
        """Verify DIRECT is the expected default."""
        assert ButtonMode.DIRECT.value == "direct"


class TestLogicOperation:
    """Test LogicOperation enum."""

    def test_basic_logic_operations(self):
        """Test basic logic operations exist."""
        assert LogicOperation.AND.value == "and"
        assert LogicOperation.OR.value == "or"
        assert LogicOperation.NOT.value == "not"
        assert LogicOperation.XOR.value == "xor"

    def test_comparison_operations(self):
        """Test comparison operations exist."""
        assert LogicOperation.EQUAL.value == "equal"
        assert LogicOperation.NOT_EQUAL.value == "not_equal"
        assert LogicOperation.LESS.value == "less"
        assert LogicOperation.GREATER.value == "greater"
        assert LogicOperation.IN_RANGE.value == "in_range"

    def test_edge_detection(self):
        """Test edge detection operations."""
        assert LogicOperation.EDGE_RISING.value == "edge_rising"
        assert LogicOperation.EDGE_FALLING.value == "edge_falling"


# ============================================================================
# ChannelBase Tests
# ============================================================================

class TestChannelBase:
    """Test ChannelBase class."""

    def test_create_channel_base(self):
        """Test creating a basic channel."""
        channel = ChannelBase(
            name="test_channel",
            channel_type=ChannelType.DIGITAL_INPUT,
            channel_id=100
        )
        assert channel.name == "test_channel"
        assert channel.channel_type == ChannelType.DIGITAL_INPUT
        assert channel.channel_id == 100

    def test_default_channel_id(self):
        """Test default channel_id is 0."""
        channel = ChannelBase(
            name="test",
            channel_type=ChannelType.DIGITAL_INPUT
        )
        assert channel.channel_id == 0

    def test_to_dict(self):
        """Test serialization to dictionary."""
        channel = ChannelBase(
            name="test_channel",
            channel_type=ChannelType.ANALOG_INPUT,
            channel_id=42
        )
        data = channel.to_dict()

        assert data["channel_id"] == 42
        assert data["channel_name"] == "test_channel"
        assert data["channel_type"] == "analog_input"

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "channel_id": 123,
            "channel_name": "loaded_channel",
            "channel_type": "power_output"
        }
        channel = ChannelBase.from_dict(data)

        assert channel.name == "loaded_channel"
        assert channel.channel_type == ChannelType.POWER_OUTPUT
        assert channel.channel_id == 123

    def test_from_dict_missing_name_raises(self):
        """Test that missing channel_name raises ValueError."""
        data = {
            "channel_id": 1,
            "channel_type": "digital_input"
        }
        with pytest.raises(ValueError, match="channel_name"):
            ChannelBase.from_dict(data)

    def test_validate_empty_name(self):
        """Test validation catches empty name."""
        channel = ChannelBase(
            name="",
            channel_type=ChannelType.DIGITAL_INPUT
        )
        errors = channel.validate()
        assert len(errors) > 0
        assert "Name is required" in errors

    def test_validate_valid_channel(self):
        """Test validation passes for valid channel."""
        channel = ChannelBase(
            name="valid_name",
            channel_type=ChannelType.DIGITAL_INPUT
        )
        errors = channel.validate()
        assert len(errors) == 0

    def test_get_output_channels(self):
        """Test get_output_channels returns channel name."""
        channel = ChannelBase(
            name="my_channel",
            channel_type=ChannelType.DIGITAL_INPUT
        )
        outputs = channel.get_output_channels()
        assert outputs == ["my_channel"]

    def test_get_input_channels_empty_by_default(self):
        """Test get_input_channels returns empty list by default."""
        channel = ChannelBase(
            name="test",
            channel_type=ChannelType.DIGITAL_INPUT
        )
        inputs = channel.get_input_channels()
        assert inputs == []

    def test_roundtrip_serialization(self):
        """Test to_dict -> from_dict roundtrip."""
        original = ChannelBase(
            name="roundtrip_test",
            channel_type=ChannelType.LOGIC,
            channel_id=999
        )
        data = original.to_dict()
        restored = ChannelBase.from_dict(data)

        assert restored.name == original.name
        assert restored.channel_type == original.channel_type
        assert restored.channel_id == original.channel_id


# ============================================================================
# DigitalInputChannel Tests
# ============================================================================

class TestDigitalInputChannel:
    """Test DigitalInputChannel class."""

    def test_create_default_digital_input(self):
        """Test creating a digital input with defaults."""
        channel = DigitalInputChannel(
            name="din_1",
            channel_type=ChannelType.DIGITAL_INPUT
        )
        assert channel.name == "din_1"
        assert channel.subtype == DigitalInputSubtype.SWITCH_ACTIVE_LOW
        assert channel.input_pin == 0
        assert channel.debounce_ms == 50
        assert channel.button_mode == ButtonMode.DIRECT

    def test_create_frequency_input(self):
        """Test creating a frequency input."""
        channel = DigitalInputChannel(
            name="freq_1",
            channel_type=ChannelType.DIGITAL_INPUT,
            subtype=DigitalInputSubtype.FREQUENCY,
            input_pin=2,
            trigger_edge=EdgeType.RISING,
            multiplier=2.0,
            divider=1.0,
            timeout_ms=500
        )
        assert channel.subtype == DigitalInputSubtype.FREQUENCY
        assert channel.trigger_edge == EdgeType.RISING
        assert channel.multiplier == 2.0

    def test_create_rpm_input(self):
        """Test creating an RPM input."""
        channel = DigitalInputChannel(
            name="rpm_1",
            channel_type=ChannelType.DIGITAL_INPUT,
            subtype=DigitalInputSubtype.RPM,
            input_pin=3,
            number_of_teeth=36
        )
        assert channel.subtype == DigitalInputSubtype.RPM
        assert channel.number_of_teeth == 36

    def test_create_keypad_button(self):
        """Test creating a CAN keypad button input."""
        channel = DigitalInputChannel(
            name="keypad_btn_1",
            channel_type=ChannelType.DIGITAL_INPUT,
            subtype=DigitalInputSubtype.KEYPAD_BUTTON,
            keypad_id="keypad_main",
            button_index=5,
            button_mode=ButtonMode.TOGGLE
        )
        assert channel.subtype == DigitalInputSubtype.KEYPAD_BUTTON
        assert channel.keypad_id == "keypad_main"
        assert channel.button_index == 5
        assert channel.button_mode == ButtonMode.TOGGLE

    def test_button_mode_long_press(self):
        """Test long press button mode settings."""
        channel = DigitalInputChannel(
            name="btn_long",
            channel_type=ChannelType.DIGITAL_INPUT,
            button_mode=ButtonMode.LONG_PRESS,
            long_press_ms=1000,
            long_press_output="long_action"
        )
        assert channel.button_mode == ButtonMode.LONG_PRESS
        assert channel.long_press_ms == 1000
        assert channel.long_press_output == "long_action"

    def test_to_dict_switch(self):
        """Test serialization of switch type."""
        channel = DigitalInputChannel(
            name="switch_1",
            channel_type=ChannelType.DIGITAL_INPUT,
            channel_id=10,
            subtype=DigitalInputSubtype.SWITCH_ACTIVE_HIGH,
            input_pin=1,
            debounce_ms=100,
            invert=True
        )
        data = channel.to_dict()

        assert data["channel_name"] == "switch_1"
        assert data["channel_id"] == 10
        assert data["subtype"] == "switch_active_high"
        assert data["input_pin"] == 1
        assert data["debounce_ms"] == 100
        assert data["invert"] is True

    def test_to_dict_frequency(self):
        """Test serialization includes frequency-specific fields."""
        channel = DigitalInputChannel(
            name="freq_ch",
            channel_type=ChannelType.DIGITAL_INPUT,
            subtype=DigitalInputSubtype.FREQUENCY,
            trigger_edge=EdgeType.FALLING,
            multiplier=3.0,
            timeout_ms=2000
        )
        data = channel.to_dict()

        assert data["trigger_edge"] == "falling"
        assert data["multiplier"] == 3.0
        assert data["timeout_ms"] == 2000

    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "channel_name": "restored_din",
            "channel_id": 50,
            "channel_type": "digital_input",
            "subtype": "switch_active_low",
            "input_pin": 4,
            "debounce_ms": 75,
            "invert": True,
            "button_mode": "toggle"
        }
        channel = DigitalInputChannel.from_dict(data)

        assert channel.name == "restored_din"
        assert channel.channel_id == 50
        assert channel.input_pin == 4
        assert channel.debounce_ms == 75
        assert channel.invert is True
        assert channel.button_mode == ButtonMode.TOGGLE

    def test_validate_valid_switch(self):
        """Test validation passes for valid switch input."""
        channel = DigitalInputChannel(
            name="valid_switch",
            channel_type=ChannelType.DIGITAL_INPUT,
            input_pin=3
        )
        errors = channel.validate()
        assert len(errors) == 0

    def test_validate_invalid_pin(self):
        """Test validation catches invalid input pin."""
        channel = DigitalInputChannel(
            name="bad_pin",
            channel_type=ChannelType.DIGITAL_INPUT,
            input_pin=10  # Invalid: must be 0-7
        )
        errors = channel.validate()
        assert any("Input pin" in e for e in errors)

    def test_validate_invalid_threshold(self):
        """Test validation catches invalid threshold voltage."""
        channel = DigitalInputChannel(
            name="bad_threshold",
            channel_type=ChannelType.DIGITAL_INPUT,
            threshold_voltage=50  # Invalid: must be 0-30V
        )
        errors = channel.validate()
        assert any("Threshold voltage" in e for e in errors)

    def test_validate_keypad_button_missing_id(self):
        """Test validation catches missing keypad ID."""
        channel = DigitalInputChannel(
            name="keypad_btn",
            channel_type=ChannelType.DIGITAL_INPUT,
            subtype=DigitalInputSubtype.KEYPAD_BUTTON,
            keypad_id=""  # Missing
        )
        errors = channel.validate()
        assert any("Keypad ID" in e for e in errors)

    def test_validate_rpm_invalid_teeth(self):
        """Test validation catches invalid number of teeth."""
        channel = DigitalInputChannel(
            name="rpm_bad",
            channel_type=ChannelType.DIGITAL_INPUT,
            subtype=DigitalInputSubtype.RPM,
            number_of_teeth=0  # Invalid: must be >= 1
        )
        errors = channel.validate()
        assert any("teeth" in e.lower() for e in errors)

    def test_validate_long_press_too_short(self):
        """Test validation catches too short long press time."""
        channel = DigitalInputChannel(
            name="btn_short",
            channel_type=ChannelType.DIGITAL_INPUT,
            button_mode=ButtonMode.LONG_PRESS,
            long_press_ms=50  # Invalid: must be >= 100ms
        )
        errors = channel.validate()
        assert any("Long press" in e for e in errors)

    def test_roundtrip_serialization(self):
        """Test to_dict -> from_dict roundtrip."""
        original = DigitalInputChannel(
            name="roundtrip_din",
            channel_type=ChannelType.DIGITAL_INPUT,
            channel_id=77,
            subtype=DigitalInputSubtype.FREQUENCY,
            input_pin=5,
            trigger_edge=EdgeType.BOTH,
            multiplier=2.5,
            divider=1.5,
            timeout_ms=750
        )
        data = original.to_dict()
        restored = DigitalInputChannel.from_dict(data)

        assert restored.name == original.name
        assert restored.channel_id == original.channel_id
        assert restored.subtype == original.subtype
        assert restored.input_pin == original.input_pin
        assert restored.multiplier == original.multiplier


# ============================================================================
# AnalogInputChannel Tests
# ============================================================================

class TestAnalogInputChannel:
    """Test AnalogInputChannel class."""

    def test_create_default_analog_input(self):
        """Test creating an analog input with defaults."""
        channel = AnalogInputChannel(
            name="ain_1",
            channel_type=ChannelType.ANALOG_INPUT
        )
        assert channel.name == "ain_1"
        assert channel.subtype == AnalogInputSubtype.LINEAR
        assert channel.input_pin == 0
        assert channel.min_voltage == 0.0
        assert channel.max_voltage == 5.0

    def test_create_linear_analog(self):
        """Test creating a linear analog input."""
        channel = AnalogInputChannel(
            name="throttle",
            channel_type=ChannelType.ANALOG_INPUT,
            subtype=AnalogInputSubtype.LINEAR,
            input_pin=5,
            min_voltage=0.5,
            max_voltage=4.5,
            min_value=0.0,
            max_value=100.0
        )
        assert channel.min_voltage == 0.5
        assert channel.max_voltage == 4.5
        assert channel.min_value == 0.0
        assert channel.max_value == 100.0

    def test_create_rotary_switch(self):
        """Test creating a rotary switch analog input."""
        channel = AnalogInputChannel(
            name="rotary_1",
            channel_type=ChannelType.ANALOG_INPUT,
            subtype=AnalogInputSubtype.ROTARY_SWITCH,
            positions=8,
            debounce_ms=100
        )
        assert channel.subtype == AnalogInputSubtype.ROTARY_SWITCH
        assert channel.positions == 8
        assert channel.debounce_ms == 100


# ============================================================================
# Channel ID Range Tests
# ============================================================================

class TestChannelIdRanges:
    """Test channel ID value ranges."""

    def test_channel_id_zero(self):
        """Test channel_id can be 0."""
        channel = ChannelBase(
            name="ch_zero",
            channel_type=ChannelType.DIGITAL_INPUT,
            channel_id=0
        )
        assert channel.channel_id == 0

    def test_channel_id_max_uint16(self):
        """Test channel_id can be max uint16 (65535)."""
        channel = ChannelBase(
            name="ch_max",
            channel_type=ChannelType.DIGITAL_INPUT,
            channel_id=65535
        )
        assert channel.channel_id == 65535

    def test_channel_id_typical_ranges(self):
        """Test typical channel ID ranges per type."""
        # Digital inputs: 1-8
        din = DigitalInputChannel(
            name="din",
            channel_type=ChannelType.DIGITAL_INPUT,
            channel_id=5
        )
        assert 0 <= din.channel_id <= 65535

        # Analog inputs: 101-120
        ain = AnalogInputChannel(
            name="ain",
            channel_type=ChannelType.ANALOG_INPUT,
            channel_id=110
        )
        assert 0 <= ain.channel_id <= 65535


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_name_allowed_in_constructor(self):
        """Test empty name is allowed in constructor (caught by validate)."""
        channel = ChannelBase(
            name="",
            channel_type=ChannelType.DIGITAL_INPUT
        )
        assert channel.name == ""

    def test_special_characters_in_name(self):
        """Test special characters in channel name."""
        channel = ChannelBase(
            name="my-channel_123.test",
            channel_type=ChannelType.DIGITAL_INPUT
        )
        assert channel.name == "my-channel_123.test"

    def test_unicode_in_name(self):
        """Test unicode characters in channel name."""
        channel = ChannelBase(
            name="канал_1",  # Russian
            channel_type=ChannelType.DIGITAL_INPUT
        )
        assert channel.name == "канал_1"

    def test_very_long_name(self):
        """Test very long channel name."""
        long_name = "a" * 1000
        channel = ChannelBase(
            name=long_name,
            channel_type=ChannelType.DIGITAL_INPUT
        )
        assert len(channel.name) == 1000

    def test_from_dict_with_unknown_fields(self):
        """Test from_dict ignores unknown fields."""
        data = {
            "channel_name": "test",
            "channel_type": "digital_input",
            "channel_id": 1,
            "unknown_field": "ignored",
            "another_unknown": 123
        }
        channel = ChannelBase.from_dict(data)
        assert channel.name == "test"
        assert not hasattr(channel, "unknown_field")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
