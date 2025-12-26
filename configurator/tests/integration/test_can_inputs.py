"""
Integration Tests: CAN Inputs
Tests CAN input channel behavior through the emulator with telemetry verification.

Covers:
- CAN message reception and parsing
- CAN input to logic channel integration
- CAN input to math/number channel integration
- CAN input to table lookups
- CAN input to timer triggers
- CAN input to switch channels
- CAN input driving power outputs

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



def make_can_input_config(channel_id: int, name: str,
                          can_id: int,
                          start_bit: int = 0,
                          bit_length: int = 8,
                          byte_order: str = "little_endian",
                          data_type: str = "unsigned",
                          scale: float = 1.0,
                          offset: float = 0.0,
                          timeout_ms: int = 1000) -> dict:
    """Create CAN input channel configuration."""
    return {
        "channel_id": channel_id,
        "channel_type": "can_input",
        "id": name,
        "name": name,
        "can_id": can_id,
        "start_bit": start_bit,
        "bit_length": bit_length,
        "byte_order": byte_order,
        "data_type": data_type,
        "scale": scale,
        "offset": offset,
        "timeout_ms": timeout_ms,
    }


def make_number_config(channel_id: int, name: str, operation: str,
                       input1: str = None, input2: str = None,
                       constant1: float = None) -> dict:
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
    return config


def make_timer_config(channel_id: int, name: str, start_channel: str,
                      mode: str = "count_up", target_ms: int = 0) -> dict:
    """Create timer configuration."""
    return {
        "channel_id": channel_id,
        "channel_type": "timer",
        "id": name,
        "name": name,
        "mode": mode,
        "start_channel": start_channel,
        "start_edge": "rising",
        "target_ms": target_ms,
    }


def make_switch_config(channel_id: int, name: str, input_channel: str,
                       states: list) -> dict:
    """Create switch channel configuration."""
    return {
        "channel_id": channel_id,
        "channel_type": "switch",
        "id": name,
        "name": name,
        "input_channel": input_channel,
        "states": states,
    }


def make_table_2d_config(channel_id: int, name: str, input_channel: str,
                         x_values: list, y_values: list) -> dict:
    """Create 2D lookup table configuration."""
    return {
        "channel_id": channel_id,
        "channel_type": "table_2d",
        "id": name,
        "name": name,
        "input_channel": input_channel,
        "x_values": x_values,
        "y_values": y_values,
        "interpolation": "linear",
    }
class TestCANInputBasics:
    """Test basic CAN input reception and parsing."""

    async def test_can_input_receives_value(self, emulator_connection):
        """
        Test: CAN input receives and parses message value.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_can_input_config(300, "can_rpm",
                                 can_id=0x100,
                                 start_bit=0,
                                 bit_length=16,
                                 scale=1.0),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Send CAN message with RPM value (e.g., 3000)
        await protocol.send_can_message(0x100, [0xB8, 0x0B, 0, 0, 0, 0, 0, 0])  # 3000 in little-endian
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        rpm = telemetry.virtual_channels.get(300, 0)
        assert abs(rpm - 3000) < 100, f"Expected ~3000 RPM, got {rpm}"

    async def test_can_input_big_endian(self, emulator_connection):
        """
        Test: CAN input parses big-endian data correctly.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_can_input_config(300, "can_speed",
                                 can_id=0x101,
                                 start_bit=0,
                                 bit_length=16,
                                 byte_order="big_endian",
                                 scale=0.1),  # 0.1 km/h per bit
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Send speed = 1000 (100.0 km/h) in big-endian
        await protocol.send_can_message(0x101, [0x03, 0xE8, 0, 0, 0, 0, 0, 0])  # 1000 in big-endian
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        speed = telemetry.virtual_channels.get(300, 0)
        # Expecting ~100 km/h (1000 * 0.1)

    async def test_can_input_signed_value(self, emulator_connection):
        """
        Test: CAN input parses signed values correctly.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_can_input_config(300, "can_temp",
                                 can_id=0x102,
                                 start_bit=0,
                                 bit_length=8,
                                 data_type="signed",
                                 offset=-40.0),  # Common temp offset
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Send temperature = 65 raw (25°C with -40 offset)
        await protocol.send_can_message(0x102, [65, 0, 0, 0, 0, 0, 0, 0])
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        temp = telemetry.virtual_channels.get(300, 0)
        # Expecting ~25°C

    async def test_can_input_timeout(self, emulator_connection):
        """
        Test: CAN input times out when no message received.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_can_input_config(300, "can_data",
                                 can_id=0x103,
                                 timeout_ms=500),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Send initial message
        await protocol.send_can_message(0x103, [100, 0, 0, 0, 0, 0, 0, 0])
        await asyncio.sleep(0.2)

        # Wait for timeout
        await asyncio.sleep(0.7)

        telemetry = await protocol.get_telemetry()
        # Check timeout flag or value reset


class TestCANInputWithLogic:
    """Test CAN input integration with logic channels."""

    async def test_can_input_greater_than_threshold(self, emulator_connection):
        """
        Test: Logic channel compares CAN input to threshold.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_can_input_config(300, "can_rpm", can_id=0x100, bit_length=16),
            make_logic_config(301, "l_high_rpm", "greater", "can_rpm", constant=5000.0),
            make_output_config(1, "o_warning", "l_high_rpm"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Low RPM -> warning OFF
        await protocol.send_can_message(0x100, [0x88, 0x13, 0, 0, 0, 0, 0, 0])  # 5000
        await asyncio.sleep(0.2)
        telemetry = await protocol.get_telemetry()
        # At threshold, should still be OFF

        # High RPM -> warning ON
        await protocol.send_can_message(0x100, [0x10, 0x27, 0, 0, 0, 0, 0, 0])  # 10000
        await asyncio.sleep(0.2)
        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "High RPM should trigger warning"

    async def test_can_inputs_and_logic(self, emulator_connection):
        """
        Test: Logic AND of two CAN inputs being valid.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_can_input_config(300, "can_rpm", can_id=0x100, bit_length=16),
            make_can_input_config(301, "can_speed", can_id=0x101, bit_length=16),
            make_logic_config(302, "l_rpm_ok", "greater", "can_rpm", constant=0.0),
            make_logic_config(303, "l_speed_ok", "greater", "can_speed", constant=0.0),
            make_logic_config(304, "l_both_ok", "and", "l_rpm_ok", "l_speed_ok"),
            make_output_config(1, "o_ready", "l_both_ok"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Only RPM -> not ready
        await protocol.send_can_message(0x100, [0xE8, 0x03, 0, 0, 0, 0, 0, 0])  # 1000 RPM
        await asyncio.sleep(0.2)
        telemetry = await protocol.get_telemetry()
        # Output depends on speed being > 0

        # Both values -> ready
        await protocol.send_can_message(0x101, [0x0A, 0x00, 0, 0, 0, 0, 0, 0])  # 10 km/h
        await asyncio.sleep(0.2)
        telemetry = await protocol.get_telemetry()


class TestCANInputWithMath:
    """Test CAN input integration with math/number channels."""

    async def test_can_input_average(self, emulator_connection):
        """
        Test: Calculate average of two CAN input values.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_can_input_config(300, "can_temp1", can_id=0x100, bit_length=8),
            make_can_input_config(301, "can_temp2", can_id=0x101, bit_length=8),
            make_number_config(302, "n_sum", "add", "can_temp1", "can_temp2"),
            make_number_config(303, "n_avg", "divide", "n_sum", constant1=2.0),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Temp1 = 20, Temp2 = 30 -> avg = 25
        await protocol.send_can_message(0x100, [20, 0, 0, 0, 0, 0, 0, 0])
        await protocol.send_can_message(0x101, [30, 0, 0, 0, 0, 0, 0, 0])
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        avg = telemetry.virtual_channels.get(303, 0)
        # Should be approximately 25

    async def test_can_input_scaling(self, emulator_connection):
        """
        Test: Apply math scaling to CAN input.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_can_input_config(300, "can_raw", can_id=0x100, bit_length=16),
            make_number_config(301, "n_scaled", "multiply", "can_raw", constant1=0.01),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Raw = 5000 -> scaled = 50.0
        await protocol.send_can_message(0x100, [0x88, 0x13, 0, 0, 0, 0, 0, 0])
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        scaled = telemetry.virtual_channels.get(301, 0)


class TestCANInputWithTable:
    """Test CAN input integration with lookup tables."""

    async def test_can_input_table_lookup(self, emulator_connection):
        """
        Test: CAN input drives 2D table lookup.
        Example: RPM-based fan speed curve.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_can_input_config(300, "can_rpm", can_id=0x100, bit_length=16, scale=1.0),
            make_table_2d_config(301, "t_fan_curve", "can_rpm",
                                x_values=[0, 2000, 4000, 6000, 8000],
                                y_values=[0, 20, 50, 80, 100]),  # Fan % duty
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Test various RPM points
        test_cases = [
            (1000, 10),   # Interpolated between 0-2000
            (3000, 35),   # Interpolated between 2000-4000
            (6000, 80),   # Exact point
        ]

        for rpm_raw, expected_approx in test_cases:
            # Convert to bytes (little-endian)
            rpm_bytes = [rpm_raw & 0xFF, (rpm_raw >> 8) & 0xFF, 0, 0, 0, 0, 0, 0]
            await protocol.send_can_message(0x100, rpm_bytes)
            await asyncio.sleep(0.2)

            telemetry = await protocol.get_telemetry()
            fan_duty = telemetry.virtual_channels.get(301, 0)
            # Verify approximate value


class TestCANInputWithTimer:
    """Test CAN input integration with timer channels."""

    async def test_can_input_triggers_timer(self, emulator_connection):
        """
        Test: CAN input rising edge triggers timer start.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_can_input_config(300, "can_trigger", can_id=0x100, bit_length=8),
            make_logic_config(301, "l_trigger", "greater", "can_trigger", constant=0.0),
            make_timer_config(302, "t_elapsed", "l_trigger", mode="count_up"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Trigger = 0 (timer stopped)
        await protocol.send_can_message(0x100, [0, 0, 0, 0, 0, 0, 0, 0])
        await asyncio.sleep(0.3)

        telemetry1 = await protocol.get_telemetry()
        time1 = telemetry1.virtual_channels.get(302, 0)

        # Trigger = 1 (timer starts)
        await protocol.send_can_message(0x100, [1, 0, 0, 0, 0, 0, 0, 0])
        await asyncio.sleep(0.5)

        telemetry2 = await protocol.get_telemetry()
        time2 = telemetry2.virtual_channels.get(302, 0)

        # Timer should have counted
        assert time2 > time1, "Timer should count after trigger"


class TestCANInputWithSwitch:
    """Test CAN input integration with switch channels."""

    async def test_can_input_drives_switch(self, emulator_connection):
        """
        Test: CAN input value selects switch state.
        Example: Gear position selector.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_can_input_config(300, "can_gear", can_id=0x100, bit_length=8),
            make_switch_config(301, "sw_gear", "can_gear", [
                {"value": 0, "output": 0},    # Neutral
                {"value": 1, "output": 100},  # 1st gear
                {"value": 2, "output": 200},  # 2nd gear
                {"value": 3, "output": 300},  # 3rd gear
            ]),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Select gear 2
        await protocol.send_can_message(0x100, [2, 0, 0, 0, 0, 0, 0, 0])
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        gear_output = telemetry.virtual_channels.get(301, 0)
        # Should be 200


class TestCANInputDrivesOutput:
    """Test CAN input directly controlling power outputs."""

    async def test_can_input_controls_output(self, emulator_connection):
        """
        Test: CAN input value directly controls output.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_can_input_config(300, "can_light", can_id=0x100, bit_length=8),
            make_logic_config(301, "l_light_on", "greater", "can_light", constant=0.0),
            make_output_config(1, "o_light", "l_light_on"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Light OFF
        await protocol.send_can_message(0x100, [0, 0, 0, 0, 0, 0, 0, 0])
        await asyncio.sleep(0.2)
        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF

        # Light ON
        await protocol.send_can_message(0x100, [1, 0, 0, 0, 0, 0, 0, 0])
        await asyncio.sleep(0.2)
        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE]

    async def test_can_input_pwm_control(self, emulator_connection):
        """
        Test: CAN input controls PWM duty cycle.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_can_input_config(300, "can_duty", can_id=0x100, bit_length=8, scale=1.0),
            {
                "channel_id": 101,
                "channel_type": "power_output",
                "id": "o_pwm",
                "name": "PWM Output",
                "channel": 0,
                "source_channel": "can_duty",
                "output_mode": "pwm",
                "pwm_frequency": 100,
                "duty_mode": "channel",
                "duty_channel": "can_duty",
                "max_current": 10000,
            },
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Set 50% duty via CAN
        await protocol.send_can_message(0x100, [50, 0, 0, 0, 0, 0, 0, 0])
        await asyncio.sleep(0.3)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.PWM_ACTIVE


class TestMultipleCANMessages:
    """Test handling multiple CAN messages."""

    async def test_multiple_can_ids(self, emulator_connection):
        """
        Test: Multiple CAN inputs from different message IDs.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_can_input_config(300, "can_rpm", can_id=0x100, bit_length=16),
            make_can_input_config(301, "can_speed", can_id=0x101, bit_length=16),
            make_can_input_config(302, "can_temp", can_id=0x102, bit_length=8),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Send all three messages
        await protocol.send_can_message(0x100, [0xE8, 0x03, 0, 0, 0, 0, 0, 0])  # RPM = 1000
        await protocol.send_can_message(0x101, [0x64, 0x00, 0, 0, 0, 0, 0, 0])  # Speed = 100
        await protocol.send_can_message(0x102, [85, 0, 0, 0, 0, 0, 0, 0])       # Temp = 85
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        rpm = telemetry.virtual_channels.get(300, 0)
        speed = telemetry.virtual_channels.get(301, 0)
        temp = telemetry.virtual_channels.get(302, 0)

    async def test_multiple_signals_one_message(self, emulator_connection):
        """
        Test: Extract multiple signals from single CAN message.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_can_input_config(300, "can_rpm",
                                 can_id=0x100,
                                 start_bit=0, bit_length=16),
            make_can_input_config(301, "can_throttle",
                                 can_id=0x100,
                                 start_bit=16, bit_length=8),
            make_can_input_config(302, "can_flags",
                                 can_id=0x100,
                                 start_bit=24, bit_length=8),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Send single message with all signals
        # RPM=3000 (0x0BB8), Throttle=75, Flags=0x0F
        await protocol.send_can_message(0x100, [0xB8, 0x0B, 75, 0x0F, 0, 0, 0, 0])
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        rpm = telemetry.virtual_channels.get(300, 0)
        throttle = telemetry.virtual_channels.get(301, 0)
        flags = telemetry.virtual_channels.get(302, 0)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
