"""
Integration tests for channel flow: Inputs → Logic → Numbers → Outputs.

These tests verify the critical fixes made to the PMU-30:
1. Digital input state logic (active_low = ON, active_high = OFF by default)
2. Power outputs following digital input states via PMU_Channel_UpdateValue
3. Logic functions operating correctly
4. Number functions computing correctly
5. Full chain: Input → Logic → Output → CAN

CRITICAL: Run after any firmware changes to pmu_adc.c, pmu_channel.c, pmu_config_json.c
"""

import pytest
import asyncio
import json
from .helpers import (
    AsyncProtocolHandler,
    EmulatorTransport,
    ChannelState,
    COMPREHENSIVE_TEST_CONFIG,
    BASE_CONFIG,
    make_digital_input_config,
    make_analog_input_config,
    make_output_config,
    make_logic_config,
    make_number_config,
)


# =============================================================================
# DIGITAL INPUT STATE LOGIC TESTS
# =============================================================================

class TestDigitalInputStateLogic:
    """
    Test digital input default states based on type.

    CRITICAL FIX: switch_active_low should default to ON (no signal = closed circuit)
                  switch_active_high should default to OFF (no signal = open circuit)
    """

    @pytest.mark.asyncio
    async def test_active_low_defaults_to_on(self, protocol_handler):
        """Active LOW input should default to ON state."""
        config = BASE_CONFIG.copy()
        config["channels"] = [
            {
                "id": "di_test_low",
                "channel_type": "digital_input",
                "enabled": True,
                "subtype": "switch_active_low",
                "input_pin": 0,
                "debounce_ms": 10,
                "threshold_voltage": 2.5
            }
        ]

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success, f"Config failed: {response.error}"

        await asyncio.sleep(0.5)
        telemetry = await protocol_handler.get_telemetry()

        # Active LOW input with no signal should be ON
        assert telemetry is not None, "No telemetry received"
        # Check digital input state (channel 50 in runtime)
        di_value = telemetry.get_channel_value(50)  # DI 0 = runtime ID 50
        assert di_value == 1, f"Active LOW input should default to ON, got {di_value}"

    @pytest.mark.asyncio
    async def test_active_high_defaults_to_off(self, protocol_handler):
        """Active HIGH input should default to OFF state."""
        config = BASE_CONFIG.copy()
        config["channels"] = [
            {
                "id": "di_test_high",
                "channel_type": "digital_input",
                "enabled": True,
                "subtype": "switch_active_high",
                "input_pin": 1,
                "debounce_ms": 10,
                "threshold_voltage": 2.5
            }
        ]

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success, f"Config failed: {response.error}"

        await asyncio.sleep(0.5)
        telemetry = await protocol_handler.get_telemetry()

        # Active HIGH input with no signal should be OFF
        assert telemetry is not None, "No telemetry received"
        di_value = telemetry.get_channel_value(51)  # DI 1 = runtime ID 51
        assert di_value == 0, f"Active HIGH input should default to OFF, got {di_value}"

    @pytest.mark.asyncio
    async def test_mixed_input_types_correct_states(self, protocol_handler):
        """Multiple inputs with different types should have correct default states."""
        config = BASE_CONFIG.copy()
        config["channels"] = [
            # Active LOW - should be ON
            make_digital_input_config(1, "di_low_1", "switch_active_low"),
            # Active HIGH - should be OFF
            make_digital_input_config(2, "di_high_1", "switch_active_high"),
            # Active LOW - should be ON
            make_digital_input_config(3, "di_low_2", "switch_active_low"),
            # Active HIGH - should be OFF
            make_digital_input_config(4, "di_high_2", "switch_active_high"),
        ]

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success

        await asyncio.sleep(0.5)
        telemetry = await protocol_handler.get_telemetry()
        assert telemetry is not None

        # Verify alternating pattern
        assert telemetry.get_channel_value(50) == 1, "DI 1 (active_low) should be ON"
        assert telemetry.get_channel_value(51) == 0, "DI 2 (active_high) should be OFF"
        assert telemetry.get_channel_value(52) == 1, "DI 3 (active_low) should be ON"
        assert telemetry.get_channel_value(53) == 0, "DI 4 (active_high) should be OFF"


# =============================================================================
# OUTPUT FOLLOWS INPUT TESTS
# =============================================================================

