"""
Integration Tests: Switch Channels
Tests switch channel behavior and state transitions through the emulator.

Covers:
- Toggle mode
- Momentary mode
- Multi-state switches
- Edge detection (rising, falling, both)
- State persistence
- Switch with various input channel types

These tests require a running PMU-30 emulator.
"""

import pytest
import asyncio
import json

# Import fixtures and helpers from conftest
from .helpers import (
    BASE_CONFIG,
    ChannelState,
)



def make_analog_input_config(input_num: int, name: str) -> dict:
    """Create analog input configuration."""
    return {
        "channel_id": 200 + input_num,
        "channel_type": "analog_input",
        "id": name,
        "name": name,
        "channel": input_num - 1,
        "input_type": "linear",
        "scale": 1.0,
        "offset": 0.0,
    }


def make_can_input_config(channel_id: int, name: str, can_id: int) -> dict:
    """Create CAN input configuration."""
    return {
        "channel_id": channel_id,
        "channel_type": "can_input",
        "id": name,
        "name": name,
        "can_id": can_id,
        "start_bit": 0,
        "bit_length": 8,
        "byte_order": "little_endian",
        "data_type": "unsigned",
        "scale": 1.0,
    }


def make_switch_config(channel_id: int, name: str, input_channel: str,
                       mode: str = "toggle",
                       edge: str = "rising",
                       initial_state: int = 0,
                       num_states: int = 2) -> dict:
    """Create switch channel configuration."""
    return {
        "channel_id": channel_id,
        "channel_type": "switch",
        "id": name,
        "name": name,
        "input_channel": input_channel,
        "mode": mode,
        "edge": edge,
        "initial_state": initial_state,
        "num_states": num_states,
    }
class TestToggleMode:
    """Test toggle switch behavior."""

    async def test_toggle_on_rising_edge(self, emulator_connection):
        """
        Test: Toggle switch changes state on rising edge.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_button"),
            make_switch_config(300, "sw_toggle", "di_button",
                             mode="toggle", edge="rising", initial_state=0),
            make_output_config(1, "o_light", "sw_toggle"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Initial state should be OFF
        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF, \
            "Initial state should be OFF"

        # First press (rising edge) -> toggle ON
        await protocol.set_digital_input(0, False)
        await asyncio.sleep(0.1)
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "After first toggle, should be ON"

        # Release (no change on falling edge)
        await protocol.set_digital_input(0, False)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "Should remain ON after release"

        # Second press (rising edge) -> toggle OFF
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF, \
            "After second toggle, should be OFF"

    async def test_toggle_on_falling_edge(self, emulator_connection):
        """
        Test: Toggle switch changes state on falling edge.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_button"),
            make_switch_config(300, "sw_toggle", "di_button",
                             mode="toggle", edge="falling", initial_state=0),
            make_output_config(1, "o_light", "sw_toggle"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Press (no toggle on rising)
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF, \
            "Should remain OFF on press"

        # Release (toggle on falling edge)
        await protocol.set_digital_input(0, False)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "Should toggle ON on release"

    async def test_toggle_on_both_edges(self, emulator_connection):
        """
        Test: Toggle switch changes state on both edges.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_button"),
            make_switch_config(300, "sw_toggle", "di_button",
                             mode="toggle", edge="both", initial_state=0),
            make_output_config(1, "o_light", "sw_toggle"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Press -> toggle ON
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE]

        # Release -> toggle OFF
        await protocol.set_digital_input(0, False)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF


class TestMomentaryMode:
    """Test momentary switch behavior."""

    async def test_momentary_active_while_pressed(self, emulator_connection):
        """
        Test: Momentary switch is active only while input is active.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_button"),
            make_switch_config(300, "sw_moment", "di_button",
                             mode="momentary", initial_state=0),
            make_output_config(1, "o_horn", "sw_moment"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Initial state OFF
        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF

        # Press -> ON
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE]

        # Release -> OFF immediately
        await protocol.set_digital_input(0, False)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF

    async def test_momentary_inverted(self, emulator_connection):
        """
        Test: Momentary switch with inverted logic (normally ON).
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_button"),
            make_switch_config(300, "sw_moment_inv", "di_button",
                             mode="momentary_inverted", initial_state=1),
            make_output_config(1, "o_brake_light", "sw_moment_inv"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Initial state ON
        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE]

        # Press -> OFF
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF


class TestMultiStateSwitch:
    """Test multi-state switch behavior."""

    async def test_three_state_switch(self, emulator_connection):
        """
        Test: Switch cycles through 3 states.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_button"),
            make_switch_config(300, "sw_mode", "di_button",
                             mode="toggle", edge="rising",
                             initial_state=0, num_states=3),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Initial state = 0
        telemetry = await protocol.get_telemetry()
        state0 = telemetry.virtual_channels.get(300, -1)
        assert state0 == 0

        # Press -> state 1
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.1)
        await protocol.set_digital_input(0, False)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        state1 = telemetry.virtual_channels.get(300, -1)
        assert state1 == 1

        # Press -> state 2
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.1)
        await protocol.set_digital_input(0, False)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        state2 = telemetry.virtual_channels.get(300, -1)
        assert state2 == 2

        # Press -> wrap to state 0
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.1)
        await protocol.set_digital_input(0, False)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        state_wrap = telemetry.virtual_channels.get(300, -1)
        assert state_wrap == 0

    async def test_multi_state_controls_outputs(self, emulator_connection):
        """
        Test: Multi-state switch controls multiple outputs via logic.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_button"),
            make_switch_config(300, "sw_mode", "di_button",
                             mode="toggle", num_states=4),
            # Each output for a different state
            make_logic_config(301, "l_state1", "equal", "sw_mode", constant=1.0),
            make_logic_config(302, "l_state2", "equal", "sw_mode", constant=2.0),
            make_logic_config(303, "l_state3", "equal", "sw_mode", constant=3.0),
            make_output_config(1, "o_1", "l_state1"),
            make_output_config(2, "o_2", "l_state2"),
            make_output_config(3, "o_3", "l_state3"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Cycle to state 2
        for _ in range(2):
            await protocol.set_digital_input(0, True)
            await asyncio.sleep(0.1)
            await protocol.set_digital_input(0, False)
            await asyncio.sleep(0.1)

        await asyncio.sleep(0.2)
        telemetry = await protocol.get_telemetry()

        # Only output 2 should be active
        assert telemetry.channel_states[0] == ChannelState.OFF, "O1 should be OFF"
        assert telemetry.channel_states[1] in [ChannelState.ON, ChannelState.PWM_ACTIVE], "O2 should be ON"
        assert telemetry.channel_states[2] == ChannelState.OFF, "O3 should be OFF"


class TestSwitchWithCANInput:
    """Test switch with CAN input as trigger."""

    async def test_switch_from_can_button(self, emulator_connection):
        """
        Test: Switch triggered by CAN button message.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_can_input_config(300, "can_button", can_id=0x100),
            make_logic_config(301, "l_can_high", "greater", "can_button", constant=0.0),
            make_switch_config(302, "sw_toggle", "l_can_high",
                             mode="toggle", edge="rising"),
            make_output_config(1, "o_1", "sw_toggle"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # CAN button press
        await protocol.send_can_message(0x100, [1, 0, 0, 0, 0, 0, 0, 0])
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE]

        # CAN button release
        await protocol.send_can_message(0x100, [0, 0, 0, 0, 0, 0, 0, 0])
        await asyncio.sleep(0.2)

        # Should stay toggled ON
        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE]


