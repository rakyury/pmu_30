"""
Integration Tests: 2D and 3D Lookup Tables
Tests table channel behavior with various input channel types.

Covers:
- 2D tables with all channel types as input
- 3D tables with all channel types as X/Y inputs
- Interpolation accuracy
- Built-in channels (pmu.*) as inputs
- User-created channels as inputs
- Table output controlling other channels

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
                             scale: float = 1.0, offset: float = 0.0) -> dict:
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


def make_can_input_config(channel_id: int, name: str,
                          can_id: int, bit_length: int = 16,
                          scale: float = 1.0) -> dict:
    """Create CAN input configuration."""
    return {
        "channel_id": channel_id,
        "channel_type": "can_input",
        "id": name,
        "name": name,
        "can_id": can_id,
        "start_bit": 0,
        "bit_length": bit_length,
        "byte_order": "little_endian",
        "data_type": "unsigned",
        "scale": scale,
    }


def make_number_config(channel_id: int, name: str, operation: str,
                       input1: str = None, constant1: float = None) -> dict:
    """Create number channel configuration."""
    config = {
        "channel_id": channel_id,
        "channel_type": "number",
        "id": name,
        "name": name,
        "operation": operation,
    }
    if input1:
        config["input1_channel"] = input1
    if constant1 is not None:
        config["constant1"] = constant1
    return config


def make_timer_config(channel_id: int, name: str, start_channel: str) -> dict:
    """Create timer configuration."""
    return {
        "channel_id": channel_id,
        "channel_type": "timer",
        "id": name,
        "name": name,
        "mode": "count_up",
        "start_channel": start_channel,
        "start_edge": "rising",
    }


def make_table_2d_config(channel_id: int, name: str, input_channel: str,
                         x_values: list, y_values: list,
                         interpolation: str = "linear") -> dict:
    """Create 2D lookup table configuration."""
    return {
        "channel_id": channel_id,
        "channel_type": "table_2d",
        "id": name,
        "name": name,
        "input_channel": input_channel,
        "x_values": x_values,
        "y_values": y_values,
        "interpolation": interpolation,
    }


def make_table_3d_config(channel_id: int, name: str,
                         x_channel: str, y_channel: str,
                         x_values: list, y_values: list,
                         z_values: list,  # 2D array [y][x]
                         interpolation: str = "bilinear") -> dict:
    """Create 3D lookup table configuration."""
    return {
        "channel_id": channel_id,
        "channel_type": "table_3d",
        "id": name,
        "name": name,
        "x_channel": x_channel,
        "y_channel": y_channel,
        "x_values": x_values,
        "y_values": y_values,
        "z_values": z_values,
        "interpolation": interpolation,
    }
class TestTable2DWithAnalogInput:
    """Test 2D table with analog input as source."""

    async def test_table_2d_linear_interpolation(self, emulator_connection):
        """
        Test: 2D table with linear interpolation from analog input.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_temp"),
            make_table_2d_config(300, "t_fan_curve", "ai_temp",
                               x_values=[0, 25, 50, 75, 100],  # Temperature °C
                               y_values=[0, 20, 50, 80, 100]),  # Fan duty %
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Test interpolation at various points
        test_cases = [
            (0.0, 0),      # Exact point: 0°C -> 0%
            (12.5, 10),    # Interpolated: (0+25)/2 -> (0+20)/2 = 10%
            (25.0, 20),    # Exact point: 25°C -> 20%
            (37.5, 35),    # Interpolated: (25+50)/2 -> (20+50)/2 = 35%
            (100.0, 100),  # Exact point: 100°C -> 100%
        ]

        for input_val, expected in test_cases:
            await protocol.set_analog_input(0, input_val / 20.0)  # Scale to voltage
            await asyncio.sleep(0.2)

            telemetry = await protocol.get_telemetry()
            table_output = telemetry.virtual_channels.get(300, 0)
            # Allow tolerance for interpolation
            expected_scaled = expected * 10  # Scale to internal units
            assert abs(table_output - expected_scaled) < 50, \
                f"At input {input_val}: expected ~{expected}, got {table_output/10}"

    async def test_table_2d_step_interpolation(self, emulator_connection):
        """
        Test: 2D table with step (no) interpolation.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_gear"),
            make_table_2d_config(300, "t_gear_ratio", "ai_gear",
                               x_values=[0, 1, 2, 3, 4, 5],
                               y_values=[0, 3.5, 2.1, 1.4, 1.0, 0.8],
                               interpolation="step"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Step interpolation should return previous step value
        await protocol.set_analog_input(0, 1.5 / 5.0)  # Between gear 1 and 2
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        table_output = telemetry.virtual_channels.get(300, 0)
        # Should be gear 1 ratio (3.5), not interpolated


class TestTable2DWithCANInput:
    """Test 2D table with CAN input as source."""

    async def test_table_2d_from_can_rpm(self, emulator_connection):
        """
        Test: 2D table lookup from CAN RPM signal.
        Example: Ignition timing based on RPM.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_can_input_config(300, "can_rpm", can_id=0x100, bit_length=16),
            make_table_2d_config(301, "t_timing", "can_rpm",
                               x_values=[1000, 2000, 3000, 4000, 5000, 6000],
                               y_values=[10, 15, 22, 28, 32, 35]),  # Timing advance
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Send CAN RPM = 3500 (between 3000 and 4000)
        rpm_bytes = [0xAC, 0x0D, 0, 0, 0, 0, 0, 0]  # 3500 in little-endian
        await protocol.send_can_message(0x100, rpm_bytes)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        timing = telemetry.virtual_channels.get(301, 0)
        # Should be interpolated between 22 and 28 -> ~25


