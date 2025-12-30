"""
Integration Tests: Power Output Control
Tests output channel behavior through the emulator with telemetry verification.

These tests require a running PMU-30 emulator.
"""

import pytest
import asyncio
import json

# Import fixtures and helpers from conftest
from .helpers import (
    BASE_CONFIG,
    make_output_config,
    make_digital_input_config,
    make_logic_config,
    ChannelState,
)


class TestOutputViaDigitalInput:
    """Test power output control via digital input."""

    async def test_output_follows_input(self, protocol_handler):
        """
        Test: Output follows digital input state.

        Scenario:
        1. Create digital input di_1
        2. Create output o_1 controlled by di_1
        3. Set di_1 = 1 -> verify o_1 activates
        4. Set di_1 = 0 -> verify o_1 deactivates
        """
        # Create test configuration
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_test1"),
            make_output_config(1, "o_test1", "di_test1"),
        ]

        # Send configuration
        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success, f"Config send failed: {response.error}"

        # Wait for config to be applied
        await asyncio.sleep(0.5)

        # Set digital input 1 = HIGH
        await protocol_handler.set_digital_input(0, True)
        await asyncio.sleep(0.2)

        # Get telemetry
        telemetry = await protocol_handler.get_telemetry()
        assert telemetry is not None, "No telemetry received"

        # Verify output 1 is active
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            f"Expected output 1 ON, got {telemetry.channel_states[0]}"

        # Set digital input 1 = LOW
        await protocol_handler.set_digital_input(0, False)
        await asyncio.sleep(0.2)

        # Get telemetry
        telemetry = await protocol_handler.get_telemetry()

        # Verify output 1 is off
        assert telemetry.channel_states[0] == ChannelState.OFF, \
            f"Expected output 1 OFF, got {telemetry.channel_states[0]}"

    async def test_multiple_outputs_independent(self, protocol_handler):
        """
        Test: Multiple outputs operate independently.

        Scenario:
        1. Create 3 digital inputs and 3 outputs
        2. Toggle each input independently
        3. Verify each output responds only to its input
        """
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_1"),
            make_digital_input_config(2, "di_2"),
            make_digital_input_config(3, "di_3"),
            make_output_config(1, "o_1", "di_1"),
            make_output_config(2, "o_2", "di_2"),
            make_output_config(3, "o_3", "di_3"),
        ]

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success, f"Config send failed: {response.error}"
        await asyncio.sleep(0.5)

        # Activate only input 2
        await protocol_handler.set_digital_input(0, False)
        await protocol_handler.set_digital_input(1, True)
        await protocol_handler.set_digital_input(2, False)
        await asyncio.sleep(0.2)

        telemetry = await protocol_handler.get_telemetry()

        # Only output 2 should be active
        assert telemetry.channel_states[0] == ChannelState.OFF, "Output 1 should be OFF"
        assert telemetry.channel_states[1] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "Output 2 should be ON"
        assert telemetry.channel_states[2] == ChannelState.OFF, "Output 3 should be OFF"


