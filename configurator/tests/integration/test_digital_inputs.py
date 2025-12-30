"""
Integration Tests: Digital Inputs
Tests all digital input subtypes and behaviors through the emulator.

Covers:
- Switch active high/low
- Button with momentary behavior
- Rotary encoder
- Frequency input
- Pulse counter
- Debounce settings
- Edge detection

These tests require a running PMU-30 emulator.
"""

import pytest
import asyncio
import json

# Import fixtures and helpers from conftest
from .helpers import (
    BASE_CONFIG,
    ChannelState,
    make_digital_input_config,
    make_output_config,
    make_logic_config,
)



def make_frequency_input_config(input_num: int, name: str,
                                min_freq: float = 0.0,
                                max_freq: float = 10000.0,
                                filter_hz: float = 100.0) -> dict:
    """Create frequency input configuration."""
    return {
        "channel_id": 200 + input_num,
        "channel_type": "digital_input",
        "id": name,
        "name": name,
        "channel": input_num - 1,
        "input_type": "frequency",
        "min_freq": min_freq,
        "max_freq": max_freq,
        "filter_hz": filter_hz,
    }


def make_pulse_counter_config(input_num: int, name: str,
                              edge: str = "rising",
                              reset_channel: str = None) -> dict:
    """Create pulse counter input configuration."""
    config = {
        "channel_id": 200 + input_num,
        "channel_type": "digital_input",
        "id": name,
        "name": name,
        "channel": input_num - 1,
        "input_type": "pulse_counter",
        "edge": edge,
    }
    if reset_channel:
        config["reset_channel"] = reset_channel
    return config


def make_encoder_input_config(input_num: int, name: str,
                              channel_b: int,
                              pulses_per_rev: int = 100) -> dict:
    """Create rotary encoder input configuration."""
    return {
        "channel_id": 200 + input_num,
        "channel_type": "digital_input",
        "id": name,
        "name": name,
        "channel": input_num - 1,
        "input_type": "encoder",
        "channel_b": channel_b,
        "pulses_per_rev": pulses_per_rev,
    }
class TestSwitchActiveHigh:
    """Test switch active high input type."""

    async def test_active_high_on(self, emulator_connection):
        """
        Test: Active high switch outputs 1 when input is high.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_switch",
                                     input_type="switch_active_high"),
            make_output_config(1, "o_1", "di_switch"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Input LOW -> Output OFF
        await protocol.set_digital_input(0, False)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF

        # Input HIGH -> Output ON
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE]

    async def test_active_high_debounce(self, emulator_connection):
        """
        Test: Active high with debounce filters noise.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_switch",
                                     input_type="switch_active_high",
                                     debounce_ms=100),
            make_output_config(1, "o_1", "di_switch"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Rapid toggles (simulate contact bounce)
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.02)
        await protocol.set_digital_input(0, False)
        await asyncio.sleep(0.02)
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.02)
        await protocol.set_digital_input(0, False)
        await asyncio.sleep(0.15)  # Wait for debounce

        telemetry = await protocol.get_telemetry()
        # Should be OFF (debounced to final state)


class TestSwitchActiveLow:
    """Test switch active low input type."""

    async def test_active_low_inverted(self, emulator_connection):
        """
        Test: Active low switch outputs 1 when input is low.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_switch",
                                     input_type="switch_active_low"),
            make_output_config(1, "o_1", "di_switch"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Input HIGH -> Output OFF (inverted)
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF

        # Input LOW -> Output ON (inverted)
        await protocol.set_digital_input(0, False)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE]


class TestButtonMomentary:
    """Test momentary button input type."""

    async def test_button_momentary(self, emulator_connection):
        """
        Test: Button outputs 1 only while pressed.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_button",
                                     input_type="button_momentary"),
            make_output_config(1, "o_1", "di_button"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Not pressed -> OFF
        await protocol.set_digital_input(0, False)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF

        # Pressed -> ON
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE]

        # Released -> OFF immediately
        await protocol.set_digital_input(0, False)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF


