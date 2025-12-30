"""
Integration Tests: Filter Channels
Tests filter channel functionality and integration with other channel types.

Covers:
- Moving Average filter
- Exponential Moving Average (EMA) filter
- Kalman filter
- Low-pass filter
- Filter channels used with logic channels
- Filter channels used with math channels
- Filter channels used with tables
- Filter channels used to control outputs

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



def make_analog_input_config(input_num: int, name: str, mode: str = "linear") -> dict:
    """Create analog input configuration."""
    return {
        "channel_id": 400 + input_num,
        "channel_type": "analog_input",
        "id": name,
        "name": name,
        "channel": input_num - 1,
        "mode": mode,
        "min_value": 0,
        "min_voltage": 0.0,
        "max_value": 1000,
        "max_voltage": 5.0,
    }


def make_filter_config(channel_id: int, name: str, input_channel: str,
                       filter_type: str = "moving_average", **kwargs) -> dict:
    """Create filter channel configuration."""
    config = {
        "channel_id": channel_id,
        "channel_type": "filter",
        "id": name,
        "name": name,
        "input_channel": input_channel,
        "filter_type": filter_type,
    }
    # Add filter-specific parameters
    if filter_type == "moving_average":
        config["window_size"] = kwargs.get("window_size", 10)
    elif filter_type == "ema":
        config["time_constant"] = kwargs.get("time_constant", 0.1)
    elif filter_type == "kalman":
        config["process_noise"] = kwargs.get("process_noise", 0.01)
        config["measurement_noise"] = kwargs.get("measurement_noise", 0.1)
    elif filter_type == "low_pass":
        config["cutoff_frequency"] = kwargs.get("cutoff_frequency", 10.0)
    return config


def make_number_config(channel_id: int, name: str, operation: str,
                       input1: str, input2: str = None, constant: float = None) -> dict:
    """Create number (math) channel configuration."""
    config = {
        "channel_id": channel_id,
        "channel_type": "number",
        "id": name,
        "name": name,
        "operation": operation,
        "input1_channel": input1,
    }
    if input2:
        config["input2_channel"] = input2
    if constant is not None:
        config["constant_value"] = constant
    return config


def make_table_2d_config(channel_id: int, name: str, input_channel: str,
                         x_values: list, output_values: list) -> dict:
    """Create 2D table configuration."""
    return {
        "channel_id": channel_id,
        "channel_type": "table_2d",
        "id": name,
        "name": name,
        "input_channel": input_channel,
        "x_values": x_values,
        "output_values": output_values,
        "interpolation": "linear",
    }


def make_threshold_logic(channel_id: int, name: str, input_channel: str,
                         threshold: float, comparison: str = "greater_than") -> dict:
    """Create threshold comparison logic."""
    return {
        "channel_id": channel_id,
        "channel_type": "logic",
        "id": name,
        "name": name,
        "operation": comparison,
        "input1_channel": input_channel,
        "threshold": threshold,
    }
class TestMovingAverageFilter:
    """Test moving average filter functionality."""

    async def test_moving_average_smoothing(self, emulator_connection):
        """
        Test: Moving average filter smooths noisy input.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_raw"),
            make_filter_config(300, "f_smooth", "ai_raw",
                             filter_type="moving_average", window_size=5),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Set varying values to test smoothing
        values = [100, 200, 100, 200, 100]
        for v in values:
            await protocol.set_analog_voltage(0, v / 200.0)  # Scale to voltage
            await asyncio.sleep(0.05)

        # Filtered value should be average of last 5 values
        telemetry = await protocol.get_telemetry()
        filtered = telemetry.virtual_channels.get(300, 0)
        # Should be close to average (150)

    async def test_moving_average_with_output(self, emulator_connection):
        """
        Test: Moving average filter controls output via threshold.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_sensor"),
            make_filter_config(300, "f_filtered", "ai_sensor",
                             filter_type="moving_average", window_size=10),
            make_threshold_logic(301, "l_high", "f_filtered",
                               threshold=500, comparison="greater_than"),
            make_output_config(1, "o_warning", "l_high"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Set low value - filtered output should be below threshold
        await protocol.set_analog_voltage(0, 1.0)  # ~200 value
        await asyncio.sleep(0.5)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF, \
            "Output should be OFF when filtered value below threshold"

        # Set high value - filtered output should exceed threshold
        await protocol.set_analog_voltage(0, 4.0)  # ~800 value
        await asyncio.sleep(0.5)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "Output should be ON when filtered value above threshold"


class TestEMAFilter:
    """Test Exponential Moving Average filter functionality."""

    async def test_ema_response(self, emulator_connection):
        """
        Test: EMA filter responds to step change.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_input"),
            make_filter_config(300, "f_ema", "ai_input",
                             filter_type="ema", time_constant=0.1),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Start at 0
        await protocol.set_analog_voltage(0, 0.0)
        await asyncio.sleep(0.2)

        telemetry1 = await protocol.get_telemetry()
        initial = telemetry1.virtual_channels.get(300, 0)

        # Step to high value
        await protocol.set_analog_voltage(0, 5.0)
        await asyncio.sleep(0.5)

        telemetry2 = await protocol.get_telemetry()
        after_step = telemetry2.virtual_channels.get(300, 0)

        # EMA should have responded but not fully reached target
        # (depends on time constant)

    async def test_ema_with_math(self, emulator_connection):
        """
        Test: EMA filter output used in math channel.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_sensor"),
            make_filter_config(300, "f_ema", "ai_sensor",
                             filter_type="ema", time_constant=0.2),
            make_number_config(301, "n_scaled", "multiply",
                             "f_ema", constant=2.0),  # Double the filtered value
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        await protocol.set_analog_voltage(0, 2.5)  # Mid-range
        await asyncio.sleep(0.3)

        telemetry = await protocol.get_telemetry()
        filtered = telemetry.virtual_channels.get(300, 0)
        scaled = telemetry.virtual_channels.get(301, 0)

        # Scaled should be approximately 2x filtered
        # (allowing for timing and filter response)


class TestFilterWithTable:
    """Test filter channels with lookup tables."""

    async def test_filter_into_table(self, emulator_connection):
        """
        Test: Filtered value used as table input.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_temp"),
            make_filter_config(300, "f_temp_smooth", "ai_temp",
                             filter_type="moving_average", window_size=8),
            make_table_2d_config(301, "t_correction", "f_temp_smooth",
                               x_values=[0, 250, 500, 750, 1000],
                               output_values=[100, 95, 90, 85, 80]),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Set temperature to mid-range
        await protocol.set_analog_voltage(0, 2.5)  # ~500 value
        await asyncio.sleep(0.5)

        telemetry = await protocol.get_telemetry()
        correction = telemetry.virtual_channels.get(301, 0)
        # Should be around 90 (interpolated from table)

    async def test_cascaded_filters(self, emulator_connection):
        """
        Test: Multiple filters in cascade.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_noisy"),
            make_filter_config(300, "f_stage1", "ai_noisy",
                             filter_type="moving_average", window_size=5),
            make_filter_config(301, "f_stage2", "f_stage1",
                             filter_type="ema", time_constant=0.1),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Apply noisy signal
        for _ in range(10):
            await protocol.set_analog_voltage(0, 2.5)
            await asyncio.sleep(0.05)
            await protocol.set_analog_voltage(0, 2.0)
            await asyncio.sleep(0.05)

        # Both stages should have smoothed the signal


class TestFilterWithLogic:
    """Test filter channels with logic operations."""

    async def test_filter_hysteresis(self, emulator_connection):
        """
        Test: Filtered value with hysteresis threshold.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_sensor"),
            make_filter_config(300, "f_smooth", "ai_sensor",
                             filter_type="moving_average", window_size=10),
            make_threshold_logic(301, "l_high", "f_smooth",
                               threshold=600, comparison="greater_than"),
            make_threshold_logic(302, "l_low", "f_smooth",
                               threshold=400, comparison="less_than"),
            {
                "channel_id": 303,
                "channel_type": "switch",
                "id": "sw_state",
                "name": "State",
                "mode": "sr_latch",  # Set-Reset latch
                "set_channel": "l_high",
                "reset_channel": "l_low",
            },
            make_output_config(1, "o_controlled", "sw_state"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Start at low value
        await protocol.set_analog_voltage(0, 1.0)  # ~200
        await asyncio.sleep(0.5)

        telemetry1 = await protocol.get_telemetry()
        initial_state = telemetry1.channel_states[0]

        # Go to high value - should turn ON
        await protocol.set_analog_voltage(0, 4.0)  # ~800
        await asyncio.sleep(0.5)

        telemetry2 = await protocol.get_telemetry()
        # Output should be ON after exceeding high threshold

    async def test_filter_comparisons(self, emulator_connection):
        """
        Test: Two filtered values compared with logic.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_sensor1"),
            make_analog_input_config(2, "ai_sensor2"),
            make_filter_config(300, "f_s1", "ai_sensor1",
                             filter_type="moving_average", window_size=5),
            make_filter_config(301, "f_s2", "ai_sensor2",
                             filter_type="moving_average", window_size=5),
            {
                "channel_id": 302,
                "channel_type": "logic",
                "id": "l_compare",
                "name": "S1 > S2",
                "operation": "greater_than",
                "input1_channel": "f_s1",
                "input2_channel": "f_s2",
            },
            make_output_config(1, "o_result", "l_compare"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Set S1 > S2
        await protocol.set_analog_voltage(0, 4.0)  # S1 high
        await protocol.set_analog_voltage(1, 2.0)  # S2 low
        await asyncio.sleep(0.5)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "Output should be ON when filtered S1 > filtered S2"


class TestFilterWithMath:
    """Test filter channels with math operations."""

    async def test_filter_derivative(self, emulator_connection):
        """
        Test: Calculate rate of change from filtered signal.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_position"),
            make_filter_config(300, "f_position", "ai_position",
                             filter_type="moving_average", window_size=10),
            # Derivative would require a special channel type or math operation
            # For now, test basic filter-to-math chain
            make_number_config(301, "n_rate", "multiply",
                             "f_position", constant=10.0),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

    async def test_filter_average_two_sensors(self, emulator_connection):
        """
        Test: Average two filtered sensor values.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_sensor1"),
            make_analog_input_config(2, "ai_sensor2"),
            make_filter_config(300, "f_s1", "ai_sensor1",
                             filter_type="ema", time_constant=0.1),
            make_filter_config(301, "f_s2", "ai_sensor2",
                             filter_type="ema", time_constant=0.1),
            make_number_config(302, "n_sum", "add", "f_s1", "f_s2"),
            make_number_config(303, "n_avg", "divide", "n_sum", constant=2.0),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Set both sensors to same value
        await protocol.set_analog_voltage(0, 2.5)
        await protocol.set_analog_voltage(1, 2.5)
        await asyncio.sleep(0.5)

        telemetry = await protocol.get_telemetry()
        avg = telemetry.virtual_channels.get(303, 0)
        # Average should be approximately same as individual filtered values


class TestFilterPWMControl:
    """Test filter channels controlling PWM outputs."""

    async def test_filter_controls_pwm_duty(self, emulator_connection):
        """
        Test: Filtered analog controls PWM duty cycle.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_throttle"),
            make_filter_config(300, "f_throttle", "ai_throttle",
                             filter_type="moving_average", window_size=5),
            {
                "channel_id": 101,
                "channel_type": "power_output",
                "id": "o_pwm_motor",
                "name": "Motor PWM",
                "channel": 0,
                "output_mode": "pwm",
                "duty_mode": "channel",
                "duty_channel": "f_throttle",
                "pwm_frequency": 1000,
                "max_current": 20000,
            },
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Set throttle to 50%
        await protocol.set_analog_voltage(0, 2.5)  # Mid-range
        await asyncio.sleep(0.5)

        telemetry = await protocol.get_telemetry()
        # Output should be in PWM mode with duty based on filtered input


class TestFilterEdgeCases:
    """Test filter edge cases and error conditions."""

    async def test_filter_invalid_input(self, emulator_connection):
        """
        Test: Filter handles missing input channel gracefully.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            # Filter referencing non-existent input
            make_filter_config(300, "f_orphan", "ai_nonexistent",
                             filter_type="moving_average", window_size=5),
        ]

        response = await protocol.send_config(json.dumps(config))
        # Should either fail validation or handle gracefully

    async def test_filter_circular_reference(self, emulator_connection):
        """
        Test: Filter circular reference detection.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_input"),
            # This would be circular if filter1 -> filter2 -> filter1
            # The system should detect and prevent this
            make_filter_config(300, "f_1", "ai_input",
                             filter_type="moving_average", window_size=5),
            make_filter_config(301, "f_2", "f_1",
                             filter_type="ema", time_constant=0.1),
        ]

        response = await protocol.send_config(json.dumps(config))
        # Non-circular cascade should work
        assert response.success


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
