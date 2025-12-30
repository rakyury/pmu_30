"""
Integration Tests: ESP32/WiFi/Bluetooth Configuration & Load Shedding

Tests configuration flow for:
- Load shedding priority on power outputs
- WiFi configuration structure
- Bluetooth configuration structure

These tests verify the configuration pipeline from Configurator to firmware,
even when actual ESP32 hardware is not present.
"""

import pytest
import asyncio
import json

from .helpers import (
    BASE_CONFIG,
    make_output_config,
    make_digital_input_config,
    ChannelState,
)


class TestLoadSheddingPriority:
    """Test load shedding priority configuration on power outputs."""

    async def test_output_with_default_priority(self, protocol_handler):
        """
        Test: Output without shed_priority uses default value.

        Scenario:
        1. Create output without shed_priority
        2. Verify config is accepted (default priority = 5)
        """
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_test"),
            make_output_config(1, "o_test", "di_test"),
        ]

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success, f"Config send failed: {response.error}"

        await asyncio.sleep(0.3)
        telemetry = await protocol_handler.get_telemetry()
        assert telemetry is not None, "Should receive telemetry after config"

    async def test_output_with_critical_priority(self, protocol_handler):
        """
        Test: Output with shed_priority=0 (critical, never shed).

        Scenario:
        1. Create output with shed_priority=0
        2. Verify config is accepted
        """
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_ignition"),
            {
                "channel_id": 101,
                "channel_type": "power_output",
                "channel_name": "o_fuel_pump",
                "output_pins": [0],
                "source_channel": "di_ignition",
                "current_limit_a": 15.0,
                "shed_priority": 0,  # Critical - never shed
            },
        ]

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success, f"Config with critical priority failed: {response.error}"

    async def test_output_with_low_priority(self, protocol_handler):
        """
        Test: Output with shed_priority=10 (lowest priority, shed first).

        Scenario:
        1. Create output with shed_priority=10
        2. Verify config is accepted
        """
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_switch"),
            {
                "channel_id": 101,
                "channel_type": "power_output",
                "channel_name": "o_heated_seat",
                "output_pins": [0],
                "source_channel": "di_switch",
                "current_limit_a": 10.0,
                "shed_priority": 10,  # Lowest priority - shed first
            },
        ]

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success, f"Config with low priority failed: {response.error}"

    async def test_multiple_outputs_with_different_priorities(self, protocol_handler):
        """
        Test: Multiple outputs with various shed_priority levels.

        Scenario:
        1. Create outputs with priorities 0, 2, 5, 8, 10
        2. Verify config is accepted
        3. This establishes the shedding order in firmware
        """
        config = BASE_CONFIG.copy()
        config["channels"] = [
            # Digital inputs
            make_digital_input_config(1, "di_ignition"),
            make_digital_input_config(2, "di_switch_1"),
            make_digital_input_config(3, "di_switch_2"),
            make_digital_input_config(4, "di_switch_3"),
            make_digital_input_config(5, "di_switch_4"),

            # Outputs with different priorities
            {
                "channel_id": 101,
                "channel_type": "power_output",
                "channel_name": "o_ecu",
                "output_pins": [0],
                "source_channel": "di_ignition",
                "current_limit_a": 5.0,
                "shed_priority": 0,  # Critical - never shed
            },
            {
                "channel_id": 102,
                "channel_type": "power_output",
                "channel_name": "o_headlights",
                "output_pins": [1],
                "source_channel": "di_switch_1",
                "current_limit_a": 15.0,
                "shed_priority": 2,  # Important - shed last
            },
            {
                "channel_id": 103,
                "channel_type": "power_output",
                "channel_name": "o_interior_light",
                "output_pins": [2],
                "source_channel": "di_switch_2",
                "current_limit_a": 2.0,
                "shed_priority": 5,  # Normal
            },
            {
                "channel_id": 104,
                "channel_type": "power_output",
                "channel_name": "o_radio",
                "output_pins": [3],
                "source_channel": "di_switch_3",
                "current_limit_a": 3.0,
                "shed_priority": 8,  # Low priority
            },
            {
                "channel_id": 105,
                "channel_type": "power_output",
                "channel_name": "o_heated_seat",
                "output_pins": [4],
                "source_channel": "di_switch_4",
                "current_limit_a": 10.0,
                "shed_priority": 10,  # Lowest - shed first
            },
        ]

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success, f"Config with multiple priorities failed: {response.error}"

        await asyncio.sleep(0.3)
        telemetry = await protocol_handler.get_telemetry()
        assert telemetry is not None, "Should receive telemetry"