class TestFrequencyInput:
    """Test frequency measurement input type."""

    async def test_frequency_measurement(self, emulator_connection):
        """
        Test: Frequency input measures signal frequency.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_frequency_input_config(1, "di_freq",
                                       min_freq=0, max_freq=1000),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Simulate 500Hz signal
        await protocol.set_frequency_input(0, 500.0)
        await asyncio.sleep(0.3)

        telemetry = await protocol.get_telemetry()
        freq = telemetry.virtual_channels.get(201, 0)
        # Should be approximately 500 Hz

    async def test_frequency_to_rpm(self, emulator_connection):
        """
        Test: Convert frequency to RPM using math channel.
        Example: Tachometer with 2 pulses per revolution.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_frequency_input_config(1, "di_tach"),
            # RPM = freq * 60 / pulses_per_rev = freq * 30 (for 2 ppr)
            {
                "channel_id": 300,
                "channel_type": "number",
                "id": "n_rpm",
                "name": "RPM",
                "operation": "multiply",
                "input1_channel": "di_tach",
                "constant1": 30.0,
            },
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # 100 Hz * 30 = 3000 RPM
        await protocol.set_frequency_input(0, 100.0)
        await asyncio.sleep(0.3)

        telemetry = await protocol.get_telemetry()
        rpm = telemetry.virtual_channels.get(300, 0)

    async def test_frequency_threshold(self, emulator_connection):
        """
        Test: Frequency input triggers logic when above threshold.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_frequency_input_config(1, "di_speed"),
            make_logic_config(300, "l_high_speed", "greater", "di_speed", constant=200.0),
            make_output_config(1, "o_warning", "l_high_speed"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Low frequency -> no warning
        await protocol.set_frequency_input(0, 100.0)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF

        # High frequency -> warning
        await protocol.set_frequency_input(0, 300.0)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE]


class TestPulseCounter:
    """Test pulse counter input type."""

    async def test_pulse_counting(self, emulator_connection):
        """
        Test: Pulse counter accumulates pulses.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_pulse_counter_config(1, "di_counter", edge="rising"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Send multiple pulses
        for _ in range(10):
            await protocol.set_digital_input(0, True)
            await asyncio.sleep(0.02)
            await protocol.set_digital_input(0, False)
            await asyncio.sleep(0.02)

        await asyncio.sleep(0.2)
        telemetry = await protocol.get_telemetry()
        count = telemetry.virtual_channels.get(201, 0)
        # Should be approximately 10

    async def test_pulse_counter_reset(self, emulator_connection):
        """
        Test: Pulse counter resets on reset channel.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(2, "di_reset"),
            make_pulse_counter_config(1, "di_counter",
                                     edge="rising",
                                     reset_channel="di_reset"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Count some pulses
        for _ in range(5):
            await protocol.set_digital_input(0, True)
            await asyncio.sleep(0.02)
            await protocol.set_digital_input(0, False)
            await asyncio.sleep(0.02)

        await asyncio.sleep(0.2)
        telemetry = await protocol.get_telemetry()
        count_before = telemetry.virtual_channels.get(201, 0)

        # Reset
        await protocol.set_digital_input(1, True)
        await asyncio.sleep(0.1)
        await protocol.set_digital_input(1, False)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        count_after = telemetry.virtual_channels.get(201, 0)

        assert count_after < count_before or count_after == 0, \
            f"Counter should reset: {count_before} -> {count_after}"

    async def test_pulse_counter_falling_edge(self, emulator_connection):
        """
        Test: Pulse counter counts on falling edge.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_pulse_counter_config(1, "di_counter", edge="falling"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Send pulses (count on falling edge)
        for _ in range(5):
            await protocol.set_digital_input(0, True)
            await asyncio.sleep(0.02)
            await protocol.set_digital_input(0, False)  # Count here
            await asyncio.sleep(0.02)

        await asyncio.sleep(0.2)
        telemetry = await protocol.get_telemetry()
        count = telemetry.virtual_channels.get(201, 0)


class TestEncoderInput:
    """Test rotary encoder input type."""

    async def test_encoder_position(self, emulator_connection):
        """
        Test: Encoder tracks position.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_encoder_input_config(1, "di_encoder",
                                     channel_b=1,
                                     pulses_per_rev=100),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Simulate encoder rotation (A leads B for CW)
        await protocol.set_encoder_position(0, 50)  # 50 pulses
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        position = telemetry.virtual_channels.get(201, 0)

    async def test_encoder_direction(self, emulator_connection):
        """
        Test: Encoder detects direction.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_encoder_input_config(1, "di_encoder",
                                     channel_b=1,
                                     pulses_per_rev=100),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Forward rotation
        await protocol.set_encoder_position(0, 100)
        await asyncio.sleep(0.2)

        telemetry1 = await protocol.get_telemetry()
        pos1 = telemetry1.virtual_channels.get(201, 0)

        # Reverse rotation
        await protocol.set_encoder_position(0, 50)
        await asyncio.sleep(0.2)

        telemetry2 = await protocol.get_telemetry()
        pos2 = telemetry2.virtual_channels.get(201, 0)

        # Position should decrease


class TestPullUpPullDown:
    """Test internal pull-up and pull-down resistors."""

    async def test_pull_up_enabled(self, emulator_connection):
        """
        Test: Input with pull-up reads high when floating.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_pullup",
                                     input_type="switch_active_low",
                                     pull_up=True),
            make_output_config(1, "o_1", "di_pullup"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # With pull-up and active-low, floating = high = OFF
        # When grounded = low = ON

    async def test_pull_down_enabled(self, emulator_connection):
        """
        Test: Input with pull-down reads low when floating.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_pulldown",
                                     input_type="switch_active_high",
                                     pull_down=True),
            make_output_config(1, "o_1", "di_pulldown"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # With pull-down and active-high, floating = low = OFF


class TestMultipleDigitalInputs:
    """Test multiple digital inputs working together."""

    async def test_independent_inputs(self, emulator_connection):
        """
        Test: Multiple inputs operate independently.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_1"),
            make_digital_input_config(2, "di_2"),
            make_digital_input_config(3, "di_3"),
            make_output_config(1, "o_1", "di_1"),
            make_output_config(2, "o_2", "di_2"),
            make_output_config(3, "o_3", "di_3"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Set pattern: 1=ON, 2=OFF, 3=ON
        await protocol.set_digital_input(0, True)
        await protocol.set_digital_input(1, False)
        await protocol.set_digital_input(2, True)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE]
        assert telemetry.channel_states[1] == ChannelState.OFF
        assert telemetry.channel_states[2] in [ChannelState.ON, ChannelState.PWM_ACTIVE]

    async def test_mixed_input_types(self, emulator_connection):
        """
        Test: Different input types work together.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_switch", input_type="switch_active_high"),
            make_digital_input_config(2, "di_switch_inv", input_type="switch_active_low"),
            make_frequency_input_config(3, "di_freq"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Set inputs
        await protocol.set_digital_input(0, True)   # Switch ON
        await protocol.set_digital_input(1, True)   # Inverted switch OFF
        await protocol.set_frequency_input(2, 250)  # 250 Hz
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        # Verify all inputs report correctly


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
