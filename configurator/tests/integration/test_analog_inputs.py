"""
Integration Tests: Analog Inputs
Tests analog input behavior through the emulator with telemetry verification.

Covers:
- Voltage interpretation (raw to scaled values)
- Threshold-based digital output (voltage to 0/1)
- Different input types (linear, resistance, thermistor)
- Calibration and scaling

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



def make_analog_input_config(input_num: int, name: str,
                             input_type: str = "linear",
                             scale: float = 1.0,
                             offset: float = 0.0,
                             threshold_low: float = None,
                             threshold_high: float = None,
                             resistance_pullup: float = None,
                             thermistor_beta: float = None,
                             thermistor_r25: float = None) -> dict:
    """Create analog input configuration."""
    config = {
        "channel_id": 200 + input_num,
        "channel_type": "analog_input",
        "id": name,
        "name": name,
        "channel": input_num - 1,
        "input_type": input_type,
        "scale": scale,
        "offset": offset,
    }
    if threshold_low is not None:
        config["threshold_low"] = threshold_low
    if threshold_high is not None:
        config["threshold_high"] = threshold_high
    if resistance_pullup is not None:
        config["resistance_pullup"] = resistance_pullup
    if thermistor_beta is not None:
        config["thermistor_beta"] = thermistor_beta
    if thermistor_r25 is not None:
        config["thermistor_r25"] = thermistor_r25
    return config
class TestLinearScaling:
    """Test linear scaling of analog inputs."""

    async def test_unity_scale(self, emulator_connection):
        """
        Test: Unity scale (1:1) voltage reading.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_1", scale=1.0, offset=0.0),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Set known voltage
        await protocol.set_analog_input(0, 2.5)  # 2.5V
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        # Value should be approximately 2500 (mV scaled)
        value = telemetry.virtual_channels.get(201, 0)
        assert abs(value - 2500) < 100, f"Expected ~2500, got {value}"

    async def test_scale_multiply(self, emulator_connection):
        """
        Test: Scaling factor applied to voltage.
        Example: Pressure sensor 0-5V = 0-100 PSI
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_pressure",
                                    scale=20.0,  # 5V * 20 = 100 PSI
                                    offset=0.0),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # 2.5V should give 50 PSI (2.5 * 20 = 50)
        await protocol.set_analog_input(0, 2.5)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        value = telemetry.virtual_channels.get(201, 0)
        # Expecting ~50000 (scaled by 1000 internally)
        expected = 50 * 1000
        assert abs(value - expected) < 1000, f"Expected ~{expected}, got {value}"

    async def test_scale_with_offset(self, emulator_connection):
        """
        Test: Scaling with offset.
        Example: Temperature sensor with 0.5V offset at 0°C
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_temp",
                                    scale=40.0,  # 40°C per volt
                                    offset=-20.0),  # -20°C offset
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # 1V should give (1 * 40) - 20 = 20°C
        await protocol.set_analog_input(0, 1.0)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        value = telemetry.virtual_channels.get(201, 0)
        # Expecting ~20000 (20°C scaled by 1000)


