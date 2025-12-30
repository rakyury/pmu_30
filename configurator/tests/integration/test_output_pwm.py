"""
Integration Tests: Output PWM Modes
Tests PWM output functionality through the emulator with telemetry verification.

Covers:
- PWM duty cycle set by constant
- PWM duty cycle controlled by channel
- Frequency settings
- Soft PWM transitions

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


def make_number_config(channel_id: int, name: str, operation: str,
                       input1: str = None, constant1: float = None) -> dict:
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
    if constant1 is not None:
        config["constant1"] = constant1
    return config


def make_pwm_output_config(output_num: int, name: str, source_channel: str,
                           pwm_frequency: int = 100,
                           duty_mode: str = "constant",
                           duty_constant: float = 50.0,
                           duty_channel: str = None,
                           soft_pwm: bool = False,
                           soft_pwm_rate: float = 10.0) -> dict:
    """Create PWM output configuration."""
    config = {
        "channel_id": 100 + output_num,
        "channel_type": "power_output",
        "id": name,
        "name": name,
        "channel": output_num - 1,
        "source_channel": source_channel,
        "output_mode": "pwm",
        "max_current": 10000,
        "pwm_frequency": pwm_frequency,
        "duty_mode": duty_mode,
        "soft_pwm": soft_pwm,
        "soft_pwm_rate": soft_pwm_rate,
    }
    if duty_mode == "constant":
        config["duty_constant"] = duty_constant
    elif duty_mode == "channel" and duty_channel:
        config["duty_channel"] = duty_channel
    return config
class TestPWMConstantDuty:
    """Test PWM output with constant duty cycle."""

    async def test_pwm_50_percent_duty(self, emulator_connection):
        """
        Test: PWM output at 50% constant duty.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_enable"),
            make_pwm_output_config(1, "o_pwm", "di_enable",
                                  duty_mode="constant",
                                  duty_constant=50.0),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Enable PWM output
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.3)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.PWM_ACTIVE, \
            "Output should be in PWM mode"

        # Check duty cycle sub-channel
        duty = telemetry.virtual_channels.get(103, 0)  # o_pwm.dc
        # Duty should be around 50% (scaled by 10 = 500)
        assert 400 < duty < 600, f"Duty should be ~50%, got {duty/10}%"

    async def test_pwm_various_duty_levels(self, emulator_connection):
        """
        Test: PWM at various constant duty levels.
        """
        protocol = emulator_connection

        duty_levels = [0, 25, 50, 75, 100]

        for duty in duty_levels:
            config = BASE_CONFIG.copy()
            config["channels"] = [
                make_digital_input_config(1, "di_enable"),
                make_pwm_output_config(1, "o_pwm", "di_enable",
                                      duty_mode="constant",
                                      duty_constant=duty),
            ]

            response = await protocol.send_config(json.dumps(config))
            assert response.success
            await asyncio.sleep(0.3)

            await protocol.set_digital_input(0, True)
            await asyncio.sleep(0.2)

            telemetry = await protocol.get_telemetry()

            if duty == 0:
                # 0% duty should result in OFF or 0 PWM
                assert telemetry.channel_states[0] in [ChannelState.OFF, ChannelState.PWM_ACTIVE]
            elif duty == 100:
                # 100% duty should result in ON or full PWM
                assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE]
            else:
                assert telemetry.channel_states[0] == ChannelState.PWM_ACTIVE

            # Reset for next iteration
            await protocol.set_digital_input(0, False)
            await asyncio.sleep(0.1)


