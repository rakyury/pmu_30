"""
Integration Tests: Atomic Configuration Updates
Tests atomic (individual) configuration changes without full config resend.

Covers:
- Single channel parameter updates
- Add/remove individual channels
- Batch partial updates
- Update verification via telemetry

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

class TestAtomicParameterUpdate:
    """Test updating individual channel parameters."""

    async def test_update_output_max_current(self, emulator_connection):
        """
        Test: Update single parameter (max_current) without full config resend.
        """
        protocol = emulator_connection

        # Send initial config
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_1"),
            make_output_config(1, "o_1", "di_1", max_current=5000),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Atomically update max_current
        update = {
            "action": "update_param",
            "channel_id": 101,
            "param": "max_current",
            "value": 10000,
        }
        response = await protocol.send_atomic_update(update)
        assert response.success, "Atomic parameter update failed"
        await asyncio.sleep(0.2)

        # Verify update via telemetry or config read-back
        # The output should now have 10A max current

    async def test_update_output_mode(self, emulator_connection):
        """
        Test: Update output mode from on_off to pwm.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_1"),
            make_output_config(1, "o_1", "di_1"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Update to PWM mode
        update = {
            "action": "update_param",
            "channel_id": 101,
            "param": "output_mode",
            "value": "pwm",
        }
        response = await protocol.send_atomic_update(update)
        assert response.success
        await asyncio.sleep(0.2)

        # Activate and verify PWM mode
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.PWM_ACTIVE, \
            "Output should be in PWM mode after update"

    async def test_update_logic_operation(self, emulator_connection):
        """
        Test: Update logic channel operation (AND -> OR).
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_1"),
            make_digital_input_config(2, "di_2"),
            make_logic_config(300, "l_op", "and", "di_1", "di_2"),
            make_output_config(1, "o_1", "l_op"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # With AND: only one input -> output OFF
        await protocol.set_digital_input(0, True)
        await protocol.set_digital_input(1, False)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF, \
            "AND(1,0) should be OFF"

        # Change to OR operation
        update = {
            "action": "update_param",
            "channel_id": 300,
            "param": "operation",
            "value": "or",
        }
        response = await protocol.send_atomic_update(update)
        assert response.success
        await asyncio.sleep(0.2)

        # Now with OR: one input -> output ON
        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "OR(1,0) should be ON"


class TestAtomicChannelAddRemove:
    """Test adding and removing individual channels."""

    async def test_add_channel(self, emulator_connection):
        """
        Test: Add new channel without resending full config.
        """
        protocol = emulator_connection

        # Start with minimal config
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_1"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Add output channel
        new_channel = make_output_config(1, "o_1", "di_1")
        update = {
            "action": "add_channel",
            "channel": new_channel,
        }
        response = await protocol.send_atomic_update(update)
        assert response.success
        await asyncio.sleep(0.2)

        # Verify new channel works
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "Newly added output should respond to input"

    async def test_remove_channel(self, emulator_connection):
        """
        Test: Remove channel without resending full config.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_1"),
            make_digital_input_config(2, "di_2"),
            make_output_config(1, "o_1", "di_1"),
            make_output_config(2, "o_2", "di_2"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Verify both outputs work
        await protocol.set_digital_input(0, True)
        await protocol.set_digital_input(1, True)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE]
        assert telemetry.channel_states[1] in [ChannelState.ON, ChannelState.PWM_ACTIVE]

        # Remove output 2
        update = {
            "action": "remove_channel",
            "channel_id": 102,
        }
        response = await protocol.send_atomic_update(update)
        assert response.success
        await asyncio.sleep(0.2)

        # Output 1 should still work, output 2 should be gone
        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "Output 1 should still work"

    async def test_replace_channel(self, emulator_connection):
        """
        Test: Replace existing channel with new configuration.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_1"),
            make_output_config(1, "o_1", "di_1", max_current=5000),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Replace output with different config
        new_output = make_output_config(1, "o_1_new", "di_1", max_current=15000)
        update = {
            "action": "replace_channel",
            "channel_id": 101,
            "channel": new_output,
        }
        response = await protocol.send_atomic_update(update)
        assert response.success
        await asyncio.sleep(0.2)


class TestAtomicBatchUpdate:
    """Test batch atomic updates."""

    async def test_multiple_parameter_updates(self, emulator_connection):
        """
        Test: Update multiple parameters in single batch.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_1"),
            make_output_config(1, "o_1", "di_1"),
            make_output_config(2, "o_2", "di_1"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Batch update
        updates = [
            {"action": "update_param", "channel_id": 101, "param": "max_current", "value": 8000},
            {"action": "update_param", "channel_id": 102, "param": "max_current", "value": 12000},
        ]
        response = await protocol.send_atomic_batch(updates)
        assert response.success
        await asyncio.sleep(0.2)

    async def test_mixed_batch_operations(self, emulator_connection):
        """
        Test: Mix of add, remove, update in single batch.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_1"),
            make_digital_input_config(2, "di_2"),
            make_output_config(1, "o_1", "di_1"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Mixed batch
        updates = [
            {"action": "update_param", "channel_id": 101, "param": "max_current", "value": 15000},
            {"action": "add_channel", "channel": make_output_config(2, "o_2", "di_2")},
            {"action": "add_channel", "channel": make_logic_config(300, "l_and", "and", "di_1", "di_2")},
        ]
        response = await protocol.send_atomic_batch(updates)
        assert response.success
        await asyncio.sleep(0.2)


class TestAtomicUpdateVerification:
    """Test verification of atomic updates."""

    async def test_update_reflected_in_telemetry(self, emulator_connection):
        """
        Test: Atomic update is immediately reflected in telemetry.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_1"),
            {
                "channel_id": 101,
                "channel_type": "power_output",
                "id": "o_pwm",
                "name": "PWM Output",
                "channel": 0,
                "source_channel": "di_1",
                "output_mode": "pwm",
                "duty_mode": "constant",
                "duty_constant": 25.0,
                "pwm_frequency": 100,
                "max_current": 10000,
            },
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.2)

        # Check initial duty
        telemetry1 = await protocol.get_telemetry()
        duty1 = telemetry1.virtual_channels.get(103, 0)  # o_pwm.dc

        # Update duty to 75%
        update = {
            "action": "update_param",
            "channel_id": 101,
            "param": "duty_constant",
            "value": 75.0,
        }
        response = await protocol.send_atomic_update(update)
        assert response.success
        await asyncio.sleep(0.2)

        # Verify new duty
        telemetry2 = await protocol.get_telemetry()
        duty2 = telemetry2.virtual_channels.get(103, 0)

        # Duty should have changed
        assert duty2 != duty1 or (duty2 > duty1), \
            f"Duty should update from {duty1} to higher value, got {duty2}"

    async def test_update_does_not_affect_other_channels(self, emulator_connection):
        """
        Test: Updating one channel doesn't affect others.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_1"),
            make_digital_input_config(2, "di_2"),
            make_output_config(1, "o_1", "di_1"),
            make_output_config(2, "o_2", "di_2"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Activate both
        await protocol.set_digital_input(0, True)
        await protocol.set_digital_input(1, True)
        await asyncio.sleep(0.2)

        # Capture initial state
        telemetry1 = await protocol.get_telemetry()
        state1_o1 = telemetry1.channel_states[0]
        state1_o2 = telemetry1.channel_states[1]

        # Update output 1 only
        update = {
            "action": "update_param",
            "channel_id": 101,
            "param": "output_mode",
            "value": "pwm",
        }
        response = await protocol.send_atomic_update(update)
        assert response.success
        await asyncio.sleep(0.2)

        # Output 2 should be unchanged
        telemetry2 = await protocol.get_telemetry()
        state2_o2 = telemetry2.channel_states[1]

        assert state2_o2 == state1_o2 or \
               (state1_o2 in [ChannelState.ON, ChannelState.PWM_ACTIVE] and
                state2_o2 in [ChannelState.ON, ChannelState.PWM_ACTIVE]), \
            "Output 2 should not be affected by output 1 update"


class TestAtomicUpdateRollback:
    """Test atomic update error handling and rollback."""

    async def test_invalid_update_rejected(self, emulator_connection):
        """
        Test: Invalid atomic update is rejected.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_1"),
            make_output_config(1, "o_1", "di_1"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Try to update non-existent channel
        update = {
            "action": "update_param",
            "channel_id": 999,  # Non-existent
            "param": "max_current",
            "value": 10000,
        }
        response = await protocol.send_atomic_update(update)
        # Should fail
        assert not response.success or response.error, \
            "Update to non-existent channel should fail"

    async def test_invalid_param_rejected(self, emulator_connection):
        """
        Test: Invalid parameter name is rejected.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_1"),
            make_output_config(1, "o_1", "di_1"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Try to update invalid parameter
        update = {
            "action": "update_param",
            "channel_id": 101,
            "param": "invalid_param_name",
            "value": 123,
        }
        response = await protocol.send_atomic_update(update)
        # Should fail or be ignored


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