class TestOutputViaLogicFunction:
    """Test power output control via logic functions."""

    async def test_output_via_and_logic(self, protocol_handler):
        """
        Test: Output activates when AND of two inputs is true.

        Scenario:
        1. Create logic AND of di_1 and di_2
        2. Output controlled by logic result
        3. Test all combinations: 00=off, 01=off, 10=off, 11=on
        """
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_1"),
            make_digital_input_config(2, "di_2"),
            make_logic_config(300, "l_and", "and", "di_1", "di_2"),
            make_output_config(1, "o_1", "l_and"),
        ]

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.5)

        test_cases = [
            (False, False, ChannelState.OFF),
            (True, False, ChannelState.OFF),
            (False, True, ChannelState.OFF),
            (True, True, ChannelState.ON),
        ]

        for in1, in2, expected in test_cases:
            await protocol_handler.set_digital_input(0, in1)
            await protocol_handler.set_digital_input(1, in2)
            await asyncio.sleep(0.2)

            telemetry = await protocol_handler.get_telemetry()
            actual = telemetry.channel_states[0]

            if expected == ChannelState.ON:
                assert actual in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
                    f"AND({in1}, {in2}) should be ON, got {actual}"
            else:
                assert actual == ChannelState.OFF, \
                    f"AND({in1}, {in2}) should be OFF, got {actual}"

    async def test_output_via_or_logic(self, protocol_handler):
        """
        Test: Output activates when OR of two inputs is true.
        """
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_1"),
            make_digital_input_config(2, "di_2"),
            make_logic_config(300, "l_or", "or", "di_1", "di_2"),
            make_output_config(1, "o_1", "l_or"),
        ]

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.5)

        test_cases = [
            (False, False, ChannelState.OFF),
            (True, False, ChannelState.ON),
            (False, True, ChannelState.ON),
            (True, True, ChannelState.ON),
        ]

        for in1, in2, expected in test_cases:
            await protocol_handler.set_digital_input(0, in1)
            await protocol_handler.set_digital_input(1, in2)
            await asyncio.sleep(0.2)

            telemetry = await protocol_handler.get_telemetry()
            actual = telemetry.channel_states[0]

            if expected == ChannelState.ON:
                assert actual in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
                    f"OR({in1}, {in2}) should be ON, got {actual}"
            else:
                assert actual == ChannelState.OFF, \
                    f"OR({in1}, {in2}) should be OFF, got {actual}"

    async def test_output_via_not_logic(self, protocol_handler):
        """
        Test: Output activates when input is inverted (NOT).
        """
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_1"),
            make_logic_config(300, "l_not", "not", "di_1"),
            make_output_config(1, "o_1", "l_not"),
        ]

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.5)

        # Input LOW -> Output ON (inverted)
        await protocol_handler.set_digital_input(0, False)
        await asyncio.sleep(0.2)
        telemetry = await protocol_handler.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "NOT(0) should be ON"

        # Input HIGH -> Output OFF (inverted)
        await protocol_handler.set_digital_input(0, True)
        await asyncio.sleep(0.2)
        telemetry = await protocol_handler.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF, \
            "NOT(1) should be OFF"

    async def test_output_via_xor_logic(self, protocol_handler):
        """
        Test: Output activates when XOR of two inputs is true.
        """
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_1"),
            make_digital_input_config(2, "di_2"),
            make_logic_config(300, "l_xor", "xor", "di_1", "di_2"),
            make_output_config(1, "o_1", "l_xor"),
        ]

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.5)

        test_cases = [
            (False, False, ChannelState.OFF),
            (True, False, ChannelState.ON),
            (False, True, ChannelState.ON),
            (True, True, ChannelState.OFF),
        ]

        for in1, in2, expected in test_cases:
            await protocol_handler.set_digital_input(0, in1)
            await protocol_handler.set_digital_input(1, in2)
            await asyncio.sleep(0.2)

            telemetry = await protocol_handler.get_telemetry()
            actual = telemetry.channel_states[0]

            if expected == ChannelState.ON:
                assert actual in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
                    f"XOR({in1}, {in2}) should be ON, got {actual}"
            else:
                assert actual == ChannelState.OFF, \
                    f"XOR({in1}, {in2}) should be OFF, got {actual}"

    async def test_chained_logic_functions(self, protocol_handler):
        """
        Test: Chained logic functions work correctly.

        Scenario: ((di_1 AND di_2) OR di_3)
        """
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_1"),
            make_digital_input_config(2, "di_2"),
            make_digital_input_config(3, "di_3"),
            make_logic_config(300, "l_and", "and", "di_1", "di_2"),
            make_logic_config(301, "l_or", "or", "l_and", "di_3"),
            make_output_config(1, "o_1", "l_or"),
        ]

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.5)

        # Test: di_1=1, di_2=1, di_3=0 -> (1 AND 1) OR 0 = 1
        await protocol_handler.set_digital_input(0, True)
        await protocol_handler.set_digital_input(1, True)
        await protocol_handler.set_digital_input(2, False)
        await asyncio.sleep(0.2)

        telemetry = await protocol_handler.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "(1 AND 1) OR 0 should be ON"

        # Test: di_1=1, di_2=0, di_3=0 -> (1 AND 0) OR 0 = 0
        await protocol_handler.set_digital_input(1, False)
        await asyncio.sleep(0.2)

        telemetry = await protocol_handler.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF, \
            "(1 AND 0) OR 0 should be OFF"

        # Test: di_1=0, di_2=0, di_3=1 -> (0 AND 0) OR 1 = 1
        await protocol_handler.set_digital_input(0, False)
        await protocol_handler.set_digital_input(2, True)
        await asyncio.sleep(0.2)

        telemetry = await protocol_handler.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "(0 AND 0) OR 1 should be ON"


class TestOutputViaComparison:
    """Test power output control via comparison logic."""

    async def test_output_via_greater_than(self, protocol_handler):
        """
        Test: Output activates when analog > threshold.
        """
        config = BASE_CONFIG.copy()
        config["channels"] = [
            {
                "channel_id": 200,
                "channel_type": "analog_input",
                "id": "ai_1",
                "name": "Analog 1",
                "channel": 0,
                "input_type": "linear",
                "scale": 1.0,
                "offset": 0.0,
            },
            make_logic_config(300, "l_gt", "greater", "ai_1", constant=2.0),
            make_output_config(1, "o_1", "l_gt"),
        ]

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.5)

        # Set analog input below threshold
        await protocol_handler.set_analog_input(0, 1.5)  # 1.5V < 2.0V threshold
        await asyncio.sleep(0.2)

        telemetry = await protocol_handler.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF, \
            "1.5V > 2.0V should be false, output OFF"

        # Set analog input above threshold
        await protocol_handler.set_analog_input(0, 2.5)  # 2.5V > 2.0V threshold
        await asyncio.sleep(0.2)

        telemetry = await protocol_handler.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "2.5V > 2.0V should be true, output ON"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