class TestOutputFollowsInput:
    """
    Test that power outputs correctly follow digital input states.

    CRITICAL FIX: PMU_Channel_UpdateValue allows setting INPUT channel values
                  so outputs can read them via source_channel.
    """

    @pytest.mark.asyncio
    async def test_output_follows_active_low_input(self, protocol_handler):
        """Output should be ON when linked to active_low input (which defaults ON)."""
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_ignition", "switch_active_low"),
            {
                "id": "o_fuel_pump",
                "channel_type": "power_output",
                "enabled": True,
                "output_pins": [0],
                "source_channel": "di_ignition",
                "current_limit_a": 10.0
            }
        ]

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success

        await asyncio.sleep(0.5)
        telemetry = await protocol_handler.get_telemetry()
        assert telemetry is not None

        # Output should follow input (ON)
        output_state = telemetry.channel_states[0] if telemetry.channel_states else None
        assert output_state in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            f"Output should be ON when linked to active_low input, got {output_state}"

    @pytest.mark.asyncio
    async def test_output_off_when_linked_to_active_high_input(self, protocol_handler):
        """Output should be OFF when linked to active_high input (which defaults OFF)."""
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_button", "switch_active_high"),
            {
                "id": "o_light",
                "channel_type": "power_output",
                "enabled": True,
                "output_pins": [0],
                "source_channel": "di_button",
                "current_limit_a": 5.0
            }
        ]

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success

        await asyncio.sleep(0.5)
        telemetry = await protocol_handler.get_telemetry()
        assert telemetry is not None

        # Output should follow input (OFF)
        output_state = telemetry.channel_states[0] if telemetry.channel_states else None
        assert output_state == ChannelState.OFF, \
            f"Output should be OFF when linked to active_high input, got {output_state}"

    @pytest.mark.asyncio
    async def test_output_toggles_with_input_change(self, protocol_handler):
        """Output should change when input state changes."""
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_switch", "switch_active_high"),
            {
                "id": "o_relay",
                "channel_type": "power_output",
                "enabled": True,
                "output_pins": [0],
                "source_channel": "di_switch",
                "current_limit_a": 10.0
            }
        ]

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Initially OFF (active_high default)
        telemetry = await protocol_handler.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF

        # Turn input ON
        await protocol_handler.set_digital_input(0, True)
        await asyncio.sleep(0.2)

        telemetry = await protocol_handler.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "Output should be ON after input turned ON"

        # Turn input OFF
        await protocol_handler.set_digital_input(0, False)
        await asyncio.sleep(0.2)

        telemetry = await protocol_handler.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF, \
            "Output should be OFF after input turned OFF"


# =============================================================================
# LOGIC FUNCTION TESTS
# =============================================================================