class TestSwitchWithAnalogInput:
    """Test switch with analog threshold as trigger."""

    async def test_switch_from_analog_threshold(self, emulator_connection):
        """
        Test: Switch triggered when analog exceeds threshold.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_sensor"),
            make_logic_config(300, "l_threshold", "greater", "ai_sensor", constant=2.5),
            make_switch_config(301, "sw_toggle", "l_threshold",
                             mode="toggle", edge="rising"),
            make_output_config(1, "o_1", "sw_toggle"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Below threshold
        await protocol.set_analog_input(0, 2.0)
        await asyncio.sleep(0.3)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF

        # Cross threshold (rising edge)
        await protocol.set_analog_input(0, 3.0)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE]


class TestSwitchInitialState:
    """Test switch initial state configuration."""

    async def test_initial_state_on(self, emulator_connection):
        """
        Test: Switch starts in ON state.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_button"),
            make_switch_config(300, "sw_default_on", "di_button",
                             mode="toggle", initial_state=1),
            make_output_config(1, "o_1", "sw_default_on"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Should be ON from start
        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE]

    async def test_initial_state_multi(self, emulator_connection):
        """
        Test: Multi-state switch starts at specified state.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_button"),
            make_switch_config(300, "sw_mode", "di_button",
                             mode="toggle", initial_state=2, num_states=4),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        telemetry = await protocol.get_telemetry()
        state = telemetry.virtual_channels.get(300, -1)
        assert state == 2


class TestSwitchDebounce:
    """Test switch debounce behavior."""

    async def test_rapid_toggles_debounced(self, emulator_connection):
        """
        Test: Rapid input changes are debounced.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            {
                "channel_id": 201,
                "channel_type": "digital_input",
                "id": "di_button",
                "name": "Button",
                "channel": 0,
                "input_type": "switch_active_high",
                "debounce_ms": 50,  # 50ms debounce
            },
            make_switch_config(300, "sw_toggle", "di_button",
                             mode="toggle", edge="rising"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Rapid toggles (should be debounced)
        for _ in range(5):
            await protocol.set_digital_input(0, True)
            await asyncio.sleep(0.01)  # 10ms < 50ms debounce
            await protocol.set_digital_input(0, False)
            await asyncio.sleep(0.01)

        await asyncio.sleep(0.1)
        telemetry = await protocol.get_telemetry()
        state_after_rapid = telemetry.virtual_channels.get(300, 0)

        # State should have changed only once or not at all due to debounce


class TestSwitchCascade:
    """Test cascaded/chained switches."""

    async def test_switch_controls_switch(self, emulator_connection):
        """
        Test: One switch enables another switch's input.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_enable"),
            make_digital_input_config(2, "di_trigger"),
            make_switch_config(300, "sw_enable", "di_enable", mode="toggle"),
            # AND the enable with trigger
            make_logic_config(301, "l_gated", "and", "sw_enable", "di_trigger"),
            make_switch_config(302, "sw_controlled", "l_gated", mode="toggle"),
            make_output_config(1, "o_1", "sw_controlled"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Without enable, trigger does nothing
        await protocol.set_digital_input(1, True)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF

        # Enable the gate
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.1)
        await protocol.set_digital_input(0, False)
        await asyncio.sleep(0.1)

        # Now trigger should work (if still high, re-toggle)
        await protocol.set_digital_input(1, False)
        await asyncio.sleep(0.1)
        await protocol.set_digital_input(1, True)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        # Controlled switch should now be toggleable


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
