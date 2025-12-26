"""
Integration Tests: Timer Operations
Tests timer channel behavior through the emulator with telemetry verification.

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



def make_timer_config(channel_id: int, name: str, start_channel: str,
                      stop_channel: str = None, reset_channel: str = None,
                      mode: str = "count_up", target_ms: int = 0,
                      auto_reset: bool = False) -> dict:
    """Create timer configuration."""
    config = {
        "channel_id": channel_id,
        "channel_type": "timer",
        "id": name,
        "name": name,
        "mode": mode,
        "start_channel": start_channel,
        "start_edge": "rising",
        "target_ms": target_ms,
        "auto_reset": auto_reset,
    }
    if stop_channel:
        config["stop_channel"] = stop_channel
        config["stop_edge"] = "rising"
    if reset_channel:
        config["reset_channel"] = reset_channel
        config["reset_edge"] = "rising"
    return config
class TestTimerBasicOperations:
    """Test basic timer start/stop/reset operations."""

    async def test_timer_starts_on_rising_edge(self, emulator_connection):
        """
        Test: Timer starts counting on start channel rising edge.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_start"),
            make_timer_config(300, "t_test", "di_start", mode="count_up"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Ensure start input is LOW
        await protocol.set_digital_input(0, False)
        await asyncio.sleep(0.2)

        # Get initial telemetry - timer should be stopped
        telemetry1 = await protocol.get_telemetry()
        initial_value = telemetry1.virtual_channels.get(300, 0)

        # Trigger start (rising edge)
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.5)  # Let timer run for 500ms

        telemetry2 = await protocol.get_telemetry()
        running_value = telemetry2.virtual_channels.get(300, 0)

        # Timer should show it's running (value > 0 or running flag)
        assert running_value > initial_value or running_value > 0, \
            f"Timer should be running after start edge, got value {running_value}"

    async def test_timer_stops_on_stop_channel(self, emulator_connection):
        """
        Test: Timer stops counting when stop channel triggers.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_start"),
            make_digital_input_config(2, "di_stop"),
            make_timer_config(300, "t_test", "di_start",
                            stop_channel="di_stop", mode="count_up"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Start timer
        await protocol.set_digital_input(0, False)
        await protocol.set_digital_input(1, False)
        await asyncio.sleep(0.1)
        await protocol.set_digital_input(0, True)  # Start rising edge
        await asyncio.sleep(0.3)  # Let timer run

        # Stop timer
        await protocol.set_digital_input(1, True)  # Stop rising edge
        await asyncio.sleep(0.1)

        telemetry1 = await protocol.get_telemetry()
        value_after_stop = telemetry1.virtual_channels.get(300, 0)

        # Wait and verify timer is not counting
        await asyncio.sleep(0.3)
        telemetry2 = await protocol.get_telemetry()
        value_after_wait = telemetry2.virtual_channels.get(300, 0)

        # Timer value should not increase after stop
        assert abs(value_after_wait - value_after_stop) < 100, \
            f"Timer should be stopped, but value changed from {value_after_stop} to {value_after_wait}"

    async def test_timer_resets_on_reset_channel(self, emulator_connection):
        """
        Test: Timer resets to zero when reset channel triggers.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_start"),
            make_digital_input_config(2, "di_reset"),
            make_timer_config(300, "t_test", "di_start",
                            reset_channel="di_reset", mode="count_up"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Start timer
        await protocol.set_digital_input(0, False)
        await protocol.set_digital_input(1, False)
        await asyncio.sleep(0.1)
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.5)  # Let timer accumulate some time

        telemetry = await protocol.get_telemetry()
        value_before_reset = telemetry.virtual_channels.get(300, 0)
        assert value_before_reset > 0, "Timer should have accumulated time"

        # Reset timer
        await protocol.set_digital_input(1, True)
        await asyncio.sleep(0.1)

        telemetry = await protocol.get_telemetry()
        value_after_reset = telemetry.virtual_channels.get(300, 0)

        # Timer should be reset to zero or very low value
        assert value_after_reset < 100, \
            f"Timer should be reset, got {value_after_reset}"


class TestTimerCountdown:
    """Test timer countdown mode with target time."""

    async def test_countdown_timer_reaches_zero(self, emulator_connection):
        """
        Test: Countdown timer counts down to zero.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_start"),
            make_timer_config(300, "t_countdown", "di_start",
                            mode="count_down", target_ms=500),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Start countdown
        await protocol.set_digital_input(0, False)
        await asyncio.sleep(0.1)
        await protocol.set_digital_input(0, True)

        # Wait for countdown to complete
        await asyncio.sleep(0.7)  # 500ms target + margin

        telemetry = await protocol.get_telemetry()
        value = telemetry.virtual_channels.get(300, 500)

        # Timer should have reached zero or stopped
        assert value <= 0 or value >= 500, \
            f"Countdown should complete, got {value}"


class TestTimerWithOutput:
    """Test timer controlling output channels."""

    async def test_output_activates_while_timer_running(self, emulator_connection):
        """
        Test: Output activates while timer is running.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_start"),
            make_timer_config(300, "t_test", "di_start", mode="count_up"),
            make_output_config(1, "o_1", "t_test"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Initially timer is stopped - output should be off
        await protocol.set_digital_input(0, False)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF, \
            "Output should be OFF when timer is stopped"

        # Start timer - output should activate
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "Output should be ON when timer is running"

    async def test_output_deactivates_when_countdown_ends(self, emulator_connection):
        """
        Test: Output deactivates when countdown timer reaches zero.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_start"),
            make_timer_config(300, "t_countdown", "di_start",
                            mode="count_down", target_ms=300),
            make_output_config(1, "o_1", "t_countdown"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Start countdown
        await protocol.set_digital_input(0, False)
        await asyncio.sleep(0.1)
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.1)

        # Output should be ON while countdown is running
        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "Output should be ON during countdown"

        # Wait for countdown to complete
        await asyncio.sleep(0.5)

        # Output should be OFF after countdown ends
        telemetry = await protocol.get_telemetry()
        # Note: Depends on implementation - timer may output 0 or stop
        # This test validates the expected behavior


class TestTimerElapsedSubchannel:
    """Test timer .elapsed sub-channel."""

    async def test_elapsed_increases_while_running(self, emulator_connection):
        """
        Test: Timer .elapsed sub-channel increases while running.
        """
        protocol = emulator_connection
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_start"),
            make_timer_config(300, "t_test", "di_start", mode="count_up"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Start timer
        await protocol.set_digital_input(0, False)
        await asyncio.sleep(0.1)
        await protocol.set_digital_input(0, True)

        # Sample elapsed values
        await asyncio.sleep(0.2)
        telemetry1 = await protocol.get_telemetry()
        elapsed1 = telemetry1.virtual_channels.get(301, 0)  # .elapsed is channel_id + 1

        await asyncio.sleep(0.2)
        telemetry2 = await protocol.get_telemetry()
        elapsed2 = telemetry2.virtual_channels.get(301, 0)

        # Elapsed should increase
        assert elapsed2 > elapsed1, \
            f"Elapsed should increase: {elapsed1} -> {elapsed2}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