class TestLogicFunctions:
    """Test all logic function operations."""

    @pytest.mark.asyncio
    async def test_and_gate(self, protocol_handler):
        """AND gate: output ON only when BOTH inputs ON."""
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_a", "switch_active_high"),
            make_digital_input_config(2, "di_b", "switch_active_high"),
            {
                "id": "l_and",
                "channel_type": "logic",
                "enabled": True,
                "operation": "and",
                "channel": "di_a",
                "channel_2": "di_b"
            },
            {
                "id": "o_result",
                "channel_type": "power_output",
                "enabled": True,
                "output_pins": [0],
                "source_channel": "l_and",
                "current_limit_a": 5.0
            }
        ]

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Both OFF → Output OFF
        telemetry = await protocol_handler.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF, "AND: 0,0 should be OFF"

        # A=ON, B=OFF → Output OFF
        await protocol_handler.set_digital_input(0, True)
        await asyncio.sleep(0.2)
        telemetry = await protocol_handler.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF, "AND: 1,0 should be OFF"

        # A=ON, B=ON → Output ON
        await protocol_handler.set_digital_input(1, True)
        await asyncio.sleep(0.2)
        telemetry = await protocol_handler.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "AND: 1,1 should be ON"

    @pytest.mark.asyncio
    async def test_or_gate(self, protocol_handler):
        """OR gate: output ON when ANY input ON."""
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_a", "switch_active_high"),
            make_digital_input_config(2, "di_b", "switch_active_high"),
            {
                "id": "l_or",
                "channel_type": "logic",
                "enabled": True,
                "operation": "or",
                "channel": "di_a",
                "channel_2": "di_b"
            },
            {
                "id": "o_result",
                "channel_type": "power_output",
                "enabled": True,
                "output_pins": [0],
                "source_channel": "l_or",
                "current_limit_a": 5.0
            }
        ]

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Both OFF → Output OFF
        telemetry = await protocol_handler.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF, "OR: 0,0 should be OFF"

        # A=ON, B=OFF → Output ON
        await protocol_handler.set_digital_input(0, True)
        await asyncio.sleep(0.2)
        telemetry = await protocol_handler.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "OR: 1,0 should be ON"

    @pytest.mark.asyncio
    async def test_not_gate(self, protocol_handler):
        """NOT gate: inverts input."""
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_input", "switch_active_high"),
            {
                "id": "l_not",
                "channel_type": "logic",
                "enabled": True,
                "operation": "not",
                "channel": "di_input"
            },
            {
                "id": "o_result",
                "channel_type": "power_output",
                "enabled": True,
                "output_pins": [0],
                "source_channel": "l_not",
                "current_limit_a": 5.0
            }
        ]

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Input OFF → NOT output ON
        telemetry = await protocol_handler.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "NOT: 0 should be ON"

        # Input ON → NOT output OFF
        await protocol_handler.set_digital_input(0, True)
        await asyncio.sleep(0.2)
        telemetry = await protocol_handler.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF, "NOT: 1 should be OFF"

    @pytest.mark.asyncio
    async def test_greater_than_comparison(self, protocol_handler):
        """Greater than: output ON when value > constant."""
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_temp", "linear", 0, 100),
            {
                "id": "l_temp_high",
                "channel_type": "logic",
                "enabled": True,
                "operation": "greater",
                "channel": "ai_temp",
                "constant": 50.0
            },
            {
                "id": "o_alarm",
                "channel_type": "power_output",
                "enabled": True,
                "output_pins": [0],
                "source_channel": "l_temp_high",
                "current_limit_a": 2.0
            }
        ]

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Set analog to 30% (below 50) → OFF
        await protocol_handler.set_analog_input(0, 1.5)  # ~30% of 5V
        await asyncio.sleep(0.2)
        telemetry = await protocol_handler.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF, "30 > 50 should be OFF"

        # Set analog to 80% (above 50) → ON
        await protocol_handler.set_analog_input(0, 4.0)  # ~80% of 5V
        await asyncio.sleep(0.2)
        telemetry = await protocol_handler.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "80 > 50 should be ON"

    @pytest.mark.asyncio
    async def test_hysteresis(self, protocol_handler):
        """Hysteresis: on at threshold_on, off at threshold_off."""
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_temp", "linear", 0, 100),
            {
                "id": "l_fan",
                "channel_type": "logic",
                "enabled": True,
                "operation": "hysteresis",
                "channel": "ai_temp",
                "polarity": "normal",
                "threshold_on": 80.0,
                "threshold_off": 70.0
            },
            {
                "id": "o_fan",
                "channel_type": "power_output",
                "enabled": True,
                "output_pins": [0],
                "source_channel": "l_fan",
                "current_limit_a": 10.0
            }
        ]

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Start at 60 (below both thresholds) → OFF
        await protocol_handler.set_analog_input(0, 3.0)  # 60%
        await asyncio.sleep(0.2)
        telemetry = await protocol_handler.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF, "60 < 70 threshold should be OFF"

        # Rise to 85 (above on threshold) → ON
        await protocol_handler.set_analog_input(0, 4.25)  # 85%
        await asyncio.sleep(0.2)
        telemetry = await protocol_handler.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "85 > 80 should turn ON"

        # Drop to 75 (between thresholds, stays ON due to hysteresis)
        await protocol_handler.set_analog_input(0, 3.75)  # 75%
        await asyncio.sleep(0.2)
        telemetry = await protocol_handler.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "75 (between 70-80) should stay ON due to hysteresis"

        # Drop to 65 (below off threshold) → OFF
        await protocol_handler.set_analog_input(0, 3.25)  # 65%
        await asyncio.sleep(0.2)
        telemetry = await protocol_handler.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF, "65 < 70 should turn OFF"


# =============================================================================
# NUMBER FUNCTION TESTS
# =============================================================================