class TestWiFiConfiguration:
    """Test WiFi configuration structure via JSON config."""

    async def test_wifi_ap_mode_config(self, protocol_handler):
        """
        Test: WiFi Access Point configuration.

        Scenario:
        1. Send config with WiFi AP settings
        2. Verify config is accepted (structure validation)
        """
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_test"),
            make_output_config(1, "o_test", "di_test"),
        ]
        config["wifi"] = {
            "enabled": True,
            "mode": "ap",
            "ap": {
                "ssid": "PMU30_TestAP",
                "password": "testpass123",
                "channel": 6,
                "max_clients": 4,
                "hidden": False,
            }
        }

        response = await protocol_handler.send_config(json.dumps(config))
        # Config should be accepted - WiFi section is optional and ignored if
        # no ESP32 hardware, but structure should be valid
        assert response.success, f"WiFi AP config failed: {response.error}"

    async def test_wifi_sta_mode_config(self, protocol_handler):
        """
        Test: WiFi Station mode configuration.

        Scenario:
        1. Send config with WiFi STA settings
        2. Verify config is accepted
        """
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_test"),
            make_output_config(1, "o_test", "di_test"),
        ]
        config["wifi"] = {
            "enabled": True,
            "mode": "sta",
            "sta": {
                "ssid": "MyHomeNetwork",
                "password": "homepass",
                "auto_reconnect": True,
            }
        }

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success, f"WiFi STA config failed: {response.error}"

    async def test_wifi_ap_sta_mode_config(self, protocol_handler):
        """
        Test: WiFi AP+STA dual mode configuration.

        Scenario:
        1. Send config with both AP and STA settings
        2. Verify config is accepted
        """
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_test"),
            make_output_config(1, "o_test", "di_test"),
        ]
        config["wifi"] = {
            "enabled": True,
            "mode": "ap_sta",
            "ap": {
                "ssid": "PMU30_AP",
                "password": "appass",
                "channel": 1,
            },
            "sta": {
                "ssid": "HomeNetwork",
                "password": "homepass",
            }
        }

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success, f"WiFi AP+STA config failed: {response.error}"

    async def test_wifi_web_server_config(self, protocol_handler):
        """
        Test: WiFi with web server configuration.

        Scenario:
        1. Send config with web server settings
        2. Verify config is accepted
        """
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_test"),
            make_output_config(1, "o_test", "di_test"),
        ]
        config["wifi"] = {
            "enabled": True,
            "mode": "ap",
            "ap": {
                "ssid": "PMU30_Web",
                "password": "webpass",
            },
            "web_server": {
                "enabled": True,
                "http_port": 80,
                "ws_port": 81,
            }
        }

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success, f"WiFi web server config failed: {response.error}"


class TestBluetoothConfiguration:
    """Test Bluetooth configuration structure via JSON config."""

    async def test_bluetooth_ble_config(self, protocol_handler):
        """
        Test: Bluetooth Low Energy configuration.

        Scenario:
        1. Send config with BLE settings
        2. Verify config is accepted
        """
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_test"),
            make_output_config(1, "o_test", "di_test"),
        ]
        config["bluetooth"] = {
            "enabled": True,
            "mode": "ble",
            "ble": {
                "device_name": "PMU30-TEST",
                "advertising_enabled": True,
                "advertising_interval_ms": 100,
                "tx_power": 0,
            }
        }

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success, f"BLE config failed: {response.error}"

    async def test_bluetooth_disabled_config(self, protocol_handler):
        """
        Test: Bluetooth disabled configuration.

        Scenario:
        1. Send config with Bluetooth disabled
        2. Verify config is accepted
        """
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_test"),
            make_output_config(1, "o_test", "di_test"),
        ]
        config["bluetooth"] = {
            "enabled": False,
        }

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success, f"Bluetooth disabled config failed: {response.error}"

    async def test_bluetooth_pairing_config(self, protocol_handler):
        """
        Test: Bluetooth with pairing configuration.

        Scenario:
        1. Send config with PIN/pairing settings
        2. Verify config is accepted
        """
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_test"),
            make_output_config(1, "o_test", "di_test"),
        ]
        config["bluetooth"] = {
            "enabled": True,
            "mode": "ble",
            "ble": {
                "device_name": "PMU30-Secure",
                "advertising_enabled": True,
                "require_bonding": True,
                "pin_code": "123456",
            }
        }

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success, f"Bluetooth pairing config failed: {response.error}"