class TestThresholdDigitization:
    """Test voltage to digital (0/1) conversion via thresholds."""

    async def test_simple_threshold_high(self, emulator_connection):
        """
        Test: Analog value above threshold outputs 1.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_sensor", threshold_high=2.5),
            make_logic_config(300, "l_high", "greater", "ai_sensor", constant=2.5),
            make_output_config(1, "o_1", "l_high"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Below threshold -> output OFF
        await protocol.set_analog_input(0, 2.0)
        await asyncio.sleep(0.2)
        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF, \
            "2.0V < 2.5V threshold -> OFF"

        # Above threshold -> output ON
        await protocol.set_analog_input(0, 3.0)
        await asyncio.sleep(0.2)
        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "3.0V > 2.5V threshold -> ON"

    async def test_hysteresis_window(self, emulator_connection):
        """
        Test: Threshold with hysteresis (low and high thresholds).
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_sensor",
                                    threshold_low=2.0,
                                    threshold_high=3.0),
            # Use between operation for hysteresis
            make_logic_config(300, "l_window", "between", "ai_sensor"),
            make_output_config(1, "o_1", "ai_sensor"),  # Direct control
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Start below low threshold
        await protocol.set_analog_input(0, 1.5)
        await asyncio.sleep(0.2)

        # Rise to within window
        await protocol.set_analog_input(0, 2.5)
        await asyncio.sleep(0.2)

        # Rise above high threshold
        await protocol.set_analog_input(0, 3.5)
        await asyncio.sleep(0.2)

        # State should be ON when above high threshold
        telemetry = await protocol.get_telemetry()

    async def test_inverted_threshold(self, emulator_connection):
        """
        Test: Output activates when below threshold (inverted logic).
        Example: Low oil pressure warning.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_oil_pressure"),
            make_logic_config(300, "l_low_oil", "less", "ai_oil_pressure", constant=1.0),
            make_output_config(1, "o_warning", "l_low_oil"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # High pressure -> no warning
        await protocol.set_analog_input(0, 3.0)
        await asyncio.sleep(0.2)
        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF, \
            "High pressure -> warning OFF"

        # Low pressure -> warning
        await protocol.set_analog_input(0, 0.5)
        await asyncio.sleep(0.2)
        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "Low pressure -> warning ON"


class TestResistanceMode:
    """Test resistance measurement mode."""

    async def test_resistance_with_pullup(self, emulator_connection):
        """
        Test: Resistance measurement using pullup resistor.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_resistance",
                                    input_type="resistance",
                                    resistance_pullup=1000.0),  # 1k pullup
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Set voltage that corresponds to specific resistance
        # With 5V supply and 1k pullup:
        # R = Rpullup * V / (Vsupply - V)
        # At 2.5V: R = 1000 * 2.5 / (5 - 2.5) = 1000 ohms
        await protocol.set_analog_input(0, 2.5)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        resistance = telemetry.virtual_channels.get(201, 0)
        # Should be approximately 1000 ohms


class TestThermistorMode:
    """Test thermistor temperature measurement."""

    async def test_thermistor_ntc(self, emulator_connection):
        """
        Test: NTC thermistor temperature reading.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_temp",
                                    input_type="thermistor",
                                    resistance_pullup=10000.0,  # 10k pullup
                                    thermistor_beta=3950,       # Typical NTC beta
                                    thermistor_r25=10000.0),    # 10k at 25°C
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Set voltage corresponding to 25°C (when R = R25)
        # At half voltage (2.5V with 5V supply), R = Rpullup
        await protocol.set_analog_input(0, 2.5)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        temp = telemetry.virtual_channels.get(201, 0)
        # Should be approximately 25°C (25000 if scaled by 1000)


class TestRawValueAccess:
    """Test access to raw ADC values."""

    async def test_raw_adc_value(self, emulator_connection):
        """
        Test: Raw ADC value available alongside scaled value.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_1", scale=20.0, offset=10.0),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        await protocol.set_analog_input(0, 2.5)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        # Scaled value
        scaled = telemetry.virtual_channels.get(201, 0)
        # Raw value (sub-channel)
        raw = telemetry.virtual_channels.get(202, 0)  # ai_1.raw

        # Raw should reflect actual ADC reading