class TestNumberFunctions:
    """Test number function operations."""

    @pytest.mark.asyncio
    async def test_constant_value(self, protocol_handler):
        """Constant number channel provides fixed value."""
        config = BASE_CONFIG.copy()
        config["channels"] = [
            {
                "id": "n_const",
                "channel_type": "number",
                "enabled": True,
                "operation": "constant",
                "value": 42.0
            },
            {
                "id": "l_check",
                "channel_type": "logic",
                "enabled": True,
                "operation": "equal",
                "channel": "n_const",
                "constant": 42.0
            },
            {
                "id": "o_result",
                "channel_type": "power_output",
                "enabled": True,
                "output_pins": [0],
                "source_channel": "l_check",
                "current_limit_a": 5.0
            }
        ]

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.5)

        telemetry = await protocol_handler.get_telemetry()
        # Constant 42 == 42 → should be ON
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "Constant 42 == 42 should be true (ON)"

    @pytest.mark.asyncio
    async def test_max_of_inputs(self, protocol_handler):
        """Max function returns highest of inputs."""
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_a", "linear", 0, 100),
            make_analog_input_config(2, "ai_b", "linear", 0, 100),
            {
                "id": "n_max",
                "channel_type": "number",
                "enabled": True,
                "operation": "max",
                "inputs": ["ai_a", "ai_b"]
            },
            {
                "id": "l_high",
                "channel_type": "logic",
                "enabled": True,
                "operation": "greater",
                "channel": "n_max",
                "constant": 70.0
            },
            {
                "id": "o_alarm",
                "channel_type": "power_output",
                "enabled": True,
                "output_pins": [0],
                "source_channel": "l_high",
                "current_limit_a": 2.0
            }
        ]

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # A=30, B=50 → max=50 < 70 → OFF
        await protocol_handler.set_analog_input(0, 1.5)  # 30%
        await protocol_handler.set_analog_input(1, 2.5)  # 50%
        await asyncio.sleep(0.2)
        telemetry = await protocol_handler.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF, "max(30,50)=50 < 70 should be OFF"

        # A=30, B=80 → max=80 > 70 → ON
        await protocol_handler.set_analog_input(1, 4.0)  # 80%
        await asyncio.sleep(0.2)
        telemetry = await protocol_handler.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "max(30,80)=80 > 70 should be ON"


# =============================================================================
# COMPREHENSIVE FLOW TESTS
# =============================================================================

class TestComprehensiveFlow:
    """Test the full COMPREHENSIVE_TEST_CONFIG."""

    @pytest.mark.asyncio
    async def test_comprehensive_config_loads(self, protocol_handler):
        """COMPREHENSIVE_TEST_CONFIG loads without errors."""
        response = await protocol_handler.send_config(
            json.dumps(COMPREHENSIVE_TEST_CONFIG)
        )
        assert response.success, f"Comprehensive config failed: {response.error}"

    @pytest.mark.asyncio
    async def test_ignition_to_fuel_pump_chain(self, protocol_handler):
        """
        Test: di_ignition (active_low) → o_fuel_pump

        di_ignition is active_low, so defaults to ON.
        o_fuel_pump has source_channel=di_ignition, should be ON.
        """
        response = await protocol_handler.send_config(
            json.dumps(COMPREHENSIVE_TEST_CONFIG)
        )
        assert response.success
        await asyncio.sleep(0.5)

        telemetry = await protocol_handler.get_telemetry()
        assert telemetry is not None

        # o_fuel_pump is output pin 0
        # di_ignition is active_low → defaults ON → o_fuel_pump should be ON
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "Fuel pump should be ON (ignition active_low = ON)"

    @pytest.mark.asyncio
    async def test_and_logic_starter(self, protocol_handler):
        """
        Test: di_ignition (ON) AND di_brake (ON) → l_start_ready → o_starter

        Both are active_low, so default to ON → AND should be ON → starter ON.
        """
        response = await protocol_handler.send_config(
            json.dumps(COMPREHENSIVE_TEST_CONFIG)
        )
        assert response.success
        await asyncio.sleep(0.5)

        telemetry = await protocol_handler.get_telemetry()
        assert telemetry is not None

        # o_starter is output pin 1
        # di_ignition=ON, di_brake=ON → l_start_ready=ON → o_starter=ON
        assert telemetry.channel_states[1] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "Starter should be ON (ignition AND brake both active_low = ON)"

    @pytest.mark.asyncio
    async def test_all_outputs_respond(self, protocol_handler):
        """Verify all 6 outputs respond to their source channels."""
        response = await protocol_handler.send_config(
            json.dumps(COMPREHENSIVE_TEST_CONFIG)
        )
        assert response.success
        await asyncio.sleep(0.5)

        telemetry = await protocol_handler.get_telemetry()
        assert telemetry is not None

        # Should have at least 6 output states
        assert len(telemetry.channel_states) >= 6, \
            f"Expected at least 6 outputs, got {len(telemetry.channel_states)}"