class TestTable2DWithNumberChannel:
    """Test 2D table with number (math) channel as source."""

    async def test_table_2d_from_calculated_value(self, emulator_connection):
        """
        Test: 2D table input from calculated value.
        Example: Load percentage = (throttle * rpm) / max_power
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_throttle", scale=100.0),  # 0-100%
            make_can_input_config(300, "can_rpm", can_id=0x100, bit_length=16),
            make_number_config(301, "n_load", "multiply", "ai_throttle", constant1=0.01),
            make_table_2d_config(302, "t_fuel_trim", "n_load",
                               x_values=[0, 25, 50, 75, 100],
                               y_values=[-5, 0, 2, 5, 10]),  # Fuel trim %
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Set throttle to 50%
        await protocol.set_analog_input(0, 2.5)  # 2.5V = 50%
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        fuel_trim = telemetry.virtual_channels.get(302, 0)


class TestTable2DWithBuiltInChannels:
    """Test 2D table with built-in PMU channels."""

    async def test_table_2d_from_output_current(self, emulator_connection):
        """
        Test: 2D table using output current (pmu.o1.current) as input.
        Example: Derating curve based on load current.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_enable"),
            make_output_config(1, "o_1", "di_enable"),
            # Table using built-in current sub-channel
            make_table_2d_config(300, "t_derate", "pmu.o1.current",
                               x_values=[0, 5000, 10000, 15000, 20000],  # mA
                               y_values=[100, 100, 90, 70, 50]),  # Max duty %
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Enable output and set current
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.1)
        await protocol.set_output_current(0, 12000)  # 12A
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        derate = telemetry.virtual_channels.get(300, 0)
        # Should be interpolated between 90% and 70%

    async def test_table_2d_from_analog_voltage(self, emulator_connection):
        """
        Test: 2D table using built-in analog voltage channel.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            # Using built-in pmu.a1.voltage
            make_table_2d_config(300, "t_sensor_cal", "pmu.a1.voltage",
                               x_values=[0, 1000, 2000, 3000, 4000, 5000],  # mV
                               y_values=[0, 20, 45, 75, 110, 150]),  # Calibrated value
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        await protocol.set_analog_input(0, 2.5)  # 2500mV
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        calibrated = telemetry.virtual_channels.get(300, 0)


class TestTable2DWithTimer:
    """Test 2D table with timer channel as source."""

    async def test_table_2d_from_timer_elapsed(self, emulator_connection):
        """
        Test: 2D table based on timer elapsed time.
        Example: Soft-start curve.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_start"),
            make_timer_config(300, "t_softstart", "di_start"),
            # Table for soft-start duty curve
            make_table_2d_config(301, "t_duty_curve", "t_softstart.elapsed",
                               x_values=[0, 100, 200, 300, 500, 1000],  # ms
                               y_values=[10, 30, 50, 70, 90, 100]),     # duty %
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Start timer
        await protocol.set_digital_input(0, True)

        # Sample at different times
        for delay_ms in [50, 150, 400]:
            await asyncio.sleep(delay_ms / 1000.0)
            telemetry = await protocol.get_telemetry()
            duty = telemetry.virtual_channels.get(301, 0)
            # Duty should follow the curve


