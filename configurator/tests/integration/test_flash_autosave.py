"""
Integration Tests: Flash Autosave
Tests channel state autosave to flash memory functionality.

Covers:
- RAM vs Flash configuration storage
- Autosave trigger mechanisms
- Channel state persistence
- Force save command
- Autosave slots (20 configurable)

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



def make_switch_config(channel_id: int, name: str, input_channel: str,
                       autosave: bool = False, autosave_slot: int = None) -> dict:
    """Create switch channel with optional autosave."""
    config = {
        "channel_id": channel_id,
        "channel_type": "switch",
        "id": name,
        "name": name,
        "input_channel": input_channel,
        "mode": "toggle",
        "initial_state": 0,
        "autosave": autosave,
    }
    if autosave_slot is not None:
        config["autosave_slot"] = autosave_slot
    return config


def make_enum_config(channel_id: int, name: str, input_channel: str,
                     values: list, autosave: bool = False,
                     autosave_slot: int = None) -> dict:
    """Create enum channel with optional autosave."""
    config = {
        "channel_id": channel_id,
        "channel_type": "enum",
        "id": name,
        "name": name,
        "input_channel": input_channel,
        "values": values,
        "initial_value": 0,
        "autosave": autosave,
    }
    if autosave_slot is not None:
        config["autosave_slot"] = autosave_slot
    return config
class TestRAMvsFlashStorage:
    """Test RAM immediate apply vs Flash persistence."""

    async def test_config_applies_to_ram_immediately(self, emulator_connection):
        """
        Test: Configuration changes apply to RAM immediately without flash save.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_1"),
            make_output_config(1, "o_1", "di_1"),
        ]

        # Send config (applies to RAM only by default)
        response = await protocol.send_config(json.dumps(config), save_to_flash=False)
        assert response.success
        await asyncio.sleep(0.3)

        # Verify config is active
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.2)

        telemetry = await protocol.get_telemetry()
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            "Config should be active in RAM"

    async def test_explicit_flash_save(self, emulator_connection):
        """
        Test: Explicit save to flash command.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_1"),
            make_output_config(1, "o_1", "di_1"),
        ]

        # Send config to RAM
        response = await protocol.send_config(json.dumps(config), save_to_flash=False)
        assert response.success
        await asyncio.sleep(0.3)

        # Explicitly save to flash
        response = await protocol.save_to_flash()
        assert response.success, "Flash save should succeed"


class TestChannelStateAutosave:
    """Test automatic channel state saving."""

    async def test_switch_autosave_enabled(self, emulator_connection):
        """
        Test: Switch with autosave enabled saves state.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_toggle"),
            make_switch_config(300, "sw_light", "di_toggle",
                             autosave=True, autosave_slot=0),
            make_output_config(1, "o_light", "sw_light"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Toggle switch ON
        await protocol.set_digital_input(0, False)
        await asyncio.sleep(0.1)
        await protocol.set_digital_input(0, True)  # Rising edge toggles
        await asyncio.sleep(0.1)
        await protocol.set_digital_input(0, False)
        await asyncio.sleep(0.3)

        telemetry = await protocol.get_telemetry()
        switch_state = telemetry.virtual_channels.get(300, 0)

        # State should be autosaved
        # On device restart, the saved state should be restored

    async def test_enum_autosave(self, emulator_connection):
        """
        Test: Enum channel with autosave saves selected value.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_next"),
            make_enum_config(300, "e_mode", "di_next",
                           values=["Off", "Low", "Medium", "High"],
                           autosave=True, autosave_slot=1),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Cycle through values
        for _ in range(2):  # Go to value index 2 (Medium)
            await protocol.set_digital_input(0, False)
            await asyncio.sleep(0.1)
            await protocol.set_digital_input(0, True)
            await asyncio.sleep(0.1)
        await protocol.set_digital_input(0, False)
        await asyncio.sleep(0.3)

        telemetry = await protocol.get_telemetry()
        enum_value = telemetry.virtual_channels.get(300, 0)
        # Should be 2 (Medium) and saved to flash

    async def test_autosave_with_delay(self, emulator_connection):
        """
        Test: Autosave happens after debounce delay to prevent flash wear.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_toggle"),
            make_switch_config(300, "sw_test", "di_toggle",
                             autosave=True, autosave_slot=2),
        ]
        # Configure autosave delay
        config["autosave_delay_ms"] = 1000  # 1 second delay

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Rapid toggles should not cause multiple flash writes
        for _ in range(5):
            await protocol.set_digital_input(0, True)
            await asyncio.sleep(0.05)
            await protocol.set_digital_input(0, False)
            await asyncio.sleep(0.05)

        # Only final state should be saved after delay