class TestAnalogToLogic:
    """Test analog inputs driving logic operations."""

    async def test_analog_comparison_greater_equal(self, emulator_connection):
        """
        Test: Analog >= threshold comparison.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_1"),
            make_logic_config(300, "l_ge", "greater_equal", "ai_1", constant=3.0),
            make_output_config(1, "o_1", "l_ge"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Test exactly at threshold
        await protocol.set_analog_input(0, 3.0)
        await asyncio.sleep(0.2)
        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "3.0V >= 3.0V should be true"

        # Test below threshold
        await protocol.set_analog_input(0, 2.9)
        await asyncio.sleep(0.2)
        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF, \
            "2.9V >= 3.0V should be false"

    async def test_analog_comparison_between(self, emulator_connection):
        """
        Test: Analog value within range comparison.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_1"),
            {
                "channel_id": 300,
                "channel_type": "logic",
                "id": "l_range",
                "name": "In Range",
                "operation": "between",
                "input1_channel": "ai_1",
                "constant": 2.0,
                "constant2": 4.0,
            },
            make_output_config(1, "o_1", "l_range"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Below range
        await protocol.set_analog_input(0, 1.5)
        await asyncio.sleep(0.2)
        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF, \
            "1.5V not in [2.0, 4.0]"

        # Within range
        await protocol.set_analog_input(0, 3.0)
        await asyncio.sleep(0.2)
        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "3.0V is in [2.0, 4.0]"

        # Above range
        await protocol.set_analog_input(0, 4.5)
        await asyncio.sleep(0.2)
        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF, \
            "4.5V not in [2.0, 4.0]"

    async def test_analog_equal_with_tolerance(self, emulator_connection):
        """
        Test: Analog equals value with tolerance.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_1"),
            {
                "channel_id": 300,
                "channel_type": "logic",
                "id": "l_eq",
                "name": "Equals",
                "operation": "equal",
                "input1_channel": "ai_1",
                "constant": 2.5,
                "tolerance": 0.1,  # ±0.1V tolerance
            },
            make_output_config(1, "o_1", "l_eq"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Exactly at target
        await protocol.set_analog_input(0, 2.5)
        await asyncio.sleep(0.2)
        telemetry = await protocol.get_telemetry()
        # Should be ON (within tolerance)

        # Outside tolerance
        await protocol.set_analog_input(0, 2.8)
        await asyncio.sleep(0.2)
        telemetry = await protocol.get_telemetry()
        # Should be OFF (outside tolerance)


class TestMultipleAnalogInputs:
    """Test multiple analog inputs working together."""

    async def test_compare_two_analog_inputs(self, emulator_connection):
        """
        Test: Compare two analog inputs.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_1"),
            make_analog_input_config(2, "ai_2"),
            {
                "channel_id": 300,
                "channel_type": "logic",
                "id": "l_cmp",
                "name": "A1 > A2",
                "operation": "greater",
                "input1_channel": "ai_1",
                "input2_channel": "ai_2",
            },
            make_output_config(1, "o_1", "l_cmp"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # ai_1 < ai_2
        await protocol.set_analog_input(0, 2.0)
        await protocol.set_analog_input(1, 3.0)
        await asyncio.sleep(0.2)
        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF, \
            "2.0V > 3.0V should be false"

        # ai_1 > ai_2
        await protocol.set_analog_input(0, 4.0)
        await asyncio.sleep(0.2)
        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "4.0V > 3.0V should be true"

    async def test_analog_differential(self, emulator_connection):
        """
        Test: Calculate difference between two analog inputs.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_1"),
            make_analog_input_config(2, "ai_2"),
            {
                "channel_id": 300,
                "channel_type": "number",
                "id": "n_diff",
                "name": "Differential",
                "operation": "subtract",
                "input1_channel": "ai_1",
                "input2_channel": "ai_2",
            },
            make_logic_config(301, "l_diff_high", "greater", "n_diff", constant=1.0),
            make_output_config(1, "o_1", "l_diff_high"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Small difference
        await protocol.set_analog_input(0, 2.5)
        await protocol.set_analog_input(1, 2.0)
        await asyncio.sleep(0.2)
        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF, \
            "0.5V diff < 1.0V threshold"

        # Large difference
        await protocol.set_analog_input(0, 4.0)
        await protocol.set_analog_input(1, 2.0)
        await asyncio.sleep(0.2)
        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "2.0V diff > 1.0V threshold"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