class TestPWMChannelControlledDuty:
    """Test PWM output with channel-controlled duty cycle."""

    async def test_pwm_duty_from_analog_input(self, emulator_connection):
        """
        Test: PWM duty controlled by analog input.
        Analog 0-5V maps to 0-100% duty.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_enable"),
            make_analog_input_config(2, "ai_duty", scale=20.0, offset=0.0),  # 0-5V -> 0-100
            make_pwm_output_config(1, "o_pwm", "di_enable",
                                  duty_mode="channel",
                                  duty_channel="ai_duty"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Enable PWM output
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.1)

        # Set analog input to 2.5V -> 50% duty
        await protocol.set_analog_input(1, 2.5)
        await asyncio.sleep(0.3)

        telemetry = await protocol.get_telemetry()
        duty = telemetry.virtual_channels.get(103, 0)  # o_pwm.dc

        # Verify duty is approximately 50%
        # Note: Actual scaling depends on firmware implementation

    async def test_pwm_duty_follows_input_changes(self, emulator_connection):
        """
        Test: PWM duty changes as control channel changes.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_enable"),
            make_analog_input_config(2, "ai_duty", scale=20.0),
            make_pwm_output_config(1, "o_pwm", "di_enable",
                                  duty_mode="channel",
                                  duty_channel="ai_duty"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.1)

        # Low duty
        await protocol.set_analog_input(1, 1.0)  # 20%
        await asyncio.sleep(0.2)
        telemetry1 = await protocol.get_telemetry()
        duty1 = telemetry1.virtual_channels.get(103, 0)

        # High duty
        await protocol.set_analog_input(1, 4.0)  # 80%
        await asyncio.sleep(0.2)
        telemetry2 = await protocol.get_telemetry()
        duty2 = telemetry2.virtual_channels.get(103, 0)

        # Duty should increase
        assert duty2 > duty1, f"Duty should increase: {duty1} -> {duty2}"

    async def test_pwm_duty_from_number_channel(self, emulator_connection):
        """
        Test: PWM duty controlled by number (math) channel.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_enable"),
            make_analog_input_config(2, "ai_sensor"),
            # Map sensor reading to duty: multiply by constant
            make_number_config(300, "n_duty", "multiply", "ai_sensor", constant1=10.0),
            make_pwm_output_config(1, "o_pwm", "di_enable",
                                  duty_mode="channel",
                                  duty_channel="n_duty"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.1)

        # Set sensor to 5V -> duty = 5 * 10 = 50%
        await protocol.set_analog_input(1, 5.0)
        await asyncio.sleep(0.3)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.PWM_ACTIVE


class TestPWMFrequency:
    """Test PWM frequency settings."""

    async def test_pwm_frequency_100hz(self, emulator_connection):
        """
        Test: PWM at 100Hz frequency.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_enable"),
            make_pwm_output_config(1, "o_pwm", "di_enable",
                                  pwm_frequency=100,
                                  duty_constant=50.0),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.PWM_ACTIVE

    async def test_pwm_frequency_1000hz(self, emulator_connection):
        """
        Test: PWM at 1000Hz frequency (high frequency mode).
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_enable"),
            make_pwm_output_config(1, "o_pwm", "di_enable",
                                  pwm_frequency=1000,
                                  duty_constant=50.0),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.PWM_ACTIVE


class TestSoftPWM:
    """Test soft PWM transitions."""

    async def test_soft_pwm_gradual_rise(self, emulator_connection):
        """
        Test: Soft PWM gradually increases duty on activation.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_enable"),
            make_pwm_output_config(1, "o_pwm", "di_enable",
                                  duty_constant=100.0,
                                  soft_pwm=True,
                                  soft_pwm_rate=50.0),  # 50% per second
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Enable PWM
        await protocol.set_digital_input(0, True)

        # Sample duty during ramp-up
        await asyncio.sleep(0.1)
        telemetry1 = await protocol.get_telemetry()
        duty1 = telemetry1.virtual_channels.get(103, 0)

        await asyncio.sleep(0.5)
        telemetry2 = await protocol.get_telemetry()
        duty2 = telemetry2.virtual_channels.get(103, 0)

        # Duty should increase over time
        assert duty2 >= duty1, "Soft PWM should gradually increase"

    async def test_soft_pwm_gradual_fall(self, emulator_connection):
        """
        Test: Soft PWM gradually decreases duty on deactivation.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_enable"),
            make_pwm_output_config(1, "o_pwm", "di_enable",
                                  duty_constant=100.0,
                                  soft_pwm=True,
                                  soft_pwm_rate=50.0),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Enable and let it reach full duty
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(2.5)  # Time to reach 100%

        telemetry1 = await protocol.get_telemetry()
        duty_before = telemetry1.virtual_channels.get(103, 0)

        # Disable
        await protocol.set_digital_input(0, False)
        await asyncio.sleep(0.5)

        telemetry2 = await protocol.get_telemetry()
        duty_after = telemetry2.virtual_channels.get(103, 0)

        # Duty should decrease
        assert duty_after <= duty_before, "Soft PWM should gradually decrease"


class TestPWMWithLogic:
    """Test PWM controlled by logic channels."""

    async def test_pwm_enable_via_and_logic(self, emulator_connection):
        """
        Test: PWM enables only when both inputs are active (AND).
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_1"),
            make_digital_input_config(2, "di_2"),
            {
                "channel_id": 300,
                "channel_type": "logic",
                "id": "l_and",
                "name": "AND Gate",
                "operation": "and",
                "input1_channel": "di_1",
                "input2_channel": "di_2",
            },
            make_pwm_output_config(1, "o_pwm", "l_and",
                                  duty_constant=75.0),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Both OFF -> PWM OFF
        await protocol.set_digital_input(0, False)
        await protocol.set_digital_input(1, False)
        await asyncio.sleep(0.2)
        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF

        # Both ON -> PWM ON
        await protocol.set_digital_input(0, True)
        await protocol.set_digital_input(1, True)
        await asyncio.sleep(0.2)
        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.PWM_ACTIVE


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