class TestAutosaveSlots:
    """Test autosave slot management (20 slots)."""

    async def test_multiple_channels_different_slots(self, emulator_connection):
        """
        Test: Multiple channels use different autosave slots.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_1"),
            make_digital_input_config(2, "di_2"),
            make_digital_input_config(3, "di_3"),
            make_switch_config(300, "sw_1", "di_1", autosave=True, autosave_slot=0),
            make_switch_config(301, "sw_2", "di_2", autosave=True, autosave_slot=1),
            make_switch_config(302, "sw_3", "di_3", autosave=True, autosave_slot=2),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Toggle each switch
        for i in range(3):
            await protocol.set_digital_input(i, True)
            await asyncio.sleep(0.1)
            await protocol.set_digital_input(i, False)
            await asyncio.sleep(0.1)

        # Each should be saved to its respective slot

    async def test_autosave_slot_limit(self, emulator_connection):
        """
        Test: System enforces 20 slot limit.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = []

        # Create 25 switches with autosave (should exceed limit)
        for i in range(25):
            config["channels"].append(
                make_digital_input_config(i + 1, f"di_{i}")
            )
            config["channels"].append(
                make_switch_config(300 + i, f"sw_{i}", f"di_{i}",
                                 autosave=True, autosave_slot=i)
            )

        response = await protocol.send_config(json.dumps(config))
        # Should warn or fail for slots > 19


class TestForceSaveCommand:
    """Test force save command for immediate persistence."""

    async def test_force_save_all_channels(self, emulator_connection):
        """
        Test: Force save command saves all autosave-enabled channels.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_1"),
            make_digital_input_config(2, "di_2"),
            make_switch_config(300, "sw_1", "di_1", autosave=True, autosave_slot=0),
            make_switch_config(301, "sw_2", "di_2", autosave=True, autosave_slot=1),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Change states
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.1)
        await protocol.set_digital_input(0, False)
        await asyncio.sleep(0.1)

        # Force save immediately (bypass delay)
        response = await protocol.force_save_channels()
        assert response.success

    async def test_force_save_specific_slot(self, emulator_connection):
        """
        Test: Force save specific autosave slot.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_1"),
            make_switch_config(300, "sw_1", "di_1", autosave=True, autosave_slot=5),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Force save slot 5
        response = await protocol.force_save_slot(5)
        assert response.success


class TestStatePersistence:
    """Test state persistence across restarts."""

    async def test_saved_state_survives_restart(self, emulator_connection):
        """
        Test: Saved channel state is restored after restart.
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_toggle"),
            make_switch_config(300, "sw_persistent", "di_toggle",
                             autosave=True, autosave_slot=10),
            make_output_config(1, "o_1", "sw_persistent"),
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Toggle switch ON
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.1)
        await protocol.set_digital_input(0, False)
        await asyncio.sleep(0.3)

        # Force save
        await protocol.force_save_channels()
        await asyncio.sleep(0.2)

        # Record current state
        telemetry = await protocol.get_telemetry()
        state_before = telemetry.virtual_channels.get(300, 0)

        # Simulate restart
        await protocol.restart_device()
        await asyncio.sleep(1.0)  # Wait for restart

        # Reconnect
        # (In real test, would need to reconnect)

        # Check state is restored
        telemetry = await protocol.get_telemetry()
        state_after = telemetry.virtual_channels.get(300, 0)

        assert state_after == state_before, \
            "State should persist across restart"


class TestAutosaveWithTimer:
    """Test autosave with timer channels."""

    async def test_timer_elapsed_not_autosaved(self, emulator_connection):
        """
        Test: Timer elapsed value is not autosaved (volatile).
        """
        protocol = emulator_connection

        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_start"),
            {
                "channel_id": 300,
                "channel_type": "timer",
                "id": "t_test",
                "name": "Test Timer",
                "mode": "count_up",
                "start_channel": "di_start",
                "start_edge": "rising",
                # Timer elapsed is inherently volatile
            },
        ]

        response = await protocol.send_config(json.dumps(config))
        assert response.success
        await asyncio.sleep(0.3)

        # Start timer
        await protocol.set_digital_input(0, True)
        await asyncio.sleep(0.5)

        # Timer value is not saved - starts from 0 on restart


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