class TestCombinedConnectivityConfig:
    """Test combined WiFi + Bluetooth + Load Shedding configuration."""

    async def test_full_connectivity_config(self, protocol_handler):
        """
        Test: Complete connectivity configuration with all features.

        Scenario:
        1. Send comprehensive config with:
           - Multiple outputs with shed_priority
           - WiFi AP mode
           - Bluetooth BLE
        2. Verify config is accepted
        """
        config = BASE_CONFIG.copy()
        config["channels"] = [
            # Digital inputs
            make_digital_input_config(1, "di_ignition"),
            make_digital_input_config(2, "di_lights"),
            make_digital_input_config(3, "di_aux"),

            # Outputs with different priorities
            {
                "channel_id": 101,
                "channel_type": "power_output",
                "channel_name": "o_ecu",
                "output_pins": [0],
                "source_channel": "di_ignition",
                "current_limit_a": 5.0,
                "shed_priority": 0,  # Critical
            },
            {
                "channel_id": 102,
                "channel_type": "power_output",
                "channel_name": "o_lights",
                "output_pins": [1],
                "source_channel": "di_lights",
                "current_limit_a": 15.0,
                "shed_priority": 3,  # Important
            },
            {
                "channel_id": 103,
                "channel_type": "power_output",
                "channel_name": "o_aux",
                "output_pins": [2],
                "source_channel": "di_aux",
                "current_limit_a": 8.0,
                "shed_priority": 7,  # Low priority
            },
        ]

        # WiFi configuration
        config["wifi"] = {
            "enabled": True,
            "mode": "ap",
            "ap": {
                "ssid": "PMU30_RaceCar",
                "password": "raceteam2025",
                "channel": 6,
                "max_clients": 3,
            },
            "web_server": {
                "enabled": True,
                "http_port": 80,
            }
        }

        # Bluetooth configuration
        config["bluetooth"] = {
            "enabled": True,
            "mode": "ble",
            "ble": {
                "device_name": "PMU30-Race",
                "advertising_enabled": True,
            }
        }

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success, f"Full connectivity config failed: {response.error}"

        await asyncio.sleep(0.3)
        telemetry = await protocol_handler.get_telemetry()
        assert telemetry is not None, "Should receive telemetry after config"

    async def test_connectivity_with_telemetry(self, protocol_handler):
        """
        Test: Verify telemetry works with connectivity features enabled.

        Scenario:
        1. Send config with WiFi/BT enabled
        2. Activate inputs and verify output states in telemetry
        """
        config = BASE_CONFIG.copy()
        config["channels"] = [
            make_digital_input_config(1, "di_test"),
            {
                "channel_id": 101,
                "channel_type": "power_output",
                "channel_name": "o_test",
                "output_pins": [0],
                "source_channel": "di_test",
                "current_limit_a": 10.0,
                "shed_priority": 5,
            },
        ]
        config["wifi"] = {"enabled": True, "mode": "ap", "ap": {"ssid": "PMU", "password": "pass"}}
        config["bluetooth"] = {"enabled": True, "mode": "ble", "ble": {"device_name": "PMU"}}

        response = await protocol_handler.send_config(json.dumps(config))
        assert response.success, f"Config failed: {response.error}"

        await asyncio.sleep(0.3)

        # Set input HIGH
        await protocol_handler.set_digital_input(0, True)
        await asyncio.sleep(0.2)

        telemetry = await protocol_handler.get_telemetry()
        assert telemetry is not None, "No telemetry"

        # Output should be ON
        assert telemetry.channel_states[0] in [ChannelState.ON, ChannelState.PWM_ACTIVE], \
            f"Expected output ON, got {telemetry.channel_states[0]}"

        # Set input LOW
        await protocol_handler.set_digital_input(0, False)
        await asyncio.sleep(0.2)

        telemetry = await protocol_handler.get_telemetry()
        assert telemetry.channel_states[0] == ChannelState.OFF, \
            f"Expected output OFF, got {telemetry.channel_states[0]}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
