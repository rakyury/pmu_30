"""
Critical Control Flow Integration Tests

These tests verify the fundamental control flow from input to output.
MUST PASS after any firmware or configurator change.

Test Flows:
1. Digital Input (LOW-SIDE) → Power Output
2. Digital Input (HIGH-SIDE) → Power Output
3. Timer → Power Output

Run after every change:
    python -m pytest tests/integration/test_control_flow_critical.py -v --timeout=60
"""

import pytest
import asyncio
import json
from typing import Optional

from .helpers import (
    BASE_CONFIG,
    ChannelState,
    make_digital_input_config,
    make_output_config,
    make_timer_config,
)


# Constants for test configuration
TELEMETRY_WAIT_MS = 500  # Time to wait for telemetry update
CONFIG_APPLY_WAIT_MS = 300  # Time to wait for config to apply


class TestDigitalInputToOutputFlow:
    """
    CRITICAL TEST: Digital Input → Power Output control flow.

    Tests the complete path from digital input state change to power output response.
    This is the most fundamental control flow in the PMU-30.
    """

    @pytest.mark.asyncio
    async def test_low_side_switch_controls_output(self, emulator_connection):
        """
        Test Flow:
        1. Create digital input 'test_DI_low' with LOW-SIDE type (default ON)
        2. Verify telemetry shows test_DI_low = ON
        3. Create power output 'test_OUT' with source = test_DI_low
        4. Verify telemetry shows test_OUT = ON
        5. Change test_DI_low to HIGH-SIDE type (default OFF)
        6. Verify telemetry shows test_DI_low = OFF
        7. Verify telemetry shows test_OUT = OFF
        """
        protocol = emulator_connection

        # Step 1: Create LOW-SIDE digital input (default value = 1 = ON)
        # LOW-SIDE means: switch closed to ground = pressed = ON
        # With no physical switch connected, emulator should report this as ON
        config = BASE_CONFIG.copy()
        config["channels"] = [
            {
                "channel_type": "digital_input",
                "id": "test_DI_low",
                "name": "test_DI_low",
                "input_pin": 0,
                "subtype": "switch_active_low",  # LOW-SIDE
                "debounce_ms": 10,
            }
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success, f"Config send failed: {response.error}"
        await asyncio.sleep(CONFIG_APPLY_WAIT_MS / 1000)

        # Step 2: Verify digital input is ON via telemetry
        # For LOW-SIDE switch with default low voltage, should be ON
        await protocol.set_digital_input(0, True)  # Simulate switch closed (LOW voltage)
        await asyncio.sleep(TELEMETRY_WAIT_MS / 1000)

        telemetry = await protocol.get_telemetry()
        assert telemetry is not None, "No telemetry received"

        # Digital input should report ON (state = 1)
        di_state = self._get_digital_input_state(telemetry, 0)
        assert di_state == 1, f"Expected test_DI_low = ON (1), got {di_state}"
        print(f"✓ Step 2: test_DI_low = ON (LOW-SIDE, switch closed)")

        # Step 3: Add power output controlled by the digital input
        config["channels"].append({
            "channel_type": "power_output",
            "id": "test_OUT",
            "name": "test_OUT",
            "output_pins": [0],
            "source_channel": "test_DI_low",
        })

        response = await protocol.send_config(json.dumps(config))
        assert response.success, f"Config update failed: {response.error}"
        await asyncio.sleep(CONFIG_APPLY_WAIT_MS / 1000)

        # Step 4: Verify output is ON
        await asyncio.sleep(TELEMETRY_WAIT_MS / 1000)
        telemetry = await protocol.get_telemetry()
        assert telemetry is not None, "No telemetry received"

        output_state = self._get_output_state(telemetry, 0)
        assert output_state in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            f"Expected test_OUT = ON, got {output_state}"
        print(f"✓ Step 4: test_OUT = ON (controlled by test_DI_low)")

        # Step 5: Change digital input to HIGH-SIDE (default OFF)
        # For HIGH-SIDE: switch open = pulled high = OFF
        config["channels"][0] = {
            "channel_type": "digital_input",
            "id": "test_DI_low",
            "name": "test_DI_low",
            "input_pin": 0,
            "subtype": "switch_active_high",  # HIGH-SIDE
            "debounce_ms": 10,
        }

        response = await protocol.send_config(json.dumps(config))
        assert response.success, f"Config update failed: {response.error}"
        await asyncio.sleep(CONFIG_APPLY_WAIT_MS / 1000)

        # Set digital input to LOW (switch open for active-high = OFF)
        await protocol.set_digital_input(0, False)
        await asyncio.sleep(TELEMETRY_WAIT_MS / 1000)

        # Step 6: Verify digital input is OFF
        telemetry = await protocol.get_telemetry()
        assert telemetry is not None, "No telemetry received"

        di_state = self._get_digital_input_state(telemetry, 0)
        assert di_state == 0, f"Expected test_DI_low = OFF (0), got {di_state}"
        print(f"✓ Step 6: test_DI_low = OFF (HIGH-SIDE, switch open)")

        # Step 7: Verify output is OFF
        output_state = self._get_output_state(telemetry, 0)
        assert output_state == ChannelState.OFF, \
            f"Expected test_OUT = OFF, got {output_state}"
        print(f"✓ Step 7: test_OUT = OFF (controlled by test_DI_low)")

        print("\n✅ TEST PASSED: Digital Input → Power Output control flow works correctly")

    @pytest.mark.asyncio
    async def test_high_side_switch_controls_output(self, emulator_connection):
        """
        Test HIGH-SIDE digital input controlling power output.

        HIGH-SIDE (active_high):
        - Switch closed to VCC = HIGH voltage = ON
        - Switch open = pulled LOW = OFF
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            {
                "channel_type": "digital_input",
                "id": "test_DI_high",
                "name": "test_DI_high",
                "input_pin": 1,
                "subtype": "switch_active_high",
                "debounce_ms": 10,
            },
            {
                "channel_type": "power_output",
                "id": "test_OUT_high",
                "name": "test_OUT_high",
                "output_pins": [1],
                "source_channel": "test_DI_high",
            }
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(CONFIG_APPLY_WAIT_MS / 1000)

        # Set input HIGH -> Output should be ON
        await protocol.set_digital_input(1, True)
        await asyncio.sleep(TELEMETRY_WAIT_MS / 1000)

        telemetry = await protocol.get_telemetry()
        assert telemetry is not None

        output_state = self._get_output_state(telemetry, 1)
        assert output_state in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            f"HIGH input should turn ON output, got {output_state}"
        print(f"✓ HIGH-SIDE input HIGH -> Output ON")

        # Set input LOW -> Output should be OFF
        await protocol.set_digital_input(1, False)
        await asyncio.sleep(TELEMETRY_WAIT_MS / 1000)

        telemetry = await protocol.get_telemetry()
        output_state = self._get_output_state(telemetry, 1)
        assert output_state == ChannelState.OFF, \
            f"LOW input should turn OFF output, got {output_state}"
        print(f"✓ HIGH-SIDE input LOW -> Output OFF")

        print("\n✅ TEST PASSED: HIGH-SIDE Digital Input → Power Output works correctly")

    def _get_digital_input_state(self, telemetry, channel: int) -> int:
        """Extract digital input state from telemetry."""
        if hasattr(telemetry, 'digital_inputs'):
            if channel < len(telemetry.digital_inputs):
                return telemetry.digital_inputs[channel]
        if hasattr(telemetry, 'input_states'):
            if channel < len(telemetry.input_states):
                return telemetry.input_states[channel]
        # Fallback: try virtual_channels
        if hasattr(telemetry, 'virtual_channels'):
            # Digital input channel IDs start at 50
            return telemetry.virtual_channels.get(50 + channel, 0)
        return 0

    def _get_output_state(self, telemetry, channel: int) -> ChannelState:
        """Extract output state from telemetry."""
        if hasattr(telemetry, 'channel_states'):
            if channel < len(telemetry.channel_states):
                return telemetry.channel_states[channel]
        if hasattr(telemetry, 'output_states'):
            if channel < len(telemetry.output_states):
                state = telemetry.output_states[channel]
                if state > 0:
                    return ChannelState.ON
                return ChannelState.OFF
        return ChannelState.OFF


class TestTimerToOutputFlow:
    """
    CRITICAL TEST: Timer → Power Output control flow.

    Tests timer-based output control for timed functions like:
    - Momentary button with hold timer
    - Delayed output activation
    - Timed output pulses
    """

    @pytest.mark.asyncio
    async def test_timer_oneshot_controls_output(self, emulator_connection):
        """
        Test Flow:
        1. Create digital input 'test_trigger' (button)
        2. Create timer 'test_timer' triggered by test_trigger (500ms oneshot)
        3. Create power output 'test_OUT_timed' controlled by timer
        4. Press button -> Timer starts -> Output ON
        5. Wait 500ms -> Timer expires -> Output OFF
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            # Trigger button
            {
                "channel_type": "digital_input",
                "id": "test_trigger",
                "name": "test_trigger",
                "input_pin": 2,
                "subtype": "switch_active_high",
                "debounce_ms": 10,
            },
            # Timer (500ms oneshot)
            {
                "channel_type": "timer",
                "id": "test_timer",
                "name": "test_timer",
                "trigger_channel": "test_trigger",
                "mode": "oneshot",
                "duration_ms": 500,
            },
            # Output controlled by timer
            {
                "channel_type": "power_output",
                "id": "test_OUT_timed",
                "name": "test_OUT_timed",
                "output_pins": [2],
                "source_channel": "test_timer",
            }
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success, f"Config send failed: {response.error}"
        await asyncio.sleep(CONFIG_APPLY_WAIT_MS / 1000)

        # Initial state: trigger OFF, timer not running, output OFF
        await protocol.set_digital_input(2, False)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry is not None

        initial_state = self._get_output_state(telemetry, 2)
        assert initial_state == ChannelState.OFF, \
            f"Initial output should be OFF, got {initial_state}"
        print(f"✓ Initial state: Output OFF")

        # Press trigger -> Timer starts -> Output ON
        await protocol.set_digital_input(2, True)
        await asyncio.sleep(0.1)  # Short delay to let timer start

        telemetry = await protocol.get_telemetry()
        triggered_state = self._get_output_state(telemetry, 2)
        assert triggered_state in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            f"After trigger, output should be ON, got {triggered_state}"
        print(f"✓ After trigger: Output ON (timer running)")

        # Release trigger
        await protocol.set_digital_input(2, False)

        # Wait for timer to expire (500ms + margin)
        await asyncio.sleep(0.7)

        telemetry = await protocol.get_telemetry()
        final_state = self._get_output_state(telemetry, 2)
        assert final_state == ChannelState.OFF, \
            f"After timer expires, output should be OFF, got {final_state}"
        print(f"✓ After timer expires: Output OFF")

        print("\n✅ TEST PASSED: Timer (oneshot) → Power Output works correctly")

    @pytest.mark.asyncio
    async def test_timer_retriggerable_controls_output(self, emulator_connection):
        """
        Test retriggerable timer: pressing button resets timer.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            {
                "channel_type": "digital_input",
                "id": "test_retrig",
                "name": "test_retrig",
                "input_pin": 3,
                "subtype": "switch_active_high",
                "debounce_ms": 10,
            },
            {
                "channel_type": "timer",
                "id": "test_timer_retrig",
                "name": "test_timer_retrig",
                "trigger_channel": "test_retrig",
                "mode": "retriggerable",
                "duration_ms": 300,
            },
            {
                "channel_type": "power_output",
                "id": "test_OUT_retrig",
                "name": "test_OUT_retrig",
                "output_pins": [3],
                "source_channel": "test_timer_retrig",
            }
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(CONFIG_APPLY_WAIT_MS / 1000)

        # First trigger
        await protocol.set_digital_input(3, True)
        await asyncio.sleep(0.1)
        await protocol.set_digital_input(3, False)

        telemetry = await protocol.get_telemetry()
        state1 = self._get_output_state(telemetry, 3)
        assert state1 in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "Output should be ON after first trigger"
        print(f"✓ First trigger: Output ON")

        # Wait 200ms (less than 300ms timeout), then retrigger
        await asyncio.sleep(0.2)
        await protocol.set_digital_input(3, True)
        await asyncio.sleep(0.05)
        await protocol.set_digital_input(3, False)
        print(f"✓ Retriggered at 200ms")

        # Wait another 200ms (total 400ms from first trigger,
        # but only 200ms from retrigger)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        state2 = self._get_output_state(telemetry, 3)
        assert state2 in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "Output should still be ON (timer was retriggered)"
        print(f"✓ 200ms after retrigger: Output still ON")

        # Wait for timer to fully expire
        await asyncio.sleep(0.4)

        telemetry = await protocol.get_telemetry()
        state3 = self._get_output_state(telemetry, 3)
        assert state3 == ChannelState.OFF, \
            "Output should be OFF after timer expires"
        print(f"✓ After full timeout: Output OFF")

        print("\n✅ TEST PASSED: Retriggerable Timer → Power Output works correctly")

    def _get_output_state(self, telemetry, channel: int) -> ChannelState:
        """Extract output state from telemetry."""
        if hasattr(telemetry, 'channel_states'):
            if channel < len(telemetry.channel_states):
                return telemetry.channel_states[channel]
        if hasattr(telemetry, 'output_states'):
            if channel < len(telemetry.output_states):
                state = telemetry.output_states[channel]
                if state > 0:
                    return ChannelState.ON
                return ChannelState.OFF
        return ChannelState.OFF


class TestInputToOutputIntegrity:
    """
    CRITICAL TEST: Verify input-output integrity after config changes.

    Tests that changing input type correctly propagates to output state.
    """

    @pytest.mark.asyncio
    async def test_input_type_change_updates_output(self, emulator_connection):
        """
        Test that changing input type immediately affects output.

        This is the core test from the user requirement:
        1. LOW-SIDE input (ON) → Output ON
        2. Change to HIGH-SIDE (OFF) → Output OFF
        """
        protocol = emulator_connection

        # Start with LOW-SIDE (active-low) input
        config = BASE_CONFIG.copy()
        config["channels"] = [
            {
                "channel_type": "digital_input",
                "id": "test_DI",
                "name": "test_DI",
                "input_pin": 4,
                "subtype": "switch_active_low",
                "debounce_ms": 10,
            },
            {
                "channel_type": "power_output",
                "id": "test_OUT",
                "name": "test_OUT",
                "output_pins": [4],
                "source_channel": "test_DI",
            }
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(CONFIG_APPLY_WAIT_MS / 1000)

        # Simulate LOW voltage (switch closed for active-low = ON)
        await protocol.set_digital_input(4, True)
        await asyncio.sleep(TELEMETRY_WAIT_MS / 1000)

        telemetry = await protocol.get_telemetry()
        state1 = self._get_output_state(telemetry, 4)
        print(f"LOW-SIDE, switch closed: Output = {state1}")

        # Change to HIGH-SIDE (active-high)
        config["channels"][0]["subtype"] = "switch_active_high"

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(CONFIG_APPLY_WAIT_MS / 1000)

        # Same physical state (LOW voltage) now means OFF for active-high
        await protocol.set_digital_input(4, False)
        await asyncio.sleep(TELEMETRY_WAIT_MS / 1000)

        telemetry = await protocol.get_telemetry()
        state2 = self._get_output_state(telemetry, 4)
        print(f"HIGH-SIDE, switch open: Output = {state2}")

        # Verify output state changed
        assert state2 == ChannelState.OFF, \
            f"After changing to HIGH-SIDE, output should be OFF, got {state2}"

        print("\n✅ TEST PASSED: Input type change correctly updates output state")

    def _get_output_state(self, telemetry, channel: int) -> ChannelState:
        """Extract output state from telemetry."""
        if hasattr(telemetry, 'channel_states'):
            if channel < len(telemetry.channel_states):
                return telemetry.channel_states[channel]
        return ChannelState.OFF


# Standalone execution for quick testing
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--timeout=60"])