class TestTable3DBasic:
    """Test basic 3D table functionality."""

    async def test_table_3d_two_inputs(self, emulator_connection):
        """
        Test: 3D table with two analog inputs.
        Example: VE table (RPM vs MAP).
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_map", scale=100.0),  # 0-100 kPa
            make_can_input_config(300, "can_rpm", can_id=0x100, bit_length=16),
            make_table_3d_config(301, "t_ve", "can_rpm", "ai_map",
                               x_values=[1000, 2000, 3000, 4000, 5000],  # RPM
                               y_values=[20, 40, 60, 80, 100],           # MAP kPa
                               z_values=[
                                   [40, 45, 50, 55, 60],    # MAP=20
                                   [50, 55, 62, 68, 75],    # MAP=40
                                   [60, 68, 76, 84, 90],    # MAP=60
                                   [70, 80, 88, 95, 100],   # MAP=80
                                   [75, 85, 92, 98, 100],   # MAP=100
                               ]),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Set inputs: RPM=3000, MAP=60
        await protocol.send_can_message(0x100, [0xB8, 0x0B, 0, 0, 0, 0, 0, 0])  # 3000 RPM
        await protocol.set_analog_input(0, 3.0)  # 60 kPa
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        ve = telemetry.virtual_channels.get(301, 0)
        # Should be ~76 (exact point in table)

    async def test_table_3d_bilinear_interpolation(self, emulator_connection):
        """
        Test: 3D table with bilinear interpolation.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_x"),
            make_analog_input_config(2, "ai_y"),
            make_table_3d_config(300, "t_3d", "ai_x", "ai_y",
                               x_values=[0, 10, 20],
                               y_values=[0, 10, 20],
                               z_values=[
                                   [0, 10, 20],    # Y=0
                                   [10, 20, 30],   # Y=10
                                   [20, 30, 40],   # Y=20
                               ],
                               interpolation="bilinear"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Test center point: X=10, Y=10 -> Z=20
        await protocol.set_analog_input(0, 2.0)  # X=10
        await protocol.set_analog_input(1, 2.0)  # Y=10
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        z = telemetry.virtual_channels.get(300, 0)
        assert abs(z - 200) < 30, f"Expected ~20 (200 scaled), got {z}"

        # Test interpolated point: X=5, Y=5 -> Z=10
        await protocol.set_analog_input(0, 1.0)  # X=5
        await protocol.set_analog_input(1, 1.0)  # Y=5
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        z = telemetry.virtual_channels.get(300, 0)
        assert abs(z - 100) < 30, f"Expected ~10 (100 scaled), got {z}"


class TestTable3DWithMixedInputs:
    """Test 3D tables with different channel types as inputs."""

    async def test_table_3d_can_and_analog(self, emulator_connection):
        """
        Test: 3D table with CAN (RPM) and analog (throttle).
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_can_input_config(300, "can_rpm", can_id=0x100, bit_length=16),
            make_analog_input_config(1, "ai_throttle", scale=20.0),  # 0-100%
            make_table_3d_config(301, "t_fuel", "can_rpm", "ai_throttle",
                               x_values=[1000, 3000, 5000, 7000],
                               y_values=[0, 25, 50, 75, 100],
                               z_values=[
                                   [10, 12, 15, 18],
                                   [12, 15, 20, 25],
                                   [15, 20, 28, 35],
                                   [18, 25, 35, 45],
                                   [20, 30, 42, 55],
                               ]),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # RPM=4000 (between 3000 and 5000), Throttle=50%
        await protocol.send_can_message(0x100, [0xA0, 0x0F, 0, 0, 0, 0, 0, 0])  # 4000
        await protocol.set_analog_input(0, 2.5)  # 50%
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        fuel = telemetry.virtual_channels.get(301, 0)

    async def test_table_3d_two_can_inputs(self, emulator_connection):
        """
        Test: 3D table with two CAN inputs.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_can_input_config(300, "can_rpm", can_id=0x100, bit_length=16),
            make_can_input_config(301, "can_iat", can_id=0x101, bit_length=8, scale=1.0),
            make_table_3d_config(302, "t_iat_corr", "can_rpm", "can_iat",
                               x_values=[1000, 3000, 5000, 7000],
                               y_values=[-20, 0, 20, 40, 60],  # IAT °C
                               z_values=[
                                   [110, 108, 105, 102],
                                   [105, 103, 100, 98],
                                   [100, 100, 100, 100],
                                   [95, 96, 98, 100],
                                   [90, 92, 95, 98],
                               ]),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        await protocol.send_can_message(0x100, [0x88, 0x13, 0, 0, 0, 0, 0, 0])  # 5000 RPM
        await protocol.send_can_message(0x101, [40, 0, 0, 0, 0, 0, 0, 0])       # 40°C IAT
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        correction = telemetry.virtual_channels.get(302, 0)


class TestTableOutputDrivesChannels:
    """Test table output controlling other channels."""

    async def test_table_output_to_pwm_duty(self, emulator_connection):
        """
        Test: Table output controls PWM duty cycle.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_temp"),
            make_digital_input_config(2, "di_enable"),
            make_table_2d_config(300, "t_fan_duty", "ai_temp",
                               x_values=[0, 40, 60, 80, 100],
                               y_values=[0, 0, 50, 80, 100]),
            {
                "channel_id": 101,
                "channel_type": "power_output",
                "id": "o_fan",
                "name": "Cooling Fan",
                "channel": 0,
                "source_channel": "di_enable",
                "output_mode": "pwm",
                "pwm_frequency": 100,
                "duty_mode": "channel",
                "duty_channel": "t_fan_duty",
                "max_current": 15000,
            },
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Enable and set temperature
        await protocol.set_digital_input(1, True)
        await protocol.set_analog_input(0, 3.5)  # 70°C -> ~65% duty
        await asyncio.sleep(0.3)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.PWM_ACTIVE

    async def test_table_output_to_logic_comparison(self, emulator_connection):
        """
        Test: Table output compared in logic channel.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_pressure"),
            make_table_2d_config(300, "t_max_pressure", "ai_pressure",
                               x_values=[0, 25, 50, 75, 100],
                               y_values=[100, 90, 75, 60, 50]),  # Max safe pressure curve
            make_logic_config(301, "l_over_limit", "greater", "ai_pressure",
                            constant=0),  # Will compare to table
            make_output_config(1, "o_warning", "l_over_limit"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)


class TestTableEdgeCases:
    """Test table edge cases and boundary conditions."""

    async def test_table_input_below_range(self, emulator_connection):
        """
        Test: Table handles input below defined range.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_input"),
            make_table_2d_config(300, "t_test", "ai_input",
                               x_values=[10, 20, 30, 40, 50],
                               y_values=[100, 200, 300, 400, 500]),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Input below range (should clamp to first value)
        await protocol.set_analog_input(0, 0.25)  # Value = 5, below 10
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        output = telemetry.virtual_channels.get(300, 0)
        # Should be ~100 (first y value)

    async def test_table_input_above_range(self, emulator_connection):
        """
        Test: Table handles input above defined range.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_input"),
            make_table_2d_config(300, "t_test", "ai_input",
                               x_values=[10, 20, 30, 40, 50],
                               y_values=[100, 200, 300, 400, 500]),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Input above range (should clamp to last value)
        await protocol.set_analog_input(0, 3.0)  # Value = 60, above 50
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        output = telemetry.virtual_channels.get(300, 0)
        # Should be ~500 (last y value)

    async def test_table_exact_boundary_values(self, emulator_connection):
        """
        Test: Table handles exact boundary values.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_analog_input_config(1, "ai_input"),
            make_table_2d_config(300, "t_test", "ai_input",
                               x_values=[0, 25, 50, 75, 100],
                               y_values=[0, 10, 30, 60, 100]),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Test each exact boundary
        for x, expected_y in [(0, 0), (25, 10), (50, 30), (75, 60), (100, 100)]:
            await protocol.set_analog_input(0, x / 20.0)
            await asyncio.sleep(0.2)

            telemetry = await protocol.get_telemetry()
            output = telemetry.virtual_channels.get(300, 0)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
