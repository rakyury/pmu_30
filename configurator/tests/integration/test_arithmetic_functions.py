"""
Integration Tests: Arithmetic Functions (Number Channel)
Tests Number channel math operations through the emulator.

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



def make_analog_input_config(input_num: int, name: str, scale: float = 1.0, offset: float = 0.0) -> dict:
    """Create analog input configuration."""
    return {
        "channel_id": 200 + input_num,
        "channel_type": "analog_input",
        "id": name,
        "name": name,
        "channel": input_num - 1,
        "input_type": "linear",
        "scale": scale,
        "offset": offset,
    }


def make_number_config(channel_id: int, name: str, operation: str,
                       input1: str = None, input2: str = None,
                       constant1: float = None, constant2: float = None) -> dict:
    """Create number/math channel configuration."""
    config = {
        "channel_id": channel_id,
        "channel_type": "number",
        "id": name,
        "name": name,
        "operation": operation,
    }
    if input1:
        config["input1_channel"] = input1
    if input2:
        config["input2_channel"] = input2
    if constant1 is not None:
        config["constant1"] = constant1
    if constant2 is not None:
        config["constant2"] = constant2
    return config
class TestBasicArithmetic:
    """Test basic arithmetic operations (add, subtract, multiply, divide)."""

    async def test_add_two_inputs(self, emulator_connection):
        """
        Test: Number channel adds two analog inputs.
        n_sum = ai_1 + ai_2
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_1"),
            make_analog_input_config(2, "ai_2"),
            make_number_config(300, "n_sum", "add", "ai_1", "ai_2"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Set inputs: 2.5V + 1.5V = 4.0V (scaled by 1000 internally)
        await protocol.set_analog_input(0, 2.5)
        await protocol.set_analog_input(1, 1.5)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        result = telemetry.virtual_channels.get(300, 0) / 1000.0  # Scale back

        assert abs(result - 4.0) < 0.1, \
            f"2.5 + 1.5 should be 4.0, got {result}"

    async def test_subtract_inputs(self, emulator_connection):
        """
        Test: Number channel subtracts two analog inputs.
        n_diff = ai_1 - ai_2
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_1"),
            make_analog_input_config(2, "ai_2"),
            make_number_config(300, "n_diff", "subtract", "ai_1", "ai_2"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Set inputs: 3.0V - 1.0V = 2.0V
        await protocol.set_analog_input(0, 3.0)
        await protocol.set_analog_input(1, 1.0)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        result = telemetry.virtual_channels.get(300, 0) / 1000.0

        assert abs(result - 2.0) < 0.1, \
            f"3.0 - 1.0 should be 2.0, got {result}"

    async def test_multiply_inputs(self, emulator_connection):
        """
        Test: Number channel multiplies two inputs.
        n_product = ai_1 * ai_2
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_1"),
            make_analog_input_config(2, "ai_2"),
            make_number_config(300, "n_product", "multiply", "ai_1", "ai_2"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Set inputs: 2.0V * 3.0V = 6.0 (scaled)
        await protocol.set_analog_input(0, 2.0)
        await protocol.set_analog_input(1, 3.0)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        result = telemetry.virtual_channels.get(300, 0) / 1000000.0  # Double scale for multiply

        assert abs(result - 6.0) < 0.5, \
            f"2.0 * 3.0 should be 6.0, got {result}"

    async def test_divide_inputs(self, emulator_connection):
        """
        Test: Number channel divides two inputs.
        n_quotient = ai_1 / ai_2
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_1"),
            make_analog_input_config(2, "ai_2"),
            make_number_config(300, "n_quotient", "divide", "ai_1", "ai_2"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Set inputs: 6.0V / 2.0V = 3.0
        await protocol.set_analog_input(0, 6.0)
        await protocol.set_analog_input(1, 2.0)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        result = telemetry.virtual_channels.get(300, 0) / 1000.0

        assert abs(result - 3.0) < 0.2, \
            f"6.0 / 2.0 should be 3.0, got {result}"


class TestMathWithConstants:
    """Test arithmetic with constant values."""

    async def test_add_constant(self, emulator_connection):
        """
        Test: Add constant to input.
        n_result = ai_1 + 5.0
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_1"),
            make_number_config(300, "n_result", "add", "ai_1", constant1=5.0),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        await protocol.set_analog_input(0, 2.0)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        result = telemetry.virtual_channels.get(300, 0) / 1000.0

        assert abs(result - 7.0) < 0.2, \
            f"2.0 + 5.0 should be 7.0, got {result}"

    async def test_scale_by_constant(self, emulator_connection):
        """
        Test: Multiply input by constant (scaling).
        n_scaled = ai_1 * 2.5
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_1"),
            make_number_config(300, "n_scaled", "multiply", "ai_1", constant1=2.5),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        await protocol.set_analog_input(0, 4.0)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        result = telemetry.virtual_channels.get(300, 0) / 1000000.0

        assert abs(result - 10.0) < 0.5, \
            f"4.0 * 2.5 should be 10.0, got {result}"


class TestMinMaxClamp:
    """Test min, max, and clamp operations."""

    async def test_min_of_two_inputs(self, emulator_connection):
        """
        Test: Return minimum of two inputs.
        n_min = min(ai_1, ai_2)
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_1"),
            make_analog_input_config(2, "ai_2"),
            make_number_config(300, "n_min", "min", "ai_1", "ai_2"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # ai_1 = 5.0, ai_2 = 3.0 -> min = 3.0
        await protocol.set_analog_input(0, 5.0)
        await protocol.set_analog_input(1, 3.0)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        result = telemetry.virtual_channels.get(300, 0) / 1000.0

        assert abs(result - 3.0) < 0.2, \
            f"min(5.0, 3.0) should be 3.0, got {result}"

    async def test_max_of_two_inputs(self, emulator_connection):
        """
        Test: Return maximum of two inputs.
        n_max = max(ai_1, ai_2)
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_1"),
            make_analog_input_config(2, "ai_2"),
            make_number_config(300, "n_max", "max", "ai_1", "ai_2"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # ai_1 = 2.0, ai_2 = 7.0 -> max = 7.0
        await protocol.set_analog_input(0, 2.0)
        await protocol.set_analog_input(1, 7.0)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        result = telemetry.virtual_channels.get(300, 0) / 1000.0

        assert abs(result - 7.0) < 0.2, \
            f"max(2.0, 7.0) should be 7.0, got {result}"

    async def test_clamp_value(self, emulator_connection):
        """
        Test: Clamp input between min and max.
        n_clamped = clamp(ai_1, 2.0, 8.0)
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_1"),
            make_number_config(300, "n_clamped", "clamp", "ai_1",
                             constant1=2.0, constant2=8.0),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        test_cases = [
            (1.0, 2.0),   # Below min -> clamped to min
            (5.0, 5.0),   # Within range -> unchanged
            (10.0, 8.0),  # Above max -> clamped to max
        ]

        for input_val, expected in test_cases:
            await protocol.set_analog_input(0, input_val)
            await asyncio.sleep(0.2)

            telemetry = await protocol.get_telemetry()
            result = telemetry.virtual_channels.get(300, 0) / 1000.0

            assert abs(result - expected) < 0.2, \
                f"clamp({input_val}, 2.0, 8.0) should be {expected}, got {result}"


class TestChainedMath:
    """Test chained arithmetic operations."""

    async def test_average_of_three_inputs(self, emulator_connection):
        """
        Test: Calculate average of three inputs.
        n_sum = ai_1 + ai_2 + ai_3
        n_avg = n_sum / 3.0
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_1"),
            make_analog_input_config(2, "ai_2"),
            make_analog_input_config(3, "ai_3"),
            make_number_config(300, "n_sum12", "add", "ai_1", "ai_2"),
            make_number_config(301, "n_sum123", "add", "n_sum12", "ai_3"),
            make_number_config(302, "n_avg", "divide", "n_sum123", constant1=3.0),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Set inputs: (3.0 + 6.0 + 9.0) / 3 = 6.0
        await protocol.set_analog_input(0, 3.0)
        await protocol.set_analog_input(1, 6.0)
        await protocol.set_analog_input(2, 9.0)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        result = telemetry.virtual_channels.get(302, 0) / 1000.0

        assert abs(result - 6.0) < 0.5, \
            f"avg(3.0, 6.0, 9.0) should be 6.0, got {result}"


class TestMathControlsOutput:
    """Test math results controlling outputs via comparison."""

    async def test_output_on_when_sum_exceeds_threshold(self, emulator_connection):
        """
        Test: Output activates when sum of inputs exceeds threshold.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_1"),
            make_analog_input_config(2, "ai_2"),
            make_number_config(300, "n_sum", "add", "ai_1", "ai_2"),
            make_logic_config(301, "l_over_threshold", "greater", "n_sum", constant=5.0),
            make_output_config(1, "o_1", "l_over_threshold"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Sum = 2.0 + 2.0 = 4.0 < 5.0 -> output OFF
        await protocol.set_analog_input(0, 2.0)
        await protocol.set_analog_input(1, 2.0)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF, \
            "Output should be OFF when sum < threshold"

        # Sum = 3.0 + 3.0 = 6.0 > 5.0 -> output ON
        await protocol.set_analog_input(0, 3.0)
        await protocol.set_analog_input(1, 3.0)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "Output should be ON when sum > threshold"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
